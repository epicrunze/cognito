"""
Revision tracking service for AI-initiated task mutations.

Records before/after snapshots and provides undo capability.
"""

import json
import logging
import sqlite3

from app.services.vikunja import VikunjaError, vikunja

logger = logging.getLogger(__name__)


class RevisionService:
    """Records and undoes AI-initiated task mutations."""

    @staticmethod
    def record(
        conn: sqlite3.Connection,
        task_id: int,
        action_type: str,
        source: str,
        before_state: dict | None = None,
        after_state: dict | None = None,
        changes: dict | None = None,
        conversation_id: str | None = None,
        proposal_id: str | None = None,
    ) -> int:
        """Record a revision and return its ID."""
        cursor = conn.execute(
            """INSERT INTO task_revisions
               (task_id, action_type, source, before_state, after_state, changes,
                conversation_id, proposal_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                task_id,
                action_type,
                source,
                json.dumps(before_state) if before_state else None,
                json.dumps(after_state) if after_state else None,
                json.dumps(changes) if changes else None,
                conversation_id,
                proposal_id,
            ],
        )
        return cursor.lastrowid  # type: ignore[return-value]

    @staticmethod
    async def undo(conn: sqlite3.Connection, revision_id: int, force: bool = False) -> dict:
        """Undo a revision. Returns result dict."""
        row = conn.execute(
            "SELECT id, task_id, action_type, source, before_state, after_state, changes, undone "
            "FROM task_revisions WHERE id = ?",
            [revision_id],
        ).fetchone()

        if not row:
            return {"error": "Revision not found", "status": 404}

        _, task_id, action_type, source, before_json, after_json, changes_json, undone = row

        if undone:
            return {"already_undone": True, "revision_id": revision_id}

        before_state = json.loads(before_json) if before_json else None
        after_state = json.loads(after_json) if after_json else None
        changes = json.loads(changes_json) if changes_json else None

        # Conflict detection (skip for create — we're deleting, and delete — task is already gone)
        if not force and action_type not in ("create", "delete") and after_state:
            try:
                current = await vikunja.get_task(task_id)
                conflict_fields = _check_conflict(current, after_state)
                if conflict_fields:
                    return {
                        "conflict": True,
                        "conflict_fields": conflict_fields,
                        "current_state": current,
                        "expected_state": after_state,
                        "revision_id": revision_id,
                    }
            except VikunjaError:
                return {"error": "Task no longer exists", "revision_id": revision_id}

        # Execute undo
        try:
            if action_type == "create":
                await vikunja.delete_task(task_id)
            elif action_type in ("update", "complete", "move"):
                if before_state:
                    restore_fields = {}
                    for key in ("title", "description", "priority", "due_date", "done", "project_id"):
                        if key in before_state:
                            restore_fields[key] = before_state[key]
                    if restore_fields:
                        await vikunja.update_task(task_id, restore_fields)
            elif action_type == "delete":
                if before_state:
                    project_id = before_state.get("project_id")
                    if project_id:
                        new_task = await vikunja.create_task(
                            project_id=project_id,
                            title=before_state.get("title", "Restored task"),
                            description=before_state.get("description"),
                            priority=before_state.get("priority", 3),
                            due_date=before_state.get("due_date"),
                        )
                        # Update revision with new task ID
                        conn.execute(
                            "UPDATE task_revisions SET task_id = ? WHERE id = ?",
                            [new_task["id"], revision_id],
                        )
            elif action_type == "auto_tag":
                if changes and changes.get("labels_added"):
                    for label_id in changes["labels_added"]:
                        try:
                            await vikunja.remove_label_from_task(task_id, label_id)
                        except VikunjaError:
                            logger.warning("Failed to remove label %d from task %d", label_id, task_id)
        except VikunjaError as e:
            return {"error": str(e), "revision_id": revision_id}

        # Mark as undone
        conn.execute(
            "UPDATE task_revisions SET undone = 1, undone_at = strftime('%Y-%m-%dT%H:%M:%S', 'now') WHERE id = ?",
            [revision_id],
        )

        return {"success": True, "revision_id": revision_id, "action_type": action_type}

    @staticmethod
    async def redo(conn: sqlite3.Connection, revision_id: int) -> dict:
        """Re-apply a previously undone revision."""
        row = conn.execute(
            "SELECT id, task_id, action_type, source, before_state, after_state, changes, undone "
            "FROM task_revisions WHERE id = ?",
            [revision_id],
        ).fetchone()

        if not row:
            return {"error": "Revision not found", "status": 404}

        _, task_id, action_type, source, before_json, after_json, changes_json, undone = row

        if not undone:
            return {"error": "Revision is not undone", "revision_id": revision_id}

        after_state = json.loads(after_json) if after_json else None
        changes = json.loads(changes_json) if changes_json else None

        try:
            if action_type == "create":
                if after_state:
                    project_id = after_state.get("project_id")
                    if project_id:
                        new_task = await vikunja.create_task(
                            project_id=project_id,
                            title=after_state.get("title", "Re-created task"),
                            description=after_state.get("description"),
                            priority=after_state.get("priority", 3),
                            due_date=after_state.get("due_date"),
                        )
                        conn.execute(
                            "UPDATE task_revisions SET task_id = ? WHERE id = ?",
                            [new_task["id"], revision_id],
                        )
            elif action_type in ("update", "complete", "move"):
                if after_state:
                    restore_fields = {}
                    for key in ("title", "description", "priority", "due_date", "done", "project_id"):
                        if key in after_state:
                            restore_fields[key] = after_state[key]
                    if restore_fields:
                        await vikunja.update_task(task_id, restore_fields)
            elif action_type == "delete":
                await vikunja.delete_task(task_id)
            elif action_type == "auto_tag":
                if changes and changes.get("labels_added"):
                    for label_id in changes["labels_added"]:
                        try:
                            await vikunja.add_label_to_task(task_id, label_id)
                        except VikunjaError:
                            logger.warning("Failed to re-add label %d to task %d", label_id, task_id)
        except VikunjaError as e:
            return {"error": str(e), "revision_id": revision_id}

        conn.execute(
            "UPDATE task_revisions SET undone = 0, undone_at = NULL WHERE id = ?",
            [revision_id],
        )

        return {"success": True, "revision_id": revision_id, "action_type": action_type}

    @staticmethod
    def get_recent(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
        """Get recent revisions, newest first."""
        rows = conn.execute(
            "SELECT id, task_id, action_type, source, before_state, after_state, changes, "
            "conversation_id, proposal_id, undone, undone_at, created_at "
            "FROM task_revisions ORDER BY id DESC LIMIT ?",
            [limit],
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, revision_id: int) -> dict | None:
        """Get a single revision."""
        row = conn.execute(
            "SELECT id, task_id, action_type, source, before_state, after_state, changes, "
            "conversation_id, proposal_id, undone, undone_at, created_at "
            "FROM task_revisions WHERE id = ?",
            [revision_id],
        ).fetchone()
        return _row_to_dict(row) if row else None


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "task_id": row[1],
        "action_type": row[2],
        "source": row[3],
        "before_state": json.loads(row[4]) if row[4] else None,
        "after_state": json.loads(row[5]) if row[5] else None,
        "changes": json.loads(row[6]) if row[6] else None,
        "conversation_id": row[7],
        "proposal_id": row[8],
        "undone": bool(row[9]),
        "undone_at": row[10],
        "created_at": row[11],
    }


def _check_conflict(current: dict, expected: dict) -> list[str]:
    """Compare key fields between current task state and expected after_state."""
    conflict_fields = []
    for field in ("title", "description", "priority", "due_date", "done", "project_id"):
        current_val = current.get(field)
        expected_val = expected.get(field)
        if current_val != expected_val:
            conflict_fields.append(field)
    return conflict_fields

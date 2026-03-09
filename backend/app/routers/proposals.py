"""Proposals router — CRUD + approve/reject lifecycle."""

import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.proposal import TaskProposal, TaskProposalUpdate
from app.models.user import User
from app.routers.projects import _add_project_to_cache
from app.services.vikunja import VikunjaError, vikunja
from app.utils.timestamp import utc_now

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


class ApproveAllRequest(BaseModel):
    ids: Optional[list[str]] = None


def _get_default_project_id() -> int | None:
    """Get default_project_id from agent_config."""
    with get_db() as conn:
        row = conn.execute("SELECT default_project_id FROM agent_config WHERE id = 1").fetchone()
        return row[0] if row and row[0] else None


def _row_to_proposal(row) -> TaskProposal:
    """Convert a DuckDB row to a TaskProposal model."""
    labels_raw = row[9]
    if isinstance(labels_raw, str):
        try:
            labels = json.loads(labels_raw)
        except json.JSONDecodeError:
            labels = []
    elif isinstance(labels_raw, list):
        labels = labels_raw
    else:
        labels = []

    due = row[7]
    if isinstance(due, str):
        try:
            due = date.fromisoformat(due)
        except ValueError:
            due = None

    return TaskProposal(
        id=str(row[0]),
        source_id=str(row[1]),
        title=row[2],
        description=row[3],
        project_name=row[4],
        project_id=row[5],
        priority=row[6] or 3,
        due_date=due,
        estimated_minutes=row[8],
        labels=labels,
        source_type=row[10],
        source_text=row[11],
        confidential=bool(row[12]),
        status=row[13],
        vikunja_task_id=row[14],
        gcal_event_id=row[15],
        created_at=row[16],
        reviewed_at=row[17],
    )


PROPOSAL_COLUMNS = """
    id, source_id, title, description, project_name, project_id,
    priority, due_date, estimated_minutes, labels, source_type,
    source_text, confidential, status, vikunja_task_id, gcal_event_id,
    created_at, reviewed_at
"""


@router.get("")
async def list_proposals(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
):
    """List proposals, optionally filtered by status."""
    with get_db() as conn:
        if status_filter:
            rows = conn.execute(
                f"SELECT {PROPOSAL_COLUMNS} FROM task_proposals WHERE status = ? ORDER BY created_at DESC",
                [status_filter],
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {PROPOSAL_COLUMNS} FROM task_proposals ORDER BY created_at DESC"
            ).fetchall()

    proposals = [_row_to_proposal(r) for r in rows]
    return {"proposals": [p.model_dump() for p in proposals], "count": len(proposals)}


@router.put("/{proposal_id}")
async def update_proposal(
    proposal_id: str,
    body: TaskProposalUpdate,
    current_user: User = Depends(get_current_user),
):
    """Edit a proposal before approving."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    set_clauses = []
    values = []
    for field, value in updates.items():
        set_clauses.append(f"{field} = ?")
        if field == "labels":
            values.append(json.dumps(value))
        elif field == "due_date" and value is not None:
            values.append(value.isoformat())
        else:
            values.append(value)

    values.append(proposal_id)

    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM task_proposals WHERE id = ?", [proposal_id]
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

        conn.execute(
            f"UPDATE task_proposals SET {', '.join(set_clauses)} WHERE id = ?",
            values,
        )
        updated = conn.execute(
            f"SELECT {PROPOSAL_COLUMNS} FROM task_proposals WHERE id = ?", [proposal_id]
        ).fetchone()

    return _row_to_proposal(updated).model_dump()


@router.post("/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
):
    """Approve a proposal — creates the task in Vikunja."""
    with get_db() as conn:
        row = conn.execute(
            f"SELECT {PROPOSAL_COLUMNS} FROM task_proposals WHERE id = ?", [proposal_id]
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

        proposal = _row_to_proposal(row)

        if proposal.status == "created":
            return {
                "success": True,
                "vikunja_task_id": proposal.vikunja_task_id,
                "message": "Already created in Vikunja",
            }
        if proposal.status == "rejected":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot approve a rejected proposal")

        new_project_created = False
        if not proposal.project_id:
            if proposal.project_name:
                # Create the suggested project in Vikunja
                try:
                    new_proj = await vikunja.create_project(proposal.project_name)
                    proposal.project_id = new_proj["id"]
                    new_project_created = True
                    _add_project_to_cache(new_proj)
                    conn.execute(
                        "UPDATE task_proposals SET project_id = ? WHERE id = ?",
                        [new_proj["id"], proposal_id],
                    )
                except VikunjaError as e:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to create project '{proposal.project_name}': {e}",
                    )
            else:
                default_pid = _get_default_project_id()
                if default_pid:
                    proposal.project_id = default_pid
                    conn.execute(
                        "UPDATE task_proposals SET project_id = ? WHERE id = ?",
                        [default_pid, proposal_id],
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Proposal has no project assigned and no default project configured.",
                    )

    # Create task in Vikunja
    try:
        task = await vikunja.create_task(
            project_id=proposal.project_id,
            title=proposal.title,
            description=proposal.description,
            priority=proposal.priority,
            due_date=proposal.due_date.isoformat() if proposal.due_date else None,
            labels=proposal.labels,
        )
        vikunja_task_id = task["id"]
        vikunja_url = f"{vikunja.base_url.replace('/api/v1', '')}/tasks/{vikunja_task_id}"
    except VikunjaError as e:
        # Keep status as "approved" (not "created") so user can retry
        with get_db() as conn:
            conn.execute(
                "UPDATE task_proposals SET status = 'approved', reviewed_at = ? WHERE id = ?",
                [utc_now(), proposal_id],
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Vikunja task creation failed: {e}. Proposal marked as approved — retry from proposal history.",
        )

    with get_db() as conn:
        conn.execute(
            """UPDATE task_proposals SET status = 'created', vikunja_task_id = ?, reviewed_at = ?
               WHERE id = ?""",
            [vikunja_task_id, utc_now(), proposal_id],
        )

    return {
        "success": True,
        "vikunja_task_id": vikunja_task_id,
        "vikunja_url": vikunja_url,
        "new_project_created": new_project_created,
    }


@router.post("/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
):
    """Reject a proposal."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM task_proposals WHERE id = ?", [proposal_id]
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

        conn.execute(
            "UPDATE task_proposals SET status = 'rejected', reviewed_at = ? WHERE id = ?",
            [utc_now(), proposal_id],
        )

    return {"success": True}


@router.post("/approve-all")
async def approve_all(
    body: ApproveAllRequest = ApproveAllRequest(),
    current_user: User = Depends(get_current_user),
):
    """Approve pending proposals. If ids provided, only approve those; otherwise all pending."""
    with get_db() as conn:
        if body.ids is not None:
            placeholders = ", ".join("?" for _ in body.ids)
            rows = conn.execute(
                f"SELECT {PROPOSAL_COLUMNS} FROM task_proposals WHERE status = 'pending' AND id IN ({placeholders}) ORDER BY created_at",
                body.ids,
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {PROPOSAL_COLUMNS} FROM task_proposals WHERE status = 'pending' ORDER BY created_at"
            ).fetchall()

    if not rows:
        return {"approved": 0, "errors": []}

    default_pid = _get_default_project_id()
    approved = 0
    errors = []
    created_projects: dict[str, int] = {}  # project_name -> project_id dedup
    new_projects: list[str] = []
    task_ids: list[int] = []

    for row in rows:
        proposal = _row_to_proposal(row)
        if not proposal.project_id:
            if proposal.project_name and proposal.project_name in created_projects:
                # Reuse already-created project from this batch
                proposal.project_id = created_projects[proposal.project_name]
                with get_db() as conn:
                    conn.execute(
                        "UPDATE task_proposals SET project_id = ? WHERE id = ?",
                        [proposal.project_id, proposal.id],
                    )
            elif proposal.project_name:
                # Create new project in Vikunja
                try:
                    new_proj = await vikunja.create_project(proposal.project_name)
                    proposal.project_id = new_proj["id"]
                    created_projects[proposal.project_name] = new_proj["id"]
                    new_projects.append(proposal.project_name)
                    _add_project_to_cache(new_proj)
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE task_proposals SET project_id = ? WHERE id = ?",
                            [new_proj["id"], proposal.id],
                        )
                except VikunjaError as e:
                    errors.append({"id": proposal.id, "title": proposal.title, "error": f"Failed to create project: {e}"})
                    continue
            elif default_pid:
                proposal.project_id = default_pid
                with get_db() as conn:
                    conn.execute(
                        "UPDATE task_proposals SET project_id = ? WHERE id = ?",
                        [default_pid, proposal.id],
                    )
            else:
                errors.append({"id": proposal.id, "title": proposal.title, "error": "No project assigned"})
                continue

        try:
            task = await vikunja.create_task(
                project_id=proposal.project_id,
                title=proposal.title,
                description=proposal.description,
                priority=proposal.priority,
                due_date=proposal.due_date.isoformat() if proposal.due_date else None,
                labels=proposal.labels,
            )
            vikunja_task_id = task["id"]
            with get_db() as conn:
                conn.execute(
                    """UPDATE task_proposals SET status = 'created', vikunja_task_id = ?, reviewed_at = ?
                       WHERE id = ?""",
                    [vikunja_task_id, utc_now(), proposal.id],
                )
            approved += 1
            task_ids.append(vikunja_task_id)
        except VikunjaError as e:
            errors.append({"id": proposal.id, "title": proposal.title, "error": str(e)})

    return {"approved": approved, "errors": errors, "new_projects": new_projects, "task_ids": task_ids}

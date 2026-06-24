"""Adapter projecting per-project notes (project_workspace) into OKF concepts."""

import re
import sqlite3

from app.services.knowledge.adapters.base import Concept, FieldCaps, SourceAdapter

_NOTES_ID_RE = re.compile(r"^projects/(\d+)/notes$")


class NotesAdapter(SourceAdapter):
    source_name = "notes"

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def owns(self, concept_id: str) -> bool:
        return bool(_NOTES_ID_RE.match(concept_id))

    def _to_concept(self, pid: int, notes: str, updated: str | None) -> Concept:
        return Concept(
            concept_id=f"projects/{pid}/notes",
            type="Project Notes",
            source="notes",
            title=f"Notes — project {pid}",
            description=None,
            resource=None,
            tags=[],
            timestamp=updated,
            frontmatter={"type": "Project Notes", "project_id": pid},
            body=notes,
        )

    async def list_concepts(self) -> list[Concept]:
        rows = self._conn.execute(
            "SELECT project_id, notes, notes_updated_at FROM project_workspace "
            "WHERE notes IS NOT NULL AND length(trim(notes)) > 0"
        ).fetchall()
        return [self._to_concept(r[0], r[1], r[2]) for r in rows]

    async def get_concept(self, concept_id: str) -> Concept | None:
        m = _NOTES_ID_RE.match(concept_id)
        if not m:
            return None
        pid = int(m.group(1))
        row = self._conn.execute(
            "SELECT notes, notes_updated_at FROM project_workspace WHERE project_id = ?",
            (pid,),
        ).fetchone()
        if not row or not (row[0] or "").strip():
            return None
        return self._to_concept(pid, row[0], row[1])

    def field_capabilities(self, concept: Concept) -> FieldCaps:
        return FieldCaps(
            writable={"body": "project_workspace.notes"},
            readonly=["project_id"],
        )

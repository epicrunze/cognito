"""Adapter over the knowledge_concepts table (native standalone concepts)."""

import json
import sqlite3

from app.services.knowledge.adapters.base import Concept, FieldCaps, SourceAdapter


class NativeConceptAdapter(SourceAdapter):
    source_name = "native"

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def owns(self, concept_id: str) -> bool:
        return concept_id.startswith("knowledge/")

    def _row_to_concept(self, row) -> Concept:
        (cid, ctype, title, desc, resource, tags, fm, body, updated) = row
        return Concept(
            concept_id=cid,
            type=ctype,
            source="native",
            title=title,
            description=desc,
            resource=resource,
            tags=json.loads(tags or "[]"),
            timestamp=updated,
            frontmatter=json.loads(fm or "{}"),
            body=body or "",
        )

    _COLS = ("concept_id, type, title, description, resource, tags, "
             "frontmatter, body, updated_at")

    async def list_concepts(self) -> list[Concept]:
        rows = self._conn.execute(
            f"SELECT {self._COLS} FROM knowledge_concepts"
        ).fetchall()
        return [self._row_to_concept(r) for r in rows]

    async def get_concept(self, concept_id: str) -> Concept | None:
        row = self._conn.execute(
            f"SELECT {self._COLS} FROM knowledge_concepts WHERE concept_id = ?",
            (concept_id,),
        ).fetchone()
        return self._row_to_concept(row) if row else None

    def field_capabilities(self, concept: Concept) -> FieldCaps:
        return FieldCaps(
            writable={
                "title": "knowledge_concepts.title",
                "description": "knowledge_concepts.description",
                "tags": "knowledge_concepts.tags",
                "body": "knowledge_concepts.body",
            },
            readonly=["concept_id", "created_at"],
        )

# backend/app/services/knowledge/materializer.py
"""Builds and refreshes the materialized OKF concept cache from source adapters."""

import json
import logging
import sqlite3
import time

from app.services.knowledge.adapters.base import Concept, SourceAdapter
from app.services.knowledge.adapters.native import NativeConceptAdapter
from app.services.knowledge.adapters.notes import NotesAdapter
from app.services.knowledge.adapters.vikunja_projects import VikunjaProjectAdapter
from app.services.knowledge.adapters.vikunja_tasks import VikunjaTaskAdapter
from app.services.knowledge.linkparse import extract_links

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 60


class KnowledgeMaterializer:
    def __init__(self, conn: sqlite3.Connection, adapters: list[SourceAdapter]):
        self._conn = conn
        self._adapters = adapters

    # ── helpers ──────────────────────────────────────────────────────────────
    def _now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S")

    def _adapter_for(self, concept_id: str) -> SourceAdapter | None:
        for a in self._adapters:
            try:
                if a.owns(concept_id):
                    return a
            except NotImplementedError:
                continue
        return None

    def _write_concept(self, c: Concept) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO concepts (concept_id, source, type, title, "
            "description, resource, tags, timestamp, frontmatter, body, materialized_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (c.concept_id, c.source, c.type, c.title, c.description, c.resource,
             json.dumps(c.tags), c.timestamp, json.dumps(c.frontmatter), c.body,
             self._now()),
        )
        self._conn.execute("DELETE FROM concepts_fts WHERE concept_id = ?", (c.concept_id,))
        self._conn.execute(
            "INSERT INTO concepts_fts (concept_id, title, description, tags, body) "
            "VALUES (?,?,?,?,?)",
            (c.concept_id, c.title or "", c.description or "", " ".join(c.tags), c.body or ""),
        )
        self._conn.execute("DELETE FROM concept_links WHERE src_id = ?", (c.concept_id,))
        for dst in extract_links(c.body or "", c.concept_id):
            self._conn.execute(
                "INSERT OR IGNORE INTO concept_links (src_id, dst_id) VALUES (?,?)",
                (c.concept_id, dst),
            )

    # ── public API ───────────────────────────────────────────────────────────
    async def rebuild(self) -> dict:
        """Full rebuild from all adapters. Failing sources are skipped, not fatal."""
        self._conn.execute("DELETE FROM concepts")
        self._conn.execute("DELETE FROM concepts_fts")
        self._conn.execute("DELETE FROM concept_links")
        count = 0
        failed: list[str] = []
        for adapter in self._adapters:
            try:
                concepts = await adapter.list_concepts()
            except Exception:
                logger.exception("adapter %s failed during rebuild", adapter.source_name)
                failed.append(adapter.source_name)
                continue
            for c in concepts:
                self._write_concept(c)
                count += 1
        self._conn.execute(
            "INSERT OR REPLACE INTO knowledge_meta (key, value) VALUES ('last_materialized', ?)",
            (str(time.time()),),
        )
        return {"concepts": count, "failed_sources": failed}

    async def refresh_concept(self, concept_id: str) -> bool:
        """Re-derive a single concept from its owning adapter. Returns True if found."""
        adapter = self._adapter_for(concept_id)
        if adapter is None:
            return False
        concept = await adapter.get_concept(concept_id)
        if concept is None:
            # concept deleted at source -> evict from cache
            self._conn.execute("DELETE FROM concepts WHERE concept_id = ?", (concept_id,))
            self._conn.execute("DELETE FROM concepts_fts WHERE concept_id = ?", (concept_id,))
            self._conn.execute("DELETE FROM concept_links WHERE src_id = ?", (concept_id,))
            return False
        self._write_concept(concept)
        return True


def build_materializer(conn: sqlite3.Connection) -> KnowledgeMaterializer:
    """Wire the standard adapter set. Vikunja adapters use the module singleton."""
    from app.services.vikunja import vikunja
    return KnowledgeMaterializer(conn, [
        VikunjaTaskAdapter(vikunja),
        VikunjaProjectAdapter(vikunja),
        NotesAdapter(conn),
        NativeConceptAdapter(conn),
    ])


async def ensure_fresh(conn: sqlite3.Connection, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
    """Rebuild the cache if it has never been built or the TTL has expired."""
    row = conn.execute(
        "SELECT value FROM knowledge_meta WHERE key='last_materialized'"
    ).fetchone()
    if row is not None:
        try:
            if time.time() - float(row[0]) < ttl_seconds:
                return
        except (TypeError, ValueError):
            pass
    await build_materializer(conn).rebuild()

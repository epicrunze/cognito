# backend/tests/test_knowledge_materializer.py
import json
import sqlite3

from unittest.mock import AsyncMock

from app.database import init_schema
from app.services.knowledge.adapters.native import NativeConceptAdapter
from app.services.knowledge.adapters.notes import NotesAdapter
from app.services.knowledge.materializer import KnowledgeMaterializer


def _db():
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(conn)
    return conn


def _seed_native(conn, cid, body, title="T"):
    conn.execute(
        "INSERT INTO knowledge_concepts (concept_id, type, title, body) VALUES (?,?,?,?)",
        (cid, "Note", title, body),
    )


async def test_rebuild_populates_cache_and_links():
    conn = _db()
    _seed_native(conn, "knowledge/a", "Links to [b](/knowledge/b.md).")
    _seed_native(conn, "knowledge/b", "Leaf note about widgets.")
    mat = KnowledgeMaterializer(conn, [NativeConceptAdapter(conn)])

    counts = await mat.rebuild()
    assert counts["concepts"] == 2

    rows = {r[0] for r in conn.execute("SELECT concept_id FROM concepts").fetchall()}
    assert rows == {"knowledge/a", "knowledge/b"}

    links = conn.execute("SELECT src_id, dst_id FROM concept_links").fetchall()
    assert ("knowledge/a", "knowledge/b") in links

    fts = conn.execute(
        "SELECT concept_id FROM concepts_fts WHERE concepts_fts MATCH 'widgets'"
    ).fetchall()
    assert fts == [("knowledge/b",)]

    meta = conn.execute(
        "SELECT value FROM knowledge_meta WHERE key='last_materialized'"
    ).fetchone()
    assert meta is not None


async def test_refresh_single_concept():
    conn = _db()
    _seed_native(conn, "knowledge/a", "Old body.")
    mat = KnowledgeMaterializer(conn, [NativeConceptAdapter(conn)])
    await mat.rebuild()

    conn.execute("UPDATE knowledge_concepts SET body='New shiny body.' WHERE concept_id='knowledge/a'")
    await mat.refresh_concept("knowledge/a")

    body = conn.execute("SELECT body FROM concepts WHERE concept_id='knowledge/a'").fetchone()[0]
    assert body == "New shiny body."
    fts = conn.execute(
        "SELECT concept_id FROM concepts_fts WHERE concepts_fts MATCH 'shiny'"
    ).fetchall()
    assert fts == [("knowledge/a",)]


async def test_rebuild_survives_failing_adapter():
    conn = _db()
    _seed_native(conn, "knowledge/a", "Good.")
    bad = AsyncMock()
    bad.list_concepts.side_effect = RuntimeError("vikunja down")
    bad.source_name = "vikunja"
    mat = KnowledgeMaterializer(conn, [NativeConceptAdapter(conn), bad])

    counts = await mat.rebuild()   # must not raise
    assert counts["concepts"] == 1
    assert "vikunja" in counts["failed_sources"]


async def test_refresh_concept_eviction():
    """refresh_concept returns False and clears all three cache tables when the
    source concept no longer exists in knowledge_concepts."""
    conn = _db()
    # Seed with a link so concept_links has a src row for "knowledge/evict"
    _seed_native(conn, "knowledge/evict", "Evict this. Links to [other](/knowledge/other.md).")
    _seed_native(conn, "knowledge/other", "Other leaf.")
    mat = KnowledgeMaterializer(conn, [NativeConceptAdapter(conn)])
    await mat.rebuild()

    # Confirm concept is in cache before eviction
    assert conn.execute(
        "SELECT 1 FROM concepts WHERE concept_id='knowledge/evict'"
    ).fetchone() is not None
    assert conn.execute(
        "SELECT 1 FROM concept_links WHERE src_id='knowledge/evict'"
    ).fetchone() is not None

    # Delete from the native source table — simulates removal at source
    conn.execute("DELETE FROM knowledge_concepts WHERE concept_id='knowledge/evict'")

    result = await mat.refresh_concept("knowledge/evict")

    assert result is False
    # Evicted from all three cache tables
    assert conn.execute(
        "SELECT 1 FROM concepts WHERE concept_id='knowledge/evict'"
    ).fetchone() is None
    assert conn.execute(
        "SELECT 1 FROM concepts_fts WHERE concept_id='knowledge/evict'"
    ).fetchone() is None
    assert conn.execute(
        "SELECT 1 FROM concept_links WHERE src_id='knowledge/evict'"
    ).fetchone() is None

# backend/tests/test_knowledge_search.py
import sqlite3

from app.database import init_schema
from app.services.knowledge.adapters.native import NativeConceptAdapter
from app.services.knowledge.materializer import KnowledgeMaterializer
from app.services.knowledge import search


def _db():
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(conn)
    return conn


async def _seed(conn):
    conn.execute(
        "INSERT INTO knowledge_concepts (concept_id, type, title, description, body) VALUES (?,?,?,?,?)",
        ("knowledge/a", "Note", "Alpha", "about widgets", "Alpha links [b](/knowledge/b.md). widgets here."),
    )
    conn.execute(
        "INSERT INTO knowledge_concepts (concept_id, type, title, description, body) VALUES (?,?,?,?,?)",
        ("knowledge/b", "Reference", "Beta", "ref doc", "Beta body, gadgets."),
    )
    await KnowledgeMaterializer(conn, [NativeConceptAdapter(conn)]).rebuild()
    return conn


async def test_search_matches_body_and_returns_snippet():
    conn = await _seed(_db())
    results = search.search_concepts(conn, "widgets")
    assert [r["concept_id"] for r in results] == ["knowledge/a"]
    assert "widgets" in results[0]["snippet"].lower()


async def test_search_type_filter():
    conn = await _seed(_db())
    results = search.search_concepts(conn, "body OR widgets OR gadgets", type="Reference")
    assert [r["concept_id"] for r in results] == ["knowledge/b"]


async def test_concept_detail_has_links_and_backlinks():
    conn = await _seed(_db())
    detail = search.concept_detail(conn, "knowledge/b")
    assert detail["title"] == "Beta"
    assert detail["backlinks"] == ["knowledge/a"]
    a = search.concept_detail(conn, "knowledge/a")
    assert a["links"] == ["knowledge/b"]
    assert search.concept_detail(conn, "knowledge/missing") is None


async def test_graph_full():
    conn = await _seed(_db())
    g = search.graph(conn)
    node_ids = {n["concept_id"] for n in g["nodes"]}
    assert node_ids == {"knowledge/a", "knowledge/b"}
    assert {"src": "knowledge/a", "dst": "knowledge/b"} in g["edges"]


async def test_index_groups_by_type():
    conn = await _seed(_db())
    md = search.synth_index(conn)
    assert "# Note" in md and "# Reference" in md
    assert "/knowledge/a.md" in md

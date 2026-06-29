"""Unit tests for KnowledgeRetriever (read primitive over the knowledge cache)."""

import sqlite3
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from app.database import init_schema
from app.services.knowledge.retriever import KnowledgeRetriever


def _db():
    c = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(c)
    return c


def _mock_db(conn):
    @contextmanager
    def _cm(database_path=None):
        yield conn
    return _cm


def _seed(conn, cid, title, body, ctype="Note", source="native", desc=""):
    conn.execute(
        "INSERT INTO concepts (concept_id, source, type, title, description, body) "
        "VALUES (?,?,?,?,?,?)",
        (cid, source, ctype, title, desc, body),
    )
    conn.execute(
        "INSERT INTO concepts_fts (concept_id, title, description, tags, body) "
        "VALUES (?,?,?,?,?)",
        (cid, title, desc, "", body),
    )


async def test_search_returns_bounded_summaries_and_calls_ensure_fresh():
    conn = _db()
    for i in range(8):
        _seed(conn, f"knowledge/n{i}", f"Note {i}", "alpha widget content")
    with patch("app.services.knowledge.retriever.get_db", _mock_db(conn)), \
         patch("app.services.knowledge.retriever.ensure_fresh", AsyncMock()) as ef:
        res = await KnowledgeRetriever().search("widget")
    assert len(res) <= 5
    assert ef.await_count == 1
    assert set(res[0].keys()) >= {"concept_id", "type", "source", "title", "snippet"}


async def test_search_caps_limit_even_when_caller_asks_more():
    conn = _db()
    for i in range(8):
        _seed(conn, f"knowledge/n{i}", f"Note {i}", "alpha widget content")
    with patch("app.services.knowledge.retriever.get_db", _mock_db(conn)), \
         patch("app.services.knowledge.retriever.ensure_fresh", AsyncMock()):
        res = await KnowledgeRetriever().search("widget", limit=100)
    assert len(res) <= 5


async def test_get_returns_detail_with_links_and_backlinks():
    conn = _db()
    _seed(conn, "knowledge/a", "Alpha", "body of a")
    _seed(conn, "knowledge/b", "Beta", "body of b")
    conn.execute("INSERT INTO concept_links (src_id, dst_id) VALUES ('knowledge/a','knowledge/b')")
    with patch("app.services.knowledge.retriever.get_db", _mock_db(conn)), \
         patch("app.services.knowledge.retriever.ensure_fresh", AsyncMock()):
        detail = await KnowledgeRetriever().get("knowledge/b")
    assert detail["title"] == "Beta"
    assert detail["backlinks"] == ["knowledge/a"]
    assert detail["links"] == []


async def test_get_truncates_long_body():
    conn = _db()
    _seed(conn, "knowledge/big", "Big", "x" * 5000)
    with patch("app.services.knowledge.retriever.get_db", _mock_db(conn)), \
         patch("app.services.knowledge.retriever.ensure_fresh", AsyncMock()):
        detail = await KnowledgeRetriever().get("knowledge/big")
    assert len(detail["body"]) < 5000
    assert detail["body"].endswith("[truncated]")


async def test_get_missing_returns_none():
    conn = _db()
    with patch("app.services.knowledge.retriever.get_db", _mock_db(conn)), \
         patch("app.services.knowledge.retriever.ensure_fresh", AsyncMock()):
        detail = await KnowledgeRetriever().get("knowledge/nope")
    assert detail is None

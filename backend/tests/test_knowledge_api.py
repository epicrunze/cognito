# backend/tests/test_knowledge_api.py
"""API tests for /api/knowledge via FastAPI TestClient."""

import sqlite3
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from app.models.user import User

_USER = User(email="test@example.com", name="Test User")


def _mock_db_cm(conn):
    @contextmanager
    def _cm(database_path=None):
        yield conn
    return _cm


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(c)
    c.execute(
        "INSERT INTO knowledge_concepts (concept_id, type, title, description, body) VALUES (?,?,?,?,?)",
        ("knowledge/a", "Note", "Alpha", "about widgets", "Alpha links [b](/knowledge/b.md). widgets."),
    )
    c.execute(
        "INSERT INTO knowledge_concepts (concept_id, type, title, body) VALUES (?,?,?,?)",
        ("knowledge/b", "Reference", "Beta", "Beta body gadgets."),
    )
    yield c
    c.close()


@pytest.fixture
def client(conn):
    # Neutralize the Vikunja-backed adapters so the cache holds only the seeded
    # native concepts. build_materializer constructs these classes; patching the
    # classes (imported at module level in materializer.py) makes them return [].
    app.dependency_overrides[get_current_user] = lambda: _USER
    with patch("app.routers.knowledge.get_db", _mock_db_cm(conn)), \
         patch("app.services.knowledge.materializer.VikunjaTaskAdapter") as T, \
         patch("app.services.knowledge.materializer.VikunjaProjectAdapter") as P:
        T.return_value.list_concepts = AsyncMock(return_value=[])
        T.return_value.owns.return_value = False
        P.return_value.list_concepts = AsyncMock(return_value=[])
        P.return_value.owns.return_value = False
        yield TestClient(app)
    app.dependency_overrides.clear()


def test_search_endpoint(client):
    r = client.get("/api/knowledge/search", params={"q": "widgets"})
    assert r.status_code == 200
    data = r.json()
    assert any(item["concept_id"] == "knowledge/a" for item in data)


def test_concept_detail_endpoint(client):
    r = client.get("/api/knowledge/concept/knowledge/b")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Beta"
    assert body["backlinks"] == ["knowledge/a"]


def test_concept_detail_404(client):
    r = client.get("/api/knowledge/concept/knowledge/missing")
    assert r.status_code == 404


def test_graph_endpoint(client):
    r = client.get("/api/knowledge/graph")
    assert r.status_code == 200
    g = r.json()
    ids = {n["concept_id"] for n in g["nodes"]}
    assert {"knowledge/a", "knowledge/b"} <= ids


def test_refresh_endpoint(client):
    r = client.post("/api/knowledge/refresh")
    assert r.status_code == 200
    assert r.json()["concepts"] >= 2

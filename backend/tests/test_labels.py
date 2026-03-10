"""Label description and stats endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from app.models.user import User

from tests.conftest import make_mock_db

_TEST_USER = User(email="test@example.com", name="Test User")


@pytest.fixture
def client(in_memory_db):
    """TestClient with auth + db overridden."""
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    import app.routers.labels as labels_mod
    labels_mod.get_db = make_mock_db(in_memory_db)
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()
    labels_mod.get_db = __import__("app.database", fromlist=["get_db"]).get_db


# ── Label Descriptions CRUD ─────────────────────────────────────────────


def test_list_descriptions_empty(client):
    res = client.get("/api/labels/descriptions")
    assert res.status_code == 200
    assert res.json()["descriptions"] == []


def test_upsert_description(client):
    res = client.put(
        "/api/labels/1/description",
        json={"title": "Bug", "description": "Bugs and defects"},
    )
    assert res.status_code == 200
    assert res.json()["label_id"] == 1
    assert res.json()["description"] == "Bugs and defects"


def test_upsert_updates_existing(client):
    client.put("/api/labels/1/description", json={"title": "Bug", "description": "v1"})
    client.put("/api/labels/1/description", json={"title": "Bug", "description": "v2"})
    res = client.get("/api/labels/descriptions")
    descs = res.json()["descriptions"]
    assert len(descs) == 1
    assert descs[0]["description"] == "v2"


def test_delete_description(client):
    client.put("/api/labels/1/description", json={"title": "Bug", "description": "test"})
    res = client.delete("/api/labels/1/description")
    assert res.status_code == 200
    assert res.json()["success"] is True
    # Verify deleted
    res = client.get("/api/labels/descriptions")
    assert len(res.json()["descriptions"]) == 0


def test_list_multiple_descriptions(client):
    client.put("/api/labels/1/description", json={"title": "Bug", "description": "Bugs"})
    client.put("/api/labels/2/description", json={"title": "Feature", "description": "New features"})
    client.put("/api/labels/3/description", json={"title": "Chore", "description": "Maintenance"})
    res = client.get("/api/labels/descriptions")
    assert len(res.json()["descriptions"]) == 3


# ── Label Stats ──────────────────────────────────────────────────────────


def test_label_stats(client):
    mock_tasks = [
        {"id": 1, "done": False, "labels": [{"id": 10, "title": "Bug"}]},
        {"id": 2, "done": True, "labels": [{"id": 10, "title": "Bug"}, {"id": 20, "title": "Feature"}]},
        {"id": 3, "done": False, "labels": [{"id": 20, "title": "Feature"}]},
        {"id": 4, "done": False, "labels": []},
    ]
    with patch("app.routers.labels.vikunja.list_tasks", new_callable=AsyncMock, return_value=mock_tasks):
        res = client.get("/api/labels/stats")
    assert res.status_code == 200
    stats = res.json()["stats"]
    assert stats["10"]["total"] == 2
    assert stats["10"]["done"] == 1
    assert stats["10"]["open"] == 1
    assert stats["20"]["total"] == 2
    assert stats["20"]["done"] == 1
    assert stats["20"]["open"] == 1


def test_label_stats_empty(client):
    with patch("app.routers.labels.vikunja.list_tasks", new_callable=AsyncMock, return_value=[]):
        res = client.get("/api/labels/stats")
    assert res.status_code == 200
    assert res.json()["stats"] == {}


# ── Label Cleanup ────────────────────────────────────────────────────────


def test_cleanup_unused_labels(client):
    """Cleanup deletes labels with 0 tasks and their SQLite descriptions."""
    mock_tasks = [
        {"id": 1, "done": False, "labels": [{"id": 10, "title": "Bug"}]},
    ]
    mock_labels = [
        {"id": 10, "title": "Bug"},
        {"id": 20, "title": "Unused"},
        {"id": 30, "title": "Also Unused"},
    ]
    # Pre-populate descriptions for labels that will be cleaned up
    client.put("/api/labels/20/description", json={"title": "Unused", "description": "desc"})
    client.put("/api/labels/30/description", json={"title": "Also Unused", "description": "desc"})

    with (
        patch("app.routers.labels.vikunja.list_tasks", new_callable=AsyncMock, return_value=mock_tasks),
        patch("app.routers.labels.vikunja.list_labels", new_callable=AsyncMock, return_value=mock_labels),
        patch("app.routers.labels.vikunja.delete_label", new_callable=AsyncMock) as mock_delete,
    ):
        res = client.post("/api/labels/cleanup")

    assert res.status_code == 200
    data = res.json()
    assert set(data["deleted"]) == {20, 30}
    assert data["count"] == 2
    assert mock_delete.call_count == 2

    # Verify SQLite descriptions were also cleaned up
    descs_res = client.get("/api/labels/descriptions")
    assert len(descs_res.json()["descriptions"]) == 0


def test_cleanup_no_unused_labels(client):
    """Cleanup with all labels in use returns empty."""
    mock_tasks = [
        {"id": 1, "done": False, "labels": [{"id": 10, "title": "Bug"}]},
    ]
    mock_labels = [{"id": 10, "title": "Bug"}]

    with (
        patch("app.routers.labels.vikunja.list_tasks", new_callable=AsyncMock, return_value=mock_tasks),
        patch("app.routers.labels.vikunja.list_labels", new_callable=AsyncMock, return_value=mock_labels),
    ):
        res = client.post("/api/labels/cleanup")

    assert res.status_code == 200
    assert res.json()["deleted"] == []
    assert res.json()["count"] == 0

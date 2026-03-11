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


# ── Label Update (color) ─────────────────────────────────────────────────


def test_update_label_color(client):
    """PUT /api/labels/{id} fetches label by ID, merges changes, sends full object."""
    current_label = {"id": 5, "title": "Bug", "hex_color": "#ff0000", "description": "", "created_by": {"id": 1}}
    updated_label = {**current_label, "hex_color": "#00ff00"}

    with (
        patch("app.routers.labels.vikunja.get_label", new_callable=AsyncMock, return_value=current_label) as mock_get,
        patch("app.routers.labels.vikunja.update_label", new_callable=AsyncMock, return_value=updated_label) as mock_update,
    ):
        res = client.put("/api/labels/5", json={"hex_color": "#00ff00"})

    assert res.status_code == 200
    mock_update.assert_called_once_with(5, {"hex_color": "#00ff00"})


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


# ── Generate Description ─────────────────────────────────────────────────


def test_generate_description(client):
    """LLM generates a label description from matching tasks."""
    mock_labels = [{"id": 10, "title": "Bug", "hex_color": "#E85D5D"}]
    mock_tasks = [
        {"id": 1, "title": "Fix login crash", "description": "App crashes on login", "done": False, "labels": [{"id": 10, "title": "Bug"}]},
        {"id": 2, "title": "Fix typo in header", "description": "", "done": False, "labels": [{"id": 10, "title": "Bug"}]},
        {"id": 3, "title": "Add dark mode", "description": "", "done": False, "labels": [{"id": 20, "title": "Feature"}]},
    ]

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="Apply this label to bug reports and defects.")

    with (
        patch("app.routers.labels.vikunja.list_labels", new_callable=AsyncMock, return_value=mock_labels),
        patch("app.routers.labels.vikunja.list_tasks", new_callable=AsyncMock, return_value=mock_tasks),
        patch("app.routers.labels.get_llm_client", return_value=mock_llm),
    ):
        res = client.post("/api/labels/10/generate-description")

    assert res.status_code == 200
    data = res.json()
    assert data["label_id"] == 10
    assert data["description"] == "Apply this label to bug reports and defects."


def test_generate_description_no_tasks(client):
    """Returns 400 when no tasks have the target label."""
    mock_labels = [{"id": 10, "title": "Bug", "hex_color": "#E85D5D"}]
    mock_tasks = [
        {"id": 1, "title": "Add dark mode", "description": "", "done": False, "labels": [{"id": 20, "title": "Feature"}]},
    ]

    with (
        patch("app.routers.labels.vikunja.list_labels", new_callable=AsyncMock, return_value=mock_labels),
        patch("app.routers.labels.vikunja.list_tasks", new_callable=AsyncMock, return_value=mock_tasks),
    ):
        res = client.post("/api/labels/10/generate-description")

    assert res.status_code == 400


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

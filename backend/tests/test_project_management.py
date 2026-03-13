"""Tests for project management endpoints (CRUD, archive, color, position)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from tests.conftest import make_mock_db


def _setup(in_memory_db, mock_user):
    """Wire up test client with in-memory DB and mock auth."""
    import app.routers.projects as projects_mod

    projects_mod.get_db = make_mock_db(in_memory_db)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


FAKE_PROJECT = {
    "id": 1,
    "title": "Test Project",
    "description": "desc",
    "hex_color": "#E8772E",
    "is_archived": False,
    "position": 1.0,
}


def test_list_projects_includes_hex_color(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    in_memory_db.execute(
        "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [1, "Proj", "desc", "#E8772E", 0, 1.0],
    )
    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.list_projects = AsyncMock(side_effect=Exception("skip"))
        res = client.get("/api/projects")
    assert res.status_code == 200
    projects = res.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["hex_color"] == "#E8772E"
    assert projects[0]["position"] == 1.0


def test_list_projects_excludes_archived(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    in_memory_db.execute(
        "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [1, "Active", "", "", 0, 0],
    )
    in_memory_db.execute(
        "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [2, "Archived", "", "", 1, 0],
    )
    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.list_projects = AsyncMock(side_effect=Exception("skip"))
        res = client.get("/api/projects")
    assert res.status_code == 200
    projects = res.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["title"] == "Active"


def test_list_projects_include_archived_param(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    in_memory_db.execute(
        "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [1, "Active", "", "", 0, 0],
    )
    in_memory_db.execute(
        "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [2, "Archived", "", "", 1, 0],
    )
    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.list_projects = AsyncMock(side_effect=Exception("skip"))
        res = client.get("/api/projects?include_archived=true")
    assert res.status_code == 200
    projects = res.json()["projects"]
    assert len(projects) == 2


def test_update_project_title(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    in_memory_db.execute(
        "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [1, "Old", "", "", 0, 0],
    )
    updated = {**FAKE_PROJECT, "title": "New Title"}
    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.update_project = AsyncMock(return_value=updated)
        res = client.post("/api/projects/1", json={"title": "New Title"})
    assert res.status_code == 200
    assert res.json()["title"] == "New Title"
    # Check cache updated
    row = in_memory_db.execute("SELECT title FROM vikunja_projects WHERE id = 1").fetchone()
    assert row[0] == "New Title"


def test_update_project_color(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    in_memory_db.execute(
        "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [1, "Proj", "", "", 0, 0],
    )
    updated = {**FAKE_PROJECT, "hex_color": "#5B8DEF"}
    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.update_project = AsyncMock(return_value=updated)
        res = client.post("/api/projects/1", json={"hex_color": "#5B8DEF"})
    assert res.status_code == 200
    row = in_memory_db.execute("SELECT hex_color FROM vikunja_projects WHERE id = 1").fetchone()
    assert row[0] == "#5B8DEF"


def test_archive_project(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    in_memory_db.execute(
        "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [1, "Proj", "", "", 0, 0],
    )
    updated = {**FAKE_PROJECT, "is_archived": True}
    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.update_project = AsyncMock(return_value=updated)
        res = client.post("/api/projects/1", json={"is_archived": True})
    assert res.status_code == 200
    row = in_memory_db.execute("SELECT is_archived FROM vikunja_projects WHERE id = 1").fetchone()
    assert row[0] == 1


def test_delete_project(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    in_memory_db.execute(
        "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        [1, "Proj", "", "", 0, 0],
    )
    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.delete_project = AsyncMock(return_value={})
        res = client.delete("/api/projects/1")
    assert res.status_code == 200
    assert res.json()["success"] is True
    row = in_memory_db.execute("SELECT id FROM vikunja_projects WHERE id = 1").fetchone()
    assert row is None


def test_delete_nonexistent_project(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    from app.services.vikunja import VikunjaError

    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.delete_project = AsyncMock(side_effect=VikunjaError("DELETE /projects/999 failed: 404"))
        res = client.delete("/api/projects/999")
    assert res.status_code == 422


def test_create_project_with_color(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    created = {**FAKE_PROJECT, "hex_color": ""}
    colored = {**FAKE_PROJECT, "hex_color": "#4CAF7D"}
    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.create_project = AsyncMock(return_value=created)
        mock_v.update_project = AsyncMock(return_value=colored)
        res = client.post("/api/projects", json={"title": "New", "hex_color": "#4CAF7D"})
    assert res.status_code == 200
    mock_v.update_project.assert_called_once()
    row = in_memory_db.execute("SELECT hex_color FROM vikunja_projects WHERE id = 1").fetchone()
    assert row[0] == "#4CAF7D"


def test_sync_preserves_all_fields(in_memory_db, mock_user):
    client = _setup(in_memory_db, mock_user)
    fresh_projects = [
        {"id": 1, "title": "P1", "description": "", "hex_color": "#E8772E", "is_archived": False, "position": 1.5},
        {"id": 2, "title": "P2", "description": "d", "hex_color": "#5B8DEF", "is_archived": True, "position": 3.0},
    ]
    with patch("app.routers.projects.vikunja") as mock_v:
        mock_v.list_projects = AsyncMock(return_value=fresh_projects)
        res = client.post("/api/projects/sync")
    assert res.status_code == 200
    assert res.json()["synced"] == 2
    rows = in_memory_db.execute("SELECT id, hex_color, is_archived, position FROM vikunja_projects ORDER BY id").fetchall()
    assert rows[0] == (1, "#E8772E", 0, 1.5)
    assert rows[1] == (2, "#5B8DEF", 1, 3.0)

"""Proposal lifecycle tests via FastAPI TestClient (sync)."""

import sqlite3
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from app.models.user import User
from app.services.vikunja import VikunjaError
from tests.conftest import make_mock_db

_TEST_USER = User(email="test@example.com", name="Test User")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def seeded_db():
    """In-memory SQLite with schema + one pending proposal (project_id=1)."""
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(conn)

    proposal_id = str(uuid.uuid4())
    source_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO task_proposals
           (id, source_id, title, description, project_name, project_id,
            priority, status, source_type, source_text)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            proposal_id, source_id,
            "Test Task", "Test description", "Test Project", 1,
            3, "pending", "notes", "test source",
        ],
    )
    yield conn, proposal_id
    conn.close()


@pytest.fixture
def client(seeded_db, monkeypatch):
    """TestClient with auth overridden and get_db patched to in-memory DB."""
    conn, _ = seeded_db
    mock_db = make_mock_db(conn)
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    monkeypatch.setattr("app.routers.proposals.get_db", mock_db)
    monkeypatch.setattr("app.routers.projects.get_db", mock_db)
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()


# ── list_proposals ────────────────────────────────────────────────────────────

def test_list_proposals(client, seeded_db):
    response = client.get("/api/proposals")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert any(p["title"] == "Test Task" for p in data["proposals"])


def test_list_proposals_status_filter(client):
    response = client.get("/api/proposals?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert all(p["status"] == "pending" for p in data["proposals"])


# ── update_proposal ───────────────────────────────────────────────────────────

def test_update_proposal(client, seeded_db):
    _, proposal_id = seeded_db
    response = client.put(
        f"/api/proposals/{proposal_id}",
        json={"title": "Updated Title"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_update_proposal_not_found(client):
    bad_id = str(uuid.uuid4())
    response = client.put(f"/api/proposals/{bad_id}", json={"title": "X"})
    assert response.status_code == 404


def test_update_proposal_no_fields(client, seeded_db):
    _, proposal_id = seeded_db
    response = client.put(f"/api/proposals/{proposal_id}", json={})
    assert response.status_code == 400


# ── approve_proposal ──────────────────────────────────────────────────────────

def test_approve_proposal_success(client, seeded_db):
    conn, proposal_id = seeded_db
    with patch(
        "app.routers.proposals.vikunja.create_task",
        new=AsyncMock(return_value={"id": 99}),
    ):
        response = client.post(f"/api/proposals/{proposal_id}/approve")

    assert response.status_code == 200
    data = response.json()
    assert data["vikunja_task_id"] == 99

    # DB row must be updated
    row = conn.execute(
        "SELECT status, vikunja_task_id FROM task_proposals WHERE id = ?",
        [proposal_id],
    ).fetchone()
    assert row[0] == "created"
    assert row[1] == 99


def test_approve_already_created(client, seeded_db):
    conn, proposal_id = seeded_db
    conn.execute(
        "UPDATE task_proposals SET status = 'created', vikunja_task_id = 77 WHERE id = ?",
        [proposal_id],
    )
    response = client.post(f"/api/proposals/{proposal_id}/approve")
    assert response.status_code == 200
    assert "Already created" in response.json()["message"]


def test_approve_rejected_proposal(client, seeded_db):
    conn, proposal_id = seeded_db
    conn.execute(
        "UPDATE task_proposals SET status = 'rejected' WHERE id = ?",
        [proposal_id],
    )
    response = client.post(f"/api/proposals/{proposal_id}/approve")
    assert response.status_code == 400


def test_approve_no_project(client, seeded_db):
    conn, proposal_id = seeded_db
    conn.execute(
        "UPDATE task_proposals SET project_id = NULL, project_name = NULL WHERE id = ?",
        [proposal_id],
    )
    response = client.post(f"/api/proposals/{proposal_id}/approve")
    assert response.status_code == 400
    assert "project" in response.json()["detail"].lower()


def test_approve_vikunja_error(client, seeded_db):
    """VikunjaError → 502; status stays 'approved' so user can retry."""
    conn, proposal_id = seeded_db
    with patch(
        "app.routers.proposals.vikunja.create_task",
        new=AsyncMock(side_effect=VikunjaError("timeout")),
    ):
        response = client.post(f"/api/proposals/{proposal_id}/approve")

    assert response.status_code == 422

    row = conn.execute(
        "SELECT status FROM task_proposals WHERE id = ?",
        [proposal_id],
    ).fetchone()
    assert row[0] == "approved"


# ── reject_proposal ───────────────────────────────────────────────────────────

def test_reject_proposal(client, seeded_db):
    conn, proposal_id = seeded_db
    response = client.post(f"/api/proposals/{proposal_id}/reject")
    assert response.status_code == 200

    row = conn.execute(
        "SELECT status FROM task_proposals WHERE id = ?",
        [proposal_id],
    ).fetchone()
    assert row[0] == "rejected"


def test_reject_not_found(client):
    bad_id = str(uuid.uuid4())
    response = client.post(f"/api/proposals/{bad_id}/reject")
    assert response.status_code == 404


# ── approve-all ───────────────────────────────────────────────────────────────

def test_approve_all(client, seeded_db):
    """Both pending proposals with project_id should be approved."""
    conn, _ = seeded_db
    p2_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO task_proposals
           (id, source_id, title, project_id, status, source_type, source_text)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [p2_id, str(uuid.uuid4()), "Task Two", 1, "pending", "notes", ""],
    )

    with patch(
        "app.routers.proposals.vikunja.create_task",
        new=AsyncMock(return_value={"id": 100}),
    ):
        response = client.post("/api/proposals/approve-all")

    assert response.status_code == 200
    data = response.json()
    assert data["approved"] == 2
    assert data["errors"] == []


def test_approve_creates_new_project(client, seeded_db):
    """Approval with project_name but no project_id creates the project."""
    conn, proposal_id = seeded_db
    conn.execute(
        "UPDATE task_proposals SET project_id = NULL, project_name = 'New Research' WHERE id = ?",
        [proposal_id],
    )

    with patch(
        "app.routers.proposals.vikunja.create_project",
        new=AsyncMock(return_value={"id": 50, "title": "New Research", "description": ""}),
    ), patch(
        "app.routers.proposals.vikunja.create_task",
        new=AsyncMock(return_value={"id": 99}),
    ):
        response = client.post(f"/api/proposals/{proposal_id}/approve")

    assert response.status_code == 200
    data = response.json()
    assert data["vikunja_task_id"] == 99
    assert data["new_project_created"] is True

    # project_id should be updated in DB
    row = conn.execute("SELECT project_id FROM task_proposals WHERE id = ?", [proposal_id]).fetchone()
    assert row[0] == 50


def test_approve_all_dedup_new_projects(client, seeded_db):
    """Approve-all with duplicate project names creates the project only once."""
    conn, proposal_id = seeded_db
    conn.execute(
        "UPDATE task_proposals SET project_id = NULL, project_name = 'Shared Project' WHERE id = ?",
        [proposal_id],
    )
    p2_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO task_proposals
           (id, source_id, title, project_name, project_id, status, source_type, source_text)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [p2_id, str(uuid.uuid4()), "Task Two", "Shared Project", None, "pending", "notes", ""],
    )

    create_project_mock = AsyncMock(return_value={"id": 60, "title": "Shared Project", "description": ""})
    with patch(
        "app.routers.proposals.vikunja.create_project",
        new=create_project_mock,
    ), patch(
        "app.routers.proposals.vikunja.create_task",
        new=AsyncMock(return_value={"id": 100}),
    ):
        response = client.post("/api/proposals/approve-all")

    assert response.status_code == 200
    data = response.json()
    assert data["approved"] == 2
    assert data["new_projects"] == ["Shared Project"]
    # create_project should only be called once (dedup)
    assert create_project_mock.call_count == 1


def test_approve_all_skips_no_project(client, seeded_db):
    """Proposal without project_id counts as an error, not approved."""
    conn, _ = seeded_db
    p2_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO task_proposals
           (id, source_id, title, project_id, status, source_type, source_text)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [p2_id, str(uuid.uuid4()), "No Project Task", None, "pending", "notes", ""],
    )

    with patch(
        "app.routers.proposals.vikunja.create_task",
        new=AsyncMock(return_value={"id": 101}),
    ):
        response = client.post("/api/proposals/approve-all")

    assert response.status_code == 200
    data = response.json()
    assert data["approved"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["id"] == p2_id

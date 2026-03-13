"""Task endpoint tests via FastAPI TestClient."""

import json
import sqlite3
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from app.models.user import User
from app.services.vikunja import VikunjaError

_TEST_USER = User(email="test@example.com", name="Test User")

_SAMPLE_TASK = {
    "id": 42,
    "title": "Test task",
    "description": "A test",
    "done": False,
    "priority": 3,
    "due_date": None,
    "project_id": 1,
    "labels": [],
}


@pytest.fixture
def client():
    """TestClient with auth overridden."""
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def revision_db():
    """In-memory DB for revision recording tests."""
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(conn)

    @contextmanager
    def _mock(database_path=None):
        yield conn

    return conn, _mock


@pytest.fixture
def rev_client(revision_db):
    """TestClient wired to in-memory DB for revision tests."""
    conn, mock_get_db = revision_db
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    with patch("app.routers.tasks.get_db", mock_get_db):
        tc = TestClient(app)
        yield tc, conn
    app.dependency_overrides.clear()


# ── List attachments ─────────────────────────────────────────────────────────

def test_list_attachments(client):
    mock_data = [
        {"id": 1, "task_id": 42, "file": {"id": 10, "name": "doc.pdf", "mime": "application/pdf", "size": 1024, "created": "2025-01-01T00:00:00Z"}, "created": "2025-01-01T00:00:00Z", "created_by": {"id": 1, "email": "t@t.com", "name": "Test"}}
    ]
    with patch("app.routers.tasks.vikunja.list_attachments", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/api/tasks/42/attachments")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["file"]["name"] == "doc.pdf"


def test_list_attachments_vikunja_error(client):
    with patch("app.routers.tasks.vikunja.list_attachments", new_callable=AsyncMock, side_effect=VikunjaError("fail")):
        res = client.get("/api/tasks/42/attachments")
    assert res.status_code == 422


# ── Upload attachment ────────────────────────────────────────────────────────

def test_upload_attachment(client):
    mock_result = {"id": 1, "task_id": 42, "file": {"id": 10, "name": "test.txt", "mime": "text/plain", "size": 5}}
    with patch("app.routers.tasks.vikunja.upload_attachment", new_callable=AsyncMock, return_value=mock_result) as mock_upload:
        res = client.put(
            "/api/tasks/42/attachments",
            files={"files": ("test.txt", b"hello", "text/plain")},
        )
    assert res.status_code == 200
    mock_upload.assert_awaited_once_with(42, "test.txt", b"hello", "text/plain")


def test_upload_too_large(client):
    # 21 MB file exceeds 20 MB limit
    big_content = b"x" * (21 * 1024 * 1024)
    res = client.put(
        "/api/tasks/42/attachments",
        files={"files": ("big.bin", big_content, "application/octet-stream")},
    )
    assert res.status_code == 413


def test_upload_vikunja_error(client):
    with patch("app.routers.tasks.vikunja.upload_attachment", new_callable=AsyncMock, side_effect=VikunjaError("fail")):
        res = client.put(
            "/api/tasks/42/attachments",
            files={"files": ("test.txt", b"hello", "text/plain")},
        )
    assert res.status_code == 422


# ── Download attachment ──────────────────────────────────────────────────────

def test_download_attachment(client):
    mock_data = (b"file-content", "application/pdf", "doc.pdf")
    with patch("app.routers.tasks.vikunja.download_attachment", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/api/tasks/42/attachments/1")
    assert res.status_code == 200
    assert res.content == b"file-content"
    assert res.headers["content-type"] == "application/pdf"
    assert "doc.pdf" in res.headers["content-disposition"]


def test_download_vikunja_error(client):
    with patch("app.routers.tasks.vikunja.download_attachment", new_callable=AsyncMock, side_effect=VikunjaError("fail")):
        res = client.get("/api/tasks/42/attachments/1")
    assert res.status_code == 422


# ── Delete attachment ────────────────────────────────────────────────────────

def test_delete_attachment(client):
    with patch("app.routers.tasks.vikunja.delete_attachment", new_callable=AsyncMock, return_value={}):
        res = client.delete("/api/tasks/42/attachments/1")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_delete_attachment_vikunja_error(client):
    with patch("app.routers.tasks.vikunja.delete_attachment", new_callable=AsyncMock, side_effect=VikunjaError("fail")):
        res = client.delete("/api/tasks/42/attachments/1")
    assert res.status_code == 422


# ── Revision recording ──────────────────────────────────────────────────────

def _get_revisions(conn):
    """Fetch all revisions from the DB."""
    rows = conn.execute(
        "SELECT task_id, action_type, source, before_state, after_state FROM task_revisions ORDER BY id"
    ).fetchall()
    return [
        {"task_id": r[0], "action_type": r[1], "source": r[2],
         "before_state": json.loads(r[3]) if r[3] else None,
         "after_state": json.loads(r[4]) if r[4] else None}
        for r in rows
    ]


def test_create_task_records_revision(rev_client):
    client, conn = rev_client
    created = {**_SAMPLE_TASK, "id": 99}
    with patch("app.routers.tasks.vikunja.create_task", new_callable=AsyncMock, return_value=created):
        res = client.put("/api/tasks", json={"project_id": 1, "title": "New task"})
    assert res.status_code == 200
    revs = _get_revisions(conn)
    assert len(revs) == 1
    assert revs[0]["action_type"] == "create"
    assert revs[0]["source"] == "manual"
    assert revs[0]["after_state"]["id"] == 99


def test_update_task_records_revision(rev_client):
    client, conn = rev_client
    updated = {**_SAMPLE_TASK, "title": "Updated title"}
    with patch("app.routers.tasks.vikunja.get_task", new_callable=AsyncMock, return_value=_SAMPLE_TASK), \
         patch("app.routers.tasks.vikunja.update_task", new_callable=AsyncMock, return_value=updated):
        res = client.post("/api/tasks/42", json={"title": "Updated title"})
    assert res.status_code == 200
    revs = _get_revisions(conn)
    assert len(revs) == 1
    assert revs[0]["action_type"] == "update"
    assert revs[0]["source"] == "manual"
    assert revs[0]["before_state"]["title"] == "Test task"
    assert revs[0]["after_state"]["title"] == "Updated title"


def test_update_done_records_complete_revision(rev_client):
    client, conn = rev_client
    completed = {**_SAMPLE_TASK, "done": True}
    with patch("app.routers.tasks.vikunja.get_task", new_callable=AsyncMock, return_value=_SAMPLE_TASK), \
         patch("app.routers.tasks.vikunja.update_task", new_callable=AsyncMock, return_value=completed):
        res = client.post("/api/tasks/42", json={"done": True})
    assert res.status_code == 200
    revs = _get_revisions(conn)
    assert len(revs) == 1
    assert revs[0]["action_type"] == "complete"


def test_update_project_records_move_revision(rev_client):
    client, conn = rev_client
    moved = {**_SAMPLE_TASK, "project_id": 5}
    with patch("app.routers.tasks.vikunja.get_task", new_callable=AsyncMock, return_value=_SAMPLE_TASK), \
         patch("app.routers.tasks.vikunja.update_task", new_callable=AsyncMock, return_value=moved):
        res = client.post("/api/tasks/42", json={"project_id": 5})
    assert res.status_code == 200
    revs = _get_revisions(conn)
    assert len(revs) == 1
    assert revs[0]["action_type"] == "move"


def test_delete_task_records_revision(rev_client):
    client, conn = rev_client
    with patch("app.routers.tasks.vikunja.get_task", new_callable=AsyncMock, return_value=_SAMPLE_TASK), \
         patch("app.routers.tasks.vikunja.delete_task", new_callable=AsyncMock, return_value={}):
        res = client.delete("/api/tasks/42")
    assert res.status_code == 200
    revs = _get_revisions(conn)
    assert len(revs) == 1
    assert revs[0]["action_type"] == "delete"
    assert revs[0]["source"] == "manual"
    assert revs[0]["before_state"]["title"] == "Test task"

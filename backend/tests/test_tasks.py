"""Task attachment endpoint tests via FastAPI TestClient."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.services.vikunja import VikunjaError

_TEST_USER = User(email="test@example.com", name="Test User")


@pytest.fixture
def client():
    """TestClient with auth overridden."""
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    tc = TestClient(app)
    yield tc
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
    assert res.status_code == 502


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
    assert res.status_code == 502


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
    assert res.status_code == 502


# ── Delete attachment ────────────────────────────────────────────────────────

def test_delete_attachment(client):
    with patch("app.routers.tasks.vikunja.delete_attachment", new_callable=AsyncMock, return_value={}):
        res = client.delete("/api/tasks/42/attachments/1")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_delete_attachment_vikunja_error(client):
    with patch("app.routers.tasks.vikunja.delete_attachment", new_callable=AsyncMock, side_effect=VikunjaError("fail")):
        res = client.delete("/api/tasks/42/attachments/1")
    assert res.status_code == 502

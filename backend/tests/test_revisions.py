"""Tests for the revision system — record, undo, conflict detection, idempotent."""

import json
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from app.models.user import User
from tests.conftest import make_mock_db


@pytest.fixture
def in_memory_db():
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def mock_user():
    return User(email="test@example.com", name="Test User")


@pytest.fixture
def client(in_memory_db, mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    import app.routers.revisions as rev_mod
    rev_mod.get_db = make_mock_db(in_memory_db)
    yield TestClient(app)
    app.dependency_overrides.clear()
    import importlib
    importlib.reload(rev_mod)


# ── RevisionService.record ──────────────────────────────────────────────────

def test_record_creates_revision(in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(
        in_memory_db,
        task_id=42,
        action_type="update",
        source="chat",
        before_state={"title": "Old"},
        after_state={"title": "New"},
        changes={"title": "New"},
    )
    assert rid is not None
    row = in_memory_db.execute("SELECT * FROM task_revisions WHERE id = ?", [rid]).fetchone()
    assert row is not None
    assert row[1] == 42  # task_id
    assert row[2] == "update"  # action_type
    assert row[3] == "chat"  # source


def test_record_with_proposal(in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(
        in_memory_db,
        task_id=10,
        action_type="create",
        source="proposal",
        after_state={"id": 10, "title": "New task"},
        proposal_id="abc-123",
    )
    rev = RevisionService.get_by_id(in_memory_db, rid)
    assert rev["proposal_id"] == "abc-123"
    assert rev["action_type"] == "create"
    assert rev["before_state"] is None
    assert rev["after_state"]["title"] == "New task"


# ── RevisionService.get_recent ──────────────────────────────────────────────

def test_get_recent(in_memory_db):
    from app.services.revisions import RevisionService

    for i in range(5):
        RevisionService.record(in_memory_db, task_id=i, action_type="update", source="chat")

    recent = RevisionService.get_recent(in_memory_db, limit=3)
    assert len(recent) == 3
    assert recent[0]["task_id"] == 4  # newest first


# ── RevisionService.undo — update ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_undo_update(in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(
        in_memory_db,
        task_id=42,
        action_type="update",
        source="chat",
        before_state={"title": "Old", "priority": 3},
        after_state={"title": "New", "priority": 5},
    )

    with patch("app.services.revisions.vikunja") as mock_v:
        mock_v.get_task = AsyncMock(return_value={"title": "New", "priority": 5})
        mock_v.update_task = AsyncMock(return_value={})
        result = await RevisionService.undo(in_memory_db, rid)

    assert result["success"] is True
    mock_v.update_task.assert_called_once()
    rev = RevisionService.get_by_id(in_memory_db, rid)
    assert rev["undone"] is True


# ── RevisionService.undo — create (deletes the task) ───────────────────────

@pytest.mark.asyncio
async def test_undo_create(in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(
        in_memory_db,
        task_id=99,
        action_type="create",
        source="proposal",
        after_state={"id": 99, "title": "Created"},
    )

    with patch("app.services.revisions.vikunja") as mock_v:
        mock_v.delete_task = AsyncMock(return_value={})
        result = await RevisionService.undo(in_memory_db, rid)

    assert result["success"] is True
    mock_v.delete_task.assert_called_once_with(99)


# ── RevisionService.undo — delete (recreates from before_state) ────────────

@pytest.mark.asyncio
async def test_undo_delete(in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(
        in_memory_db,
        task_id=50,
        action_type="delete",
        source="chat",
        before_state={"id": 50, "title": "Deleted task", "project_id": 1, "priority": 3},
    )

    with patch("app.services.revisions.vikunja") as mock_v:
        mock_v.create_task = AsyncMock(return_value={"id": 51, "title": "Deleted task"})
        result = await RevisionService.undo(in_memory_db, rid)

    assert result["success"] is True
    mock_v.create_task.assert_called_once()


# ── Idempotent undo ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_undo_idempotent(in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(
        in_memory_db, task_id=42, action_type="complete", source="chat",
        before_state={"done": False}, after_state={"done": True},
    )

    with patch("app.services.revisions.vikunja") as mock_v:
        mock_v.get_task = AsyncMock(return_value={"done": True})
        mock_v.update_task = AsyncMock(return_value={})
        await RevisionService.undo(in_memory_db, rid)

    # Second undo should return already_undone
    result = await RevisionService.undo(in_memory_db, rid)
    assert result["already_undone"] is True


# ── Conflict detection ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_undo_conflict(in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(
        in_memory_db,
        task_id=42,
        action_type="update",
        source="chat",
        before_state={"title": "Old", "priority": 3},
        after_state={"title": "New", "priority": 5},
    )

    with patch("app.services.revisions.vikunja") as mock_v:
        # Current state differs from after_state — someone edited the task
        mock_v.get_task = AsyncMock(return_value={"title": "Edited by user", "priority": 5})
        result = await RevisionService.undo(in_memory_db, rid)

    assert result["conflict"] is True
    assert "title" in result["conflict_fields"]


# ── Force undo ignores conflict ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_undo_force_skips_conflict(in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(
        in_memory_db,
        task_id=42,
        action_type="update",
        source="chat",
        before_state={"title": "Old"},
        after_state={"title": "New"},
    )

    with patch("app.services.revisions.vikunja") as mock_v:
        mock_v.update_task = AsyncMock(return_value={})
        result = await RevisionService.undo(in_memory_db, rid, force=True)

    assert result["success"] is True


# ── Auto-tag undo ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_undo_auto_tag(in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(
        in_memory_db,
        task_id=42,
        action_type="auto_tag",
        source="auto_tag",
        changes={"labels_added": [1, 2]},
    )

    with patch("app.services.revisions.vikunja") as mock_v:
        mock_v.remove_label_from_task = AsyncMock(return_value={})
        result = await RevisionService.undo(in_memory_db, rid)

    assert result["success"] is True
    assert mock_v.remove_label_from_task.call_count == 2


# ── API endpoints ───────────────────────────────────────────────────────────

def test_list_revisions_api(client, in_memory_db):
    from app.services.revisions import RevisionService

    RevisionService.record(in_memory_db, task_id=1, action_type="update", source="chat")
    RevisionService.record(in_memory_db, task_id=2, action_type="create", source="proposal")

    res = client.get("/api/revisions")
    assert res.status_code == 200
    data = res.json()
    assert len(data["revisions"]) == 2


def test_get_revision_api(client, in_memory_db):
    from app.services.revisions import RevisionService

    rid = RevisionService.record(in_memory_db, task_id=1, action_type="update", source="chat")
    res = client.get(f"/api/revisions/{rid}")
    assert res.status_code == 200
    assert res.json()["task_id"] == 1


def test_get_revision_not_found(client):
    res = client.get("/api/revisions/9999")
    assert res.status_code == 404

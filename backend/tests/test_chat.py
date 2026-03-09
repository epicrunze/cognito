"""Chat endpoint tests."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from app.models.proposal import TaskProposal
from app.models.user import User

from tests.conftest import make_mock_db

_TEST_USER = User(email="test@example.com", name="Test User")


@pytest.fixture
def client(in_memory_db):
    """TestClient with auth + db overridden."""
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    import app.routers.chat as chat_mod
    chat_mod.get_db = make_mock_db(in_memory_db)
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()
    chat_mod.get_db = __import__("app.database", fromlist=["get_db"]).get_db


# ── Chat endpoint ──────────────────────────────────────────────────────


def test_chat_creates_conversation(client):
    mock_proposals = [
        TaskProposal(
            id="p1", source_id="s1", title="Write tests",
            source_type="chat", source_text="test", status="pending",
        )
    ]
    mock_result = {
        "reply": "Got it! I extracted 1 task.",
        "proposals": mock_proposals,
        "actions": [],
        "pending_actions": [],
    }
    with patch("app.routers.chat.ChatAgent") as MockAgent:
        mock_instance = MockAgent.return_value
        mock_instance.process = AsyncMock(return_value=mock_result)
        res = client.post("/api/chat", json={"message": "I need to write tests"})

    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    assert data["reply"] == "Got it! I extracted 1 task."
    assert len(data["proposals"]) == 1
    assert data["proposals"][0]["title"] == "Write tests"


def test_chat_empty_message(client):
    res = client.post("/api/chat", json={"message": "  "})
    assert res.status_code == 400


def test_chat_continues_conversation(client):
    # First message
    with patch("app.routers.chat.ChatAgent") as MockAgent:
        mock_instance = MockAgent.return_value
        mock_instance.process = AsyncMock(return_value={
            "reply": "Hello!", "proposals": [], "actions": [], "pending_actions": [],
        })
        res1 = client.post("/api/chat", json={"message": "Hi"})
    conv_id = res1.json()["conversation_id"]

    # Second message in same conversation
    with patch("app.routers.chat.ChatAgent") as MockAgent:
        mock_instance = MockAgent.return_value
        mock_instance.process = AsyncMock(return_value={
            "reply": "How can I help?", "proposals": [], "actions": [], "pending_actions": [],
        })
        res2 = client.post("/api/chat", json={"message": "What can you do?", "conversation_id": conv_id})

    assert res2.status_code == 200
    assert res2.json()["conversation_id"] == conv_id


def test_get_conversation(client):
    # Create conversation
    with patch("app.routers.chat.ChatAgent") as MockAgent:
        mock_instance = MockAgent.return_value
        mock_instance.process = AsyncMock(return_value={
            "reply": "Hi!", "proposals": [], "actions": [], "pending_actions": [],
        })
        res = client.post("/api/chat", json={"message": "Hello"})
    conv_id = res.json()["conversation_id"]

    # Fetch conversation
    res = client.get(f"/api/chat/{conv_id}")
    assert res.status_code == 200
    data = res.json()
    assert len(data["messages"]) == 2  # user + assistant
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"


def test_get_conversation_not_found(client):
    res = client.get("/api/chat/nonexistent-id")
    assert res.status_code == 404


def test_chat_extraction_failure_graceful(client):
    """Chat still returns a reply even if agent fails."""
    with patch("app.routers.chat.ChatAgent") as MockAgent:
        mock_instance = MockAgent.return_value
        mock_instance.process = AsyncMock(side_effect=Exception("LLM down"))
        res = client.post("/api/chat", json={"message": "Do something"})
    assert res.status_code == 200
    assert len(res.json()["proposals"]) == 0
    assert "trouble" in res.json()["reply"].lower()


def test_chat_returns_actions(client):
    """Chat returns actions from agent."""
    actions = [{"type": "complete", "task_id": 1, "title": "Buy groceries"}]
    with patch("app.routers.chat.ChatAgent") as MockAgent:
        mock_instance = MockAgent.return_value
        mock_instance.process = AsyncMock(return_value={
            "reply": "Done! Marked 'Buy groceries' as complete.",
            "proposals": [],
            "actions": actions,
            "pending_actions": [],
        })
        res = client.post("/api/chat", json={"message": "mark buy groceries as done"})

    assert res.status_code == 200
    data = res.json()
    assert len(data["actions"]) == 1
    assert data["actions"][0]["type"] == "complete"


def test_chat_returns_pending_actions(client):
    """Chat returns pending delete confirmations."""
    pending = [{"type": "delete", "task_id": 5, "task_title": "Old task"}]
    with patch("app.routers.chat.ChatAgent") as MockAgent:
        mock_instance = MockAgent.return_value
        mock_instance.process = AsyncMock(return_value={
            "reply": "I need your confirmation to delete 'Old task'.",
            "proposals": [],
            "actions": [],
            "pending_actions": pending,
        })
        res = client.post("/api/chat", json={"message": "delete old task"})

    assert res.status_code == 200
    data = res.json()
    assert len(data["pending_actions"]) == 1
    assert data["pending_actions"][0]["type"] == "delete"


# ── Execute action endpoint ──────────────────────────────────────────


def test_execute_action_complete(client):
    """Execute a complete action via the endpoint."""
    with patch("app.routers.chat.vikunja") as mock_v:
        mock_v.update_task = AsyncMock(return_value={"id": 1, "title": "Task", "done": True})
        res = client.post("/api/chat/execute-action", json={"type": "complete", "task_id": 1})

    assert res.status_code == 200
    assert res.json()["success"] is True
    mock_v.update_task.assert_called_once_with(1, {"done": True})


def test_execute_action_update(client):
    """Execute an update action via the endpoint."""
    changes = {"title": "New title", "priority": 5}
    with patch("app.routers.chat.vikunja") as mock_v:
        mock_v.update_task = AsyncMock(return_value={"id": 1, "title": "New title"})
        res = client.post("/api/chat/execute-action", json={"type": "update", "task_id": 1, "changes": changes})

    assert res.status_code == 200
    assert res.json()["success"] is True
    mock_v.update_task.assert_called_once_with(1, changes)


def test_execute_action_move(client):
    """Execute a move action via the endpoint."""
    with patch("app.routers.chat.vikunja") as mock_v:
        mock_v.update_task = AsyncMock(return_value={"id": 1, "title": "Task"})
        res = client.post("/api/chat/execute-action", json={"type": "move", "task_id": 1, "project_id": 10})

    assert res.status_code == 200
    mock_v.update_task.assert_called_once_with(1, {"project_id": 10})


def test_execute_action_delete(client):
    """Execute a delete action via the endpoint."""
    with patch("app.routers.chat.vikunja") as mock_v:
        mock_v.delete_task = AsyncMock(return_value={"success": True})
        res = client.post("/api/chat/execute-action", json={"type": "delete", "task_id": 5})

    assert res.status_code == 200
    mock_v.delete_task.assert_called_once_with(5)


def test_execute_action_update_requires_changes(client):
    """Update action without changes returns 400."""
    res = client.post("/api/chat/execute-action", json={"type": "update", "task_id": 1})
    assert res.status_code == 400


def test_execute_action_unknown_type(client):
    """Unknown action type returns 400."""
    res = client.post("/api/chat/execute-action", json={"type": "unknown", "task_id": 1})
    assert res.status_code == 400

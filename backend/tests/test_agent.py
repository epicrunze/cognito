"""ChatAgent unit tests."""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.agent import ChatAgent


@pytest.fixture
def agent():
    return ChatAgent()


async def test_search_tasks_tool(agent):
    mock_tasks = [
        {"id": 1, "title": "Buy groceries", "done": False, "project_id": 5},
        {"id": 2, "title": "Buy milk", "done": True, "project_id": 5},
    ]
    with patch("app.services.agent.vikunja") as mock_v:
        mock_v.search_tasks = AsyncMock(return_value=mock_tasks)
        result = await agent._tool_handler("search_tasks", {"query": "buy"})

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["title"] == "Buy groceries"


async def test_complete_task_tool(agent):
    with patch("app.services.agent.vikunja") as mock_v:
        mock_v.get_task = AsyncMock(return_value={"id": 1, "title": "Buy groceries"})
        result = await agent._tool_handler("complete_task", {"task_id": 1})

    assert result["pending_confirmation"] is True
    assert result["task_title"] == "Buy groceries"
    assert len(agent._pending_actions) == 1
    assert agent._pending_actions[0]["type"] == "complete"
    assert agent._pending_actions[0]["task_id"] == 1


async def test_update_task_tool(agent):
    with patch("app.services.agent.vikunja") as mock_v:
        mock_v.get_task = AsyncMock(return_value={"id": 1, "title": "Buy groceries"})
        result = await agent._tool_handler("update_task", {"task_id": 1, "title": "New title"})

    assert result["pending_confirmation"] is True
    assert len(agent._pending_actions) == 1
    assert agent._pending_actions[0]["type"] == "update"
    assert agent._pending_actions[0]["changes"] == {"title": "New title"}


async def test_move_task_tool(agent):
    with patch("app.services.agent.vikunja") as mock_v:
        mock_v.get_task = AsyncMock(return_value={"id": 1, "title": "Buy groceries"})
        result = await agent._tool_handler("move_task", {"task_id": 1, "project_id": 10})

    assert result["pending_confirmation"] is True
    assert len(agent._pending_actions) == 1
    assert agent._pending_actions[0]["type"] == "move"
    assert agent._pending_actions[0]["project_id"] == 10


async def test_delete_task_returns_pending(agent):
    with patch("app.services.agent.vikunja") as mock_v:
        mock_v.get_task = AsyncMock(return_value={"id": 1, "title": "Buy groceries"})
        result = await agent._tool_handler("delete_task", {"task_id": 1})

    assert result["pending_confirmation"] is True
    assert result["task_title"] == "Buy groceries"
    assert len(agent._pending_actions) == 1
    assert agent._pending_actions[0]["type"] == "delete"


async def test_create_task_tool(agent):
    result = await agent._tool_handler("create_task", {"title": "Write report", "project_id": 5})

    assert result["pending_confirmation"] is True
    assert result["task_title"] == "Write report"
    assert result["project_id"] == 5
    assert len(agent._pending_actions) == 1
    assert agent._pending_actions[0]["type"] == "create"
    assert agent._pending_actions[0]["task_id"] == 0
    assert agent._pending_actions[0]["changes"]["title"] == "Write report"


async def test_create_task_tool_missing_fields(agent):
    result = await agent._tool_handler("create_task", {"title": "No project"})
    assert "error" in result

    result = await agent._tool_handler("create_task", {"project_id": 5})
    assert "error" in result


async def test_unknown_tool(agent):
    result = await agent._tool_handler("nonexistent_tool", {})
    assert "error" in result


async def test_process_returns_structure(agent):
    """ChatAgent.process returns the expected dict shape."""
    with patch("app.services.agent.get_llm_client") as mock_llm_fn, \
         patch("app.services.agent.get_db") as mock_db:
        mock_llm = MagicMock()
        mock_llm.generate_with_tools = AsyncMock(return_value="I couldn't find any tasks in that.")
        mock_llm_fn.return_value = mock_llm

        # Mock get_db for system_prompt_override lookup
        from tests.conftest import make_mock_db
        import sqlite3
        from app.database import init_schema
        conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        init_schema(conn)
        mock_db.side_effect = make_mock_db(conn)

        result = await agent.process(message="Hello", history=[], model="gemini-flash")

    assert "reply" in result
    assert "proposals" in result
    assert "actions" in result
    assert "pending_actions" in result
    conn.close()


async def test_fallback_reply_with_actions(agent):
    agent._actions = [{"type": "complete", "title": "Buy groceries", "task_id": 1}]
    reply = agent._fallback_reply([])
    assert "Buy groceries" in reply
    assert "done" in reply


async def test_fallback_reply_no_results(agent):
    reply = agent._fallback_reply([])
    assert "details" in reply.lower() or "couldn't" in reply.lower()


# --- Phase 2a: knowledge read tools ---
import sqlite3 as _sqlite3
from contextlib import contextmanager as _contextmanager

from app.database import init_schema as _init_schema


def _agent_mock_db(conn):
    @_contextmanager
    def _cm(database_path=None):
        yield conn
    return _cm


def test_knowledge_tools_present_in_all_tools(agent):
    names = {t["name"] for t in agent.all_tools}
    assert "search_knowledge" in names
    assert "get_concept" in names


async def test_search_knowledge_tool_is_readonly(agent):
    agent._retriever.search = AsyncMock(return_value=[
        {"concept_id": "knowledge/auth", "type": "Note", "source": "native",
         "title": "Auth", "description": "", "snippet": "auth redesign"}
    ])
    result = await agent._tool_handler("search_knowledge", {"query": "auth"})
    assert isinstance(result, list)
    assert result[0]["concept_id"] == "knowledge/auth"
    # read-only: no side effects
    assert agent._pending_actions == []
    assert agent._actions == []
    agent._retriever.search.assert_awaited_once()


async def test_get_concept_tool_returns_detail(agent):
    agent._retriever.get = AsyncMock(return_value={
        "concept_id": "knowledge/b", "title": "Beta", "body": "hello",
        "links": [], "backlinks": ["knowledge/a"],
    })
    result = await agent._tool_handler("get_concept", {"concept_id": "knowledge/b"})
    assert result["title"] == "Beta"
    assert result["backlinks"] == ["knowledge/a"]
    assert agent._pending_actions == []


async def test_get_concept_missing_returns_error(agent):
    agent._retriever.get = AsyncMock(return_value=None)
    result = await agent._tool_handler("get_concept", {"concept_id": "knowledge/nope"})
    assert "error" in result


async def test_get_concept_requires_id(agent):
    result = await agent._tool_handler("get_concept", {})
    assert "error" in result


async def test_chat_flow_routes_search_knowledge(agent):
    """End-to-end: the LLM calls search_knowledge; the tool result flows back."""
    captured = {}

    class FakeLLM:
        async def generate_with_tools(self, messages, system_prompt, tools, tool_handler):
            captured["tool_result"] = await tool_handler("search_knowledge", {"query": "auth"})
            captured["tool_names"] = {t["name"] for t in tools}
            return "Your notes mention the auth redesign."

    agent._retriever.search = AsyncMock(return_value=[
        {"concept_id": "knowledge/auth", "type": "Note", "source": "native",
         "title": "Auth", "description": "", "snippet": "auth redesign"}
    ])
    conn = _sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    _init_schema(conn)
    with patch("app.services.agent.get_llm_client", return_value=FakeLLM()), \
         patch("app.services.agent.get_db", _agent_mock_db(conn)):
        out = await agent.process("what about auth?", history=[])
    assert "auth" in out["reply"].lower()
    assert "search_knowledge" in captured["tool_names"]
    assert captured["tool_result"][0]["concept_id"] == "knowledge/auth"

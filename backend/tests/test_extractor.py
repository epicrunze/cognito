"""Tests for TaskExtractor — mocked LLM + Vikunja, in-memory SQLite."""

import json
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.database import init_schema
from app.services.extractor import TaskExtractor
from app.services.vikunja import VikunjaError
from tests.conftest import make_mock_db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    """In-memory SQLite pre-seeded with a default_project_id."""
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(conn)
    conn.execute("UPDATE agent_config SET default_project_id = 99 WHERE id = 1")
    yield conn
    conn.close()


# ── _parse_output (sync, unit) ────────────────────────────────────────────────

def test_parse_plain_json():
    extractor = TaskExtractor()
    raw = json.dumps([{"title": "Write paper", "priority": 5}])
    result = extractor._parse_output(raw, "notes", "source text")
    assert len(result) == 1
    assert result[0].title == "Write paper"
    assert result[0].priority == 5


def test_parse_markdown_fenced_json():
    extractor = TaskExtractor()
    raw = '```json\n[{"title": "Review PR"}]\n```'
    result = extractor._parse_output(raw, "notes", "source")
    assert len(result) == 1
    assert result[0].title == "Review PR"


def test_parse_malformed_json():
    extractor = TaskExtractor()
    result = extractor._parse_output("This is not JSON at all!!!", "notes", "")
    assert result == []


def test_parse_empty_array():
    extractor = TaskExtractor()
    result = extractor._parse_output("[]", "notes", "")
    assert result == []


def test_parse_skips_items_without_title():
    extractor = TaskExtractor()
    raw = json.dumps([{"description": "no title here"}, {"title": "Has title"}])
    result = extractor._parse_output(raw, "notes", "")
    assert len(result) == 1
    assert result[0].title == "Has title"


def test_parse_bad_due_date():
    """Invalid due_date string → due_date=None, no crash."""
    extractor = TaskExtractor()
    raw = json.dumps([{"title": "Task", "due_date": "not-a-date"}])
    result = extractor._parse_output(raw, "notes", "")
    assert len(result) == 1
    assert result[0].due_date is None


# ── _tool_handler (async) ─────────────────────────────────────────────────────

async def test_tool_lookup_projects():
    extractor = TaskExtractor()
    projects = [
        {"id": 1, "title": "PhD Research", "description": "Doctoral work"},
        {"id": 2, "title": "Personal", "description": ""},
    ]
    with patch("app.services.extractor.vikunja") as mock_vk:
        mock_vk.list_projects = AsyncMock(return_value=projects)
        result = await extractor._tool_handler("lookup_projects", {})

    assert len(result) == 2
    assert result[0] == {"id": 1, "title": "PhD Research", "description": "Doctoral work"}


async def test_tool_resolve_project_exact():
    extractor = TaskExtractor()
    projects = [{"id": 1, "title": "PhD Research", "description": ""}]
    with patch("app.services.extractor.vikunja") as mock_vk:
        mock_vk.list_projects = AsyncMock(return_value=projects)
        result = await extractor._tool_handler("resolve_project", {"name": "PhD Research"})

    assert result["project_id"] == 1
    assert result["project_name"] == "PhD Research"


async def test_tool_resolve_project_partial():
    extractor = TaskExtractor()
    projects = [{"id": 1, "title": "PhD Research", "description": ""}]
    with patch("app.services.extractor.vikunja") as mock_vk:
        mock_vk.list_projects = AsyncMock(return_value=projects)
        result = await extractor._tool_handler("resolve_project", {"name": "phd"})

    assert result["project_id"] == 1


async def test_tool_resolve_project_fallback(db):
    """No match → returns matched=False with the suggested name."""
    extractor = TaskExtractor()
    projects = [{"id": 1, "title": "Some Project", "description": ""}]
    with patch("app.services.extractor.vikunja") as mock_vk:
        mock_vk.list_projects = AsyncMock(return_value=projects)
        result = await extractor._tool_handler("resolve_project", {"name": "nonexistent"})

    assert result["project_id"] is None
    assert result["project_name"] == "nonexistent"
    assert result["matched"] is False


async def test_tool_check_existing_tasks():
    extractor = TaskExtractor()
    tasks = [{"id": 1, "title": "Write report"}, {"id": 2, "title": "Write paper"}]
    with patch("app.services.extractor.vikunja") as mock_vk:
        mock_vk.search_tasks = AsyncMock(return_value=tasks)
        result = await extractor._tool_handler("check_existing_tasks", {"title": "Write"})

    assert len(result) == 2
    assert result[0] == {"id": 1, "title": "Write report"}


async def test_tool_check_existing_tasks_vikunja_error():
    """VikunjaError in search_tasks → silent failure, return []."""
    extractor = TaskExtractor()
    with patch("app.services.extractor.vikunja") as mock_vk:
        mock_vk.search_tasks = AsyncMock(side_effect=VikunjaError("Connection refused"))
        result = await extractor._tool_handler("check_existing_tasks", {"title": "Write"})

    assert result == []


async def test_tool_unknown():
    extractor = TaskExtractor()
    result = await extractor._tool_handler("unknown_tool", {})
    assert "error" in result


# ── end-to-end extract() ──────────────────────────────────────────────────────

async def test_extract_saves_proposals(db):
    """Patch LLM + vikunja; verify proposals returned and persisted in DB."""
    tasks_json = json.dumps([
        {
            "title": "Write thesis chapter",
            "description": "Chapter 3 draft",
            "project_id": 1,
            "project_name": "PhD Research",
            "priority": 4,
            "due_date": "2026-03-15",
        }
    ])

    mock_llm = MagicMock()
    mock_llm.generate_with_tools = AsyncMock(return_value=tasks_json)

    with patch("app.services.extractor.get_llm_client", return_value=mock_llm), \
         patch("app.services.extractor.vikunja") as mock_vk, \
         patch("app.services.extractor.get_db", make_mock_db(db)):
        mock_vk.list_projects = AsyncMock(return_value=[])
        extractor = TaskExtractor()
        proposals = await extractor.extract("Write my thesis chapter", source_type="notes")

    assert len(proposals) == 1
    assert proposals[0].title == "Write thesis chapter"
    assert proposals[0].priority == 4

    # Verify persisted in the in-memory DB
    rows = db.execute("SELECT title, status FROM task_proposals").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Write thesis chapter"
    assert rows[0][1] == "pending"

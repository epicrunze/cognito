"""Tests for the /api/briefing Today endpoint."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.services.nudge_engine import NudgeEngine
from tests.conftest import make_mock_db

_TEST_USER = User(email="test@example.com", name="Test User")

NOW = datetime.now(timezone.utc)
NOON_TODAY = NOW.replace(hour=12, minute=0, second=0, microsecond=0)
NOON_YESTERDAY = NOON_TODAY - timedelta(days=1)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def make_task(id, title, due: datetime | None = None, done_at: datetime | None = None):
    return {
        "id": id,
        "title": title,
        "priority": 3,
        "done": done_at is not None,
        "due_date": _iso(due) if due else "0001-01-01T00:00:00Z",
        "done_at": _iso(done_at) if done_at else "0001-01-01T00:00:00Z",
    }


@pytest.fixture
def client(in_memory_db):
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    import app.routers.briefing as briefing_mod

    briefing_mod.get_db = make_mock_db(in_memory_db)
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()
    briefing_mod.get_db = __import__("app.database", fromlist=["get_db"]).get_db


@contextmanager
def patched_engine(open_tasks, done_tasks, llm_text="Today's briefing."):
    """Patch NudgeEngine (vikunja + calendar) and the LLM factory."""

    def list_tasks(filter=None, **kw):
        return list(done_tasks) if "done = true" in (filter or "") else list(open_tasks)

    def make_engine():
        eng = NudgeEngine()
        eng.vikunja = AsyncMock()
        eng.vikunja.list_tasks.side_effect = list_tasks
        eng._fetch_today_events = AsyncMock(return_value=[])
        return eng

    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=llm_text)
    with patch("app.routers.briefing.NudgeEngine", make_engine), patch(
        "app.services.llm.get_llm_client", return_value=llm
    ):
        yield llm


def test_get_briefing_returns_structured_lists(client):
    open_tasks = [
        make_task(1, "Due today", due=NOON_TODAY),
        make_task(2, "Overdue thing", due=NOON_YESTERDAY),
        make_task(3, "Important, no date"),
        make_task(6, "Also no date"),
    ]
    done_tasks = [
        make_task(4, "Done today", done_at=NOW),
        make_task(5, "Done long ago", done_at=NOW - timedelta(days=3)),
    ]
    with patched_engine(open_tasks, done_tasks, llm_text="Three things today."):
        res = client.get("/api/briefing")

    assert res.status_code == 200
    body = res.json()
    assert body["briefing_text"] == "Three things today."
    assert [t["id"] for t in body["due_today"]] == [1]
    assert [t["id"] for t in body["overdue"]] == [2]
    assert [t["id"] for t in body["undated"]] == [3, 6]  # dateless tasks still surface
    assert [t["id"] for t in body["done_today"]] == [4]  # 3-day-old excluded
    assert body["calendar"] == []


def test_get_briefing_caches_ai_line(client):
    with patched_engine([], []) as llm:
        client.get("/api/briefing")
        client.get("/api/briefing")
    # Second call serves the cached line — only one LLM generation.
    assert llm.generate.call_count == 1


def test_regenerate_forces_new_line(client):
    with patched_engine([], [], llm_text="First.") as llm:
        first = client.get("/api/briefing").json()
        assert first["briefing_text"] == "First."
        llm.generate.return_value = "Second."
        regen = client.post("/api/briefing/regenerate").json()

    assert regen["briefing_text"] == "Second."
    assert llm.generate.call_count == 2


def test_ai_line_failure_is_non_fatal(client):
    open_tasks = [make_task(1, "Due today", due=NOON_TODAY)]
    with patched_engine(open_tasks, []) as llm:
        llm.generate.side_effect = RuntimeError("LLM down")
        res = client.get("/api/briefing")

    assert res.status_code == 200
    body = res.json()
    assert body["briefing_text"] == ""  # fallback — lists still render
    assert [t["id"] for t in body["due_today"]] == [1]


def test_briefing_requires_auth(in_memory_db):
    import app.routers.briefing as briefing_mod

    briefing_mod.get_db = make_mock_db(in_memory_db)
    tc = TestClient(app)
    try:
        res = tc.get("/api/briefing")
        assert res.status_code == 401
    finally:
        briefing_mod.get_db = __import__("app.database", fromlist=["get_db"]).get_db

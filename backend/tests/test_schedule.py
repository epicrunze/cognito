"""Schedule endpoint tests — Google Calendar integration."""

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

_TEST_USER = User(email="test@example.com", name="Test User")


@pytest.fixture
def schedule_db():
    """In-memory DB with a test user that has a refresh token."""
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(conn)
    conn.execute(
        "INSERT INTO users (id, email, name, refresh_token) VALUES (?, ?, ?, ?)",
        ("user-1", "test@example.com", "Test User", "fake-refresh-token"),
    )
    return conn


@pytest.fixture
def mock_get_db(schedule_db):
    @contextmanager
    def _mock(database_path=None):
        yield schedule_db

    return _mock


@pytest.fixture
def client(mock_get_db):
    """TestClient wired to in-memory DB."""
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    with patch("app.routers.schedule.get_db", mock_get_db):
        tc = TestClient(app)
        yield tc
    app.dependency_overrides.clear()


def _patch_gcal(mock_refresh, gcal_method_name, mock_method):
    """Helper to patch refresh_access_token + a GoogleCalendarClient method."""
    from app.services.gcal import GoogleCalendarClient

    return (
        patch("app.routers.schedule.refresh_access_token", mock_refresh),
        patch.object(GoogleCalendarClient, gcal_method_name, mock_method),
    )


# ── list events ──────────────────────────────────────────────────────────────


def test_list_events_success(client):
    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})
    mock_list = AsyncMock(
        return_value=[
            {
                "id": "evt_1",
                "summary": "Standup",
                "start": "2026-03-27T09:00:00Z",
                "end": "2026-03-27T09:30:00Z",
                "description": None,
                "html_link": "https://calendar.google.com/event?eid=1",
            }
        ]
    )

    p1, p2 = _patch_gcal(mock_refresh, "list_events", mock_list)
    with p1, p2:
        resp = client.get(
            "/api/schedule",
            params={"time_min": "2026-03-27T00:00:00Z", "time_max": "2026-03-28T00:00:00Z"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["summary"] == "Standup"


def test_list_events_no_refresh_token(client, schedule_db):
    schedule_db.execute("UPDATE users SET refresh_token = NULL WHERE email = ?", ("test@example.com",))

    resp = client.get(
        "/api/schedule",
        params={"time_min": "2026-03-27T00:00:00Z", "time_max": "2026-03-28T00:00:00Z"},
    )
    assert resp.status_code == 401
    assert "refresh token" in resp.json()["detail"].lower()


def test_list_events_calendar_error_graceful(client):
    """When a calendar fails, we return 200 with empty events (graceful degradation)."""
    from app.services.gcal import GoogleCalendarError

    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})
    mock_list = AsyncMock(side_effect=GoogleCalendarError("API error"))

    p1, p2 = _patch_gcal(mock_refresh, "list_events", mock_list)
    with p1, p2:
        resp = client.get(
            "/api/schedule",
            params={"time_min": "2026-03-27T00:00:00Z", "time_max": "2026-03-28T00:00:00Z"},
        )
    assert resp.status_code == 200
    assert resp.json()["events"] == []


# ── create event ─────────────────────────────────────────────────────────────


def test_create_event_success(client):
    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})
    mock_create = AsyncMock(
        return_value={
            "id": "evt_new",
            "summary": "Focus time",
            "start": "2026-03-27T14:00:00Z",
            "end": "2026-03-27T15:00:00Z",
            "description": "Deep work",
            "html_link": "https://calendar.google.com/event?eid=new",
        }
    )

    p1, p2 = _patch_gcal(mock_refresh, "create_event", mock_create)
    with p1, p2:
        resp = client.post(
            "/api/schedule",
            json={
                "summary": "Focus time",
                "start": "2026-03-27T14:00:00Z",
                "end": "2026-03-27T15:00:00Z",
                "description": "Deep work",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "evt_new"
    assert data["summary"] == "Focus time"


def test_create_event_with_task_link(client, schedule_db):
    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})
    mock_create = AsyncMock(
        return_value={
            "id": "evt_linked",
            "summary": "Fix auth bug",
            "start": "2026-03-27T10:00:00Z",
            "end": "2026-03-27T11:00:00Z",
            "description": "",
            "html_link": None,
        }
    )

    p1, p2 = _patch_gcal(mock_refresh, "create_event", mock_create)
    with p1, p2:
        resp = client.post(
            "/api/schedule",
            json={
                "summary": "Fix auth bug",
                "start": "2026-03-27T10:00:00Z",
                "end": "2026-03-27T11:00:00Z",
                "task_id": 42,
            },
        )

    assert resp.status_code == 200
    assert resp.json()["task_id"] == 42

    # Verify link stored in DB
    row = schedule_db.execute(
        "SELECT task_id, gcal_event_id FROM task_calendar_links WHERE task_id = 42"
    ).fetchone()
    assert row is not None
    assert row[1] == "evt_linked"


# ── delete event ─────────────────────────────────────────────────────────────


def test_delete_event_success(client, schedule_db):
    schedule_db.execute(
        "INSERT INTO task_calendar_links (task_id, gcal_event_id) VALUES (?, ?)",
        (42, "evt_to_delete"),
    )

    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})
    mock_delete = AsyncMock(return_value=None)

    p1, p2 = _patch_gcal(mock_refresh, "delete_event", mock_delete)
    with p1, p2:
        resp = client.delete("/api/schedule/evt_to_delete")

    assert resp.status_code == 200
    assert resp.json()["success"] is True

    row = schedule_db.execute(
        "SELECT * FROM task_calendar_links WHERE gcal_event_id = 'evt_to_delete'"
    ).fetchone()
    assert row is None


# ── suggest ──────────────────────────────────────────────────────────────────


def test_suggest_schedule_success(client):
    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})
    mock_list = AsyncMock(
        return_value=[
            {
                "id": "evt_1",
                "summary": "Standup",
                "start": "2026-03-27T09:00:00Z",
                "end": "2026-03-27T09:30:00Z",
            }
        ]
    )
    mock_vikunja_tasks = AsyncMock(
        return_value=[
            {
                "id": 10,
                "title": "Fix auth bug",
                "priority": 5,
                "done": False,
                "start_date": "",
                "due_date": "",
                "estimated_minutes": 60,
            },
            {
                "id": 11,
                "title": "Write docs",
                "priority": 2,
                "done": False,
                "start_date": "",
                "due_date": "",
                "estimated_minutes": 30,
            },
        ]
    )
    llm_response = json.dumps(
        [
            {
                "task_id": 10,
                "task_title": "Fix auth bug",
                "suggested_start": "2026-03-27T10:00:00Z",
                "suggested_end": "2026-03-27T11:00:00Z",
                "reason": "High priority, morning slot for focus",
            },
            {
                "task_id": 11,
                "task_title": "Write docs",
                "suggested_start": "2026-03-27T14:00:00Z",
                "suggested_end": "2026-03-27T14:30:00Z",
                "reason": "Low priority, afternoon slot",
            },
        ]
    )
    mock_llm_client = AsyncMock()
    mock_llm_client.generate = AsyncMock(return_value=llm_response)

    from app.services.gcal import GoogleCalendarClient

    with (
        patch("app.routers.schedule.refresh_access_token", mock_refresh),
        patch.object(GoogleCalendarClient, "list_events", mock_list),
        patch("app.routers.schedule.VikunjaClient") as MockVikunja,
        patch("app.services.llm.get_llm_client", return_value=mock_llm_client),
    ):
        MockVikunja.return_value.list_tasks = mock_vikunja_tasks
        resp = client.get("/api/schedule/suggest", params={"date": "2026-03-27"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suggestions"]) == 2
    assert data["suggestions"][0]["task_id"] == 10
    assert data["suggestions"][1]["task_id"] == 11
    assert "2 time block" in data["summary"]


def test_suggest_schedule_no_tasks(client):
    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})
    mock_list = AsyncMock(return_value=[])
    mock_vikunja_tasks = AsyncMock(return_value=[])

    from app.services.gcal import GoogleCalendarClient

    with (
        patch("app.routers.schedule.refresh_access_token", mock_refresh),
        patch.object(GoogleCalendarClient, "list_events", mock_list),
        patch("app.routers.schedule.VikunjaClient") as MockVikunja,
    ):
        MockVikunja.return_value.list_tasks = mock_vikunja_tasks
        resp = client.get("/api/schedule/suggest", params={"date": "2026-03-27"})

    assert resp.status_code == 200
    assert len(resp.json()["suggestions"]) == 0


def test_suggest_schedule_invalid_date(client):
    resp = client.get("/api/schedule/suggest", params={"date": "not-a-date"})
    assert resp.status_code == 400


def test_suggest_schedule_llm_bad_json(client):
    """LLM returns unparseable response — should return empty suggestions, not 500."""
    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})
    mock_list = AsyncMock(return_value=[])
    mock_vikunja_tasks = AsyncMock(
        return_value=[{"id": 1, "title": "Task", "priority": 3, "start_date": "", "due_date": ""}]
    )
    mock_llm_client = AsyncMock()
    mock_llm_client.generate = AsyncMock(return_value="Sorry, I can't help with that.")

    from app.services.gcal import GoogleCalendarClient

    with (
        patch("app.routers.schedule.refresh_access_token", mock_refresh),
        patch.object(GoogleCalendarClient, "list_events", mock_list),
        patch("app.routers.schedule.VikunjaClient") as MockVikunja,
        patch("app.services.llm.get_llm_client", return_value=mock_llm_client),
    ):
        MockVikunja.return_value.list_tasks = mock_vikunja_tasks
        resp = client.get("/api/schedule/suggest", params={"date": "2026-03-27"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suggestions"]) == 0
    assert "failed" in data["summary"].lower()


# ── calendar selection ───────────────────────────────────────────────────────


def test_list_calendars(client):
    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})

    from app.services.gcal import GoogleCalendarClient

    mock_list_cals = AsyncMock(
        return_value=[
            {"id": "primary", "summary": "Personal", "background_color": "#4285f4", "primary": True},
            {"id": "work@group.calendar.google.com", "summary": "Work", "background_color": "#e67c73", "primary": False},
        ]
    )

    with (
        patch("app.routers.schedule.refresh_access_token", mock_refresh),
        patch.object(GoogleCalendarClient, "list_calendars", mock_list_cals),
    ):
        resp = client.get("/api/schedule/calendars")

    assert resp.status_code == 200
    cals = resp.json()["calendars"]
    assert len(cals) == 2
    assert cals[0]["id"] == "primary"
    assert cals[0]["primary"] is True
    assert cals[0]["enabled"] is False  # nothing selected yet


def test_update_and_list_calendars(client, schedule_db):
    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})

    from app.services.gcal import GoogleCalendarClient

    mock_list_cals = AsyncMock(
        return_value=[
            {"id": "primary", "summary": "Personal", "background_color": "#4285f4", "primary": True},
            {"id": "work@group.calendar.google.com", "summary": "Work", "background_color": "#e67c73", "primary": False},
        ]
    )

    with (
        patch("app.routers.schedule.refresh_access_token", mock_refresh),
        patch.object(GoogleCalendarClient, "list_calendars", mock_list_cals),
    ):
        # Select both calendars
        resp = client.put(
            "/api/schedule/calendars",
            json={"calendar_ids": ["primary", "work@group.calendar.google.com"]},
        )
        assert resp.status_code == 200

        # Verify they show as enabled
        resp = client.get("/api/schedule/calendars")
        cals = resp.json()["calendars"]
        assert all(c["enabled"] for c in cals)


def test_multi_calendar_list_events(client, schedule_db):
    """Events from multiple selected calendars are merged and sorted."""
    # Select two calendars
    schedule_db.execute(
        "INSERT INTO gcal_selected_calendars (calendar_id, summary, color) VALUES (?, ?, ?)",
        ("primary", "Personal", "#4285f4"),
    )
    schedule_db.execute(
        "INSERT INTO gcal_selected_calendars (calendar_id, summary, color) VALUES (?, ?, ?)",
        ("work@group.calendar.google.com", "Work", "#e67c73"),
    )

    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})

    from app.services.gcal import GoogleCalendarClient

    call_count = 0
    original_calendar_ids = []

    async def mock_list(self, time_min, time_max, max_results=100):
        nonlocal call_count
        original_calendar_ids.append(self.calendar_id)
        call_count += 1
        if self.calendar_id == "primary":
            return [{"id": "evt_1", "summary": "Personal event", "start": "2026-03-27T10:00:00Z", "end": "2026-03-27T11:00:00Z"}]
        return [{"id": "evt_2", "summary": "Work meeting", "start": "2026-03-27T09:00:00Z", "end": "2026-03-27T09:30:00Z"}]

    with (
        patch("app.routers.schedule.refresh_access_token", mock_refresh),
        patch.object(GoogleCalendarClient, "list_events", mock_list),
    ):
        resp = client.get(
            "/api/schedule",
            params={"time_min": "2026-03-27T00:00:00Z", "time_max": "2026-03-28T00:00:00Z"},
        )

    assert resp.status_code == 200
    events = resp.json()["events"]
    assert len(events) == 2
    assert call_count == 2
    # Should be sorted by start time — work meeting first
    assert events[0]["summary"] == "Work meeting"
    assert events[0]["calendar_color"] == "#e67c73"
    assert events[1]["summary"] == "Personal event"
    assert events[1]["calendar_color"] == "#4285f4"


# ── task-event links in list ─────────────────────────────────────────────────


def test_list_events_includes_task_links(client, schedule_db):
    """Events linked to tasks should have task_id populated."""
    schedule_db.execute(
        "INSERT INTO task_calendar_links (task_id, gcal_event_id) VALUES (?, ?)",
        (99, "evt_linked"),
    )

    mock_refresh = AsyncMock(return_value={"access_token": "fake-access"})
    mock_list = AsyncMock(
        return_value=[
            {
                "id": "evt_linked",
                "summary": "Linked event",
                "start": "2026-03-27T10:00:00Z",
                "end": "2026-03-27T11:00:00Z",
            },
            {
                "id": "evt_unlinked",
                "summary": "Unlinked event",
                "start": "2026-03-27T14:00:00Z",
                "end": "2026-03-27T15:00:00Z",
            },
        ]
    )

    p1, p2 = _patch_gcal(mock_refresh, "list_events", mock_list)
    with p1, p2:
        resp = client.get(
            "/api/schedule",
            params={"time_min": "2026-03-27T00:00:00Z", "time_max": "2026-03-28T00:00:00Z"},
        )

    assert resp.status_code == 200
    events = resp.json()["events"]
    linked = next(e for e in events if e["id"] == "evt_linked")
    unlinked = next(e for e in events if e["id"] == "evt_unlinked")
    assert linked["task_id"] == 99
    assert unlinked["task_id"] is None

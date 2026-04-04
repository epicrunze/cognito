"""
Router: /api/schedule

Google Calendar integration — list, create, delete events.
Also provides LLM-powered schedule suggestions.
Supports multiple calendars selected via /api/schedule/calendars.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user
from app.auth.oauth import OAuthRefreshError, refresh_access_token
from app.database import get_db
from app.models.schedule import (
    CalendarEvent,
    CalendarsResponse,
    CreateEventRequest,
    EventsResponse,
    GoogleCalendar,
    ScheduleSuggestion,
    SelectedCalendarsUpdate,
    SuggestResponse,
)
from app.models.user import User
from app.services.gcal import GoogleCalendarClient, GoogleCalendarError
from app.services.vikunja import VikunjaClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


async def _get_access_token(user: User, conn: sqlite3.Connection) -> str:
    """Get a fresh Google access token for the user."""
    row = conn.execute(
        "SELECT refresh_token FROM users WHERE email = ?", (user.email,)
    ).fetchone()
    if not row or not row[0]:
        raise HTTPException(
            status_code=401,
            detail="No Google refresh token found. Please re-login to grant calendar access.",
        )

    try:
        token_data = await refresh_access_token(row[0])
    except OAuthRefreshError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Failed to refresh Google token: {exc}. Please re-login.",
        )

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token in refresh response.")

    return access_token


def _get_selected_calendars(conn: sqlite3.Connection) -> list[dict]:
    """Get enabled calendars from DB. Returns list of {id, summary, color}."""
    rows = conn.execute(
        "SELECT calendar_id, summary, color FROM gcal_selected_calendars WHERE enabled = 1"
    ).fetchall()
    return [{"id": r[0], "summary": r[1], "color": r[2]} for r in rows]


async def _get_gcal_client(
    user: User, conn: sqlite3.Connection
) -> GoogleCalendarClient:
    """Build a GoogleCalendarClient using the user's stored refresh token."""
    access_token = await _get_access_token(user, conn)

    config_row = conn.execute(
        "SELECT gcal_calendar_id FROM agent_config WHERE id = 1"
    ).fetchone()
    calendar_id = (config_row[0] if config_row and config_row[0] else "primary")

    return GoogleCalendarClient(access_token=access_token, calendar_id=calendar_id)


def _enrich_events_with_task_links(
    events: list[dict], conn: sqlite3.Connection
) -> list[CalendarEvent]:
    """Add task_id to events that are linked to tasks."""
    rows = conn.execute("SELECT task_id, gcal_event_id FROM task_calendar_links").fetchall()
    link_map = {r[1]: r[0] for r in rows}

    result = []
    for e in events:
        result.append(
            CalendarEvent(
                id=e["id"],
                summary=e["summary"],
                start=e["start"],
                end=e["end"],
                description=e.get("description"),
                html_link=e.get("html_link"),
                task_id=link_map.get(e["id"]),
                calendar_id=e.get("calendar_id"),
                calendar_color=e.get("calendar_color"),
                calendar_name=e.get("calendar_name"),
            )
        )
    return result


async def _fetch_all_events(
    access_token: str,
    conn: sqlite3.Connection,
    time_min: str,
    time_max: str,
) -> list[dict]:
    """Fetch events from all selected calendars in parallel."""
    selected = _get_selected_calendars(conn)
    if not selected:
        selected = [{"id": "primary", "summary": "Primary", "color": "#4285f4"}]

    async def fetch_one(cal: dict) -> list[dict]:
        client = GoogleCalendarClient(access_token=access_token, calendar_id=cal["id"])
        try:
            events = await client.list_events(time_min, time_max)
            for e in events:
                e["calendar_id"] = cal["id"]
                e["calendar_color"] = cal["color"]
                e["calendar_name"] = cal["summary"]
            return events
        except GoogleCalendarError as exc:
            logger.warning("Failed to fetch calendar %s: %s", cal["id"], exc)
            return []

    results = await asyncio.gather(*[fetch_one(cal) for cal in selected])
    all_events = [e for batch in results for e in batch]
    all_events.sort(key=lambda e: e.get("start", ""))
    return all_events


# ── Calendar selection ──────────────────────────────────────────────────────


@router.get("/calendars", response_model=CalendarsResponse)
async def list_calendars(
    current_user: User = Depends(get_current_user),
):
    """List all Google Calendars the user has access to, with enabled state."""
    with get_db() as conn:
        access_token = await _get_access_token(current_user, conn)
        client = GoogleCalendarClient(access_token=access_token)

        try:
            raw_calendars = await client.list_calendars()
        except GoogleCalendarError as exc:
            logger.error("Failed to list calendars: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        enabled_ids = {
            r[0]
            for r in conn.execute(
                "SELECT calendar_id FROM gcal_selected_calendars WHERE enabled = 1"
            ).fetchall()
        }

        calendars = [
            GoogleCalendar(
                id=c["id"],
                summary=c["summary"],
                background_color=c["background_color"],
                primary=c["primary"],
                enabled=c["id"] in enabled_ids,
            )
            for c in raw_calendars
        ]
        return CalendarsResponse(calendars=calendars)


@router.put("/calendars")
async def update_calendars(
    body: SelectedCalendarsUpdate,
    current_user: User = Depends(get_current_user),
):
    """Save which calendars are selected for display."""
    with get_db() as conn:
        # Fetch calendar metadata from Google to store names/colors
        access_token = await _get_access_token(current_user, conn)
        client = GoogleCalendarClient(access_token=access_token)

        try:
            raw_calendars = await client.list_calendars()
        except GoogleCalendarError as exc:
            logger.error("Failed to list calendars: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        cal_map = {c["id"]: c for c in raw_calendars}
        selected_ids = set(body.calendar_ids)

        # Replace all rows
        conn.execute("DELETE FROM gcal_selected_calendars")
        for cal_id in selected_ids:
            cal = cal_map.get(cal_id)
            if cal:
                conn.execute(
                    "INSERT INTO gcal_selected_calendars (calendar_id, summary, color, enabled) VALUES (?, ?, ?, 1)",
                    (cal_id, cal["summary"], cal["background_color"]),
                )

        return {"success": True}


# ── Events ──────────────────────────────────────────────────────────────────


@router.get("", response_model=EventsResponse)
async def list_events(
    time_min: str = Query(..., description="RFC3339 start datetime"),
    time_max: str = Query(..., description="RFC3339 end datetime"),
    current_user: User = Depends(get_current_user),
):
    """List Google Calendar events from all selected calendars."""
    with get_db() as conn:
        access_token = await _get_access_token(current_user, conn)
        try:
            raw_events = await _fetch_all_events(access_token, conn, time_min, time_max)
        except GoogleCalendarError as exc:
            logger.error("Google Calendar API error: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        events = _enrich_events_with_task_links(raw_events, conn)
        return EventsResponse(events=events)


@router.post("", response_model=CalendarEvent)
async def create_event(
    body: CreateEventRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a Google Calendar event. Optionally link to a task."""
    with get_db() as conn:
        gcal = await _get_gcal_client(current_user, conn)
        try:
            event = await gcal.create_event(
                summary=body.summary,
                start=body.start,
                end=body.end,
                description=body.description,
            )
        except GoogleCalendarError as exc:
            logger.error("Google Calendar API error: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        # Link to task if requested
        if body.task_id and event.get("id"):
            conn.execute(
                "INSERT OR REPLACE INTO task_calendar_links (task_id, gcal_event_id, calendar_id) VALUES (?, ?, ?)",
                (body.task_id, event["id"], gcal.calendar_id),
            )

        return CalendarEvent(
            id=event["id"],
            summary=event["summary"],
            start=event["start"],
            end=event["end"],
            description=event.get("description"),
            html_link=event.get("html_link"),
            task_id=body.task_id,
        )


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a Google Calendar event and clean up any task link."""
    with get_db() as conn:
        gcal = await _get_gcal_client(current_user, conn)
        try:
            await gcal.delete_event(event_id)
        except GoogleCalendarError as exc:
            logger.error("Google Calendar API error: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        conn.execute(
            "DELETE FROM task_calendar_links WHERE gcal_event_id = ?", (event_id,)
        )
        return {"success": True}


@router.get("/suggest", response_model=SuggestResponse)
async def suggest_schedule(
    date: str = Query(..., description="ISO date, e.g. 2026-03-27"),
    current_user: User = Depends(get_current_user),
):
    """LLM suggests time blocks for unscheduled tasks given existing calendar events."""
    try:
        day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    day_start = day.replace(hour=6, minute=0, second=0).isoformat()
    day_end = day.replace(hour=22, minute=0, second=0).isoformat()

    with get_db() as conn:
        access_token = await _get_access_token(current_user, conn)
        try:
            cal_events = await _fetch_all_events(access_token, conn, day_start, day_end)
        except GoogleCalendarError as exc:
            logger.error("Google Calendar API error: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

    # 2. Fetch open tasks from Vikunja (unscheduled, not done)
    vikunja = VikunjaClient()
    try:
        all_tasks = await vikunja.list_tasks(
            filter="done = false",
            sort_by="priority",
            order_by="desc",
            per_page=50,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vikunja error: {exc}")

    # Filter to unscheduled or due-today tasks
    unscheduled = []
    for t in all_tasks:
        start = t.get("start_date") or ""
        if start.startswith("0001-01-01") or not start:
            unscheduled.append(t)
        else:
            due = t.get("due_date") or ""
            if due.startswith(date):
                unscheduled.append(t)

    if not unscheduled:
        return SuggestResponse(
            suggestions=[],
            summary="No unscheduled tasks to suggest time blocks for.",
        )

    # 3. Build LLM prompt
    busy_blocks = "\n".join(
        f"- {e['summary']}: {e['start']} to {e['end']}" for e in cal_events
    ) or "No existing events."

    task_list = "\n".join(
        f"- [ID:{t['id']}] {t['title']} (priority: {t.get('priority', 3)}, "
        f"est: {t.get('estimated_minutes') or '?'}min)"
        for t in unscheduled[:15]
    )

    prompt = f"""You are a scheduling assistant. Given the user's existing calendar events and unscheduled tasks, suggest optimal time blocks for each task on {date}.

## Existing calendar events (busy times):
{busy_blocks}

## Available hours: 6:00 AM to 10:00 PM

## Unscheduled tasks (sorted by priority, highest first):
{task_list}

## Rules:
- Never overlap with existing events. Leave 15-minute buffers between events.
- High priority tasks (4-5) should go in morning slots when focus is best.
- If estimated_minutes is unknown, assume 60 minutes.
- Suggest realistic blocks — not more than 6 hours of focused work total.
- Return ONLY valid JSON array, no other text.

## Response format (JSON array):
[
  {{"task_id": 123, "task_title": "Task name", "suggested_start": "2026-03-27T09:00:00Z", "suggested_end": "2026-03-27T10:00:00Z", "reason": "Brief reason"}}
]"""

    # 4. Call LLM
    from app.services.llm import get_llm_client

    llm = get_llm_client()
    try:
        response_text = await llm.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a scheduling assistant. Respond only with valid JSON.",
        )
    except Exception as exc:
        logger.error("LLM suggest failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    # 5. Parse response
    try:
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        raw_suggestions = json.loads(text)
        suggestions = [
            ScheduleSuggestion(
                task_id=s["task_id"],
                task_title=s["task_title"],
                suggested_start=s["suggested_start"],
                suggested_end=s["suggested_end"],
                reason=s.get("reason", ""),
            )
            for s in raw_suggestions
        ]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse LLM suggestions: %s\nRaw: %s", exc, response_text)
        return SuggestResponse(
            suggestions=[],
            summary="Failed to parse scheduling suggestions. Try again.",
        )

    summary = f"Suggested {len(suggestions)} time block(s) for {date}."
    return SuggestResponse(suggestions=suggestions, summary=summary)

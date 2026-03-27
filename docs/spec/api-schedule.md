# API: Schedule (Google Calendar)

> **Note:** This feature is fully implemented but requires Google Calendar OAuth scopes. The user must have a valid Google refresh token stored (granted during login).

## GET /api/schedule?time_min=...&time_max=...

List Google Calendar events in a date range. Both params are required RFC 3339 datetimes. Events are enriched with `task_id` if a Vikunja task is linked.

```json
{
  "events": [
    {
      "id": "gcal_event_id", "summary": "Meeting", "start": "...", "end": "...",
      "description": null, "html_link": "https://calendar.google.com/...", "task_id": 42
    }
  ]
}
```

## POST /api/schedule

Create a Google Calendar event. Optionally link it to a Vikunja task.

```json
{
  "summary": "Work on report",
  "start": "2026-03-27T09:00:00Z",
  "end": "2026-03-27T10:00:00Z",
  "description": "optional",
  "task_id": 42
}
```

Returns the created `CalendarEvent`.

## DELETE /api/schedule/{event_id}

Delete a Google Calendar event and remove any task link. Returns `{"success": true}`.

## GET /api/schedule/suggest?date=2026-03-27

LLM-powered scheduling assistant. Given a date, it:

1. Fetches existing calendar events for the 6 AM -- 10 PM window
2. Fetches unscheduled/due-today tasks from Vikunja (up to 50, sorted by priority)
3. Asks the LLM to suggest optimal time blocks avoiding conflicts

```json
{
  "suggestions": [
    {
      "task_id": 42, "task_title": "Write report",
      "suggested_start": "2026-03-27T09:00:00Z",
      "suggested_end": "2026-03-27T10:00:00Z",
      "reason": "High priority, scheduled in morning focus block"
    }
  ],
  "summary": "Suggested 3 time block(s) for 2026-03-27."
}
```

Rules the LLM follows: 15-minute buffers between events, high-priority tasks in morning slots, 60-minute default for unknown estimates, max 6 hours of focused work.

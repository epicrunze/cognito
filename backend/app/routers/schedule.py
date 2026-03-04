"""
Router: /api/schedule

Google Calendar integration (Phase 3, Spec §3.5).
Reads calendar events and surfaces them alongside tasks for unified scheduling.

TODO:
- GET /api/schedule — list upcoming events (date range query params)
- GET /api/schedule/{event_id} — get single event
- POST /api/schedule/sync — trigger manual calendar sync
- GET /api/schedule/free-slots — find free time blocks for task scheduling
- OAuth flow for Google Calendar token (separate from login OAuth)
"""

# TODO: Implement schedule router (Phase 3)

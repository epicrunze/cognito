"""
Service: Google Calendar client (Phase 3, Spec §3.5)

Fetches calendar events using the Google Calendar API v3.
Uses per-user OAuth tokens stored in the database (separate from login OAuth).

TODO:
- GoogleCalendarClient class with httpx async client
- get_events(user_id, time_min, time_max) — list events in date range
- get_free_busy(user_id, time_min, time_max) — check availability
- OAuth token refresh logic (access token expires, use refresh token)
- Store/retrieve tokens via database (encrypt at rest)
- Handle calendar pagination (nextPageToken)
"""

# TODO: Implement GoogleCalendarClient (Phase 3)

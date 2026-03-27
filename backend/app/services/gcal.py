"""
Google Calendar API v3 client.

Uses httpx async, follows the same pattern as VikunjaClient.
Token management is external — the caller provides a fresh access_token.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GoogleCalendarError(Exception):
    """Base error for Google Calendar API failures."""


class GoogleCalendarClient:
    """Async httpx client for Google Calendar API v3."""

    BASE = "https://www.googleapis.com/calendar/v3"

    def __init__(self, access_token: str, calendar_id: str = "primary"):
        self.access_token = access_token
        self.calendar_id = calendar_id

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """Authenticated request to Calendar API."""
        url = f"{self.BASE}{path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.request(
                    method, url, headers=self._headers, **kwargs
                )
                if not response.is_success:
                    detail = response.text
                    try:
                        body = response.json()
                        if isinstance(body, dict) and "error" in body:
                            err = body["error"]
                            detail = err.get("message", detail) if isinstance(err, dict) else str(err)
                    except Exception:
                        pass
                    raise GoogleCalendarError(
                        f"{method} {path} failed ({response.status_code}): {detail}"
                    )
                # DELETE returns 204 No Content
                if response.status_code == 204:
                    return {}
                return response.json()
        except GoogleCalendarError:
            raise
        except httpx.HTTPError as exc:
            raise GoogleCalendarError(f"{method} {path} failed: {exc}") from exc

    def _parse_event(self, raw: dict) -> dict:
        """Normalize a Google Calendar event into our standard shape."""
        start = raw.get("start", {})
        end = raw.get("end", {})
        return {
            "id": raw.get("id", ""),
            "summary": raw.get("summary", "(No title)"),
            "start": start.get("dateTime") or start.get("date", ""),
            "end": end.get("dateTime") or end.get("date", ""),
            "description": raw.get("description"),
            "html_link": raw.get("htmlLink"),
        }

    async def list_events(
        self,
        time_min: str,
        time_max: str,
        max_results: int = 100,
    ) -> list[dict]:
        """List events in a date range. time_min/time_max are RFC3339."""
        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        data = await self._request(
            "GET", f"/calendars/{self.calendar_id}/events", params=params
        )
        items = data.get("items", [])
        return [self._parse_event(e) for e in items]

    async def create_event(
        self,
        summary: str,
        start: str,
        end: str,
        description: str = "",
    ) -> dict:
        """Create a calendar event. start/end are RFC3339 datetimes."""
        body = {
            "summary": summary,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }
        if description:
            body["description"] = description
        raw = await self._request(
            "POST", f"/calendars/{self.calendar_id}/events", json=body
        )
        return self._parse_event(raw)

    async def update_event(self, event_id: str, **fields) -> dict:
        """Update event fields (summary, start, end, description)."""
        body: dict = {}
        if "summary" in fields:
            body["summary"] = fields["summary"]
        if "description" in fields:
            body["description"] = fields["description"]
        if "start" in fields:
            body["start"] = {"dateTime": fields["start"]}
        if "end" in fields:
            body["end"] = {"dateTime": fields["end"]}
        raw = await self._request(
            "PATCH", f"/calendars/{self.calendar_id}/events/{event_id}", json=body
        )
        return self._parse_event(raw)

    async def delete_event(self, event_id: str) -> None:
        """Delete a calendar event."""
        await self._request(
            "DELETE", f"/calendars/{self.calendar_id}/events/{event_id}"
        )

    async def get_free_busy(self, time_min: str, time_max: str) -> list[dict]:
        """Get busy time ranges. Returns list of {start, end} dicts."""
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": self.calendar_id}],
        }
        data = await self._request("POST", "/freeBusy", json=body)
        calendars = data.get("calendars", {})
        cal_data = calendars.get(self.calendar_id, {})
        return cal_data.get("busy", [])

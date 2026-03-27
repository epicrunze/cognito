"""
Pydantic models: Schedule / Google Calendar integration.
"""

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    id: str
    summary: str
    start: str  # ISO datetime
    end: str  # ISO datetime
    description: str | None = None
    html_link: str | None = None
    task_id: int | None = None  # linked Cognito task


class CreateEventRequest(BaseModel):
    summary: str
    start: str  # ISO datetime
    end: str  # ISO datetime
    description: str = ""
    task_id: int | None = None


class EventsResponse(BaseModel):
    events: list[CalendarEvent]


class ScheduleSuggestion(BaseModel):
    task_id: int
    task_title: str
    suggested_start: str  # ISO datetime
    suggested_end: str  # ISO datetime
    reason: str


class SuggestResponse(BaseModel):
    suggestions: list[ScheduleSuggestion]
    summary: str

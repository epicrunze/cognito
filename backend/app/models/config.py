"""
Pydantic models: AgentConfig

Represents per-user agent configuration stored in the `agent_config` table.
"""

import zoneinfo

from pydantic import BaseModel, Field, field_validator


class AgentConfigResponse(BaseModel):
    default_project_id: int | None = None
    ollama_model: str | None = None
    gemini_model: str | None = None
    gcal_calendar_id: str | None = None
    system_prompt_override: str | None = None
    base_prompt_override: str | None = None
    schedule_weekday_start: int = 8
    schedule_weekday_end: int = 18
    schedule_weekend_start: int = 10
    schedule_weekend_end: int = 16
    schedule_weekend_enabled: bool = True
    notif_digest_enabled: bool = True
    notif_reminders_enabled: bool = True
    notif_nudges_enabled: bool = True
    notif_review_enabled: bool = True
    notif_digest_time: str = "08:00"
    notif_review_time: str = "21:00"
    notif_max_per_day: int = 5
    notif_max_nudges_per_day: int = 2
    notif_reminder_lead_hours: int = 2
    notif_quiet_start: int = 22
    notif_quiet_end: int = 7
    notif_nudge_runs_per_day: int = 3
    notif_timezone: str = "UTC"


class AgentConfigUpdate(BaseModel):
    default_project_id: int | None = None
    ollama_model: str | None = None
    gemini_model: str | None = None
    gcal_calendar_id: str | None = None
    system_prompt_override: str | None = None
    base_prompt_override: str | None = None
    schedule_weekday_start: int | None = None
    schedule_weekday_end: int | None = None
    schedule_weekend_start: int | None = None
    schedule_weekend_end: int | None = None
    schedule_weekend_enabled: bool | None = None
    notif_digest_enabled: bool | None = None
    notif_reminders_enabled: bool | None = None
    notif_nudges_enabled: bool | None = None
    notif_review_enabled: bool | None = None
    notif_digest_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    notif_review_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    notif_max_per_day: int | None = Field(default=None, ge=0, le=50)
    notif_max_nudges_per_day: int | None = Field(default=None, ge=0, le=20)
    notif_reminder_lead_hours: int | None = Field(default=None, ge=0, le=24)
    notif_quiet_start: int | None = Field(default=None, ge=0, le=23)
    notif_quiet_end: int | None = Field(default=None, ge=0, le=23)
    notif_nudge_runs_per_day: int | None = Field(default=None, ge=0, le=12)
    notif_timezone: str | None = None

    @field_validator("notif_timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                zoneinfo.ZoneInfo(v)
            except (zoneinfo.ZoneInfoNotFoundError, KeyError):
                raise ValueError("Unknown timezone")
        return v

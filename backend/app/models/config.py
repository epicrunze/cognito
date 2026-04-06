"""
Pydantic models: AgentConfig

Represents per-user agent configuration stored in the `agent_config` table.
"""

from pydantic import BaseModel


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

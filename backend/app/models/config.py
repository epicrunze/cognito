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


class AgentConfigUpdate(BaseModel):
    default_project_id: int | None = None
    ollama_model: str | None = None
    gemini_model: str | None = None
    gcal_calendar_id: str | None = None
    system_prompt_override: str | None = None

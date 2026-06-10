"""
Router: /api/config

Read and update agent configuration (singleton row).
"""

from datetime import date

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.config import AgentConfigResponse, AgentConfigUpdate
from app.models.user import User
from app.services.agent import AGENT_SYSTEM_PROMPT, MODIFICATION_TOOLS
from app.services.extractor import EXTRACTION_TOOLS

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=AgentConfigResponse)
async def get_config(current_user: User = Depends(get_current_user)):
    """Return the singleton agent_config row."""
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM agent_config WHERE id = 1")
        row = cur.fetchone()
        if not row:
            return AgentConfigResponse()
        data = dict(zip([c[0] for c in cur.description], row))

    return AgentConfigResponse(
        default_project_id=data.get("default_project_id"),
        ollama_model=data.get("ollama_model"),
        gemini_model=data.get("gemini_model"),
        gcal_calendar_id=data.get("gcal_calendar_id"),
        system_prompt_override=data.get("system_prompt_override"),
        base_prompt_override=data.get("base_prompt_override"),
        schedule_weekday_start=data.get("schedule_weekday_start") or 8,
        schedule_weekday_end=data.get("schedule_weekday_end") or 18,
        schedule_weekend_start=data.get("schedule_weekend_start") or 10,
        schedule_weekend_end=data.get("schedule_weekend_end") or 16,
        schedule_weekend_enabled=bool(data.get("schedule_weekend_enabled"))
        if data.get("schedule_weekend_enabled") is not None
        else True,
        notif_digest_enabled=bool(data.get("notif_digest_enabled"))
        if data.get("notif_digest_enabled") is not None
        else True,
        notif_reminders_enabled=bool(data.get("notif_reminders_enabled"))
        if data.get("notif_reminders_enabled") is not None
        else True,
        notif_nudges_enabled=bool(data.get("notif_nudges_enabled"))
        if data.get("notif_nudges_enabled") is not None
        else True,
        notif_review_enabled=bool(data.get("notif_review_enabled"))
        if data.get("notif_review_enabled") is not None
        else True,
        notif_digest_time=data.get("notif_digest_time") or "08:00",
        notif_review_time=data.get("notif_review_time") or "21:00",
        notif_max_per_day=data.get("notif_max_per_day")
        if data.get("notif_max_per_day") is not None
        else 5,
        notif_max_nudges_per_day=data.get("notif_max_nudges_per_day")
        if data.get("notif_max_nudges_per_day") is not None
        else 2,
        notif_reminder_lead_hours=data.get("notif_reminder_lead_hours")
        if data.get("notif_reminder_lead_hours") is not None
        else 2,
        notif_quiet_start=data.get("notif_quiet_start")
        if data.get("notif_quiet_start") is not None
        else 22,
        notif_quiet_end=data.get("notif_quiet_end")
        if data.get("notif_quiet_end") is not None
        else 7,
        notif_nudge_runs_per_day=data.get("notif_nudge_runs_per_day")
        if data.get("notif_nudge_runs_per_day") is not None
        else 3,
        notif_timezone=data.get("notif_timezone") or "UTC",
    )


@router.put("", response_model=AgentConfigResponse)
async def update_config(
    body: AgentConfigUpdate,
    current_user: User = Depends(get_current_user),
):
    """Partial update of agent config — only provided fields are updated."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return await get_config(current_user)

    set_clauses = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [1]

    with get_db() as conn:
        conn.execute(
            f"UPDATE agent_config SET {set_clauses} WHERE id = ?",
            values,
        )

    return await get_config(current_user)


@router.get("/system-prompt")
async def get_system_prompt(current_user: User = Depends(get_current_user)):
    """Return the formatted agent system prompt with today's date."""
    today = date.today().isoformat()

    # Check for base_prompt_override in agent_config
    base_prompt = AGENT_SYSTEM_PROMPT
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT base_prompt_override FROM agent_config WHERE id = 1"
            ).fetchone()
            if row and row[0]:
                base_prompt = row[0]
    except Exception:
        pass

    formatted = base_prompt.format(today=today)
    return {"prompt": formatted}


@router.get("/tools")
async def get_tools(current_user: User = Depends(get_current_user)):
    """Return the full list of extraction + modification tools."""
    return {"tools": EXTRACTION_TOOLS + MODIFICATION_TOOLS}

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
        row = conn.execute(
            "SELECT default_project_id, ollama_model, gemini_model, gcal_calendar_id, system_prompt_override, base_prompt_override "
            "FROM agent_config WHERE id = 1"
        ).fetchone()
    if not row:
        return AgentConfigResponse()
    return AgentConfigResponse(
        default_project_id=row[0],
        ollama_model=row[1],
        gemini_model=row[2],
        gcal_calendar_id=row[3],
        system_prompt_override=row[4],
        base_prompt_override=row[5],
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

"""
Router: /api/briefing

The "Today" briefing page: an AI-authored line (shared with the morning digest
notification, cached per day) plus today's structured task and calendar lists.
This is the in-app landing spot for digest / review / nudge notification clicks.
"""

import logging

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.notifications import get_local_now, load_notif_config
from app.services.nudge_engine import NudgeEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


async def _build(force_regen: bool) -> dict:
    engine = NudgeEngine()
    with get_db() as conn:
        cfg = load_notif_config(conn)
        local_now = get_local_now(cfg)
        return await engine.build_briefing(
            conn, cfg, local_now, force_regen=force_regen
        )


@router.get("")
async def get_briefing(current_user: User = Depends(get_current_user)):
    """Today's briefing — AI line (cached) + due-today / overdue / done-today / calendar."""
    return await _build(force_regen=False)


@router.post("/regenerate")
async def regenerate_briefing(current_user: User = Depends(get_current_user)):
    """Force a fresh AI briefing line for today, replacing the cached one."""
    return await _build(force_regen=True)

"""
Router: /api/notifications

Web Push subscription management + test send.
Settings live on /api/config (agent_config notif_* columns).
"""

import logging

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.models.notifications import PushSubscriptionRequest, UnsubscribeRequest
from app.models.user import User
from app.services.notifications import NotificationService, load_notif_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/vapid-public-key")
async def vapid_public_key(current_user: User = Depends(get_current_user)):
    """Public VAPID key the browser needs to subscribe."""
    return {"public_key": settings.vapid_public_key}


@router.post("/subscribe")
async def subscribe(
    body: PushSubscriptionRequest,
    current_user: User = Depends(get_current_user),
):
    """Store (or refresh) a push subscription for this browser/device."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO push_subscriptions (user_email, endpoint, p256dh, auth) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(endpoint) DO UPDATE SET p256dh = excluded.p256dh, auth = excluded.auth",
            (current_user.email, body.endpoint, body.keys.p256dh, body.keys.auth),
        )
    return {"success": True}


@router.delete("/subscribe")
async def unsubscribe(
    body: UnsubscribeRequest,
    current_user: User = Depends(get_current_user),
):
    """Remove a push subscription."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM push_subscriptions WHERE endpoint = ?", (body.endpoint,)
        )
    return {"success": True}


@router.post("/test")
async def send_test_notification(current_user: User = Depends(get_current_user)):
    """Send a test push, bypassing caps/quiet hours. Returns success=False if no subscriptions."""
    svc = NotificationService()
    with get_db() as conn:
        cfg = load_notif_config(conn)
        delivered = await svc.send(
            conn,
            cfg,
            type="test",
            title="Cognito test notification",
            body="Push notifications are working 🎉",
            bypass_guardrails=True,
        )
    return {"success": delivered}

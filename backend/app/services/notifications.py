"""
NotificationService — the single choke point for Web Push sends.

Every notification flows through send(), which enforces (unless bypassed):
  - quiet hours (in the user's configured timezone)
  - daily total cap and daily nudge cap (counted as pushes, not log rows)
  - logging to notification_log (one row per task_id for dedup; one row
    with NULL task_id when the notification isn't task-linked)

Dead subscriptions (HTTP 404/410 from the push service) are pruned.
pywebpush is synchronous — calls are wrapped in asyncio.to_thread.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pywebpush import WebPushException, webpush

from app.config import settings

logger = logging.getLogger(__name__)

NOTIF_DEFAULTS = {
    "notif_digest_enabled": 1,
    "notif_reminders_enabled": 1,
    "notif_nudges_enabled": 1,
    "notif_review_enabled": 1,
    "notif_digest_time": "08:00",
    "notif_review_time": "21:00",
    "notif_max_per_day": 5,
    "notif_max_nudges_per_day": 2,
    "notif_reminder_lead_hours": 2,
    "notif_quiet_start": 22,
    "notif_quiet_end": 7,
    "notif_nudge_runs_per_day": 3,
    "notif_timezone": "UTC",
}


def load_notif_config(conn: sqlite3.Connection) -> dict:
    """Read the notif_* columns from the singleton agent_config row."""
    cur = conn.execute("SELECT * FROM agent_config WHERE id = 1")
    row = cur.fetchone()
    if not row:
        return dict(NOTIF_DEFAULTS)
    data = dict(zip([c[0] for c in cur.description], row))
    cfg = {}
    for key, default in NOTIF_DEFAULTS.items():
        value = data.get(key)
        cfg[key] = default if value is None else value
    return cfg


def get_local_now(cfg: dict, now: datetime | None = None) -> datetime:
    """Current time in the user's configured timezone."""
    assert now is None or now.tzinfo is not None, "now must be timezone-aware"
    base = now or datetime.now(timezone.utc)
    try:
        tz = ZoneInfo(cfg.get("notif_timezone") or "UTC")
    except Exception:
        tz = timezone.utc
    return base.astimezone(tz)


def in_quiet_hours(local_now: datetime, cfg: dict) -> bool:
    """Quiet window spans quiet_start → quiet_end overnight. start == end → never quiet."""
    start = cfg["notif_quiet_start"]
    end = cfg["notif_quiet_end"]
    if start == end:
        return False
    hour = local_now.hour
    if start > end:  # overnight window, e.g. 22 → 7
        return hour >= start or hour < end
    return start <= hour < end


def local_day_start_utc(local_now: datetime) -> str:
    """UTC ISO timestamp for midnight (local) of the given local datetime."""
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return day_start.astimezone(timezone.utc).isoformat()


def pushes_sent_since(conn: sqlite3.Connection, since_utc_iso: str, type: str | None = None) -> int:
    """Count distinct pushes (a batch logs N rows but is one push).

    Test sends (type='test') are excluded from the untyped total so that
    bypassed test pushes do not consume the user's daily cap.
    """
    if type:
        # type is pinned by the WHERE clause, so DISTINCT sent_at is sufficient
        row = conn.execute(
            "SELECT COUNT(DISTINCT sent_at) FROM notification_log "
            "WHERE sent_at >= ? AND type = ?",
            (since_utc_iso, type),
        ).fetchone()
    else:
        # Separate types with a delimiter to avoid false collisions (e.g.
        # sent_at="...1" + type="nudge" vs sent_at="...1n" + type="udge").
        # Exclude type='test' so test pushes don't consume the daily cap.
        row = conn.execute(
            "SELECT COUNT(DISTINCT sent_at || '|' || type) FROM notification_log "
            "WHERE sent_at >= ? AND type != 'test'",
            (since_utc_iso,),
        ).fetchone()
    return row[0]


class NotificationService:
    """Sends Web Push notifications to all stored subscriptions."""

    async def send(
        self,
        conn: sqlite3.Connection,
        cfg: dict,
        *,
        type: str,
        title: str,
        body: str,
        task_ids: list[int] | None = None,
        bypass_guardrails: bool = False,
        now: datetime | None = None,
    ) -> bool:
        """Send one push to every subscription. Returns True if any delivery succeeded."""
        assert now is None or now.tzinfo is not None, "now must be timezone-aware"
        local_now = get_local_now(cfg, now)

        # NOTE: the check-then-send sequence below is not atomic.  This is
        # intentional and accepted: callers are a single sequential scheduler
        # plus the /test endpoint (which bypasses guardrails).  If a new
        # concurrent guarded caller is added in the future, hold an
        # asyncio.Lock across the check+send to prevent races.
        if not bypass_guardrails:
            if in_quiet_hours(local_now, cfg):
                logger.info("Notification suppressed (quiet hours): %s", title)
                return False
            day_start = local_day_start_utc(local_now)
            if pushes_sent_since(conn, day_start) >= cfg["notif_max_per_day"]:
                logger.info("Notification suppressed (daily cap): %s", title)
                return False
            if (
                type == "nudge"
                and pushes_sent_since(conn, day_start, type="nudge")
                >= cfg["notif_max_nudges_per_day"]
            ):
                logger.info("Nudge suppressed (nudge cap): %s", title)
                return False

        subs = conn.execute(
            "SELECT id, endpoint, p256dh, auth FROM push_subscriptions"
        ).fetchall()
        if not subs:
            return False

        payload = json.dumps(
            {
                "title": title,
                "body": body,
                "type": type,
                "task_id": (task_ids or [None])[0],
            }
        )

        delivered = False
        for sub_id, endpoint, p256dh, auth in subs:
            try:
                await asyncio.to_thread(
                    webpush,
                    subscription_info={
                        "endpoint": endpoint,
                        "keys": {"p256dh": p256dh, "auth": auth},
                    },
                    data=payload,
                    vapid_private_key=settings.vapid_private_key,
                    vapid_claims={"sub": settings.vapid_subject},
                )
                delivered = True
            except WebPushException as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in (404, 410):
                    conn.execute(
                        "DELETE FROM push_subscriptions WHERE id = ?", (sub_id,)
                    )
                    logger.info("Pruned dead push subscription %s", endpoint)
                else:
                    logger.warning("Push send failed (%s): %s", endpoint, exc)
            except Exception as exc:
                logger.warning("Push send failed (%s): %s", endpoint, exc)

        if delivered:
            sent_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
            for tid in task_ids or [None]:
                conn.execute(
                    "INSERT INTO notification_log (type, task_id, title, body, sent_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (type, tid, title, body, sent_at),
                )
        return delivered

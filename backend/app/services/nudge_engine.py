"""
NudgeEngine — background notification scheduler.

An asyncio task (started from the FastAPI lifespan) ticks once a minute.
Each tick evaluates four triggers in the user's configured timezone:

  - Morning digest   : LLM-authored briefing at notif_digest_time
  - Evening review   : completed-vs-open template at notif_review_time
  - Reminder sweep   : due-soon / newly-overdue tasks, every 15 minutes
  - Nudge evaluation : LLM decides whether anything is worth a nudge,
                       at evenly spaced slots across the waking window

Last-run state lives in the scheduler_state table so restarts neither
double-fire nor skip. Fixed-time triggers fire up to FIRE_WINDOW_HOURS
late (covers restarts) but never twice in a day. Every trigger body is
wrapped so one failure can't kill the loop; a missed nudge is fine, a
crash loop is not.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.services.notifications import (
    NotificationService,
    get_local_now,
    in_quiet_hours,
    load_notif_config,
)
from app.services.vikunja import VikunjaClient

logger = logging.getLogger(__name__)

TICK_SECONDS = 60
REMINDER_SWEEP_MINUTES = 15
FIRE_WINDOW_HOURS = 3
OVERDUE_LOOKBACK_HOURS = 48  # only "newly overdue" tasks get reminders
TASK_DEDUP_HOURS = 24


# ── scheduler_state helpers ──────────────────────────────────────────────────


def get_state(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM scheduler_state WHERE key = ?", (key,)
    ).fetchone()
    return row[0] if row else None


def set_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO scheduler_state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


# ── trigger gating ───────────────────────────────────────────────────────────


def due_slot_date(local_now: datetime, hhmm: str) -> str | None:
    """ISO date of the scheduled slot if local_now is within its fire window, else None.

    Checks today's and yesterday's slot — a late-evening schedule's window can
    cross midnight, in which case the slot date is yesterday.
    """
    try:
        hour, minute = (int(p) for p in hhmm.split(":"))
        target = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except (ValueError, AttributeError):
        return None
    for candidate in (target, target - timedelta(days=1)):
        if candidate <= local_now < candidate + timedelta(hours=FIRE_WINDOW_HOURS):
            return candidate.date().isoformat()
    return None


def fixed_time_due(local_now: datetime, hhmm: str) -> bool:
    """True if local_now is within [scheduled time, scheduled + FIRE_WINDOW_HOURS)."""
    return due_slot_date(local_now, hhmm) is not None


def nudge_slot_hours(cfg: dict) -> list[int]:
    """Evenly spaced hours across the waking window (quiet_end → quiet_start).

    Slots are clamped to stay strictly inside the waking window (never landing
    on quiet_start itself) and deduplicated while preserving insertion order.
    span is always at least 1 because span == 0 is replaced by 24.
    """
    runs = cfg["notif_nudge_runs_per_day"]
    if runs <= 0:
        return []
    start = cfg["notif_quiet_end"]
    span = (cfg["notif_quiet_start"] - start) % 24
    if span == 0:
        span = 24
    slots: list[int] = []
    for i in range(runs):
        offset = min(round(span * (i + 1) / (runs + 1)), span - 1)
        h = (start + offset) % 24
        if h not in slots:
            slots.append(h)
    return slots


# ── reminder sweep helpers ───────────────────────────────────────────────────


def _truncate(text: str, limit: int = 60) -> str:
    return text[:limit]


def parse_vikunja_date(value: str | None) -> datetime | None:
    """Vikunja uses '0001-01-01...' as the unset sentinel.

    Naive datetimes (no UTC offset) are assumed UTC to prevent TypeError when
    comparing with timezone-aware datetimes in the sweep window calculation.
    """
    if not value or value.startswith("0001-01-01"):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def recently_notified_task_ids(conn: sqlite3.Connection, now_utc: datetime) -> set[int]:
    cutoff = (now_utc - timedelta(hours=TASK_DEDUP_HOURS)).isoformat()
    rows = conn.execute(
        "SELECT DISTINCT task_id FROM notification_log "
        "WHERE task_id IS NOT NULL AND sent_at >= ?",
        (cutoff,),
    ).fetchall()
    return {r[0] for r in rows}


class NudgeEngine:
    def __init__(self):
        self.vikunja = VikunjaClient()
        self.notifier = NotificationService()

    # ── Trigger: due/overdue reminder sweep ──────────────────────────────────

    async def run_reminder_sweep(
        self, conn: sqlite3.Connection, cfg: dict, now: datetime
    ) -> None:
        if not cfg["notif_reminders_enabled"]:
            return

        now_utc = now.astimezone(timezone.utc)
        last = get_state(conn, "last_reminder_sweep")
        if last:
            last_dt = datetime.fromisoformat(last)
            if now_utc - last_dt < timedelta(minutes=REMINDER_SWEEP_MINUTES):
                return

        # State is advanced BEFORE doing work so that failures skip this window
        # instead of retry-spamming.  Per-task dedup + the 48h lookback mean any
        # missed tasks will fire on the next sweep.  Suppressed sends (quiet
        # hours / daily caps) write no log row, so those tasks also retry next
        # sweep.
        set_state(conn, "last_reminder_sweep", now_utc.isoformat())

        tasks = await self.vikunja.list_tasks(filter="done = false", per_page=100)
        already = recently_notified_task_ids(conn, now_utc)
        lead = timedelta(hours=cfg["notif_reminder_lead_hours"])
        lookback = timedelta(hours=OVERDUE_LOOKBACK_HOURS)

        due_soon = []
        for t in tasks:
            due = parse_vikunja_date(t.get("due_date"))
            if due is None or t["id"] in already:
                continue
            if now_utc - lookback < due <= now_utc + lead:
                due_soon.append(t)

        if not due_soon:
            return

        if len(due_soon) == 1:
            t = due_soon[0]
            due = parse_vikunja_date(t["due_date"])
            overdue = due is not None and due < now_utc
            title = "Task overdue" if overdue else "Task due soon"
            body = _truncate(t["title"])
        else:
            title = f"{len(due_soon)} tasks due soon"
            body = ", ".join(_truncate(t["title"]) for t in due_soon[:5])

        await self.notifier.send(
            conn,
            cfg,
            type="reminder",
            title=title,
            body=body,
            task_ids=[t["id"] for t in due_soon],
            now=now_utc,
        )

    # ── Calendar context (best-effort) ────────────────────────────────────────

    async def _fetch_today_events(
        self, conn: sqlite3.Connection, local_now: datetime
    ) -> list[dict]:
        """Today's events across all selected calendars, or [] if unavailable.

        Best-effort: any failure (no Google account, refresh error, API error)
        collapses to an empty list so callers degrade gracefully.
        """
        row = conn.execute(
            "SELECT refresh_token FROM users WHERE refresh_token IS NOT NULL LIMIT 1"
        ).fetchone()
        if not row:
            return []
        try:
            from app.auth.oauth import refresh_access_token
            from app.routers.schedule import _fetch_all_events

            token_data = await refresh_access_token(row[0])
            access_token = token_data.get("access_token")
            if not access_token:
                return []
            day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            return await _fetch_all_events(
                access_token, conn, day_start.isoformat(), day_end.isoformat()
            )
        except Exception as exc:
            logger.warning("Calendar fetch failed: %s", exc)
            return []

    def _calendar_lines(self, events: list[dict]) -> str:
        """One-line-per-event prompt summary, or a fallback string."""
        if not events:
            return "No calendar events today."
        return "\n".join(
            f"- {e['summary']}: {e['start']} to {e['end']}" for e in events[:10]
        )

    async def _calendar_summary(
        self, conn: sqlite3.Connection, local_now: datetime
    ) -> str:
        """One-line-per-event summary of today's calendar, or a fallback string."""
        return self._calendar_lines(await self._fetch_today_events(conn, local_now))

    # ── Trigger: morning digest ───────────────────────────────────────────────

    async def run_digest(
        self, conn: sqlite3.Connection, cfg: dict, local_now: datetime
    ) -> None:
        if not cfg["notif_digest_enabled"]:
            return
        slot_date = due_slot_date(local_now, cfg["notif_digest_time"])
        if slot_date is None:
            return
        if get_state(conn, "last_digest_date") == slot_date:
            return
        # Don't consume the slot during quiet hours — the fire window may
        # extend past quiet-end, so the digest can still deliver later.
        if in_quiet_hours(local_now, cfg):
            return
        # Record BEFORE generating: an LLM failure skips today's digest
        # instead of retrying every tick (a missing digest is fine).
        set_state(conn, "last_digest_date", slot_date)

        now_utc = local_now.astimezone(timezone.utc)
        tasks = await self.vikunja.list_tasks(
            filter="done = false", sort_by="priority", order_by="desc", per_page=50
        )
        # tasks arrive sorted by priority desc, so undated stays priority-ordered.
        due_today, overdue, undated = [], [], []
        for t in tasks:
            due = parse_vikunja_date(t.get("due_date"))
            if due is None:
                undated.append(t)
            elif due.astimezone(local_now.tzinfo).date() == local_now.date():
                due_today.append(t)
            elif due < now_utc:
                overdue.append(t)

        calendar = await self._calendar_summary(conn, local_now)
        try:
            body, _ = await self._get_or_create_briefing_text(
                conn, cfg, local_now,
                due_today=due_today, overdue=overdue, undated=undated, calendar=calendar,
            )
        except Exception as exc:
            logger.warning("Digest LLM call failed, skipping today: %s", exc)
            return

        await self.notifier.send(
            conn, cfg, type="digest", title="Morning digest", body=body, now=now_utc
        )

    # ── Shared briefing (digest notification + /api/briefing page) ────────────

    async def _get_or_create_briefing_text(
        self,
        conn: sqlite3.Connection,
        cfg: dict,
        local_now: datetime,
        *,
        due_today: list[dict],
        overdue: list[dict],
        undated: list[dict],
        calendar: str,
        force_regen: bool = False,
    ) -> tuple[str, str]:
        """Return (text, generated_at_iso) for today's AI briefing line.

        Cached per local day in scheduler_state so the morning digest and the
        Today page show the SAME line, and repeat page loads don't re-bill the
        LLM. A cache hit ignores the passed task context (the cached line was
        written from the same day's data). Raises if generation fails — the
        caller decides whether that's fatal (digest skips, endpoint 502s).
        """
        key = f"daily_briefing:{local_now.date().isoformat()}"
        if not force_regen:
            cached = get_state(conn, key)
            if cached:
                try:
                    data = json.loads(cached)
                    return data["text"], data["generated_at"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass  # corrupt cache → regenerate

        task_lines = "\n".join(
            f"- {t['title']} (priority {t.get('priority', 3)})" for t in due_today[:10]
        ) or "Nothing due today."

        undated_lines = "\n".join(
            f"- {t['title']} (priority {t.get('priority', 3)})" for t in undated[:10]
        ) or "None."
        if len(undated) > 10:
            undated_lines += f"\n…and {len(undated) - 10} more."

        prompt = f"""Write a morning briefing for a personal task app notification. 2-3 short sentences, friendly but not saccharine, no emoji spam (one emoji max). Mention what's due, the calendar shape, and surface any important no-deadline tasks worth attention. Suggest what to tackle first.

## Tasks due today:
{task_lines}

## Overdue: {len(overdue)} task(s)

## No due date (sorted by priority — call out the important ones):
{undated_lines}

## Today's calendar:
{calendar}

Respond with ONLY the briefing text, no preamble."""

        from app.services.llm import get_llm_client

        llm = get_llm_client()
        text = (await llm.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You write concise, helpful daily briefings.",
        )).strip()[:300]
        generated_at = local_now.astimezone(timezone.utc).isoformat()
        set_state(conn, key, json.dumps({"text": text, "generated_at": generated_at}))
        return text, generated_at

    async def build_briefing(
        self,
        conn: sqlite3.Connection,
        cfg: dict,
        local_now: datetime,
        *,
        force_regen: bool = False,
    ) -> dict:
        """Assemble the Today page payload: AI line + structured task/calendar lists.

        Fetches calendar once and derives both the prompt string and the
        structured event list from it. Tasks are returned as raw Vikunja dicts
        (the frontend Task shape).
        """
        now_utc = local_now.astimezone(timezone.utc)
        open_tasks = await self.vikunja.list_tasks(
            filter="done = false", sort_by="priority", order_by="desc", per_page=100
        )
        # open_tasks arrive sorted by priority desc, so undated stays priority-ordered.
        due_today, overdue, undated = [], [], []
        for t in open_tasks:
            due = parse_vikunja_date(t.get("due_date"))
            if due is None:
                undated.append(t)
            elif due.astimezone(local_now.tzinfo).date() == local_now.date():
                due_today.append(t)
            elif due < now_utc:
                overdue.append(t)

        day_start_utc = local_now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).astimezone(timezone.utc)
        done = await self.vikunja.list_tasks(
            filter="done = true", sort_by="done_at", order_by="desc", per_page=50
        )
        done_today = [
            t for t in done
            if (d := parse_vikunja_date(t.get("done_at"))) and d >= day_start_utc
        ]

        events = await self._fetch_today_events(conn, local_now)
        calendar = [
            {
                "summary": e.get("summary", "(untitled)"),
                "start": e.get("start", ""),
                "end": e.get("end", ""),
                "color": e.get("calendar_color"),
            }
            for e in events[:10]
        ]

        # AI line failure is non-fatal for the page — still show the lists.
        try:
            text, generated_at = await self._get_or_create_briefing_text(
                conn, cfg, local_now,
                due_today=due_today, overdue=overdue, undated=undated,
                calendar=self._calendar_lines(events), force_regen=force_regen,
            )
        except Exception as exc:
            logger.warning("Briefing text generation failed: %s", exc)
            text, generated_at = "", now_utc.isoformat()
        return {
            "briefing_text": text,
            "generated_at": generated_at,
            "due_today": due_today,
            "overdue": overdue,
            "undated": undated,
            "done_today": done_today,
            "calendar": calendar,
        }

    # ── Trigger: evening review ───────────────────────────────────────────────

    async def run_review(
        self, conn: sqlite3.Connection, cfg: dict, local_now: datetime
    ) -> None:
        if not cfg["notif_review_enabled"]:
            return
        slot_date = due_slot_date(local_now, cfg["notif_review_time"])
        if slot_date is None:
            return
        if get_state(conn, "last_review_date") == slot_date:
            return
        # Don't consume the slot during quiet hours (see run_digest).
        if in_quiet_hours(local_now, cfg):
            return
        set_state(conn, "last_review_date", slot_date)

        now_utc = local_now.astimezone(timezone.utc)
        day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_start_utc = day_start.astimezone(timezone.utc)

        done = await self.vikunja.list_tasks(
            filter="done = true", sort_by="done_at", order_by="desc", per_page=50
        )
        done_today = [
            t for t in done
            if (d := parse_vikunja_date(t.get("done_at"))) and d >= day_start_utc
        ]

        open_tasks = await self.vikunja.list_tasks(filter="done = false", per_page=100)
        still_open = []
        for t in open_tasks:
            due = parse_vikunja_date(t.get("due_date"))
            if due and due <= day_start_utc + timedelta(days=1):
                still_open.append(t)

        if not done_today and not still_open:
            return  # nothing worth saying

        def plural(n):
            return "task" if n == 1 else "tasks"

        parts = [f"You completed {len(done_today)} {plural(len(done_today))} today."]
        if still_open:
            parts.append(
                f"{len(still_open)} {plural(len(still_open))} still due — push to tomorrow?"
            )
        await self.notifier.send(
            conn, cfg, type="review", title="Evening review",
            body=" ".join(parts), now=now_utc,
        )

    # ── Trigger: LLM-decided nudges ───────────────────────────────────────────

    async def run_nudge_eval(
        self, conn: sqlite3.Connection, cfg: dict, local_now: datetime
    ) -> None:
        if not cfg["notif_nudges_enabled"]:
            return
        slots = nudge_slot_hours(cfg)
        if local_now.hour not in slots:
            return
        slot_key = f"{local_now.date().isoformat()}:{local_now.hour}"
        if get_state(conn, "last_nudge_slot") == slot_key:
            return
        set_state(conn, "last_nudge_slot", slot_key)

        now_utc = local_now.astimezone(timezone.utc)
        tasks = await self.vikunja.list_tasks(
            filter="done = false", sort_by="priority", order_by="desc", per_page=50
        )
        task_lines = "\n".join(
            f"- [ID:{t['id']}] {_truncate(t['title'])} (priority {t.get('priority', 3)}, "
            f"due {due.isoformat() if (due := parse_vikunja_date(t.get('due_date'))) else 'none'})"
            for t in tasks[:20]
        ) or "No open tasks."

        recent = conn.execute(
            "SELECT type, title, sent_at FROM notification_log "
            "ORDER BY sent_at DESC LIMIT 10"
        ).fetchall()
        recent_lines = "\n".join(
            f"- [{r[0]}] {r[1]} at {r[2]}" for r in recent
        ) or "None."

        calendar = await self._calendar_summary(conn, local_now)

        prompt = f"""You are deciding whether to send the user a push notification nudge from their task app. Current local time: {local_now.isoformat()}.

## Open tasks:
{task_lines}

## Today's calendar:
{calendar}

## Notifications already sent recently (do NOT repeat these topics):
{recent_lines}

## Your job
Decide if there is ONE genuinely useful thing worth nudging about right now — a stale high-priority task, a free block with nothing planned, a deadline creeping up. **Silence is a valid and common choice.** If nothing clears the bar, do not send.

Respond ONLY with JSON:
{{"send": true, "title": "max 40 chars", "body": "max 140 chars"}}
or
{{"send": false}}"""

        from app.services.llm import get_llm_client

        try:
            llm = get_llm_client()
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You decide whether a notification is worth sending. Respond only with valid JSON.",
            )
        except Exception as exc:
            logger.warning("Nudge eval LLM call failed: %s", exc)
            return

        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            decision = json.loads(text)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Nudge eval returned unparseable JSON: %s", exc)
            return

        if not isinstance(decision, dict):
            logger.warning("Nudge eval returned non-dict JSON: %r", decision)
            return

        if not decision.get("send"):
            return
        title = (decision.get("title") or "Nudge").strip()[:60]
        body = (decision.get("body") or "").strip()[:200]
        if not body:
            return
        await self.notifier.send(
            conn, cfg, type="nudge", title=title, body=body, now=now_utc
        )

    # ── Tick + loop ───────────────────────────────────────────────────────────

    async def tick(self, now: datetime | None = None) -> None:
        """Evaluate all triggers once. Each is isolated — one failure never blocks the rest."""
        with get_db() as conn:
            cfg = load_notif_config(conn)
            local_now = get_local_now(cfg, now)
            for trigger in (
                self.run_digest,
                self.run_review,
                self.run_reminder_sweep,
                self.run_nudge_eval,
            ):
                try:
                    await trigger(conn, cfg, local_now)
                except Exception as exc:
                    logger.error("Trigger %s failed: %s", trigger.__name__, exc)


async def scheduler_loop() -> None:
    """Run the nudge engine forever, one tick per minute."""
    engine = NudgeEngine()
    logger.info("Nudge engine started (tick every %ss)", TICK_SECONDS)
    while True:
        try:
            await engine.tick()
        except Exception as exc:
            logger.error("Nudge engine tick crashed: %s", exc)
        await asyncio.sleep(TICK_SECONDS)

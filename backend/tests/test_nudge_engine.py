"""Tests for the nudge engine: helpers, triggers, tick dispatch."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.nudge_engine import (
    NudgeEngine,
    fixed_time_due,
    get_state,
    nudge_slot_hours,
    parse_vikunja_date,
    set_state,
)
from app.services.notifications import load_notif_config


def dt(hour, minute=0, day=9):
    return datetime(2026, 6, day, hour, minute, tzinfo=timezone.utc)


# ── scheduler_state ─────────────────────────────────────────────────────────


def test_state_roundtrip(in_memory_db):
    assert get_state(in_memory_db, "missing") is None
    set_state(in_memory_db, "k", "v1")
    assert get_state(in_memory_db, "k") == "v1"
    set_state(in_memory_db, "k", "v2")
    assert get_state(in_memory_db, "k") == "v2"


# ── fixed-time gating ───────────────────────────────────────────────────────


def test_fixed_time_due_within_window():
    # scheduled 08:00, fire window 3h
    assert fixed_time_due(dt(7, 59), "08:00") is False
    assert fixed_time_due(dt(8, 0), "08:00") is True
    assert fixed_time_due(dt(10, 59), "08:00") is True
    assert fixed_time_due(dt(11, 0), "08:00") is False  # window closed


def test_fixed_time_due_bad_value_defaults_safe():
    assert fixed_time_due(dt(8, 0), "garbage") is False


# ── nudge slots ─────────────────────────────────────────────────────────────


def test_nudge_slot_hours_default():
    cfg = {"notif_quiet_start": 22, "notif_quiet_end": 7, "notif_nudge_runs_per_day": 3}
    slots = nudge_slot_hours(cfg)
    assert len(slots) == 3
    # all slots inside the waking window
    assert all(7 <= h < 22 for h in slots)
    # roughly evenly spaced
    assert slots == sorted(slots)


def test_nudge_slot_hours_zero_runs():
    cfg = {"notif_quiet_start": 22, "notif_quiet_end": 7, "notif_nudge_runs_per_day": 0}
    assert nudge_slot_hours(cfg) == []


# ── reminder sweep ───────────────────────────────────────────────────────────


def make_task(id, title, due: datetime | None):
    return {
        "id": id,
        "title": title,
        "due_date": due.isoformat().replace("+00:00", "Z") if due else "0001-01-01T00:00:00Z",
        "done": False,
        "priority": 3,
    }


@pytest.fixture
def engine(in_memory_db, monkeypatch):
    """Engine with mocked vikunja + notifier, get_db patched to the test conn."""
    import app.services.nudge_engine as mod
    from tests.conftest import make_mock_db

    monkeypatch.setattr(mod, "get_db", make_mock_db(in_memory_db))
    eng = NudgeEngine()
    eng.vikunja = AsyncMock()
    eng.notifier = AsyncMock()
    eng.notifier.send = AsyncMock(return_value=True)
    return eng


NOW = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)


async def test_sweep_notifies_due_soon_task(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    engine.vikunja.list_tasks.return_value = [
        make_task(1, "Due soon", NOW + timedelta(hours=1)),
        make_task(2, "Far future", NOW + timedelta(days=3)),
        make_task(3, "Unscheduled", None),
    ]
    await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    engine.notifier.send.assert_called_once()
    kwargs = engine.notifier.send.call_args.kwargs
    assert kwargs["type"] == "reminder"
    assert kwargs["task_ids"] == [1]
    assert "Due soon" in kwargs["body"]


async def test_sweep_includes_newly_overdue_excludes_ancient(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    engine.vikunja.list_tasks.return_value = [
        make_task(1, "Newly overdue", NOW - timedelta(hours=5)),
        make_task(2, "Ancient overdue", NOW - timedelta(days=30)),
    ]
    await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    kwargs = engine.notifier.send.call_args.kwargs
    assert kwargs["task_ids"] == [1]


async def test_sweep_batches_multiple_tasks(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    engine.vikunja.list_tasks.return_value = [
        make_task(1, "A", NOW + timedelta(hours=1)),
        make_task(2, "B", NOW + timedelta(minutes=30)),
    ]
    await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    kwargs = engine.notifier.send.call_args.kwargs
    assert sorted(kwargs["task_ids"]) == [1, 2]
    assert "2 tasks" in kwargs["title"]


async def test_sweep_dedups_recently_notified(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    in_memory_db.execute(
        "INSERT INTO notification_log (type, task_id, title, body, sent_at) "
        "VALUES ('reminder', 1, 'x', 'x', ?)",
        ((NOW - timedelta(hours=2)).isoformat(),),
    )
    engine.vikunja.list_tasks.return_value = [
        make_task(1, "Already notified", NOW + timedelta(hours=1)),
    ]
    await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    engine.notifier.send.assert_not_called()


async def test_sweep_respects_interval_state(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    set_state(in_memory_db, "last_reminder_sweep", (NOW - timedelta(minutes=5)).isoformat())
    engine.vikunja.list_tasks.return_value = []
    await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    engine.vikunja.list_tasks.assert_not_called()


async def test_sweep_disabled_flag(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    cfg["notif_reminders_enabled"] = 0
    await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    engine.vikunja.list_tasks.assert_not_called()


# ── Fix 1: fixed_time_due crosses midnight ───────────────────────────────────


def test_fixed_time_due_window_crosses_midnight():
    # scheduled 22:00, window 3h → still due at 00:30 next day
    assert fixed_time_due(dt(22, 0), "22:00") is True
    assert fixed_time_due(dt(0, 30, day=10), "22:00") is True
    assert fixed_time_due(dt(1, 0, day=10), "22:00") is False  # window closed at 01:00


# ── Fix 2: parse_vikunja_date handles naive datetimes and garbage ────────────


def test_parse_vikunja_date_handles_naive_and_garbage():
    d = parse_vikunja_date("2026-06-09T10:00:00")  # no offset
    assert d is not None and d.tzinfo is not None
    assert parse_vikunja_date("garbage") is None
    assert parse_vikunja_date(None) is None
    assert parse_vikunja_date("0001-01-01T00:00:00Z") is None


# ── Fix 3: nudge_slot_hours dedup and waking window constraints ──────────────


def test_nudge_slot_hours_no_duplicates_no_quiet_start():
    # tiny waking window: quiet 23 → 22 next day is span 23; instead use span 1
    cfg = {"notif_quiet_start": 8, "notif_quiet_end": 7, "notif_nudge_runs_per_day": 3}
    slots = nudge_slot_hours(cfg)
    assert len(slots) == len(set(slots))
    assert all(s == 7 for s in slots) or all(7 <= s < 8 for s in slots)  # never at quiet_start (8)


def test_nudge_slot_hours_overnight_waking_window():
    # quiet 6→20 means waking window is 20:00 → 06:00 (overnight)
    cfg = {"notif_quiet_start": 6, "notif_quiet_end": 20, "notif_nudge_runs_per_day": 2}
    slots = nudge_slot_hours(cfg)
    assert len(slots) >= 1
    # every slot must be outside quiet hours [6, 20)
    assert all(s >= 20 or s < 6 for s in slots)


# ── Fix 4: reminder body titles are truncated to 60 chars ───────────────────


async def test_sweep_truncates_long_title_single(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    long_title = "A" * 100
    engine.vikunja.list_tasks.return_value = [
        make_task(1, long_title, NOW + timedelta(hours=1)),
    ]
    await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    kwargs = engine.notifier.send.call_args.kwargs
    assert len(kwargs["body"]) <= 60


async def test_sweep_truncates_long_title_batch(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    long_title = "B" * 100
    engine.vikunja.list_tasks.return_value = [
        make_task(1, long_title, NOW + timedelta(hours=1)),
        make_task(2, long_title, NOW + timedelta(minutes=30)),
    ]
    await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    kwargs = engine.notifier.send.call_args.kwargs
    # Each truncated title is ≤60, joined by ", "
    for part in kwargs["body"].split(", "):
        assert len(part) <= 60


# ── Fix 6: failure-path semantics ───────────────────────────────────────────


async def test_sweep_advances_state_even_when_vikunja_fails(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    engine.vikunja.list_tasks.side_effect = RuntimeError("vikunja down")
    with pytest.raises(RuntimeError):
        await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    # interval state was advanced before the failure — no retry-spam
    assert get_state(in_memory_db, "last_reminder_sweep") == NOW.astimezone(timezone.utc).isoformat()


async def test_sweep_window_boundaries(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)  # lead = 2h
    engine.vikunja.list_tasks.return_value = [
        make_task(1, "Exactly at lead", NOW + timedelta(hours=2)),      # included
        make_task(2, "Just past lead", NOW + timedelta(hours=2, seconds=1)),  # excluded
        make_task(3, "Exactly at lookback", NOW - timedelta(hours=48)),  # excluded
    ]
    await engine.run_reminder_sweep(in_memory_db, cfg, NOW)
    kwargs = engine.notifier.send.call_args.kwargs
    assert kwargs["task_ids"] == [1]


# ── due_slot_date helper ─────────────────────────────────────────────────────


def test_due_slot_date_returns_slot_date():
    from app.services.nudge_engine import due_slot_date

    # in-window same day
    assert due_slot_date(dt(8, 30), "08:00") == "2026-06-09"
    # window crossing midnight: at 00:30 on the 10th, the slot is the 9th's 22:00
    assert due_slot_date(dt(0, 30, day=10), "22:00") == "2026-06-09"
    # not due
    assert due_slot_date(dt(13, 0), "08:00") is None
    assert due_slot_date(dt(8, 0), "garbage") is None


# ── digest + review ──────────────────────────────────────────────────────────

MORNING = datetime(2026, 6, 9, 8, 5, tzinfo=timezone.utc)   # within 08:00 window
EVENING = datetime(2026, 6, 9, 21, 10, tzinfo=timezone.utc)  # within 21:00 window


@pytest.fixture
def llm_mock():
    with patch("app.services.llm.get_llm_client") as factory:
        client = AsyncMock()
        client.generate = AsyncMock(return_value="Your briefing.")
        factory.return_value = client
        yield client


async def test_digest_fires_once_per_day(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    engine.vikunja.list_tasks.return_value = [
        make_task(1, "Due today", MORNING + timedelta(hours=2)),
    ]
    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        await engine.run_digest(in_memory_db, cfg, MORNING)
        await engine.run_digest(in_memory_db, cfg, MORNING + timedelta(minutes=30))
    assert engine.notifier.send.call_count == 1
    assert engine.notifier.send.call_args.kwargs["type"] == "digest"
    assert engine.notifier.send.call_args.kwargs["body"] == "Your briefing."


async def test_digest_not_fired_outside_window(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    await engine.run_digest(in_memory_db, cfg, dt(13, 0))  # 08:00 + 3h window passed
    engine.notifier.send.assert_not_called()


async def test_digest_disabled_flag(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    cfg["notif_digest_enabled"] = 0
    await engine.run_digest(in_memory_db, cfg, MORNING)
    engine.vikunja.list_tasks.assert_not_called()
    engine.notifier.send.assert_not_called()


async def test_digest_llm_failure_skips_silently(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    llm_mock.generate.side_effect = RuntimeError("LLM down")
    engine.vikunja.list_tasks.return_value = []
    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        await engine.run_digest(in_memory_db, cfg, MORNING)
    engine.notifier.send.assert_not_called()
    # state recorded → no retry-spam later the same day
    assert get_state(in_memory_db, "last_digest_date") == "2026-06-09"


async def test_review_counts_completed_and_open(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)

    def list_tasks_side_effect(filter=None, **kwargs):
        if "done = true" in (filter or ""):
            return [
                {"id": 1, "title": "Done A", "done": True,
                 "done_at": (EVENING - timedelta(hours=3)).isoformat()},
                {"id": 2, "title": "Done old", "done": True,
                 "done_at": (EVENING - timedelta(days=2)).isoformat()},
            ]
        return [make_task(3, "Still open", EVENING + timedelta(hours=1))]

    engine.vikunja.list_tasks.side_effect = list_tasks_side_effect
    await engine.run_review(in_memory_db, cfg, EVENING)
    kwargs = engine.notifier.send.call_args.kwargs
    assert kwargs["type"] == "review"
    assert "1 task" in kwargs["body"]  # 1 completed today (not the 2-day-old one)


async def test_review_fires_once_per_day(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)

    def list_tasks_side_effect(filter=None, **kwargs):
        if "done = true" in (filter or ""):
            return [{"id": 1, "title": "Done A", "done": True,
                     "done_at": (EVENING - timedelta(hours=3)).isoformat()}]
        return []

    engine.vikunja.list_tasks.side_effect = list_tasks_side_effect
    await engine.run_review(in_memory_db, cfg, EVENING)
    await engine.run_review(in_memory_db, cfg, EVENING + timedelta(minutes=20))
    assert engine.notifier.send.call_count == 1


# ── LLM nudge evaluation ─────────────────────────────────────────────────────


async def test_nudge_eval_sends_when_llm_says_send(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    slots = nudge_slot_hours(cfg)
    at = dt(slots[0], 0)
    llm_mock.generate.return_value = (
        '{"send": true, "title": "Stalled task", "body": "Refactor PR has sat 5 days."}'
    )
    engine.vikunja.list_tasks.return_value = [make_task(1, "Refactor PR", None)]
    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        await engine.run_nudge_eval(in_memory_db, cfg, at)
    kwargs = engine.notifier.send.call_args.kwargs
    assert kwargs["type"] == "nudge"
    assert kwargs["title"] == "Stalled task"


async def test_nudge_eval_respects_silence(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    slots = nudge_slot_hours(cfg)
    llm_mock.generate.return_value = '{"send": false}'
    engine.vikunja.list_tasks.return_value = []
    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        await engine.run_nudge_eval(in_memory_db, cfg, dt(slots[0], 0))
    engine.notifier.send.assert_not_called()


async def test_nudge_eval_only_at_slot_hours(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    slots = set(nudge_slot_hours(cfg))
    non_slot = next(h for h in range(7, 22) if h not in slots)
    await engine.run_nudge_eval(in_memory_db, cfg, dt(non_slot, 0))
    engine.vikunja.list_tasks.assert_not_called()


async def test_nudge_eval_once_per_slot(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    slots = nudge_slot_hours(cfg)
    llm_mock.generate.return_value = '{"send": false}'
    engine.vikunja.list_tasks.return_value = []
    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        await engine.run_nudge_eval(in_memory_db, cfg, dt(slots[0], 0))
        await engine.run_nudge_eval(in_memory_db, cfg, dt(slots[0], 30))
    assert engine.vikunja.list_tasks.call_count == 1


async def test_nudge_eval_disabled_flag(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    cfg["notif_nudges_enabled"] = 0
    slots = nudge_slot_hours(cfg)
    await engine.run_nudge_eval(in_memory_db, cfg, dt(slots[0], 0))
    engine.vikunja.list_tasks.assert_not_called()


async def test_nudge_eval_bad_json_skips(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    slots = nudge_slot_hours(cfg)
    llm_mock.generate.return_value = "I think you should do the thing!"
    engine.vikunja.list_tasks.return_value = []
    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        await engine.run_nudge_eval(in_memory_db, cfg, dt(slots[0], 0))
    engine.notifier.send.assert_not_called()


# ── Fix 1: sentinel due dates hidden from LLM prompt ────────────────────────


async def test_nudge_eval_prompt_hides_sentinel_due_dates(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    slots = nudge_slot_hours(cfg)
    llm_mock.generate.return_value = '{"send": false}'
    engine.vikunja.list_tasks.return_value = [make_task(1, "No due date", None)]
    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        await engine.run_nudge_eval(in_memory_db, cfg, dt(slots[0], 0))
    prompt = llm_mock.generate.call_args.kwargs["messages"][0]["content"]
    assert "0001-01-01" not in prompt
    assert "due none" in prompt


# ── Fix 2: non-dict JSON (e.g. bare true) must not raise ────────────────────


async def test_nudge_eval_non_dict_json_skips(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    slots = nudge_slot_hours(cfg)
    llm_mock.generate.return_value = "true"
    engine.vikunja.list_tasks.return_value = []
    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        await engine.run_nudge_eval(in_memory_db, cfg, dt(slots[0], 0))  # must not raise
    engine.notifier.send.assert_not_called()


# ── Fix 6: markdown-fenced JSON is parsed correctly ─────────────────────────


async def test_nudge_eval_parses_fenced_json(engine, in_memory_db, llm_mock):
    cfg = load_notif_config(in_memory_db)
    slots = nudge_slot_hours(cfg)
    llm_mock.generate.return_value = (
        '```json\n{"send": true, "title": "Go", "body": "Do the thing."}\n```'
    )
    engine.vikunja.list_tasks.return_value = []
    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        await engine.run_nudge_eval(in_memory_db, cfg, dt(slots[0], 0))
    assert engine.notifier.send.call_args.kwargs["title"] == "Go"


# ── tick dispatch ────────────────────────────────────────────────────────────


async def test_tick_dispatches_all_triggers(engine, in_memory_db):
    with (
        patch.object(engine, "run_digest", AsyncMock()) as digest,
        patch.object(engine, "run_review", AsyncMock()) as review,
        patch.object(engine, "run_reminder_sweep", AsyncMock()) as sweep,
        patch.object(engine, "run_nudge_eval", AsyncMock()) as nudge,
    ):
        await engine.tick(NOW)
    digest.assert_called_once()
    review.assert_called_once()
    sweep.assert_called_once()
    nudge.assert_called_once()


async def test_tick_survives_trigger_exception(engine, in_memory_db):
    with (
        patch.object(engine, "run_digest", AsyncMock(side_effect=RuntimeError("boom"))),
        patch.object(engine, "run_review", AsyncMock()) as review,
        patch.object(engine, "run_reminder_sweep", AsyncMock()),
        patch.object(engine, "run_nudge_eval", AsyncMock()),
    ):
        await engine.tick(NOW)  # must not raise
    review.assert_called_once()


async def test_digest_in_quiet_hours_does_not_consume_slot(engine, in_memory_db, llm_mock):
    """A digest scheduled inside quiet hours must not burn its once-per-day slot —
    the fire window can extend past quiet-end and deliver then."""
    cfg = load_notif_config(in_memory_db)
    cfg["notif_digest_time"] = "06:00"  # inside default quiet hours (22 -> 7)
    engine.vikunja.list_tasks.return_value = []

    with patch.object(engine, "_calendar_summary", AsyncMock(return_value="No events.")):
        # 06:30 is quiet: nothing sent, slot NOT consumed
        await engine.run_digest(in_memory_db, cfg, dt(6, 30))
        assert get_state(in_memory_db, "last_digest_date") is None
        engine.notifier.send.assert_not_called()

        # 07:30 is past quiet-end and still inside the 3h fire window: fires
        await engine.run_digest(in_memory_db, cfg, dt(7, 30))
        assert get_state(in_memory_db, "last_digest_date") == "2026-06-09"
        engine.notifier.send.assert_called_once()


async def test_review_in_quiet_hours_does_not_consume_slot(engine, in_memory_db):
    cfg = load_notif_config(in_memory_db)
    cfg["notif_review_time"] = "23:00"  # inside default quiet hours
    engine.vikunja.list_tasks.return_value = []
    await engine.run_review(in_memory_db, cfg, dt(23, 30))
    assert get_state(in_memory_db, "last_review_date") is None
    engine.notifier.send.assert_not_called()

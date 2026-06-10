"""Tests for push notifications: schema, router, NotificationService."""

import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from tests.conftest import make_mock_db


# ── Schema ───────────────────────────────────────────────────────────────────


def test_schema_creates_notification_tables(in_memory_db):
    tables = {
        r[0]
        for r in in_memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "push_subscriptions" in tables
    assert "notification_log" in tables
    assert "scheduler_state" in tables


def test_agent_config_has_notification_columns(in_memory_db):
    cols = {
        r[1]
        for r in in_memory_db.execute("PRAGMA table_info(agent_config)").fetchall()
    }
    expected = {
        "notif_digest_enabled",
        "notif_reminders_enabled",
        "notif_nudges_enabled",
        "notif_review_enabled",
        "notif_digest_time",
        "notif_review_time",
        "notif_max_per_day",
        "notif_max_nudges_per_day",
        "notif_reminder_lead_hours",
        "notif_quiet_start",
        "notif_quiet_end",
        "notif_nudge_runs_per_day",
        "notif_timezone",
    }
    assert expected <= cols


def test_notification_defaults_seeded(in_memory_db):
    row = in_memory_db.execute(
        "SELECT notif_digest_enabled, notif_digest_time, notif_max_per_day, "
        "notif_quiet_start, notif_quiet_end, notif_timezone "
        "FROM agent_config WHERE id = 1"
    ).fetchone()
    assert row == (1, "08:00", 5, 22, 7, "UTC")


# ── Router ───────────────────────────────────────────────────────────────────


@pytest.fixture
def client(in_memory_db, mock_user, monkeypatch):
    import app.routers.notifications as notif_router

    monkeypatch.setattr(notif_router, "get_db", make_mock_db(in_memory_db))
    app.dependency_overrides[get_current_user] = lambda: mock_user
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()


SUB_PAYLOAD = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/abc123",
    "keys": {"p256dh": "BPubKey", "auth": "AuthSecret"},
}


def test_vapid_public_key(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "vapid_public_key", "test-public-key")
    resp = client.get("/api/notifications/vapid-public-key")
    assert resp.status_code == 200
    assert resp.json() == {"public_key": "test-public-key"}


def test_subscribe_stores_subscription(client, in_memory_db):
    resp = client.post("/api/notifications/subscribe", json=SUB_PAYLOAD)
    assert resp.status_code == 200
    rows = in_memory_db.execute(
        "SELECT user_email, endpoint, p256dh, auth FROM push_subscriptions"
    ).fetchall()
    assert rows == [
        ("test@example.com", SUB_PAYLOAD["endpoint"], "BPubKey", "AuthSecret")
    ]


def test_subscribe_same_endpoint_upserts(client, in_memory_db):
    client.post("/api/notifications/subscribe", json=SUB_PAYLOAD)
    updated = {**SUB_PAYLOAD, "keys": {"p256dh": "NewKey", "auth": "NewAuth"}}
    client.post("/api/notifications/subscribe", json=updated)
    rows = in_memory_db.execute(
        "SELECT p256dh, auth FROM push_subscriptions"
    ).fetchall()
    assert rows == [("NewKey", "NewAuth")]


def test_unsubscribe_deletes(client, in_memory_db):
    client.post("/api/notifications/subscribe", json=SUB_PAYLOAD)
    resp = client.request(
        "DELETE",
        "/api/notifications/subscribe",
        json={"endpoint": SUB_PAYLOAD["endpoint"]},
    )
    assert resp.status_code == 200
    count = in_memory_db.execute(
        "SELECT COUNT(*) FROM push_subscriptions"
    ).fetchone()[0]
    assert count == 0


# ── NotificationService ──────────────────────────────────────────────────────

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.services.notifications import (
    NotificationService,
    in_quiet_hours,
    load_notif_config,
)

NOON = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)  # Tuesday, not quiet
NIGHT = datetime(2026, 6, 9, 23, 0, tzinfo=timezone.utc)  # inside 22→7 quiet


def _insert_sub(conn, endpoint="https://push.example/1"):
    conn.execute(
        "INSERT INTO push_subscriptions (user_email, endpoint, p256dh, auth) "
        "VALUES ('test@example.com', ?, 'k', 'a')",
        (endpoint,),
    )


def test_load_notif_config_defaults(in_memory_db):
    cfg = load_notif_config(in_memory_db)
    assert cfg["notif_max_per_day"] == 5
    assert cfg["notif_timezone"] == "UTC"
    assert cfg["notif_quiet_start"] == 22


def test_in_quiet_hours():
    cfg = {"notif_quiet_start": 22, "notif_quiet_end": 7}
    assert in_quiet_hours(NIGHT, cfg) is True
    assert in_quiet_hours(NOON, cfg) is False
    # degenerate config: start == end means never quiet
    assert in_quiet_hours(NIGHT, {"notif_quiet_start": 8, "notif_quiet_end": 8}) is False


async def test_send_delivers_and_logs(in_memory_db):
    _insert_sub(in_memory_db)
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    with patch("app.services.notifications.webpush") as mock_push:
        ok = await svc.send(
            in_memory_db, cfg, type="nudge", title="T", body="B", now=NOON
        )
    assert ok is True
    mock_push.assert_called_once()
    rows = in_memory_db.execute(
        "SELECT type, title, body FROM notification_log"
    ).fetchall()
    assert rows == [("nudge", "T", "B")]


async def test_send_blocked_in_quiet_hours(in_memory_db):
    _insert_sub(in_memory_db)
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    with patch("app.services.notifications.webpush") as mock_push:
        ok = await svc.send(
            in_memory_db, cfg, type="nudge", title="T", body="B", now=NIGHT
        )
    assert ok is False
    mock_push.assert_not_called()


async def test_send_test_type_bypasses_quiet_hours(in_memory_db):
    _insert_sub(in_memory_db)
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    with patch("app.services.notifications.webpush"):
        ok = await svc.send(
            in_memory_db, cfg, type="test", title="T", body="B",
            now=NIGHT, bypass_guardrails=True,
        )
    assert ok is True


async def test_daily_cap_enforced(in_memory_db):
    _insert_sub(in_memory_db)
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    with patch("app.services.notifications.webpush"):
        for i in range(5):
            assert await svc.send(
                in_memory_db, cfg, type="reminder", title="T", body="B",
                now=NOON + timedelta(seconds=i),
            ) is True
        # 6th push of the day is blocked (cap = 5)
        assert await svc.send(
            in_memory_db, cfg, type="reminder", title="T", body="B",
            now=NOON + timedelta(seconds=5),
        ) is False


async def test_nudge_cap_enforced(in_memory_db):
    _insert_sub(in_memory_db)
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    with patch("app.services.notifications.webpush"):
        assert await svc.send(in_memory_db, cfg, type="nudge", title="T", body="B", now=NOON)
        assert await svc.send(in_memory_db, cfg, type="nudge", title="T", body="B", now=NOON + timedelta(seconds=1))
        # 3rd nudge blocked (cap = 2) even though total cap (5) not reached
        assert await svc.send(
            in_memory_db, cfg, type="nudge", title="T", body="B",
            now=NOON + timedelta(seconds=2),
        ) is False


async def test_batch_send_logs_per_task_but_counts_one_push(in_memory_db):
    _insert_sub(in_memory_db)
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    with patch("app.services.notifications.webpush"):
        await svc.send(
            in_memory_db, cfg, type="reminder", title="3 due", body="a, b, c",
            task_ids=[1, 2, 3], now=NOON,
        )
        # one push consumed from the cap, so 4 more sends still allowed
        for i in range(4):
            assert await svc.send(
                in_memory_db, cfg, type="reminder", title="T", body="B",
                now=NOON + timedelta(seconds=1 + i),
            ) is True
    log_count = in_memory_db.execute(
        "SELECT COUNT(*) FROM notification_log WHERE task_id IN (1,2,3)"
    ).fetchone()[0]
    assert log_count == 3


async def test_dead_subscription_pruned_on_410(in_memory_db):
    from pywebpush import WebPushException

    _insert_sub(in_memory_db, "https://push.example/dead")
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    resp = MagicMock()
    resp.status_code = 410
    with patch(
        "app.services.notifications.webpush",
        side_effect=WebPushException("gone", response=resp),
    ):
        ok = await svc.send(
            in_memory_db, cfg, type="digest", title="T", body="B", now=NOON
        )
    assert ok is False
    count = in_memory_db.execute("SELECT COUNT(*) FROM push_subscriptions").fetchone()[0]
    assert count == 0


async def test_no_subscriptions_returns_false(in_memory_db):
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    with patch("app.services.notifications.webpush") as mock_push:
        ok = await svc.send(
            in_memory_db, cfg, type="digest", title="T", body="B", now=NOON
        )
    assert ok is False
    mock_push.assert_not_called()


async def test_send_test_notification_endpoint(client, in_memory_db):
    _insert_sub(in_memory_db)
    with patch("app.services.notifications.webpush") as mock_push:
        resp = client.post("/api/notifications/test")
    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    mock_push.assert_called_once()


async def test_send_test_notification_no_subscriptions(client):
    resp = client.post("/api/notifications/test")
    assert resp.status_code == 200
    assert resp.json() == {"success": False}


async def test_test_sends_do_not_consume_daily_cap(in_memory_db):
    _insert_sub(in_memory_db)
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    with patch("app.services.notifications.webpush"):
        for i in range(5):
            await svc.send(
                in_memory_db, cfg, type="test", title="T", body="B",
                now=NOON + timedelta(seconds=i), bypass_guardrails=True,
            )
        # real sends still allowed — test pushes don't count toward the cap
        assert await svc.send(
            in_memory_db, cfg, type="reminder", title="T", body="B",
            now=NOON + timedelta(seconds=10),
        ) is True


async def test_partial_delivery_multiple_subscriptions(in_memory_db):
    from pywebpush import WebPushException

    _insert_sub(in_memory_db, "https://push.example/dead")
    _insert_sub(in_memory_db, "https://push.example/alive")
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    resp = MagicMock()
    resp.status_code = 410

    def push_side_effect(**kwargs):
        if kwargs.get("subscription_info", {}).get("endpoint", "").endswith("/dead"):
            raise WebPushException("gone", response=resp)

    with patch("app.services.notifications.webpush", side_effect=push_side_effect):
        ok = await svc.send(
            in_memory_db, cfg, type="digest", title="T", body="B", now=NOON
        )
    assert ok is True  # one delivery succeeded
    endpoints = [
        r[0] for r in in_memory_db.execute("SELECT endpoint FROM push_subscriptions").fetchall()
    ]
    assert endpoints == ["https://push.example/alive"]  # dead pruned, live kept
    log_count = in_memory_db.execute("SELECT COUNT(*) FROM notification_log").fetchone()[0]
    assert log_count == 1


async def test_transient_failure_not_pruned_not_logged(in_memory_db):
    from pywebpush import WebPushException

    _insert_sub(in_memory_db)
    cfg = load_notif_config(in_memory_db)
    svc = NotificationService()
    resp = MagicMock()
    resp.status_code = 500
    with patch(
        "app.services.notifications.webpush",
        side_effect=WebPushException("server error", response=resp),
    ):
        ok = await svc.send(
            in_memory_db, cfg, type="digest", title="T", body="B", now=NOON
        )
    assert ok is False
    assert in_memory_db.execute("SELECT COUNT(*) FROM push_subscriptions").fetchone()[0] == 1
    assert in_memory_db.execute("SELECT COUNT(*) FROM notification_log").fetchone()[0] == 0

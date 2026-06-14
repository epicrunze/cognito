"""
SQLite database connection and schema management.

Single SQLite file holds all tables:
  - users                    (auth)
  - task_proposals           (proposal queue)
  - vikunja_projects         (project cache)
  - agent_config             (singleton config row)
  - label_descriptions       (label metadata)
  - conversations            (chat history)
  - conversation_messages    (chat messages)
  - task_revisions           (AI action undo/redo)
  - task_calendar_links      (task ↔ GCal event)
  - gcal_selected_calendars  (selected Google Calendars)
  - push_subscriptions       (Web Push device subscriptions)
  - notification_log         (sent notification history)
  - scheduler_state          (background scheduler last-run state)
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from app.config import settings


def get_connection(database_path: str | None = None) -> sqlite3.Connection:
    """
    Open a SQLite connection in autocommit mode.

    Args:
        database_path: Optional path override. Falls back to settings.

    Returns:
        SQLite connection instance.
    """
    path = database_path or settings.get_database_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    return conn


@contextmanager
def get_db(database_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager — ensures connections are properly closed."""
    conn = get_connection(database_path)
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Create all tables if they don't exist.

    Safe to call multiple times — uses IF NOT EXISTS throughout.
    """

    # ── Auth ──────────────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                       TEXT PRIMARY KEY,
            email                    TEXT UNIQUE NOT NULL,
            name                     TEXT,
            picture                  TEXT,
            refresh_token            TEXT,
            refresh_token_expires_at TEXT,
            created_at               TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
            last_login_at            TEXT
        )
    """)

    # ── Proposal queue ────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_proposals (
            id                TEXT PRIMARY KEY,
            source_id         TEXT NOT NULL,
            title             TEXT NOT NULL,
            description       TEXT,
            project_name      TEXT,
            project_id        INTEGER,
            priority          INTEGER DEFAULT 3,
            due_date          TEXT,
            estimated_minutes INTEGER,
            labels            TEXT DEFAULT '[]',
            source_type       TEXT NOT NULL DEFAULT 'notes',
            source_text       TEXT NOT NULL DEFAULT '',
            confidential      INTEGER DEFAULT 0,
            status            TEXT DEFAULT 'pending',
            vikunja_task_id   INTEGER,
            gcal_event_id     TEXT,
            created_at        TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
            reviewed_at       TEXT
        )
    """)

    # ── Vikunja project cache ─────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vikunja_projects (
            id             INTEGER PRIMARY KEY,
            title          TEXT NOT NULL,
            description    TEXT,
            last_synced_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        )
    """)

    # ── Agent config (singleton — always id = 1) ──────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_config (
            id                      INTEGER PRIMARY KEY,
            default_project_id      INTEGER,
            ollama_model            TEXT DEFAULT 'qwen3:4b',
            gemini_model            TEXT DEFAULT 'gemini-3.1-flash-lite-preview',
            gcal_calendar_id        TEXT,
            system_prompt_override  TEXT
        )
    """)

    # Migration: add system_prompt_override to existing DBs
    try:
        conn.execute("ALTER TABLE agent_config ADD COLUMN system_prompt_override TEXT")
    except Exception:
        pass  # Column already exists

    # Migration: add base_prompt_override to existing DBs
    try:
        conn.execute("ALTER TABLE agent_config ADD COLUMN base_prompt_override TEXT")
    except Exception:
        pass  # Column already exists

    # Migration: add schedule preferences to existing DBs
    for col, default in [
        ("schedule_weekday_start", 8),
        ("schedule_weekday_end", 18),
        ("schedule_weekend_start", 10),
        ("schedule_weekend_end", 16),
        ("schedule_weekend_enabled", 1),
    ]:
        try:
            conn.execute(f"ALTER TABLE agent_config ADD COLUMN {col} INTEGER DEFAULT {default}")
        except Exception:
            pass  # Column already exists

    # ── Label descriptions ────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS label_descriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            label_id    INTEGER NOT NULL UNIQUE,
            title       TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
            updated_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        )
    """)

    # ── Conversations (chat mode) ──────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
            updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL REFERENCES conversations(id),
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            proposals_json  TEXT,
            actions_json    TEXT,
            created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        )
    """)

    # Migration: add actions_json to existing DBs
    try:
        conn.execute("ALTER TABLE conversation_messages ADD COLUMN actions_json TEXT")
    except Exception:
        pass  # Column already exists

    # Migration: add hex_color, is_archived, position to vikunja_projects
    for col, defn in [
        ("hex_color", "TEXT DEFAULT ''"),
        ("is_archived", "INTEGER DEFAULT 0"),
        ("position", "REAL DEFAULT 0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE vikunja_projects ADD COLUMN {col} {defn}")
        except Exception:
            pass  # Column already exists

    # ── Project workspace (jun 2026) ──────────────────────────────────────────
    # Per-project markdown notes + AI status briefing. Kept in its own table so
    # the vikunja_projects cache can be rebuilt (DELETE+INSERT) without losing
    # this user/AI-authored data.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_workspace (
            project_id            INTEGER PRIMARY KEY,
            notes                 TEXT DEFAULT '',
            notes_updated_at      TEXT,
            briefing              TEXT DEFAULT '',
            briefing_generated_at TEXT,
            briefing_stale        INTEGER DEFAULT 0
        )
    """)

    # ── Task revisions (AI action undo/redo) ─────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_revisions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id         INTEGER NOT NULL,
            action_type     TEXT NOT NULL,
            source          TEXT NOT NULL,
            before_state    TEXT,
            after_state     TEXT,
            changes         TEXT,
            conversation_id TEXT,
            proposal_id     TEXT,
            undone          INTEGER DEFAULT 0,
            undone_at       TEXT,
            created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        )
    """)

    # ── Task ↔ Calendar event links ──────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_calendar_links (
            task_id        INTEGER PRIMARY KEY,
            gcal_event_id  TEXT NOT NULL,
            calendar_id    TEXT NOT NULL DEFAULT 'primary',
            created_at     TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        )
    """)

    # ── Selected Google Calendars ─────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gcal_selected_calendars (
            calendar_id    TEXT PRIMARY KEY,
            summary        TEXT NOT NULL,
            color          TEXT NOT NULL DEFAULT '#4285f4',
            enabled        INTEGER NOT NULL DEFAULT 1,
            created_at     TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        )
    """)

    # ── Push notification subscriptions (one row per browser/device) ─────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            endpoint   TEXT NOT NULL UNIQUE,
            p256dh     TEXT NOT NULL,
            auth       TEXT NOT NULL,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        )
    """)

    # ── Notification log (drives dedup, daily caps, history) ─────────────────
    # sent_at is always a UTC ISO-8601 string with offset (datetime.isoformat()
    # of an aware UTC datetime) — cap/dedup window queries compare against it.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            type    TEXT NOT NULL,
            task_id INTEGER,
            title   TEXT NOT NULL,
            body    TEXT NOT NULL,
            sent_at TEXT NOT NULL
        )
    """)

    # ── Scheduler last-run state (survives restarts) ──────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Migration: add notification preferences to agent_config
    for col, defn in [
        ("notif_digest_enabled", "INTEGER DEFAULT 1"),
        ("notif_reminders_enabled", "INTEGER DEFAULT 1"),
        ("notif_nudges_enabled", "INTEGER DEFAULT 1"),
        ("notif_review_enabled", "INTEGER DEFAULT 1"),
        ("notif_digest_time", "TEXT DEFAULT '08:00'"),
        ("notif_review_time", "TEXT DEFAULT '21:00'"),
        ("notif_max_per_day", "INTEGER DEFAULT 5"),
        ("notif_max_nudges_per_day", "INTEGER DEFAULT 2"),
        ("notif_reminder_lead_hours", "INTEGER DEFAULT 2"),
        ("notif_quiet_start", "INTEGER DEFAULT 22"),
        ("notif_quiet_end", "INTEGER DEFAULT 7"),
        ("notif_nudge_runs_per_day", "INTEGER DEFAULT 3"),
        ("notif_timezone", "TEXT DEFAULT 'UTC'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE agent_config ADD COLUMN {col} {defn}")
        except Exception:
            pass  # Column already exists

    # Seed the singleton config row if it doesn't exist
    conn.execute("INSERT OR IGNORE INTO agent_config (id) VALUES (1)")


def get_tables(conn: sqlite3.Connection) -> list[str]:
    """Return list of all table names."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]

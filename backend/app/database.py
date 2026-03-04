"""
DuckDB database connection and schema management.

Single DuckDB file holds all tables:
  - users              (auth — ported from archive)
  - task_proposals     (proposal queue)
  - vikunja_projects   (project cache)
  - agent_config       (singleton config row)
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import duckdb

from app.config import settings


def get_connection(database_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """
    Open a DuckDB connection.

    Args:
        database_path: Optional path override. Falls back to settings.

    Returns:
        DuckDB connection instance.
    """
    path = database_path or settings.get_database_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(path)


@contextmanager
def get_db(database_path: str | None = None) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager — ensures connections are properly closed."""
    conn = get_connection(database_path)
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Create all tables if they don't exist.

    Safe to call multiple times — uses IF NOT EXISTS throughout.
    """

    # ── Auth ──────────────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email                    VARCHAR UNIQUE NOT NULL,
            name                     VARCHAR,
            picture                  VARCHAR,
            refresh_token            VARCHAR,
            refresh_token_expires_at TIMESTAMP,
            created_at               TIMESTAMP DEFAULT now(),
            last_login_at            TIMESTAMP
        )
    """)

    # ── Proposal queue ────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_proposals (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id         UUID NOT NULL,
            title             VARCHAR NOT NULL,
            description       VARCHAR,
            project_name      VARCHAR,
            project_id        INTEGER,
            priority          INTEGER DEFAULT 3,
            due_date          DATE,
            estimated_minutes INTEGER,
            labels            JSON DEFAULT '[]',
            source_type       VARCHAR NOT NULL DEFAULT 'notes',
            source_text       VARCHAR NOT NULL DEFAULT '',
            confidential      BOOLEAN DEFAULT FALSE,
            status            VARCHAR DEFAULT 'pending',
            vikunja_task_id   INTEGER,
            gcal_event_id     VARCHAR,
            created_at        TIMESTAMP DEFAULT now(),
            reviewed_at       TIMESTAMP
        )
    """)

    # ── Vikunja project cache ─────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vikunja_projects (
            id             INTEGER PRIMARY KEY,
            title          VARCHAR NOT NULL,
            description    VARCHAR,
            last_synced_at TIMESTAMP DEFAULT now()
        )
    """)

    # ── Agent config (singleton — always id = 1) ──────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_config (
            id                 INTEGER PRIMARY KEY,
            default_project_id INTEGER,
            ollama_model       VARCHAR DEFAULT 'qwen3:4b',
            gemini_model       VARCHAR DEFAULT 'gemini-2.0-flash',
            gcal_calendar_id   VARCHAR
        )
    """)

    # Seed the singleton config row if it doesn't exist
    conn.execute("""
        INSERT INTO agent_config (id) VALUES (1)
        ON CONFLICT (id) DO NOTHING
    """)


def get_tables(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Return list of all table names."""
    return [row[0] for row in conn.execute("SHOW TABLES").fetchall()]

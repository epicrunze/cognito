"""
DuckDB database connection and schema management.

Provides connection handling and schema initialization for the Cognito PWA.
"""

import duckdb
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from app.config import settings


def get_connection(database_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """
    Get a DuckDB connection.

    Args:
        database_path: Optional path override. Uses settings if not provided.

    Returns:
        DuckDB connection instance.
    """
    path = database_path or settings.get_database_path()

    # Ensure the data directory exists
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return duckdb.connect(path)


@contextmanager
def get_db(database_path: str | None = None) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Context manager for database connections.

    Ensures connections are properly closed after use.
    """
    conn = get_connection(database_path)
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Initialize the database schema.

    Creates all tables if they don't exist. Safe to call multiple times.

    Args:
        conn: DuckDB connection instance.
    """
    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR UNIQUE NOT NULL,
            name VARCHAR,
            picture VARCHAR,
            refresh_token VARCHAR,
            refresh_token_expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT now(),
            last_login_at TIMESTAMP
        )
    """)

    # Add columns for existing databases (DuckDB doesn't have IF NOT EXISTS for columns)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN refresh_token VARCHAR")
    except Exception:
        pass  # Column already exists

    try:
        conn.execute("ALTER TABLE users ADD COLUMN refresh_token_expires_at TIMESTAMP")
    except Exception:
        pass  # Column already exists

    # Entries table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            date DATE NOT NULL,
            conversations JSON DEFAULT '[]',
            refined_output TEXT DEFAULT '',
            relevance_score FLOAT DEFAULT 1.0,
            last_interacted_at TIMESTAMP DEFAULT now(),
            interaction_count INTEGER DEFAULT 0,
            status VARCHAR DEFAULT 'active',
            pending_refine BOOLEAN DEFAULT FALSE,
            refine_status VARCHAR DEFAULT 'idle',
            refine_error TEXT,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        )
    """)

    # Entry versions table (for conflict resolution)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entry_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entry_id UUID,
            version INTEGER NOT NULL,
            content_snapshot TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT now()
        )
    """)

    # Goals table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            category VARCHAR NOT NULL,
            description TEXT NOT NULL,
            active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        )
    """)

    # Proposals table (cleanup suggestions)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS proposals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            type VARCHAR NOT NULL,
            target_entry_id UUID,
            description TEXT NOT NULL,
            diff_before TEXT,
            diff_after TEXT,
            status VARCHAR DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT now(),
            reviewed_at TIMESTAMP
        )
    """)

    # Code specs table (self-modifying code)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS code_specs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            title VARCHAR NOT NULL,
            problem TEXT NOT NULL,
            requirements JSON DEFAULT '[]',
            suggested_approach TEXT,
            affected_areas JSON DEFAULT '[]',
            acceptance_criteria JSON DEFAULT '[]',
            priority VARCHAR DEFAULT 'medium',
            status VARCHAR DEFAULT 'proposed',
            github_pr_url VARCHAR,
            created_at TIMESTAMP DEFAULT now(),
            approved_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # Scheduled notifications table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            prompt TEXT NOT NULL,
            related_entry_ids JSON DEFAULT '[]',
            related_goal_ids JSON DEFAULT '[]',
            scheduled_for TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            status VARCHAR DEFAULT 'pending',
            sent_at TIMESTAMP,
            interacted_at TIMESTAMP
        )
    """)

    # Notification config table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_config (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID UNIQUE,
            prompts_per_day INTEGER DEFAULT 1,
            quiet_hours_start TIME DEFAULT '22:00',
            quiet_hours_end TIME DEFAULT '08:00',
            preferred_times JSON DEFAULT '["09:00", "14:00", "19:00"]',
            timezone VARCHAR DEFAULT 'UTC'
        )
    """)

    # Push subscriptions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            endpoint TEXT NOT NULL,
            p256dh_key TEXT NOT NULL,
            auth_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT now()
        )
    """)


def get_tables(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """
    Get list of all tables in the database.

    Args:
        conn: DuckDB connection instance.

    Returns:
        List of table names.
    """
    result = conn.execute("SHOW TABLES").fetchall()
    return [row[0] for row in result]

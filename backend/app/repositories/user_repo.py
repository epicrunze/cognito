"""
User repository for database operations.

Handles user CRUD operations with race condition safety.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import duckdb

from app.models.user import User, UserInDB
from app.utils.timestamp import utc_now, ensure_utc


def get_user_by_email(
    conn: duckdb.DuckDBPyConnection,
    email: str,
) -> Optional[UserInDB]:
    """
    Get user by email address.

    Args:
        conn: DuckDB connection
        email: User email address

    Returns:
        User if found, None otherwise
    """
    result = conn.execute(
        "SELECT id, email, name, picture, created_at, last_login_at FROM users WHERE email = ?",
        [email],
    ).fetchone()

    if not result:
        return None

    return UserInDB(
        id=result[0] if isinstance(result[0], UUID) else UUID(result[0]),
        email=result[1],
        name=result[2],
        picture=result[3],
        created_at=ensure_utc(result[4]),
        last_login_at=ensure_utc(result[5]),
    )


def create_user(
    conn: duckdb.DuckDBPyConnection,
    user: User,
) -> UserInDB:
    """
    Create new user in database.

    Handles race condition gracefully: if user already exists (UNIQUE constraint
    violation), fetches and returns the existing user instead of failing.

    Args:
        conn: DuckDB connection
        user: User data (email, name, picture)

    Returns:
        Created or existing user with database fields
    """
    user_id = uuid4()
    now = utc_now()

    try:
        conn.execute(
            """
            INSERT INTO users (id, email, name, picture, created_at, last_login_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                str(user_id),
                user.email,
                user.name,
                user.picture,
                now,
                now,
            ],
        )

        # Successfully created, return new user with timezone-aware datetimes
        return UserInDB(
            id=user_id,
            email=user.email,
            name=user.name,
            picture=user.picture,
            created_at=ensure_utc(now),
            last_login_at=ensure_utc(now),
        )

    except Exception:
        # Race condition: another request created the user
        # This can happen if multiple tabs authenticate simultaneously
        # Re-fetch the existing user and return it
        existing_user = get_user_by_email(conn, user.email)
        if existing_user:
            return existing_user

        # If we still can't find the user, something is really wrong
        raise


def update_last_login(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
) -> None:
    """
    Update last_login_at timestamp for a user.

    Args:
        conn: DuckDB connection
        user_id: User ID to update
    """
    conn.execute(
        "UPDATE users SET last_login_at = ? WHERE id = ?",
        [utc_now(), str(user_id)],
    )

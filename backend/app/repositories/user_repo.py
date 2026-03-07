"""
User repository — SQLite CRUD for the users table.
"""

import sqlite3
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.models.user import User, UserInDB
from app.utils.timestamp import ensure_utc, utc_now


def get_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[UserInDB]:
    result = conn.execute(
        """SELECT id, email, name, picture, created_at, last_login_at,
                  refresh_token, refresh_token_expires_at
           FROM users WHERE email = ?""",
        [email],
    ).fetchone()

    if not result:
        return None

    return UserInDB(
        id=UUID(str(result[0])),
        email=result[1],
        name=result[2],
        picture=result[3],
        created_at=ensure_utc(result[4]) or datetime.now(),
        last_login_at=ensure_utc(result[5]),
        refresh_token=result[6],
        refresh_token_expires_at=ensure_utc(result[7]) if result[7] else None,
    )


def create_user(conn: sqlite3.Connection, user: User) -> UserInDB:
    """Create user, returning existing user if email already taken."""
    user_id = uuid4()
    now = utc_now()

    try:
        conn.execute(
            """INSERT INTO users (id, email, name, picture, created_at, last_login_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [str(user_id), user.email, user.name, user.picture, now.isoformat(), now.isoformat()],
        )
        return UserInDB(
            id=user_id,
            email=user.email,
            name=user.name,
            picture=user.picture,
            created_at=ensure_utc(now),
            last_login_at=ensure_utc(now),
        )
    except Exception:
        existing = get_user_by_email(conn, user.email)
        if existing:
            return existing
        raise


def update_last_login(conn: sqlite3.Connection, user_id: UUID) -> None:
    conn.execute(
        "UPDATE users SET last_login_at = ? WHERE id = ?",
        [utc_now().isoformat(), str(user_id)],
    )


def update_refresh_token(
    conn: sqlite3.Connection,
    user_id: UUID,
    refresh_token: str,
    expires_at: datetime,
) -> None:
    conn.execute(
        "UPDATE users SET refresh_token = ?, refresh_token_expires_at = ? WHERE id = ?",
        [refresh_token, expires_at.isoformat() if expires_at else None, str(user_id)],
    )


def clear_refresh_token(conn: sqlite3.Connection, user_id: UUID) -> None:
    conn.execute(
        "UPDATE users SET refresh_token = NULL, refresh_token_expires_at = NULL WHERE id = ?",
        [str(user_id)],
    )


def get_user_by_id(conn: sqlite3.Connection, user_id: UUID) -> Optional[UserInDB]:
    result = conn.execute(
        """SELECT id, email, name, picture, created_at, last_login_at,
                  refresh_token, refresh_token_expires_at
           FROM users WHERE id = ?""",
        [str(user_id)],
    ).fetchone()

    if not result:
        return None

    return UserInDB(
        id=UUID(str(result[0])),
        email=result[1],
        name=result[2],
        picture=result[3],
        created_at=ensure_utc(result[4]) or datetime.now(),
        last_login_at=ensure_utc(result[5]),
        refresh_token=result[6],
        refresh_token_expires_at=ensure_utc(result[7]) if result[7] else None,
    )

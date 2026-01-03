"""
Goal repository for database operations.

Handles all Goal CRUD operations using DuckDB.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import duckdb

from app.models.goal import GoalCreate, GoalInDB, GoalUpdate
from app.utils.timestamp import utc_now


def get_goals(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    active_filter: Optional[bool] = None,
) -> list[GoalInDB]:
    """
    Get goals with optional filtering.

    Args:
        conn: DuckDB connection
        user_id: User ID to filter by
        active_filter: Filter by active status (True/False/None for all)

    Returns:
        List of goals
    """
    query = "SELECT * FROM goals WHERE user_id = ?"
    params = [str(user_id)]

    if active_filter is not None:
        query += " AND active = ?"
        params.append(active_filter)

    query += " ORDER BY created_at DESC"

    result = conn.execute(query, params).fetchall()

    goals = []
    for row in result:
        goals.append(
            GoalInDB(
                id=row[0] if isinstance(row[0], UUID) else UUID(row[0]),
                user_id=row[1] if isinstance(row[1], UUID) else UUID(row[1]),
                category=row[2],
                description=row[3],
                active=row[4],
                created_at=row[5],
                updated_at=row[6],
            )
        )

    return goals


def get_goal_by_id(
    conn: duckdb.DuckDBPyConnection,
    goal_id: UUID,
    user_id: UUID,
) -> Optional[GoalInDB]:
    """
    Get a single goal by ID.

    Args:
        conn: DuckDB connection
        goal_id: Goal ID
        user_id: User ID for ownership check

    Returns:
        Goal if found and owned by user, None otherwise
    """
    result = conn.execute(
        "SELECT * FROM goals WHERE id = ? AND user_id = ?",
        [str(goal_id), str(user_id)],
    ).fetchone()

    if not result:
        return None

    return GoalInDB(
        id=result[0] if isinstance(result[0], UUID) else UUID(result[0]),
        user_id=result[1] if isinstance(result[1], UUID) else UUID(result[1]),
        category=result[2],
        description=result[3],
        active=result[4],
        created_at=result[5],
        updated_at=result[6],
    )


def create_goal(
    conn: duckdb.DuckDBPyConnection,
    goal_data: GoalCreate,
    user_id: UUID,
    goal_id: Optional[UUID] = None,
) -> GoalInDB:
    """
    Create a new goal.

    Args:
        conn: DuckDB connection
        goal_data: Goal creation data
        user_id: User ID
        goal_id: Optional goal ID (for sync with client-generated UUIDs)

    Returns:
        Created goal
    """
    if goal_id is None:
        goal_id = uuid4()
    now = utc_now()

    conn.execute(
        """
        INSERT INTO goals (id, user_id, category, description, active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            str(goal_id),
            str(user_id),
            goal_data.category,
            goal_data.description,
            True,
            now,
            now,
        ],
    )

    return GoalInDB(
        id=goal_id,
        user_id=user_id,
        category=goal_data.category,
        description=goal_data.description,
        active=True,
        created_at=now,
        updated_at=now,
    )


def update_goal(
    conn: duckdb.DuckDBPyConnection,
    goal_id: UUID,
    user_id: UUID,
    goal_data: GoalUpdate,
) -> Optional[GoalInDB]:
    """
    Update a goal.

    Args:
        conn: DuckDB connection
        goal_id: Goal ID
        user_id: User ID for ownership check
        goal_data: Update data

    Returns:
        Updated goal if found and owned by user, None otherwise
    """
    # Check if goal exists and is owned by user
    existing = get_goal_by_id(conn, goal_id, user_id)
    if not existing:
        return None

    # Build update query dynamically based on provided fields
    updates = []
    params = []

    if goal_data.category is not None:
        updates.append("category = ?")
        params.append(goal_data.category)

    if goal_data.description is not None:
        updates.append("description = ?")
        params.append(goal_data.description)

    if goal_data.active is not None:
        updates.append("active = ?")
        params.append(goal_data.active)

    if not updates:
        # No fields to update, return existing
        return existing

    # Always update updated_at
    updates.append("updated_at = ?")
    params.append(utc_now())

    # Add WHERE clause params
    params.extend([str(goal_id), str(user_id)])

    query = f"UPDATE goals SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
    conn.execute(query, params)

    # Fetch and return updated goal
    return get_goal_by_id(conn, goal_id, user_id)


def delete_goal(
    conn: duckdb.DuckDBPyConnection,
    goal_id: UUID,
    user_id: UUID,
    soft_delete: bool = True,
) -> bool:
    """
    Delete a goal.

    Args:
        conn: DuckDB connection
        goal_id: Goal ID
        user_id: User ID for ownership check
        soft_delete: If True, set active=false; if False, hard delete

    Returns:
        True if goal was deleted, False if not found or not owned
    """
    # Check if goal exists and is owned by user
    existing = get_goal_by_id(conn, goal_id, user_id)
    if not existing:
        return False

    if soft_delete:
        # Soft delete: set active to false
        conn.execute(
            "UPDATE goals SET active = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            [False, utc_now(), str(goal_id), str(user_id)],
        )
    else:
        # Hard delete: remove from database
        conn.execute(
            "DELETE FROM goals WHERE id = ? AND user_id = ?",
            [str(goal_id), str(user_id)],
        )

    return True


def get_goals_since(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    since: Optional[datetime] = None,
) -> list[GoalInDB]:
    """
    Get goals modified since a given timestamp.

    Args:
        conn: DuckDB connection
        user_id: User ID
        since: Get goals updated after this timestamp (None for all)

    Returns:
        List of goals
    """
    if since:
        query = """
            SELECT * FROM goals
            WHERE user_id = ? AND updated_at > ?
            ORDER BY updated_at DESC
        """
        results = conn.execute(query, [str(user_id), since]).fetchall()
    else:
        query = """
            SELECT * FROM goals
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """
        results = conn.execute(query, [str(user_id)]).fetchall()

    goals = []
    for row in results:
        goals.append(GoalInDB(
            id=row[0] if isinstance(row[0], UUID) else UUID(row[0]),
            user_id=row[1] if isinstance(row[1], UUID) else UUID(row[1]),
            category=row[2],
            description=row[3],
            active=row[4],
            created_at=row[5],
            updated_at=row[6],
        ))

    return goals


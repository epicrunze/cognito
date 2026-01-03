"""
Goal router.

Handles Goal CRUD operations with authentication.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.goal import Goal, GoalCreate, GoalUpdate
from app.models.user import User
from app.repositories import goal_repo

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("")
async def list_goals(
    active_filter: Optional[bool] = Query(None, alias="active"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    List goals with optional filtering.

    Query Parameters:
        active: Filter by active status (true/false, omit for all)

    Returns:
        {
            "goals": [Goal]
        }
    """
    with get_db() as conn:
        # Get user from database
        from app.repositories import user_repo

        db_user = user_repo.get_user_by_email(conn, current_user.email)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User not found - authentication error",
            )
        user_id = db_user.id

        goals = goal_repo.get_goals(
            conn=conn,
            user_id=user_id,
            active_filter=active_filter,
        )

        # Convert to response models (exclude user_id)
        goal_list = [
            Goal(
                id=g.id,
                category=g.category,
                description=g.description,
                active=g.active,
                created_at=g.created_at,
                updated_at=g.updated_at,
            )
            for g in goals
        ]

        return {"goals": goal_list}


@router.get("/{goal_id}")
async def get_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Goal:
    """
    Get a single goal by ID.

    Args:
        goal_id: Goal UUID

    Returns:
        Goal object

    Raises:
        404: Goal not found or not owned by user
    """
    with get_db() as conn:
        # Get user from database
        from app.repositories import user_repo

        db_user = user_repo.get_user_by_email(conn, current_user.email)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User not found - authentication error",
            )
        user_id = db_user.id

        # Get goal
        goal = goal_repo.get_goal_by_id(conn, goal_id, user_id)

        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found",
            )

        # Return without user_id
        return Goal(
            id=goal.id,
            category=goal.category,
            description=goal.description,
            active=goal.active,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal_data: GoalCreate,
    current_user: User = Depends(get_current_user),
) -> Goal:
    """
    Create a new goal.

    Args:
        goal_data: Goal creation data

    Returns:
        Created goal
    """
    with get_db() as conn:
        # Get user from database
        from app.repositories import user_repo

        db_user = user_repo.get_user_by_email(conn, current_user.email)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User not found - authentication error",
            )
        user_id = db_user.id

        # Create new goal
        new_goal = goal_repo.create_goal(conn, goal_data, user_id)

        return Goal(
            id=new_goal.id,
            category=new_goal.category,
            description=new_goal.description,
            active=new_goal.active,
            created_at=new_goal.created_at,
            updated_at=new_goal.updated_at,
        )


@router.put("/{goal_id}")
async def update_goal(
    goal_id: UUID,
    goal_data: GoalUpdate,
    current_user: User = Depends(get_current_user),
) -> Goal:
    """
    Update an existing goal.

    Args:
        goal_id: Goal UUID
        goal_data: Update data (partial)

    Returns:
        Updated goal

    Raises:
        404: Goal not found or not owned by user
    """
    with get_db() as conn:
        # Get user from database
        from app.repositories import user_repo

        db_user = user_repo.get_user_by_email(conn, current_user.email)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User not found - authentication error",
            )
        user_id = db_user.id

        # Update goal
        updated_goal = goal_repo.update_goal(conn, goal_id, user_id, goal_data)

        if not updated_goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found",
            )

        return Goal(
            id=updated_goal.id,
            category=updated_goal.category,
            description=updated_goal.description,
            active=updated_goal.active,
            created_at=updated_goal.created_at,
            updated_at=updated_goal.updated_at,
        )


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete a goal (soft delete - sets active=false).

    Args:
        goal_id: Goal UUID

    Returns:
        {"success": true}

    Raises:
        404: Goal not found or not owned by user
    """
    with get_db() as conn:
        # Get user from database
        from app.repositories import user_repo

        db_user = user_repo.get_user_by_email(conn, current_user.email)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User not found - authentication error",
            )
        user_id = db_user.id

        # Delete goal (soft delete by default)
        success = goal_repo.delete_goal(conn, goal_id, user_id, soft_delete=True)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found",
            )

        return {"success": True}

"""
Entry router.

Handles Entry CRUD operations with authentication.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.entry import Entry, EntryCreate, EntryUpdate, EntryVersion
from app.models.user import User
from app.repositories import entry_repo

router = APIRouter(prefix="/api/entries", tags=["entries"])


@router.get("")
async def list_entries(
    status_filter: Optional[str] = Query(None, alias="status"),
    after_date: Optional[str] = Query(None),
    before_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    order_by: str = Query("date:desc"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    List entries with optional filtering.

    Query Parameters:
        status: Filter by status (active/archived)
        after_date: Filter entries after this date (YYYY-MM-DD)
        before_date: Filter entries before this date (YYYY-MM-DD)
        limit: Maximum number of entries (1-100, default 50)
        offset: Number of entries to skip (default 0)
        order_by: Order by field:direction (default "date:desc")

    Returns:
        {
            "entries": [Entry],
            "total": number
        }
    """
    with get_db() as conn:
        # TODO: Get user_id from database based on email
        # For now, using a placeholder approach
        # We need to either store user_id in JWT or look it up
        user_result = conn.execute(
            "SELECT id FROM users WHERE email = ?", [current_user.email]
        ).fetchone()

        if not user_result:
            # Create user if doesn't exist
            from uuid import uuid4
            from datetime import datetime

            user_id = uuid4()
            conn.execute(
                """
                INSERT INTO users (id, email, name, picture, created_at, last_login_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    str(user_id),
                    current_user.email,
                    current_user.name,
                    current_user.picture,
                    datetime.now(),
                    datetime.now(),
                ],
            )
        else:
            user_id = user_result[0] if isinstance(user_result[0], UUID) else UUID(user_result[0])

        entries, total = entry_repo.get_entries(
            conn=conn,
            user_id=user_id,
            status=status_filter,
            after_date=after_date,
            before_date=before_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

        # Convert to response models (exclude user_id)
        entry_list = [
            Entry(
                id=e.id,
                date=e.date,
                conversations=e.conversations,
                refined_output=e.refined_output,
                relevance_score=e.relevance_score,
                last_interacted_at=e.last_interacted_at,
                interaction_count=e.interaction_count,
                status=e.status,
                version=e.version,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in entries
        ]

        return {"entries": entry_list, "total": total}


@router.get("/{entry_id}")
async def get_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Entry:
    """
    Get a single entry by ID.

    Updates last_interacted_at timestamp.

    Args:
        entry_id: Entry UUID

    Returns:
        Entry object

    Raises:
        404: Entry not found
        403: Entry belongs to different user
    """
    with get_db() as conn:
        # Get user_id
        user_result = conn.execute(
            "SELECT id FROM users WHERE email = ?", [current_user.email]
        ).fetchone()

        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user_id = user_result[0] if isinstance(user_result[0], UUID) else UUID(user_result[0])

        # Get entry
        entry = entry_repo.get_entry_by_id(conn, entry_id, user_id)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entry not found",
            )

        # Update interaction timestamp
        entry_repo.update_last_interacted_at(conn, entry_id)

        # Return without user_id
        return Entry(
            id=entry.id,
            date=entry.date,
            conversations=entry.conversations,
            refined_output=entry.refined_output,
            relevance_score=entry.relevance_score,
            last_interacted_at=entry.last_interacted_at,
            interaction_count=entry.interaction_count,
            status=entry.status,
            version=entry.version,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_entry(
    entry_data: EntryCreate,
    current_user: User = Depends(get_current_user),
) -> Entry:
    """
    Create a new entry.

    If an entry for the given date already exists, returns the existing entry
    instead of creating a duplicate.

    Args:
        entry_data: Entry creation data

    Returns:
        Created or existing entry
    """
    with get_db() as conn:
        # Get or create user
        user_result = conn.execute(
            "SELECT id FROM users WHERE email = ?", [current_user.email]
        ).fetchone()

        if not user_result:
            from uuid import uuid4
            from datetime import datetime

            user_id = uuid4()
            conn.execute(
                """
                INSERT INTO users (id, email, name, picture, created_at, last_login_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    str(user_id),
                    current_user.email,
                    current_user.name,
                    current_user.picture,
                    datetime.now(),
                    datetime.now(),
                ],
            )
        else:
            user_id = user_result[0] if isinstance(user_result[0], UUID) else UUID(user_result[0])

        # Check if entry for this date already exists
        existing_entry = entry_repo.get_entry_by_date(conn, user_id, entry_data.date)

        if existing_entry:
            # Return existing entry
            return Entry(
                id=existing_entry.id,
                date=existing_entry.date,
                conversations=existing_entry.conversations,
                refined_output=existing_entry.refined_output,
                relevance_score=existing_entry.relevance_score,
                last_interacted_at=existing_entry.last_interacted_at,
                interaction_count=existing_entry.interaction_count,
                status=existing_entry.status,
                version=existing_entry.version,
                created_at=existing_entry.created_at,
                updated_at=existing_entry.updated_at,
            )

        # Create new entry
        new_entry = entry_repo.create_entry(conn, user_id, entry_data)

        return Entry(
            id=new_entry.id,
            date=new_entry.date,
            conversations=new_entry.conversations,
            refined_output=new_entry.refined_output,
            relevance_score=new_entry.relevance_score,
            last_interacted_at=new_entry.last_interacted_at,
            interaction_count=new_entry.interaction_count,
            status=new_entry.status,
            version=new_entry.version,
            created_at=new_entry.created_at,
            updated_at=new_entry.updated_at,
        )


@router.put("/{entry_id}")
async def update_entry(
    entry_id: UUID,
    entry_data: EntryUpdate,
    current_user: User = Depends(get_current_user),
) -> Entry:
    """
    Update an existing entry.

    Creates a version snapshot before updating.

    Args:
        entry_id: Entry UUID
        entry_data: Update data (partial)

    Returns:
        Updated entry

    Raises:
        404: Entry not found
        403: Entry belongs to different user
    """
    with get_db() as conn:
        # Get user_id
        user_result = conn.execute(
            "SELECT id FROM users WHERE email = ?", [current_user.email]
        ).fetchone()

        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user_id = user_result[0] if isinstance(user_result[0], UUID) else UUID(user_result[0])

        # Update entry
        updated_entry = entry_repo.update_entry(conn, entry_id, user_id, entry_data)

        if not updated_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entry not found",
            )

        return Entry(
            id=updated_entry.id,
            date=updated_entry.date,
            conversations=updated_entry.conversations,
            refined_output=updated_entry.refined_output,
            relevance_score=updated_entry.relevance_score,
            last_interacted_at=updated_entry.last_interacted_at,
            interaction_count=updated_entry.interaction_count,
            status=updated_entry.status,
            version=updated_entry.version,
            created_at=updated_entry.created_at,
            updated_at=updated_entry.updated_at,
        )


@router.get("/{entry_id}/versions")
async def get_entry_versions(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get version history for an entry.

    Args:
        entry_id: Entry UUID

    Returns:
        {"versions": [EntryVersion]}

    Raises:
        404: Entry not found
        403: Entry belongs to different user
    """
    with get_db() as conn:
        # Get user_id
        user_result = conn.execute(
            "SELECT id FROM users WHERE email = ?", [current_user.email]
        ).fetchone()

        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user_id = user_result[0] if isinstance(user_result[0], UUID) else UUID(user_result[0])

        # Get versions
        versions = entry_repo.get_entry_versions(conn, entry_id, user_id)

        return {"versions": versions}

"""
Sync router.

Handles sync endpoints for offline-first synchronization.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.logging import info, debug, error
from app.models.user import User
from app.repositories import user_repo
from app.services.sync import SyncService
from app.utils.timestamp import utc_now

router = APIRouter(prefix="/api/sync", tags=["sync"])


# Request/Response Models

class PendingChange(BaseModel):
    """A single pending change from the client."""
    id: str
    type: str  # 'create' | 'update' | 'delete'
    entity: str  # 'entry' | 'goal'
    entity_id: str
    data: dict = Field(default_factory=dict)
    base_version: Optional[int] = None
    timestamp: str  # ISO 8601


class SyncRequest(BaseModel):
    """Sync request from client."""
    last_synced_at: Optional[str] = None  # ISO 8601 or null for first sync
    pending_changes: list[PendingChange] = Field(default_factory=list)
    base_versions: dict[str, int] = Field(default_factory=dict)  # entity_id -> version


class ServerChanges(BaseModel):
    """Server changes to send to client."""
    entries: list[dict] = Field(default_factory=list)
    goals: list[dict] = Field(default_factory=list)


class SyncResponse(BaseModel):
    """Sync response to client."""
    applied: list[str] = Field(default_factory=list)  # IDs of successfully applied changes
    skipped: list[str] = Field(default_factory=list)  # IDs of skipped changes (server was newer)
    server_changes: ServerChanges
    sync_timestamp: str  # New sync timestamp for client to store
    pending_messages_processed: list[str] = Field(default_factory=list)  # Entries with LLM responses added


def _get_user_id(conn, current_user: User) -> UUID:
    """Get user ID from database."""
    db_user = user_repo.get_user_by_email(conn, current_user.email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User not found - authentication error",
        )
    return db_user.id


@router.post("", response_model=SyncResponse)
async def sync(
    request: SyncRequest,
    current_user: User = Depends(get_current_user),
) -> SyncResponse:
    """
    Synchronize local changes with server.

    Processes pending changes from client using last-write-wins strategy,
    and returns server changes since last sync.

    Args:
        request: Sync request with pending changes and last sync timestamp

    Returns:
        SyncResponse with applied IDs, server changes, and new sync timestamp
    """
    sync_start = utc_now()
    info(
        "Sync started",
        user=current_user.email,
        pending_count=len(request.pending_changes),
        last_synced=request.last_synced_at
    )

    with get_db() as conn:
        user_id = _get_user_id(conn, current_user)
        sync_service = SyncService(conn, user_id)

        # Process pending changes
        applied: list[str] = []
        skipped: list[str] = []
        
        if request.pending_changes:
            changes_dicts = [change.model_dump() for change in request.pending_changes]
            applied, skipped = sync_service.process_pending_changes(
                changes_dicts,
                request.base_versions
            )

        # Get server changes since last sync
        server_changes = sync_service.get_server_changes(request.last_synced_at)

        # Process pending messages (messages needing LLM responses)
        pending_messages_processed: list[str] = []
        try:
            pending_messages_processed = await sync_service.process_pending_messages()
        except Exception as e:
            error(f"Failed to process pending messages: {e}")
            # Don't fail the whole sync if LLM processing fails

        sync_timestamp = utc_now().isoformat()

        info(
            "Sync completed",
            user=current_user.email,
            applied=len(applied),
            skipped=len(skipped),
            server_entries=len(server_changes.get("entries", [])),
            server_goals=len(server_changes.get("goals", [])),
            pending_messages=len(pending_messages_processed)
        )

        return SyncResponse(
            applied=applied,
            skipped=skipped,
            server_changes=ServerChanges(
                entries=server_changes.get("entries", []),
                goals=server_changes.get("goals", [])
            ),
            sync_timestamp=sync_timestamp,
            pending_messages_processed=pending_messages_processed
        )

"""Router: /api/revisions — AI action revision history + undo/redo."""

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.revisions import RevisionService

router = APIRouter(prefix="/api/revisions", tags=["revisions"])


@router.get("")
async def list_revisions(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    """List recent revisions, newest first."""
    with get_db() as conn:
        revisions = RevisionService.get_recent(conn, limit=limit)
    return {"revisions": revisions}


@router.get("/{revision_id}")
async def get_revision(
    revision_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get a single revision by ID."""
    with get_db() as conn:
        revision = RevisionService.get_by_id(conn, revision_id)
    if not revision:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    return revision


@router.post("/{revision_id}/undo")
async def undo_revision(
    revision_id: int,
    force: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    """Undo a revision. Pass ?force=true to skip conflict check."""
    with get_db() as conn:
        result = await RevisionService.undo(conn, revision_id, force=force)
    return result


@router.post("/{revision_id}/redo")
async def redo_revision(
    revision_id: int,
    current_user: User = Depends(get_current_user),
):
    """Re-apply a previously undone revision."""
    with get_db() as conn:
        result = await RevisionService.redo(conn, revision_id)
    return result

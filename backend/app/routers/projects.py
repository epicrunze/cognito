"""Projects router — Vikunja project list + cache management."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.vikunja import VikunjaError, vikunja
from app.utils.timestamp import utc_now

router = APIRouter(prefix="/api/projects", tags=["projects"])

CACHE_TTL_HOURS = 1


@router.get("")
async def list_projects(current_user: User = Depends(get_current_user)):
    """
    Return Vikunja project list.

    Uses the local SQLite cache, refreshing automatically if stale (>1 hour).
    """
    with get_db() as conn:
        # Check if cache is fresh
        row = conn.execute(
            "SELECT MAX(last_synced_at) FROM vikunja_projects"
        ).fetchone()
        last_synced = row[0] if row else None

    cache_stale = True
    if last_synced:
        from app.utils.timestamp import ensure_utc
        synced_aware = ensure_utc(last_synced)
        if synced_aware and (utc_now() - synced_aware.replace(tzinfo=None)) < timedelta(hours=CACHE_TTL_HOURS):
            cache_stale = False

    if cache_stale:
        try:
            fresh = await vikunja.list_projects()
            _update_cache(fresh)
        except VikunjaError:
            pass  # Return stale cache rather than failing

    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, description FROM vikunja_projects ORDER BY title"
        ).fetchall()

    projects = [{"id": r[0], "title": r[1], "description": r[2]} for r in rows]
    return {"projects": projects}


@router.post("/sync")
async def sync_projects(current_user: User = Depends(get_current_user)):
    """Force-refresh the Vikunja project cache."""
    try:
        fresh = await vikunja.list_projects()
        _update_cache(fresh)
        return {"synced": len(fresh)}
    except VikunjaError as e:
        return {"synced": 0, "error": str(e)}


class CreateProjectRequest(BaseModel):
    title: str
    description: str = ""


@router.post("")
async def create_project(
    body: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a project in Vikunja and add to local cache."""
    try:
        project = await vikunja.create_project(body.title, body.description)
    except VikunjaError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create project in Vikunja: {e}",
        )
    _add_project_to_cache(project)
    return project


def _add_project_to_cache(project: dict) -> None:
    """Insert or replace a single project in the cache."""
    now = utc_now()
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO vikunja_projects (id, title, description, last_synced_at) VALUES (?, ?, ?, ?)",
            [project["id"], project.get("title", ""), project.get("description", ""), now],
        )


def _update_cache(projects: list[dict]) -> None:
    """Replace the vikunja_projects cache with fresh data."""
    now = utc_now()
    with get_db() as conn:
        conn.execute("DELETE FROM vikunja_projects")
        for p in projects:
            conn.execute(
                "INSERT INTO vikunja_projects (id, title, description, last_synced_at) VALUES (?, ?, ?, ?)",
                [p["id"], p.get("title", ""), p.get("description", ""), now],
            )

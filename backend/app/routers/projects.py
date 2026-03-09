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


# ── Views & Buckets (Kanban) ───────────────────────────────────────────────


@router.get("/{project_id}/views")
async def list_views(
    project_id: int,
    current_user: User = Depends(get_current_user),
):
    """List all views for a project."""
    try:
        views = await vikunja.list_project_views(project_id)
        return {"views": views}
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


class CreateViewRequest(BaseModel):
    title: str
    view_kind: str = "kanban"


@router.put("/{project_id}/views")
async def create_view(
    project_id: int,
    body: CreateViewRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a view for a project."""
    try:
        view = await vikunja.create_view(project_id, body.title, body.view_kind)
        return view
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{project_id}/views/{view_id}/buckets")
async def list_buckets(
    project_id: int,
    view_id: int,
    current_user: User = Depends(get_current_user),
):
    """List buckets for a kanban view."""
    try:
        buckets = await vikunja.list_buckets(project_id, view_id)
        return {"buckets": buckets}
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


class CreateBucketRequest(BaseModel):
    title: str
    limit: int = 0


@router.put("/{project_id}/views/{view_id}/buckets")
async def create_bucket(
    project_id: int,
    view_id: int,
    body: CreateBucketRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a bucket in a kanban view."""
    try:
        bucket = await vikunja.create_bucket(project_id, view_id, body.title, body.limit)
        return bucket
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/{project_id}/views/{view_id}/buckets/{bucket_id}")
async def update_bucket(
    project_id: int,
    view_id: int,
    bucket_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """Update a bucket."""
    try:
        return await vikunja.update_bucket(project_id, view_id, bucket_id, body)
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.delete("/{project_id}/views/{view_id}/buckets/{bucket_id}")
async def delete_bucket(
    project_id: int,
    view_id: int,
    bucket_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a bucket."""
    try:
        await vikunja.delete_bucket(project_id, view_id, bucket_id)
        return {"success": True}
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{project_id}/views/{view_id}/tasks")
async def list_view_tasks(
    project_id: int,
    view_id: int,
    current_user: User = Depends(get_current_user),
):
    """List tasks for a view. For kanban views, returns buckets with nested tasks."""
    try:
        data = await vikunja.list_view_tasks(project_id, view_id)
        # Filter subtasks from kanban buckets
        if isinstance(data, list):
            for bucket in data:
                if isinstance(bucket, dict) and "tasks" in bucket and bucket["tasks"]:
                    bucket["tasks"] = [
                        t for t in bucket["tasks"]
                        if not bool((t.get("related_tasks") or {}).get("parenttask"))
                    ]
        return data
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


class MoveTaskRequest(BaseModel):
    task_id: int


@router.post("/{project_id}/views/{view_id}/buckets/{bucket_id}/tasks")
async def move_task_to_bucket(
    project_id: int,
    view_id: int,
    bucket_id: int,
    body: MoveTaskRequest,
    current_user: User = Depends(get_current_user),
):
    """Move a task to a bucket."""
    try:
        return await vikunja.move_task_to_bucket(
            project_id, view_id, body.task_id, bucket_id
        )
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


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

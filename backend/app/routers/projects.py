"""Projects router — Vikunja project list + cache management."""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.vikunja import VikunjaError, vikunja
from app.utils.timestamp import utc_now

router = APIRouter(prefix="/api/projects", tags=["projects"])

CACHE_TTL_HOURS = 1


def _normalize_hex_color(color: str | None) -> str:
    """Ensure hex color has '#' prefix or return empty string."""
    if not color:
        return ""
    color = color.strip()
    if not color:
        return ""
    # Add '#' if it looks like a bare hex color (6 hex digits)
    if len(color) == 6 and all(c in "0123456789abcdefABCDEF" for c in color):
        return f"#{color}"
    return color


@router.get("")
async def list_projects(
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    """
    Return Vikunja project list.

    Uses the local SQLite cache, refreshing automatically if stale (>1 hour).
    Excludes archived projects by default; pass include_archived=true to include them.
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
        if include_archived:
            rows = conn.execute(
                "SELECT id, title, description, hex_color, is_archived, position FROM vikunja_projects ORDER BY position, title"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, description, hex_color, is_archived, position FROM vikunja_projects WHERE is_archived = 0 ORDER BY position, title"
            ).fetchall()

    projects = [
        {
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "hex_color": _normalize_hex_color(r[3]),
            "is_archived": bool(r[4]),
            "position": r[5] or 0,
        }
        for r in rows
    ]
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
    hex_color: Optional[str] = None


@router.post("")
async def create_project(
    body: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a project in Vikunja and add to local cache."""
    try:
        project = await vikunja.create_project(body.title, body.description)
        # If hex_color was specified, update the project with it
        if body.hex_color:
            project = await vikunja.update_project(project["id"], {"hex_color": body.hex_color})
    except VikunjaError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create project in Vikunja: {e}",
        )
    _add_project_to_cache(project)
    return project


class UpdateProjectRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hex_color: Optional[str] = None
    is_archived: Optional[bool] = None
    position: Optional[float] = None


@router.post("/{project_id}")
async def update_project(
    project_id: int,
    body: UpdateProjectRequest,
    current_user: User = Depends(get_current_user),
):
    """Update a project in Vikunja and update local cache."""
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        project = await vikunja.update_project(project_id, data)
    except VikunjaError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to update project in Vikunja: {e}",
        )
    _add_project_to_cache(project)
    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a project from Vikunja and remove from local cache."""
    try:
        await vikunja.delete_project(project_id)
    except VikunjaError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete project in Vikunja: {e}",
        )
    with get_db() as conn:
        conn.execute("DELETE FROM vikunja_projects WHERE id = ?", [project_id])
    return {"success": True}


def _add_project_to_cache(project: dict) -> None:
    """Insert or replace a single project in the cache."""
    now = utc_now()
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                project["id"],
                project.get("title", ""),
                project.get("description", ""),
                _normalize_hex_color(project.get("hex_color", "")),
                1 if project.get("is_archived") else 0,
                project.get("position", 0),
                now,
            ],
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
                "INSERT INTO vikunja_projects (id, title, description, hex_color, is_archived, position, last_synced_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    p["id"],
                    p.get("title", ""),
                    p.get("description", ""),
                    _normalize_hex_color(p.get("hex_color", "")),
                    1 if p.get("is_archived") else 0,
                    p.get("position", 0),
                    now,
                ],
            )

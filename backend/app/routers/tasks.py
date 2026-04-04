"""
Router: /api/tasks

Vikunja task proxy (Spec §3.2).
Proxies task CRUD operations to Vikunja, injecting the API token server-side
so the frontend never needs direct Vikunja access.

NOTE: Vikunja uses PUT to create and POST to update (opposite of standard REST).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.revisions import RevisionService
from app.services.tagger import AutoTagger
from app.services.vikunja import VikunjaError, vikunja

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    priority: int = 3
    due_date: Optional[str] = None  # ISO date YYYY-MM-DD
    start_date: Optional[str] = None  # ISO datetime for schedule start
    end_date: Optional[str] = None  # ISO datetime for schedule end
    labels: Optional[list[str]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    done: Optional[bool] = None
    project_id: Optional[int] = None


class SubtaskCreate(BaseModel):
    title: str
    project_id: Optional[int] = None


def _is_subtask(task: dict) -> bool:
    """Return True if this task is a child of another task (has a parenttask relation)."""
    related = task.get("related_tasks") or {}
    return bool(related.get("parenttask"))


def _enrich_subtask_counts(task: dict) -> dict:
    """Add subtask_done / subtask_total counts from related_tasks.subtask."""
    related = task.get("related_tasks") or {}
    subtasks = related.get("subtask", [])
    if subtasks:
        task["subtask_total"] = len(subtasks)
        task["subtask_done"] = sum(1 for s in subtasks if s.get("done"))
    return task


@router.get("")
async def list_tasks(
    project_id: Optional[int] = Query(None),
    view_id: Optional[int] = Query(None),
    s: Optional[str] = Query(None),
    filter: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    order_by: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """List tasks across all projects or for a specific project view."""
    try:
        tasks = await vikunja.list_tasks(
            project_id=project_id,
            view_id=view_id,
            filter=filter,
            sort_by=sort_by,
            order_by=order_by,
            s=s,
        )
        tasks = [_enrich_subtask_counts(t) for t in tasks]
        tasks = [t for t in tasks if not _is_subtask(t)]
        return {"tasks": tasks}
    except VikunjaError as e:
        logger.error("Failed to list tasks: %s", e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


# ── Auto-tag (must be before /{task_id} routes) ─────────────────────────


class AutoTagRequest(BaseModel):
    task_ids: Optional[list[int]] = None
    model: Optional[str] = None


@router.post("/auto-tag")
async def auto_tag(
    body: AutoTagRequest,
    current_user: User = Depends(get_current_user),
):
    """Auto-tag tasks using LLM + label descriptions."""
    # Load label descriptions
    with get_db() as conn:
        rows = conn.execute(
            "SELECT label_id, title, description FROM label_descriptions"
        ).fetchall()
    label_descriptions = [{"label_id": r[0], "title": r[1], "description": r[2]} for r in rows]

    if not label_descriptions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No label descriptions configured. Add descriptions in Settings > Labels first.",
        )

    # Fetch tasks
    try:
        if body.task_ids:
            tasks = []
            for tid in body.task_ids:
                tasks.append(await vikunja.get_task(tid))
        else:
            all_tasks = await vikunja.list_tasks(per_page=200)
            tasks = [t for t in all_tasks if not t.get("done") and not (t.get("labels") or [])]
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

    if not tasks:
        return {"tagged": 0, "results": []}

    # Get LLM suggestions
    from app.models_registry import get_model_id
    model = get_model_id(body.model) if body.model else None
    tagger = AutoTagger()
    suggestions = await tagger.suggest_labels(tasks, label_descriptions, model=model)

    # Apply labels
    results = []
    tagged = 0
    for task in tasks:
        tid = task["id"]
        label_ids = suggestions.get(tid, [])
        if not label_ids:
            continue
        existing_label_ids = {l["id"] for l in (task.get("labels") or [])}
        added = []
        for lid in label_ids:
            if lid in existing_label_ids:
                continue
            try:
                await vikunja.add_label_to_task(tid, lid)
                added.append(lid)
            except VikunjaError:
                logger.warning("Failed to add label %d to task %d", lid, tid)
        if added:
            tagged += 1
            results.append({"task_id": tid, "labels_added": added})
            with get_db() as conn:
                RevisionService.record(
                    conn,
                    task_id=tid,
                    action_type="auto_tag",
                    source="auto_tag",
                    before_state=task,
                    after_state=None,
                    changes={"labels_added": added},
                )

    return {"tagged": tagged, "results": results}


# ── Single task routes ─────────────────────────────────────────────────


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get a single task by ID."""
    try:
        task = await vikunja.get_task(task_id)
        return _enrich_subtask_counts(task)
    except VikunjaError as e:
        logger.error("Failed to get task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.put("")
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Create a task in Vikunja.

    PUT creates in Vikunja (opposite of standard REST).
    """
    try:
        result = await vikunja.create_task(
            project_id=body.project_id,
            title=body.title,
            description=body.description,
            priority=body.priority,
            due_date=body.due_date,
            start_date=body.start_date,
            end_date=body.end_date,
            labels=body.labels,
        )
        if "project_id" not in result:
            result["project_id"] = body.project_id
        logger.info("Created task id=%s project=%s title=%r", result.get("id"), result.get("project_id"), body.title)
        with get_db() as conn:
            RevisionService.record(
                conn,
                task_id=result["id"],
                action_type="create",
                source="manual",
                after_state=result,
            )
        return result
    except VikunjaError as e:
        logger.error("Task creation failed: %s", e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Update a task in Vikunja.

    POST updates in Vikunja (opposite of standard REST).
    """
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    # Vikunja expects dates as RFC3339 — normalize and ensure timezone suffix
    for date_field in ("due_date", "start_date", "end_date"):
        if date_field in data and data[date_field]:
            val = data[date_field]
            if "T" not in val:
                data[date_field] = f"{val}T00:00:00Z"
            elif not val.endswith("Z") and "+" not in val:
                data[date_field] = f"{val}Z"

    try:
        before_state = await vikunja.get_task(task_id)
        result = await vikunja.update_task(task_id, data)

        # Determine action_type from which fields changed
        changed_keys = set(data.keys())
        if changed_keys == {"done"}:
            action_type = "complete"
        elif changed_keys == {"project_id"}:
            action_type = "move"
        else:
            action_type = "update"

        with get_db() as conn:
            RevisionService.record(
                conn,
                task_id=task_id,
                action_type=action_type,
                source="manual",
                before_state=before_state,
                after_state=result,
            )
        return result
    except VikunjaError as e:
        logger.error("Failed to update task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a task."""
    try:
        before_state = await vikunja.get_task(task_id)
        await vikunja.delete_task(task_id)
        with get_db() as conn:
            RevisionService.record(
                conn,
                task_id=task_id,
                action_type="delete",
                source="manual",
                before_state=before_state,
            )
        return {"success": True}
    except VikunjaError as e:
        logger.error("Failed to delete task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


class UpdatePositionRequest(BaseModel):
    position: float
    project_view_id: int


@router.post("/{task_id}/position")
async def update_task_position(
    task_id: int,
    body: UpdatePositionRequest,
    current_user: User = Depends(get_current_user),
):
    """Update a task's position within a view."""
    try:
        return await vikunja.update_task_position(
            task_id, body.position, body.project_view_id
        )
    except VikunjaError as e:
        logger.error("Failed to update position for task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.put("/{task_id}/labels")
async def add_label(
    task_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """Add a label to a task."""
    label_id = body.get("label_id")
    if not label_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="label_id required")
    try:
        return await vikunja.add_label_to_task(task_id, label_id)
    except VikunjaError as e:
        logger.error("Failed to add label to task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.delete("/{task_id}/labels/{label_id}")
async def remove_label(
    task_id: int,
    label_id: int,
    current_user: User = Depends(get_current_user),
):
    """Remove a label from a task."""
    try:
        await vikunja.remove_label_from_task(task_id, label_id)
        return {"success": True}
    except VikunjaError as e:
        logger.error("Failed to remove label %s from task %s: %s", label_id, task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


# ── Attachments ──────────────────────────────────────────────────────────

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB


@router.get("/{task_id}/attachments")
async def list_attachments(
    task_id: int,
    current_user: User = Depends(get_current_user),
):
    """List attachments for a task."""
    try:
        return await vikunja.list_attachments(task_id)
    except VikunjaError as e:
        logger.error("Failed to list attachments for task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.put("/{task_id}/attachments")
async def upload_attachment(
    task_id: int,
    files: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload an attachment to a task."""
    content = await files.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_UPLOAD_SIZE // (1024 * 1024)} MB)",
        )
    try:
        return await vikunja.upload_attachment(
            task_id,
            files.filename or "file",
            content,
            files.content_type or "application/octet-stream",
        )
    except VikunjaError as e:
        logger.error("Failed to upload attachment to task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.get("/{task_id}/attachments/{attachment_id}")
async def download_attachment(
    task_id: int,
    attachment_id: int,
    preview_size: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Download an attachment, optionally as a preview thumbnail."""
    try:
        content, content_type, filename = await vikunja.download_attachment(
            task_id, attachment_id, preview_size=preview_size
        )
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except VikunjaError as e:
        logger.error("Failed to download attachment %s: %s", attachment_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.delete("/{task_id}/attachments/{attachment_id}")
async def delete_attachment(
    task_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete an attachment."""
    try:
        await vikunja.delete_attachment(task_id, attachment_id)
        return {"success": True}
    except VikunjaError as e:
        logger.error("Failed to delete attachment %s: %s", attachment_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


# ── Subtasks ────────────────────────────────────────────────────────────


@router.get("/{task_id}/subtasks")
async def list_subtasks(
    task_id: int,
    current_user: User = Depends(get_current_user),
):
    """List subtasks for a task."""
    try:
        subtasks = await vikunja.get_subtasks(task_id)
        return {"subtasks": subtasks}
    except VikunjaError as e:
        logger.error("Failed to list subtasks for task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.put("/{task_id}/subtasks")
async def create_subtask(
    task_id: int,
    body: SubtaskCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a subtask. Inherits parent's project_id if not specified."""
    try:
        project_id = body.project_id
        if not project_id:
            parent = await vikunja.get_task(task_id)
            project_id = parent["project_id"]
        result = await vikunja.create_subtask(task_id, body.title, project_id)
        return result
    except VikunjaError as e:
        logger.error("Failed to create subtask for task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/{task_id}/subtasks/{subtask_id}")
async def update_subtask(
    task_id: int,
    subtask_id: int,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a subtask."""
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    try:
        return await vikunja.update_task(subtask_id, data)
    except VikunjaError as e:
        logger.error("Failed to update subtask %s: %s", subtask_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.delete("/{task_id}/subtasks/{subtask_id}")
async def delete_subtask(
    task_id: int,
    subtask_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a subtask and its relation."""
    try:
        await vikunja.delete_subtask(task_id, subtask_id)
        return {"message": "ok"}
    except VikunjaError as e:
        logger.error("Failed to delete subtask %s: %s", subtask_id, e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

"""
Router: /api/tasks

Vikunja task proxy (Spec §3.2).
Proxies task CRUD operations to Vikunja, injecting the API token server-side
so the frontend never needs direct Vikunja access.

NOTE: Vikunja uses PUT to create and POST to update (opposite of standard REST).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.vikunja import VikunjaError, vikunja

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    priority: int = 3
    due_date: Optional[str] = None  # ISO date YYYY-MM-DD
    labels: Optional[list[str]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[str] = None
    done: Optional[bool] = None
    project_id: Optional[int] = None


@router.get("")
async def list_tasks(
    project_id: Optional[int] = Query(None),
    s: Optional[str] = Query(None),
    filter: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    order_by: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
):
    """List tasks across all projects or for a specific project."""
    try:
        tasks = await vikunja.list_tasks(
            project_id=project_id,
            filter=filter,
            sort_by=sort_by,
            order_by=order_by,
            page=page,
            per_page=per_page,
            s=s,
        )
        return {"tasks": tasks}
    except VikunjaError as e:
        logger.error("Failed to list tasks: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get a single task by ID."""
    try:
        return await vikunja.get_task(task_id)
    except VikunjaError as e:
        logger.error("Failed to get task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


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
            labels=body.labels,
        )
        if "project_id" not in result:
            result["project_id"] = body.project_id
        logger.info("Created task id=%s project=%s title=%r", result.get("id"), result.get("project_id"), body.title)
        return result
    except VikunjaError as e:
        logger.error("Task creation failed: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


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

    # Vikunja expects due_date as RFC3339
    if "due_date" in data and data["due_date"]:
        data["due_date"] = f"{data['due_date']}T00:00:00Z"

    try:
        return await vikunja.update_task(task_id, data)
    except VikunjaError as e:
        logger.error("Failed to update task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a task."""
    try:
        await vikunja.delete_task(task_id)
        return {"success": True}
    except VikunjaError as e:
        logger.error("Failed to delete task %s: %s", task_id, e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

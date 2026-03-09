"""
Router: /api/labels

Vikunja label proxy (Spec §3.2).
Proxies label management to Vikunja, injecting the API token server-side.

NOTE: Label updates use PUT (same as task creation — Vikunja convention).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.vikunja import VikunjaError, vikunja

router = APIRouter(prefix="/api/labels", tags=["labels"])


class LabelCreate(BaseModel):
    title: str
    hex_color: Optional[str] = None
    description: Optional[str] = None


@router.get("")
async def list_labels(current_user: User = Depends(get_current_user)):
    """Return all labels."""
    try:
        labels = await vikunja.list_labels()
        return {"labels": labels}
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.put("")
async def create_label(
    body: LabelCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a label. PUT creates in Vikunja."""
    try:
        return await vikunja.create_label(body.model_dump(exclude_none=True))
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


class LabelUpdate(BaseModel):
    title: Optional[str] = None
    hex_color: Optional[str] = None
    description: Optional[str] = None


@router.put("/{label_id}")
async def update_label(
    label_id: int,
    body: LabelUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a label. PUT updates in Vikunja."""
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    try:
        return await vikunja.update_label(label_id, data)
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.delete("/{label_id}")
async def delete_label(
    label_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a label."""
    try:
        await vikunja.delete_label(label_id)
        return {"success": True}
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


# ── Label Descriptions (SQLite) ──────────────────────────────────────────


class LabelDescriptionUpsert(BaseModel):
    title: str
    description: str


@router.get("/descriptions")
async def list_descriptions(current_user: User = Depends(get_current_user)):
    """Return all label descriptions from SQLite."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT label_id, title, description, created_at, updated_at FROM label_descriptions ORDER BY label_id"
        ).fetchall()
    return {
        "descriptions": [
            {"label_id": r[0], "title": r[1], "description": r[2], "created_at": r[3], "updated_at": r[4]}
            for r in rows
        ]
    }


@router.put("/{label_id}/description")
async def upsert_description(
    label_id: int,
    body: LabelDescriptionUpsert,
    current_user: User = Depends(get_current_user),
):
    """Upsert a label description."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO label_descriptions (label_id, title, description, updated_at)
               VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%S', 'now'))
               ON CONFLICT(label_id) DO UPDATE SET
                 title = excluded.title,
                 description = excluded.description,
                 updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now')""",
            [label_id, body.title, body.description],
        )
    return {"label_id": label_id, "title": body.title, "description": body.description}


@router.delete("/{label_id}/description")
async def delete_description(
    label_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a label description."""
    with get_db() as conn:
        conn.execute("DELETE FROM label_descriptions WHERE label_id = ?", [label_id])
    return {"success": True}


# ── Label Stats ──────────────────────────────────────────────────────────


@router.get("/stats")
async def label_stats(current_user: User = Depends(get_current_user)):
    """Return per-label task counts (total, done, open)."""
    try:
        tasks = await vikunja.list_tasks(per_page=500)
    except VikunjaError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    stats: dict[int, dict] = {}
    for task in tasks:
        for label in task.get("labels") or []:
            lid = label["id"]
            if lid not in stats:
                stats[lid] = {"total": 0, "done": 0, "open": 0}
            stats[lid]["total"] += 1
            if task.get("done"):
                stats[lid]["done"] += 1
            else:
                stats[lid]["open"] += 1

    return {"stats": stats}

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

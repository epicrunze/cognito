"""TaskProposal model and related schemas."""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskProposal(BaseModel):
    """Full proposal as stored in the DB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    title: str
    description: Optional[str] = None
    project_name: Optional[str] = None
    project_id: Optional[int] = None
    priority: int = 3
    due_date: Optional[date] = None
    estimated_minutes: Optional[int] = None
    labels: list[str] = Field(default_factory=list)
    source_type: str = "notes"
    source_text: str = ""
    confidential: bool = False
    status: str = "pending"
    vikunja_task_id: Optional[int] = None
    gcal_event_id: Optional[str] = None
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None


class TaskProposalCreate(BaseModel):
    """LLM-extracted proposal before it's saved (no DB fields)."""
    title: str
    description: Optional[str] = None
    project_name: Optional[str] = None
    project_id: Optional[int] = None
    priority: int = 3
    due_date: Optional[date] = None
    estimated_minutes: Optional[int] = None
    labels: list[str] = Field(default_factory=list)


class TaskProposalUpdate(BaseModel):
    """Partial update — all fields optional for inline editing."""
    title: Optional[str] = None
    description: Optional[str] = None
    project_name: Optional[str] = None
    project_id: Optional[int] = None
    priority: Optional[int] = None
    due_date: Optional[date] = None
    estimated_minutes: Optional[int] = None
    labels: Optional[list[str]] = None

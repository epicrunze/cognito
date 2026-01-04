"""
Entry models for journal entries.

Pydantic models for Entry data representation following spec Section 3.1.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Individual message in a conversation."""

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime


class Conversation(BaseModel):
    """Conversation structure within an Entry."""

    id: UUID
    started_at: datetime
    messages: list[Message] = Field(default_factory=list)
    prompt_source: Literal["user", "notification", "continuation"]
    notification_id: Optional[UUID] = None


class EntryCreate(BaseModel):
    """Request model for creating an entry."""

    date: str  # YYYY-MM-DD format
    conversations: list[Conversation] = Field(default_factory=list)
    refined_output: str = ""


class EntryUpdate(BaseModel):
    """Request model for updating an entry (partial updates)."""

    conversations: Optional[list[Conversation]] = None
    refined_output: Optional[str] = None
    relevance_score: Optional[float] = None
    status: Optional[Literal["active", "archived"]] = None
    pending_refine: Optional[bool] = None
    refine_status: Optional[Literal["idle", "processing", "completed", "failed"]] = None
    refine_error: Optional[str] = None


class Entry(BaseModel):
    """Entry response model."""

    id: UUID
    date: str  # YYYY-MM-DD format
    conversations: list[Conversation] = Field(default_factory=list)
    refined_output: str = ""
    relevance_score: float = 1.0
    last_interacted_at: datetime
    interaction_count: int = 0
    status: Literal["active", "archived"] = "active"
    pending_refine: bool = False
    refine_status: Literal["idle", "processing", "completed", "failed"] = "idle"
    refine_error: Optional[str] = None
    version: int = 1
    created_at: datetime
    updated_at: datetime


class EntryInDB(Entry):
    """Entry with database-specific fields."""

    user_id: UUID


class EntryVersion(BaseModel):
    """Entry version snapshot for conflict resolution."""

    id: UUID
    entry_id: UUID
    version: int
    content_snapshot: str
    created_at: datetime

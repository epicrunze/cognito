"""
Chat models for conversational journaling.

Pydantic models for Chat API requests and responses.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for sending a chat message."""

    entry_id: UUID
    conversation_id: Optional[UUID] = None  # None for new conversation
    message: str
    use_local_model: bool = False


class ChatResponse(BaseModel):
    """Response model for chat message."""

    response: str
    conversation_id: UUID
    entry_id: UUID


class RefineRequest(BaseModel):
    """Request model for refining an entry."""

    entry_id: UUID
    use_local_model: bool = False


class RefineResponse(BaseModel):
    """Response model for refined entry."""

    refined_output: str
    entry_id: UUID

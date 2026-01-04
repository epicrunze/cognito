"""
Chat router.

Handles chat endpoints for conversational journaling with LLM integration.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.chat import ChatRequest, ChatResponse, RefineRequest, RefineResponse
from app.models.entry import Conversation, Message
from app.models.user import User
from app.repositories import entry_repo, user_repo
from app.services.chat import (
    ChatService,
    ChatServiceError,
    EntryNotFoundError,
    ConversationNotFoundError,
    NoConversationsError,
    LLMError,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# Request/Response models for new endpoints
class QueueRefineRequest(BaseModel):
    """Request model for queuing an entry for refinement."""
    entry_id: UUID


class RefineQueueResponse(BaseModel):
    """Response model for queue refine operation."""
    queued: bool
    entry_id: UUID
    message: str


class RefineStatusResponse(BaseModel):
    """Response model for refine status."""
    entry_id: UUID
    pending_refine: bool
    refine_status: str
    refine_error: Optional[str] = None


def _get_user_id(conn, current_user: User) -> UUID:
    """Get user ID from database."""
    db_user = user_repo.get_user_by_email(conn, current_user.email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User not found - authentication error",
        )
    return db_user.id


def _build_context_messages(conversations: list[Conversation]) -> list[dict]:
    """Build message history for LLM context from conversations."""
    messages = []
    for conv in conversations:
        for msg in conv.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
    return messages


def _format_conversations_for_refine(conversations: list[Conversation]) -> str:
    """Format all conversations as text for the refine prompt."""
    parts = []

    for i, conv in enumerate(conversations, 1):
        parts.append(f"## Conversation {i}")
        parts.append(f"Started: {conv.started_at.isoformat()}")
        parts.append("")

        for msg in conv.messages:
            role = "User" if msg.role == "user" else "Assistant"
            parts.append(f"**{role}:** {msg.content}")
            parts.append("")

        parts.append("---")
        parts.append("")

    return "\n".join(parts)


@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    Send a message and get an LLM response.

    Creates a new conversation if conversation_id is not provided.
    Stores both user message and assistant response in the entry.

    Args:
        request: Chat request with entry_id, optional conversation_id, message

    Returns:
        ChatResponse with LLM response and conversation_id

    Raises:
        404: Entry not found
        403: Entry belongs to different user
    """
    with get_db() as conn:
        user_id = _get_user_id(conn, current_user)
        chat_service = ChatService(conn, user_id)

        try:
            result = await chat_service.send_message(
                entry_id=request.entry_id,
                message=request.message,
                conversation_id=request.conversation_id,
                use_local_model=request.use_local_model,
            )
            return ChatResponse(
                response=result["response"],
                conversation_id=result["conversation_id"],
                entry_id=result["entry_id"],
            )
        except EntryNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entry not found",
            )
        except ConversationNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        except LLMError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LLM service error: {str(e)}",
            )


@router.post("/refine", response_model=RefineResponse)
async def refine_entry(
    request: RefineRequest,
    current_user: User = Depends(get_current_user),
) -> RefineResponse:
    """
    Generate a refined output from all conversations in an entry.

    Uses the LLM to synthesize all conversations into a coherent journal entry.

    Args:
        request: Refine request with entry_id

    Returns:
        RefineResponse with the refined output

    Raises:
        404: Entry not found
        403: Entry belongs to different user
        400: No conversations to refine
    """
    with get_db() as conn:
        user_id = _get_user_id(conn, current_user)
        chat_service = ChatService(conn, user_id)

        try:
            result = await chat_service.refine_entry(
                entry_id=request.entry_id,
                use_local_model=request.use_local_model,
            )
            return RefineResponse(
                refined_output=result["refined_output"],
                entry_id=result["entry_id"],
            )
        except EntryNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entry not found",
            )
        except NoConversationsError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No conversations to refine",
            )
        except LLMError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LLM service error: {str(e)}",
            )


@router.post("/refine/queue", response_model=RefineQueueResponse)
async def queue_refine(
    request: QueueRefineRequest,
    current_user: User = Depends(get_current_user),
) -> RefineQueueResponse:
    """
    Queue an entry for refinement.

    Sets pending_refine=True if not already pending or processing.
    The entry will be refined by the background sync process.

    Args:
        request: Queue refine request with entry_id

    Returns:
        RefineQueueResponse indicating if queued successfully
    """
    with get_db() as conn:
        user_id = _get_user_id(conn, current_user)

        # Check entry exists
        entry = entry_repo.get_entry_by_id(conn, request.entry_id, user_id)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entry not found",
            )

        # Try to set pending_refine flag
        queued = entry_repo.set_pending_refine(conn, request.entry_id, user_id)

        if queued:
            return RefineQueueResponse(
                queued=True,
                entry_id=request.entry_id,
                message="Entry queued for refinement",
            )
        else:
            return RefineQueueResponse(
                queued=False,
                entry_id=request.entry_id,
                message="Entry is already pending or processing refinement",
            )


@router.get("/refine/status", response_model=RefineStatusResponse)
async def get_refine_status(
    entry_id: UUID = Query(..., description="Entry ID to check status for"),
    current_user: User = Depends(get_current_user),
) -> RefineStatusResponse:
    """
    Get refinement status for an entry.

    Args:
        entry_id: Entry ID to check

    Returns:
        RefineStatusResponse with current status
    """
    with get_db() as conn:
        user_id = _get_user_id(conn, current_user)

        entry = entry_repo.get_entry_by_id(conn, entry_id, user_id)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entry not found",
            )

        return RefineStatusResponse(
            entry_id=entry_id,
            pending_refine=entry.pending_refine,
            refine_status=entry.refine_status,
            refine_error=entry.refine_error,
        )

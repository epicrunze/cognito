"""
Chat router.

Handles chat endpoints for conversational journaling with LLM integration.
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.chat import ChatRequest, ChatResponse, RefineRequest, RefineResponse
from app.models.entry import Conversation, Message
from app.models.user import User
from app.repositories import entry_repo, user_repo
from app.services.llm import llm_router

router = APIRouter(prefix="/api/chat", tags=["chat"])


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

        # Get the entry
        entry = entry_repo.get_entry_by_id(conn, request.entry_id, user_id)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entry not found",
            )

        # Parse existing conversations
        conversations_data = entry.conversations
        if isinstance(conversations_data, str):
            conversations_data = json.loads(conversations_data)

        conversations = [
            Conversation(**c) if isinstance(c, dict) else c
            for c in conversations_data
        ]

        # Find or create conversation
        conversation_id = request.conversation_id
        current_conversation: Optional[Conversation] = None

        if conversation_id:
            # Find existing conversation
            for conv in conversations:
                if conv.id == conversation_id:
                    current_conversation = conv
                    break

            if not current_conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
        else:
            # Create new conversation
            conversation_id = uuid4()
            current_conversation = Conversation(
                id=conversation_id,
                started_at=datetime.utcnow(),
                messages=[],
                prompt_source="user",
                notification_id=None,
            )
            conversations.append(current_conversation)

        # Add user message
        now = datetime.utcnow()
        user_message = Message(
            role="user",
            content=request.message,
            timestamp=now,
        )
        current_conversation.messages.append(user_message)

        # Build context from all messages in this conversation
        context_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in current_conversation.messages
        ]

        # Get LLM response
        try:
            response_text = await llm_router.chat(
                messages=context_messages,
                use_local_model=request.use_local_model,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LLM service error: {str(e)}",
            )

        # Add assistant message
        assistant_message = Message(
            role="assistant",
            content=response_text,
            timestamp=datetime.utcnow(),
        )
        current_conversation.messages.append(assistant_message)

        # Update entry with modified conversations
        conversations_list = [
            conv.model_dump(mode="json") for conv in conversations
        ]

        from app.models.entry import EntryUpdate
        update_data = EntryUpdate(
            conversations=conversations,
        )
        entry_repo.update_entry(conn, request.entry_id, user_id, update_data)

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            entry_id=request.entry_id,
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

        # Get the entry
        entry = entry_repo.get_entry_by_id(conn, request.entry_id, user_id)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entry not found",
            )

        # Parse conversations
        conversations_data = entry.conversations
        if isinstance(conversations_data, str):
            conversations_data = json.loads(conversations_data)

        conversations = [
            Conversation(**c) if isinstance(c, dict) else c
            for c in conversations_data
        ]

        if not conversations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No conversations to refine",
            )

        # Format conversations for the refine prompt
        conversations_text = _format_conversations_for_refine(conversations)

        # Get refined output from LLM
        try:
            refined_output = await llm_router.refine(
                conversations_text=conversations_text,
                use_local_model=request.use_local_model,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LLM service error: {str(e)}",
            )

        # Update entry with refined output
        from app.models.entry import EntryUpdate
        update_data = EntryUpdate(refined_output=refined_output)
        entry_repo.update_entry(conn, request.entry_id, user_id, update_data)

        return RefineResponse(
            refined_output=refined_output,
            entry_id=request.entry_id,
        )

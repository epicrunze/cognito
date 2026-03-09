"""
Router: /api/chat

Conversational task extraction — chat mode.
Users can have a back-and-forth conversation with the AI,
and it will extract tasks as proposals inline.
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.extractor import TaskExtractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    model: str = "gemini-flash"


@router.post("")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Send a chat message. Returns AI reply + any extracted proposals.

    Creates a new conversation if conversation_id is not provided.
    """
    if not body.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    conversation_id = body.conversation_id or str(uuid.uuid4())

    with get_db() as conn:
        # Create conversation if new
        existing = conn.execute(
            "SELECT id FROM conversations WHERE id = ?", [conversation_id]
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO conversations (id, user_id) VALUES (?, ?)",
                [conversation_id, current_user.email],
            )

        # Load conversation history
        rows = conn.execute(
            "SELECT role, content FROM conversation_messages WHERE conversation_id = ? ORDER BY id",
            [conversation_id],
        ).fetchall()
        history = [{"role": r[0], "content": r[1]} for r in rows]

    # Build context for extraction
    context_parts = []
    for msg in history[-10:]:  # Last 10 messages for context
        context_parts.append(f"{msg['role'].upper()}: {msg['content']}")
    context_parts.append(f"USER: {body.message}")
    full_text = "\n\n".join(context_parts)

    # Extract tasks
    extractor = TaskExtractor()
    try:
        proposals = await extractor.extract(
            text=full_text,
            source_type="chat",
            model=body.model,
        )
    except Exception as e:
        logger.exception("Chat extraction failed")
        proposals = []

    # Generate a conversational reply
    from app.models_registry import get_model_id
    from app.services.llm import get_llm_client

    resolved_model = get_model_id(body.model)
    llm = get_llm_client(model=resolved_model)

    reply_prompt = (
        "You are a helpful task management assistant. The user is having a conversation with you. "
        "Respond naturally and briefly. If you extracted tasks, acknowledge them. "
        "Keep responses under 3 sentences unless the user asks a detailed question."
    )

    reply_messages = history[-6:] + [{"role": "user", "content": body.message}]
    if proposals:
        task_summary = ", ".join(f'"{p.title}"' for p in proposals[:5])
        reply_messages.append({
            "role": "assistant",
            "content": f"[System: I extracted these tasks: {task_summary}]",
        })

    try:
        reply = await llm.generate(
            messages=reply_messages,
            system_prompt=reply_prompt,
        )
    except Exception:
        reply = f"I extracted {len(proposals)} task{'s' if len(proposals) != 1 else ''} from your message." if proposals else "I couldn't extract any tasks from that. Could you give me more details?"

    # Save messages
    proposals_json = json.dumps([p.model_dump(mode="json") for p in proposals]) if proposals else None
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversation_messages (conversation_id, role, content) VALUES (?, 'user', ?)",
            [conversation_id, body.message],
        )
        conn.execute(
            "INSERT INTO conversation_messages (conversation_id, role, content, proposals_json) VALUES (?, 'assistant', ?, ?)",
            [conversation_id, reply, proposals_json],
        )
        conn.execute(
            "UPDATE conversations SET updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now') WHERE id = ?",
            [conversation_id],
        )

    return {
        "reply": reply,
        "proposals": [p.model_dump(mode="json") for p in proposals],
        "conversation_id": conversation_id,
    }


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Load a conversation's message history."""
    with get_db() as conn:
        conv = conn.execute(
            "SELECT id, user_id, created_at, updated_at FROM conversations WHERE id = ?",
            [conversation_id],
        ).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        rows = conn.execute(
            "SELECT role, content, proposals_json, created_at FROM conversation_messages WHERE conversation_id = ? ORDER BY id",
            [conversation_id],
        ).fetchall()

    messages = []
    for r in rows:
        msg = {"role": r[0], "content": r[1], "created_at": r[3]}
        if r[2]:
            msg["proposals"] = json.loads(r[2])
        messages.append(msg)

    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "created_at": conv[2],
        "updated_at": conv[3],
    }

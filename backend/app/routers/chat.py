"""
Router: /api/chat

Conversational task extraction + task modification via ChatAgent.
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.agent import ChatAgent
from app.services.vikunja import vikunja

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
    Send a chat message. Returns AI reply + any extracted proposals + actions.

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

    # Process via ChatAgent
    agent = ChatAgent()
    try:
        result = await agent.process(
            message=body.message,
            history=history,
            model=body.model,
        )
    except Exception:
        logger.exception("ChatAgent processing failed")
        result = {
            "reply": "Sorry, I had trouble processing that. Could you try again?",
            "proposals": [],
            "actions": [],
            "pending_actions": [],
        }

    reply = result["reply"]
    proposals = result["proposals"]
    actions = result["actions"]
    pending_actions = result["pending_actions"]

    # Save messages
    proposals_json = json.dumps([p.model_dump(mode="json") for p in proposals]) if proposals else None
    all_actions = actions + pending_actions
    actions_json = json.dumps(all_actions) if all_actions else None

    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversation_messages (conversation_id, role, content) VALUES (?, 'user', ?)",
            [conversation_id, body.message],
        )
        conn.execute(
            "INSERT INTO conversation_messages (conversation_id, role, content, proposals_json, actions_json) "
            "VALUES (?, 'assistant', ?, ?, ?)",
            [conversation_id, reply, proposals_json, actions_json],
        )
        conn.execute(
            "UPDATE conversations SET updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now') WHERE id = ?",
            [conversation_id],
        )

    return {
        "reply": reply,
        "proposals": [p.model_dump(mode="json") for p in proposals],
        "actions": actions,
        "pending_actions": pending_actions,
        "conversation_id": conversation_id,
    }


class ExecuteActionRequest(BaseModel):
    type: str
    task_id: int
    changes: dict | None = None
    project_id: int | None = None


@router.post("/execute-action")
async def execute_action(
    body: ExecuteActionRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute a previously pending action after user approval."""
    try:
        if body.type == "update":
            if not body.changes:
                raise HTTPException(status_code=400, detail="changes required for update action")
            await vikunja.update_task(body.task_id, body.changes)
        elif body.type == "complete":
            await vikunja.update_task(body.task_id, {"done": True})
        elif body.type == "move":
            if not body.project_id:
                raise HTTPException(status_code=400, detail="project_id required for move action")
            await vikunja.update_task(body.task_id, {"project_id": body.project_id})
        elif body.type == "delete":
            await vikunja.delete_task(body.task_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action type: {body.type}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to execute action")
        raise HTTPException(status_code=500, detail=str(e))

    return {"success": True}


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
            "SELECT role, content, proposals_json, actions_json, created_at "
            "FROM conversation_messages WHERE conversation_id = ? ORDER BY id",
            [conversation_id],
        ).fetchall()

    messages = []
    for r in rows:
        msg = {"role": r[0], "content": r[1], "created_at": r[4]}
        if r[2]:
            msg["proposals"] = json.loads(r[2])
        if r[3]:
            msg["actions"] = json.loads(r[3])
        messages.append(msg)

    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "created_at": conv[2],
        "updated_at": conv[3],
    }

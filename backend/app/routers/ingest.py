"""Ingest router — POST /api/ingest with optional SSE streaming."""

import asyncio
import json
import logging
import uuid
from typing import AsyncIterator

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.extractor import TaskExtractor

router = APIRouter(prefix="/api", tags=["ingest"])


def _save_conversation(user_email: str, user_text: str, proposals: list) -> str:
    """Persist an extract interaction as a conversation with messages."""
    conversation_id = str(uuid.uuid4())
    proposals_json = json.dumps([p.model_dump(mode='json') for p in proposals])
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, user_id) VALUES (?, ?)",
            [conversation_id, user_email],
        )
        conn.execute(
            "INSERT INTO conversation_messages (conversation_id, role, content) "
            "VALUES (?, 'user', ?)",
            [conversation_id, user_text],
        )
        conn.execute(
            "INSERT INTO conversation_messages (conversation_id, role, content, proposals_json) "
            "VALUES (?, 'assistant', '', ?)",
            [conversation_id, proposals_json],
        )
    return conversation_id


class IngestRequest(BaseModel):
    text: str
    source_type: str = "notes"  # notes | email | idea | manual
    confidential: bool = False
    project_hint: str | None = None
    model: str = "gemini-flash"


@router.post("/ingest")
async def ingest(
    body: IngestRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Accept unstructured text, extract task proposals via LLM tool-calling.

    Returns standard JSON by default.
    If the client sends `Accept: text/event-stream`, streams proposals as SSE
    events so they appear in the UI as each one is extracted.
    """
    if not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input text cannot be empty.",
        )

    accept = request.headers.get("accept", "")
    use_sse = "text/event-stream" in accept

    extractor = TaskExtractor()

    if use_sse:
        # SSE: stream proposals as they're extracted
        # Note: current extraction is atomic (all proposals returned at once),
        # so we emit them one by one after extraction completes.
        async def event_generator() -> AsyncIterator[dict]:
            try:
                proposals = await extractor.extract(
                    text=body.text,
                    source_type=body.source_type,
                    model=body.model,
                    project_hint=body.project_hint,
                )
                for proposal in proposals:
                    yield {"event": "proposal", "data": proposal.model_dump_json()}
                    await asyncio.sleep(0.05)  # small delay for visual effect

                done_data: dict = {"count": len(proposals)}
                if proposals:
                    conversation_id = _save_conversation(
                        current_user.email, body.text, proposals
                    )
                    done_data["conversation_id"] = conversation_id

                yield {"event": "done", "data": json.dumps(done_data)}
            except Exception as e:
                logger.exception("Extraction failed")
                yield {"event": "error", "data": json.dumps({"detail": str(e)})}

        return EventSourceResponse(event_generator())

    # Standard JSON response
    proposals = await extractor.extract(
        text=body.text,
        source_type=body.source_type,
        model=body.model,
        project_hint=body.project_hint,
    )

    result: dict = {
        "source_id": proposals[0].source_id if proposals else None,
        "proposals": [p.model_dump() for p in proposals],
    }
    if proposals:
        result["conversation_id"] = _save_conversation(
            current_user.email, body.text, proposals
        )
    return result

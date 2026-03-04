"""Ingest router — POST /api/ingest with optional SSE streaming."""

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.extractor import TaskExtractor

router = APIRouter(prefix="/api", tags=["ingest"])


class IngestRequest(BaseModel):
    text: str
    source_type: str = "notes"  # notes | email | idea | manual
    confidential: bool = False
    project_hint: str | None = None


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
    if body.confidential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confidential mode (Ollama) is coming in Phase 2.",
        )

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
                    confidential=body.confidential,
                    project_hint=body.project_hint,
                )
                for proposal in proposals:
                    yield {"event": "proposal", "data": proposal.model_dump_json()}
                    await asyncio.sleep(0.05)  # small delay for visual effect
                yield {"event": "done", "data": json.dumps({"count": len(proposals)})}
            except Exception as e:
                yield {"event": "error", "data": json.dumps({"detail": str(e)})}

        return EventSourceResponse(event_generator())

    # Standard JSON response
    proposals = await extractor.extract(
        text=body.text,
        source_type=body.source_type,
        confidential=body.confidential,
        project_hint=body.project_hint,
    )

    return {
        "source_id": proposals[0].source_id if proposals else None,
        "proposals": [p.model_dump() for p in proposals],
    }

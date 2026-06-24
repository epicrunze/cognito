# backend/app/routers/knowledge.py
"""Read endpoints for the OKF knowledge layer."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.knowledge import (ConceptDetail, ConceptSummary, GraphResponse,
                                   RefreshResult)
from app.models.user import User
from app.services.knowledge import search
from app.services.knowledge.materializer import build_materializer, ensure_fresh

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/search", response_model=list[ConceptSummary])
async def search_knowledge(
    q: str = Query(..., min_length=1),
    type: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    with get_db() as conn:
        await ensure_fresh(conn)
        return search.search_concepts(conn, q, type=type, source=source, limit=limit)


@router.get("/concept/{concept_id:path}", response_model=ConceptDetail)
async def get_concept(concept_id: str, current_user: User = Depends(get_current_user)):
    with get_db() as conn:
        await ensure_fresh(conn)
        detail = search.concept_detail(conn, concept_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Concept not found")
        return detail


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    root: str | None = Query(None),
    depth: int | None = Query(None, ge=1, le=10),
    current_user: User = Depends(get_current_user),
):
    with get_db() as conn:
        await ensure_fresh(conn)
        return search.graph(conn, root=root, depth=depth)


@router.get("/index", response_class=Response)
async def get_index(current_user: User = Depends(get_current_user)):
    with get_db() as conn:
        await ensure_fresh(conn)
        return Response(content=search.synth_index(conn), media_type="text/markdown")


@router.post("/refresh", response_model=RefreshResult)
async def refresh_knowledge(current_user: User = Depends(get_current_user)):
    with get_db() as conn:
        return await build_materializer(conn).rebuild()

"""Reusable read primitive over the materialized knowledge cache.

Wraps the Phase 1 search functions and owns freshness (ensure_fresh) plus its
own DB connection, so callers (ChatAgent now; briefing/digest later) need not
thread a connection. Returns plain dicts for LLM tool results, not pydantic.
"""

from app.database import get_db
from app.services.knowledge import search
from app.services.knowledge.materializer import ensure_fresh


class KnowledgeRetriever:
    DEFAULT_LIMIT = 5
    BODY_CHAR_BUDGET = 4000

    async def search(self, query: str, type: str | None = None,
                     source: str | None = None, limit: int = 5) -> list[dict]:
        capped = min(limit, self.DEFAULT_LIMIT)
        with get_db() as conn:
            await ensure_fresh(conn)
            return search.search_concepts(conn, query, type=type, source=source, limit=capped)

    async def get(self, concept_id: str) -> dict | None:
        with get_db() as conn:
            await ensure_fresh(conn)
            detail = search.concept_detail(conn, concept_id)
        if detail and len(detail.get("body") or "") > self.BODY_CHAR_BUDGET:
            detail["body"] = detail["body"][:self.BODY_CHAR_BUDGET] + "\n\n…[truncated]"
        return detail

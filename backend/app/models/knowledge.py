"""Pydantic response models for the /api/knowledge endpoints."""

from pydantic import BaseModel


class ConceptSummary(BaseModel):
    concept_id: str
    type: str
    source: str
    title: str | None = None
    description: str | None = None
    snippet: str | None = None


class ConceptDetail(BaseModel):
    concept_id: str
    source: str
    type: str
    title: str | None = None
    description: str | None = None
    resource: str | None = None
    tags: list[str] = []
    timestamp: str | None = None
    frontmatter: dict = {}
    body: str = ""
    links: list[str] = []
    backlinks: list[str] = []


class GraphNode(BaseModel):
    concept_id: str
    type: str
    source: str
    title: str | None = None


class GraphEdge(BaseModel):
    src: str
    dst: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class RefreshResult(BaseModel):
    concepts: int
    failed_sources: list[str] = []

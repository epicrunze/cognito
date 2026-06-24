"""Common concept model and source-adapter interface for the knowledge layer."""

from dataclasses import dataclass, field


@dataclass
class FieldCaps:
    """Per-concept write contract. Consumed in Phase 2; declared in Phase 1."""
    writable: dict[str, str]      # field name -> route description
    readonly: list[str]           # derived/immutable fields mutations must refuse


@dataclass
class Concept:
    concept_id: str
    type: str
    source: str                   # "vikunja" | "notes" | "native"
    title: str | None = None
    description: str | None = None
    resource: str | None = None
    tags: list[str] = field(default_factory=list)
    timestamp: str | None = None
    frontmatter: dict = field(default_factory=dict)
    body: str = ""


class SourceAdapter:
    """Projects one source of truth into Concepts. Read-only in Phase 1."""

    source_name: str = "base"

    async def list_concepts(self) -> list[Concept]:
        raise NotImplementedError

    async def get_concept(self, concept_id: str) -> Concept | None:
        raise NotImplementedError

    def field_capabilities(self, concept: Concept) -> FieldCaps:
        """Default: nothing writable. Adapters override."""
        return FieldCaps(writable={}, readonly=[])

    def owns(self, concept_id: str) -> bool:
        """Whether this adapter owns *concept_id* (used for refresh routing)."""
        raise NotImplementedError

"""Adapter projecting Vikunja projects into OKF concepts."""

from app.services.knowledge.adapters.base import Concept, FieldCaps, SourceAdapter


class VikunjaProjectAdapter(SourceAdapter):
    source_name = "vikunja"

    def __init__(self, vikunja):
        self._vik = vikunja

    def owns(self, concept_id: str) -> bool:
        # Owns "projects/<id>" but NOT "projects/<id>/notes".
        if not concept_id.startswith("projects/"):
            return False
        rest = concept_id[len("projects/"):]
        return "/" not in rest

    def _to_concept(self, project: dict) -> Concept:
        pid = project["id"]
        desc = (project.get("description") or "").strip()
        body = "\n".join([
            f"# {project.get('title', '')}",
            "",
            desc or "_No description._",
            "",
            f"See [notes](/projects/{pid}/notes.md).",
        ])
        return Concept(
            concept_id=f"projects/{pid}",
            type="Project",
            source="vikunja",
            title=project.get("title"),
            description=desc or None,
            resource=None,
            tags=[],
            timestamp=project.get("updated"),
            frontmatter={"type": "Project", "project_id": pid},
            body=body,
        )

    async def list_concepts(self) -> list[Concept]:
        projects = await self._vik.list_projects()
        return [self._to_concept(p) for p in projects]

    async def get_concept(self, concept_id: str) -> Concept | None:
        if not self.owns(concept_id):
            return None
        pid = int(concept_id.split("/", 1)[1])
        project = await self._vik.get_project(pid)
        return self._to_concept(project) if project else None

    def field_capabilities(self, concept: Concept) -> FieldCaps:
        return FieldCaps(
            writable={
                "title": "vikunja.update_project(title=…)",
                "description": "vikunja.update_project(description=…)",
            },
            readonly=["project_id"],
        )

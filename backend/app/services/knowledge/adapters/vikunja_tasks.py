"""Adapter projecting Vikunja tasks into OKF concepts."""

from app.services.knowledge.adapters.base import Concept, FieldCaps, SourceAdapter


def _task_body(task: dict) -> str:
    desc = (task.get("description") or "").strip()
    labels = ", ".join(l.get("title", "") for l in task.get("labels") or []) or "—"
    lines = [
        f"# {task.get('title', '')}",
        "",
        desc or "_No description._",
        "",
        "## Metadata",
        f"- Status: {'done' if task.get('done') else 'open'}",
        f"- Priority: {task.get('priority', 0)}",
        f"- Due: {task.get('due_date') or '—'}",
        f"- Labels: {labels}",
        "",
        f"Part of [project](/projects/{task.get('project_id')}.md).",
    ]
    return "\n".join(lines)


class VikunjaTaskAdapter(SourceAdapter):
    source_name = "vikunja"

    def __init__(self, vikunja):
        self._vik = vikunja

    def owns(self, concept_id: str) -> bool:
        return concept_id.startswith("tasks/")

    def _to_concept(self, task: dict) -> Concept:
        tags = [l.get("title", "") for l in task.get("labels") or []]
        return Concept(
            concept_id=f"tasks/{task['id']}",
            type="Task",
            source="vikunja",
            title=task.get("title"),
            description=(task.get("description") or "").strip() or None,
            resource=None,
            tags=[t for t in tags if t],
            timestamp=task.get("updated"),
            frontmatter={
                "type": "Task",
                "identifier": task.get("identifier"),
                "priority": task.get("priority", 0),
                "done": bool(task.get("done")),
                "percent_done": task.get("percent_done", 0),
                "project_id": task.get("project_id"),
            },
            body=_task_body(task),
        )

    async def list_concepts(self) -> list[Concept]:
        tasks = await self._vik.list_tasks()
        return [self._to_concept(t) for t in tasks]

    async def get_concept(self, concept_id: str) -> Concept | None:
        if not self.owns(concept_id):
            return None
        task_id = int(concept_id.split("/", 1)[1])
        task = await self._vik.get_task(task_id)
        return self._to_concept(task) if task else None

    def field_capabilities(self, concept: Concept) -> FieldCaps:
        return FieldCaps(
            writable={
                "title": "vikunja.update_task(title=…)",
                "description": "vikunja.update_task(description=…)",
                "priority": "vikunja.update_task(priority=…)",
                "due_date": "vikunja.update_task(due_date=…)",
                "done": "vikunja.update_task(done=…)",
                "labels": "vikunja.add_label_to_task / remove_label_from_task",
            },
            readonly=["identifier", "percent_done", "project_id"],
        )

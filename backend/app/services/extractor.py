"""
Task extraction pipeline.

Sends unstructured text to Gemini with tool-calling so the LLM can look up
real Vikunja project IDs during extraction. Returns a list of TaskProposal
objects saved to the DuckDB proposal queue.
"""

import json
import logging
import uuid
from datetime import date, datetime

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.proposal import TaskProposal, TaskProposalCreate
from app.services.llm import get_llm_client
from app.services.vikunja import VikunjaError, vikunja

# ── Extraction prompt ─────────────────────────────────────────────────────────
EXTRACTION_SYSTEM_PROMPT = """\
You are a task extraction assistant for a PhD student.

Given unstructured text (meeting notes, emails, or freeform ideas), extract
actionable tasks. Use the provided tools to look up real project data.

TOOL USAGE:
1. Call lookup_projects first to get the list of available Vikunja projects.
2. For each task, call resolve_project(name) to get the correct project_id.
3. Optionally call check_existing_tasks(title) if a title might be a duplicate.

For each task, produce JSON with these fields:
{{
  "title": "Short, actionable task title starting with a verb",
  "description": "1-2 sentences of context (nullable)",
  "project_name": "Best matching project from lookup_projects, or suggest a clear new project name",
  "project_id": <resolved via resolve_project>,
  "priority": 1-5 (1=low, 3=normal, 5=urgent),
  "due_date": "YYYY-MM-DD or null",
  "estimated_minutes": integer or null,
  "labels": ["relevant", "labels"]
}}

RULES:
- Only extract tasks FOR THE USER (not tasks for others).
- Start titles with a verb: Write, Email, Review, Submit, etc.
- If a deadline is mentioned, include it. Convert "next Friday" etc to a date.
- "John will send the dataset" is NOT a user task.
- "Preprocess dataset once John sends it" IS a user task.
- Today's date is {today}.

Return a JSON array of task objects. If no actionable tasks, return [].
"""

# ── Tools exposed to the LLM ──────────────────────────────────────────────────
EXTRACTION_TOOLS = [
    {
        "name": "lookup_projects",
        "description": "Returns the list of available Vikunja projects with their IDs and titles.",
        "parameters": {},
    },
    {
        "name": "resolve_project",
        "description": (
            "Maps a project name string to its Vikunja project ID. "
            "Returns matched=true with project_id if found, or matched=false with the suggested name if no match."
        ),
        "parameters": {
            "name": {"type": "string", "description": "Project name to look up"},
        },
    },
    {
        "name": "check_existing_tasks",
        "description": "Fuzzy-searches recent Vikunja tasks by title to detect duplicates.",
        "parameters": {
            "title": {"type": "string", "description": "Task title to check for duplicates"},
        },
    },
]


class TaskExtractor:
    """Orchestrates the LLM tool-calling extraction pipeline."""

    def __init__(self):
        self._project_cache: list[dict] | None = None
        self._default_project_id: int | None = None

    async def _load_projects(self) -> list[dict]:
        """Fetch and cache Vikunja projects for this extraction run."""
        if self._project_cache is None:
            try:
                self._project_cache = await vikunja.list_projects()
            except VikunjaError:
                self._project_cache = []
        return self._project_cache

    async def _load_default_project_id(self) -> int | None:
        """Get the default_project_id from agent_config."""
        if self._default_project_id is None:
            with get_db() as conn:
                result = conn.execute(
                    "SELECT default_project_id FROM agent_config WHERE id = 1"
                ).fetchone()
                self._default_project_id = result[0] if result else None
        return self._default_project_id

    async def _tool_handler(self, tool_name: str, args: dict):
        """Dispatch tool calls from the LLM to the appropriate service."""
        if tool_name == "lookup_projects":
            projects = await self._load_projects()
            return [{"id": p["id"], "title": p["title"], "description": p.get("description", "")}
                    for p in projects]

        elif tool_name == "resolve_project":
            name = args.get("name", "").lower().strip()
            projects = await self._load_projects()

            # Exact match first
            for p in projects:
                if p["title"].lower() == name:
                    return {"project_id": p["id"], "project_name": p["title"]}

            # Partial match
            for p in projects:
                if name in p["title"].lower() or p["title"].lower() in name:
                    return {"project_id": p["id"], "project_name": p["title"]}

            # No match — return the suggested name without a project_id
            return {"project_id": None, "project_name": args.get("name", "").strip(), "matched": False}

        elif tool_name == "check_existing_tasks":
            title = args.get("title", "")
            try:
                tasks = await vikunja.search_tasks(title)
                return [{"id": t["id"], "title": t["title"]} for t in tasks[:5]]
            except VikunjaError:
                return []

        return {"error": f"Unknown tool: {tool_name}"}

    async def extract(
        self,
        text: str,
        source_type: str = "notes",
        model: str = "gemini-flash",
        project_hint: str | None = None,
    ) -> list[TaskProposal]:
        """
        Run the full extraction pipeline.

        Returns a list of saved TaskProposal objects.
        """
        from app.models_registry import get_model_id

        today = date.today().isoformat()
        system_prompt = EXTRACTION_SYSTEM_PROMPT.format(today=today)

        user_message = text
        if project_hint:
            user_message = f"[Project context: {project_hint}]\n\n{user_message}"

        resolved_model = get_model_id(model)
        llm = get_llm_client(model=resolved_model)
        messages = [{"role": "user", "content": user_message}]

        raw_output = await llm.generate_with_tools(
            messages=messages,
            system_prompt=system_prompt,
            tools=EXTRACTION_TOOLS,
            tool_handler=self._tool_handler,
        )

        logger.debug("LLM raw output: %s", raw_output)
        proposals = self._parse_output(raw_output, source_type, text)
        return self._save_proposals(proposals, source_type, text)

    def _parse_output(
        self,
        raw: str,
        source_type: str,
        source_text: str,
    ) -> list[TaskProposalCreate]:
        """Parse LLM JSON output into TaskProposalCreate objects."""
        # Strip markdown code fences if present
        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            stripped = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            import re
            match = re.search(r"\[.*\]", stripped, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.warning("_parse_output: JSON array found but failed to parse. raw=%r", stripped[:500])
                    return []
            else:
                logger.warning("_parse_output: no JSON array found in LLM output. raw=%r", stripped[:500])
                return []

        if not isinstance(data, list):
            logger.warning("_parse_output: expected list, got %s. raw=%r", type(data).__name__, stripped[:200])
            return []

        results = []
        for item in data:
            if not isinstance(item, dict) or not item.get("title"):
                continue
            try:
                due_date = None
                if item.get("due_date"):
                    due_date = date.fromisoformat(item["due_date"])
            except (ValueError, TypeError):
                due_date = None

            results.append(TaskProposalCreate(
                title=item["title"],
                description=item.get("description"),
                project_name=item.get("project_name"),
                project_id=item.get("project_id"),
                priority=int(item.get("priority", 3)),
                due_date=due_date,
                estimated_minutes=item.get("estimated_minutes"),
                labels=item.get("labels", []),
            ))
        return results

    def _save_proposals(
        self,
        proposals: list[TaskProposalCreate],
        source_type: str,
        source_text: str,
    ) -> list[TaskProposal]:
        """Persist proposals to DuckDB and return full TaskProposal objects."""
        if not proposals:
            return []

        source_id = str(uuid.uuid4())
        saved = []

        with get_db() as conn:
            for p in proposals:
                proposal_id = str(uuid.uuid4())
                labels_json = json.dumps(p.labels) if p.labels else "[]"

                conn.execute(
                    """INSERT INTO task_proposals
                       (id, source_id, title, description, project_name, project_id,
                        priority, due_date, estimated_minutes, labels,
                        source_type, source_text, confidential, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        proposal_id, source_id, p.title, p.description,
                        p.project_name, p.project_id, p.priority,
                        p.due_date.isoformat() if p.due_date else None,
                        p.estimated_minutes, labels_json,
                        source_type, source_text[:2000], False, "pending",
                    ],
                )

                saved.append(TaskProposal(
                    id=proposal_id,
                    source_id=source_id,
                    title=p.title,
                    description=p.description,
                    project_name=p.project_name,
                    project_id=p.project_id,
                    priority=p.priority,
                    due_date=p.due_date,
                    estimated_minutes=p.estimated_minutes,
                    labels=p.labels,
                    source_type=source_type,
                    source_text=source_text[:2000],
                    status="pending",
                ))

        return saved

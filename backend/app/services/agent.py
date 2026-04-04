"""
ChatAgent — unified chat service with extraction + task modification tools.

Combines TaskExtractor's extraction capabilities with new tools for
searching, updating, completing, moving, and deleting tasks.
"""

import json
import logging
import uuid
from datetime import date

from app.database import get_db
from app.models.proposal import TaskProposal, TaskProposalCreate
from app.services.extractor import EXTRACTION_TOOLS, TaskExtractor
from app.services.llm import get_llm_client
from app.services.vikunja import VikunjaError, vikunja

logger = logging.getLogger(__name__)

# Additional tools for task modification
MODIFICATION_TOOLS = [
    {
        "name": "search_tasks",
        "description": "Search existing tasks by keyword. Returns matching tasks with id, title, done status, and project_id.",
        "parameters": {
            "query": {"type": "string", "description": "Search query to find tasks"},
        },
    },
    {
        "name": "update_task",
        "description": "Update an existing task's fields (title, description, priority, due_date).",
        "parameters": {
            "task_id": {"type": "integer", "description": "The Vikunja task ID to update"},
            "title": {"type": "string", "description": "New title (optional)"},
            "description": {"type": "string", "description": "New description (optional)"},
            "priority": {"type": "integer", "description": "New priority 1-5 (optional)"},
            "due_date": {"type": "string", "description": "New due date YYYY-MM-DD or empty to clear (optional)"},
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as done/completed.",
        "parameters": {
            "task_id": {"type": "integer", "description": "The Vikunja task ID to mark done"},
        },
    },
    {
        "name": "move_task",
        "description": "Move a task to a different project.",
        "parameters": {
            "task_id": {"type": "integer", "description": "The Vikunja task ID to move"},
            "project_id": {"type": "integer", "description": "The target project ID"},
        },
    },
    {
        "name": "delete_task",
        "description": "Request deletion of a task. Returns a pending confirmation instead of deleting immediately.",
        "parameters": {
            "task_id": {"type": "integer", "description": "The Vikunja task ID to delete"},
        },
    },
    {
        "name": "create_task",
        "description": "Create a new task directly in a project. Use resolve_project first to get the project_id. Returns a pending confirmation.",
        "parameters": {
            "title": {"type": "string", "description": "Task title (start with a verb)"},
            "project_id": {"type": "integer", "description": "The project ID to create the task in (use resolve_project to find it)"},
            "description": {"type": "string", "description": "Task description (optional)"},
            "priority": {"type": "integer", "description": "Priority 1-5, default 3 (optional)"},
            "due_date": {"type": "string", "description": "Due date YYYY-MM-DD (optional)"},
            "labels": {"type": "array", "items": {"type": "string"}, "description": "Label names to apply (optional)"},
        },
    },
]

AGENT_SYSTEM_PROMPT = """\
You are a task management assistant for a PhD student. You can both extract new tasks \
from unstructured text AND modify existing tasks.

AUTO-DETECT MODE:
- If the user pastes a long block of text (meeting notes, emails, ideas), extract tasks from it.
- If the user gives a short command ("mark X as done", "delete Y", "move Z to Project A"), modify tasks.
- If unsure, ask for clarification.

EXTRACTION (for new tasks):
Use lookup_projects, resolve_project, check_existing_tasks, and get_label_descriptions \
to produce structured task proposals. Return them as a JSON array.

TASK CREATION (for direct requests like "create a task called X"):
Use resolve_project to find the project_id, then create_task. This creates the task directly \
without going through proposals. The tool returns a pending confirmation — tell the user \
what you'll create and that you need their approval.

TASK MODIFICATION:
Use search_tasks to find tasks, then update_task, complete_task, move_task, or delete_task.
- Always search first to confirm the task exists and get the correct task_id.
- For delete, the tool returns a pending confirmation — tell the user you're asking for confirmation.

For each extracted task, produce JSON:
{{{{
  "title": "Short, actionable task title starting with a verb",
  "description": "1-2 sentences of context (nullable)",
  "project_name": "Best matching project",
  "project_id": <resolved via resolve_project>,
  "priority": 1-5 (1=low, 3=normal, 5=urgent),
  "due_date": "YYYY-MM-DD or null",
  "estimated_minutes": integer or null,
  "labels": ["relevant", "labels"]
}}}}

RULES:
- Only extract tasks FOR THE USER (not tasks for others).
- Start titles with a verb.
- Today's date is {today}.
- Keep responses brief and conversational (1-3 sentences).
- When you complete an action, summarize what you did.
"""


class ChatAgent:
    """Unified chat agent with extraction + task modification capabilities."""

    def __init__(self):
        self._extractor = TaskExtractor()
        self._actions: list[dict] = []
        self._pending_actions: list[dict] = []
        self._proposals: list[TaskProposal] = []

    @property
    def all_tools(self) -> list[dict]:
        return EXTRACTION_TOOLS + MODIFICATION_TOOLS

    async def _tool_handler(self, tool_name: str, args: dict):
        """Dispatch tool calls — extraction tools + modification tools."""
        # Extraction tools — delegate to TaskExtractor
        if tool_name in ("lookup_projects", "resolve_project", "check_existing_tasks", "get_label_descriptions"):
            return await self._extractor._tool_handler(tool_name, args)

        # Modification tools
        if tool_name == "search_tasks":
            query = args.get("query", "")
            try:
                tasks = await vikunja.search_tasks(query)
                return [
                    {
                        "id": t["id"],
                        "title": t["title"],
                        "done": t.get("done", False),
                        "project_id": t.get("project_id"),
                    }
                    for t in tasks[:10]
                ]
            except VikunjaError as e:
                return {"error": str(e)}

        if tool_name == "update_task":
            task_id = args.get("task_id")
            if not task_id:
                return {"error": "task_id is required"}
            update_data = {}
            if "title" in args and args["title"]:
                update_data["title"] = args["title"]
            if "description" in args and args["description"]:
                update_data["description"] = args["description"]
            if "priority" in args and args["priority"]:
                update_data["priority"] = int(args["priority"])
            if "due_date" in args:
                if args["due_date"]:
                    update_data["due_date"] = f"{args['due_date']}T00:00:00Z"
                else:
                    update_data["due_date"] = None
            try:
                task = await vikunja.get_task(int(task_id))
                pending = {
                    "type": "update",
                    "task_id": int(task_id),
                    "task_title": task.get("title", f"Task #{task_id}"),
                    "changes": update_data,
                }
                self._pending_actions.append(pending)
                return {"pending_confirmation": True, "task_id": int(task_id), "task_title": task.get("title", ""), "changes": update_data, "message": "Update requires user confirmation. Tell the user what changes you want to make and that you need their approval."}
            except VikunjaError as e:
                return {"error": str(e)}

        if tool_name == "complete_task":
            task_id = args.get("task_id")
            if not task_id:
                return {"error": "task_id is required"}
            try:
                task = await vikunja.get_task(int(task_id))
                pending = {
                    "type": "complete",
                    "task_id": int(task_id),
                    "task_title": task.get("title", f"Task #{task_id}"),
                }
                self._pending_actions.append(pending)
                return {"pending_confirmation": True, "task_id": int(task_id), "task_title": task.get("title", ""), "message": "Completion requires user confirmation. Tell the user you need their approval to mark this task as done."}
            except VikunjaError as e:
                return {"error": str(e)}

        if tool_name == "move_task":
            task_id = args.get("task_id")
            project_id = args.get("project_id")
            if not task_id or not project_id:
                return {"error": "task_id and project_id are required"}
            try:
                task = await vikunja.get_task(int(task_id))
                pending = {
                    "type": "move",
                    "task_id": int(task_id),
                    "task_title": task.get("title", f"Task #{task_id}"),
                    "project_id": int(project_id),
                }
                self._pending_actions.append(pending)
                return {"pending_confirmation": True, "task_id": int(task_id), "task_title": task.get("title", ""), "project_id": int(project_id), "message": "Move requires user confirmation. Tell the user you need their approval to move this task."}
            except VikunjaError as e:
                return {"error": str(e)}

        if tool_name == "delete_task":
            task_id = args.get("task_id")
            if not task_id:
                return {"error": "task_id is required"}
            # Don't actually delete — return a pending confirmation
            try:
                task = await vikunja.get_task(int(task_id))
                pending = {"type": "delete", "task_id": int(task_id), "task_title": task.get("title", f"Task #{task_id}")}
                self._pending_actions.append(pending)
                return {"pending_confirmation": True, "task_id": int(task_id), "task_title": task.get("title", ""), "message": "Deletion requires user confirmation. Tell the user you need their confirmation to delete this task."}
            except VikunjaError as e:
                return {"error": str(e)}

        if tool_name == "create_task":
            title = args.get("title")
            project_id = args.get("project_id")
            if not title:
                return {"error": "title is required"}
            if not project_id:
                return {"error": "project_id is required. Use resolve_project first to find it."}
            create_data = {
                "title": title,
                "project_id": int(project_id),
            }
            if args.get("description"):
                create_data["description"] = args["description"]
            if args.get("priority"):
                create_data["priority"] = int(args["priority"])
            if args.get("due_date"):
                create_data["due_date"] = args["due_date"]
            if args.get("labels"):
                create_data["labels"] = args["labels"]
            pending = {
                "type": "create",
                "task_id": 0,  # No ID yet — task doesn't exist
                "task_title": title,
                "project_id": int(project_id),
                "changes": create_data,
            }
            self._pending_actions.append(pending)
            return {
                "pending_confirmation": True,
                "task_title": title,
                "project_id": int(project_id),
                "create_data": create_data,
                "message": "Task creation requires user confirmation. Tell the user what task you'll create and that you need their approval.",
            }

        return {"error": f"Unknown tool: {tool_name}"}

    async def process(
        self,
        message: str,
        history: list[dict],
        model: str = "gemini-flash",
    ) -> dict:
        """
        Process a chat message. Returns:
        {
            "reply": str,
            "proposals": list[TaskProposal],
            "actions": list[dict],
            "pending_actions": list[dict],
        }
        """
        from app.models_registry import get_model_id

        self._actions = []
        self._pending_actions = []
        self._proposals = []

        today = date.today().isoformat()
        system_prompt = AGENT_SYSTEM_PROMPT.format(today=today)

        # Use base_prompt_override if configured (replaces default prompt entirely)
        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT base_prompt_override FROM agent_config WHERE id = 1"
                ).fetchone()
                if row and row[0]:
                    system_prompt = row[0].format(today=today)
        except Exception:
            pass

        # Append user's custom system prompt if configured
        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT system_prompt_override FROM agent_config WHERE id = 1"
                ).fetchone()
                if row and row[0]:
                    system_prompt += f"\n\nAdditional user instructions:\n{row[0]}"
        except Exception:
            pass

        resolved_model = get_model_id(model)
        llm = get_llm_client(model=resolved_model)

        messages = history[-10:] + [{"role": "user", "content": message}]

        try:
            raw_output = await llm.generate_with_tools(
                messages=messages,
                system_prompt=system_prompt,
                tools=self.all_tools,
                tool_handler=self._tool_handler,
            )
        except Exception as e:
            logger.exception("ChatAgent LLM call failed")
            raw_output = ""

        # Try to parse proposals from output (extraction mode)
        proposals = self._parse_proposals(raw_output, message)

        # If no tool-generated reply, use the raw output as the reply
        reply = raw_output if raw_output else self._fallback_reply(proposals)

        return {
            "reply": reply,
            "proposals": proposals,
            "actions": self._actions,
            "pending_actions": self._pending_actions,
        }

    def _parse_proposals(self, raw: str, source_text: str) -> list[TaskProposal]:
        """Try to extract task proposals from LLM output."""
        if not raw:
            return []

        # Use the extractor's parse logic
        proposals_create = self._extractor._parse_output(raw, "chat", source_text)
        if not proposals_create:
            return []

        return self._extractor._save_proposals(proposals_create, "chat", source_text)

    def _fallback_reply(self, proposals: list[TaskProposal]) -> str:
        if self._actions:
            summaries = []
            for a in self._actions:
                if a["type"] == "complete":
                    summaries.append(f"Marked '{a['title']}' as done")
                elif a["type"] == "update":
                    summaries.append(f"Updated '{a['title']}'")
                elif a["type"] == "move":
                    summaries.append(f"Moved '{a['title']}'")
            return ". ".join(summaries) + "."
        if proposals:
            return f"I extracted {len(proposals)} task{'s' if len(proposals) != 1 else ''} from your message."
        return "I couldn't find any tasks to extract or actions to take. Could you give me more details?"

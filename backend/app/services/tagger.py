"""
Auto-tagging service.

Matches tasks to labels using LLM + label descriptions.
"""

import json
import logging

from app.services.llm import LLMError, get_llm_client

logger = logging.getLogger(__name__)

TAGGING_SYSTEM_PROMPT = """\
You are a task labeling assistant. Given a list of tasks and a list of labels with descriptions,
assign the most relevant labels to each task.

Return a JSON object mapping task_id (integer) to an array of label_ids (integers).
Only assign labels that genuinely match the task. If no labels match, return an empty array for that task.

Example output:
{{"42": [1, 3], "55": [2], "60": []}}
"""


class AutoTagger:
    """Suggests labels for tasks based on label descriptions."""

    async def suggest_labels(
        self,
        tasks: list[dict],
        label_descriptions: list[dict],
        model: str | None = None,
    ) -> dict[int, list[int]]:
        """
        Match tasks to labels via LLM.

        Args:
            tasks: List of dicts with at least {id, title, description?}
            label_descriptions: List of dicts with {label_id, title, description}
            model: LLM model to use

        Returns:
            Dict mapping task_id -> list of label_ids
        """
        if not tasks or not label_descriptions:
            return {}

        user_message = json.dumps({
            "tasks": [{"id": t["id"], "title": t["title"], "description": t.get("description", "")} for t in tasks],
            "labels": [{"label_id": ld["label_id"], "title": ld["title"], "description": ld["description"]} for ld in label_descriptions],
        })

        llm = get_llm_client(model=model)

        try:
            raw = await llm.generate(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=TAGGING_SYSTEM_PROMPT,
            )
        except LLMError as e:
            logger.error("Auto-tagger LLM call failed: %s", e)
            return {}

        return self._parse_output(raw)

    def _parse_output(self, raw: str) -> dict[int, list[int]]:
        """Parse LLM JSON output into {task_id: [label_ids]}."""
        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            stripped = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", stripped, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.warning("Auto-tagger: failed to parse JSON. raw=%r", stripped[:500])
                    return {}
            else:
                logger.warning("Auto-tagger: no JSON object found. raw=%r", stripped[:500])
                return {}

        if not isinstance(data, dict):
            return {}

        result = {}
        for task_id_str, label_ids in data.items():
            try:
                tid = int(task_id_str)
                if isinstance(label_ids, list):
                    result[tid] = [int(lid) for lid in label_ids]
            except (ValueError, TypeError):
                continue
        return result

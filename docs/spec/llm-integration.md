# LLM Integration

## Model Selection

`get_llm_client(model, confidential)` in `backend/app/services/llm.py` returns the appropriate client:

| Condition | Client | Default Model |
|-----------|--------|---------------|
| `confidential=True` or model contains `ollama`/starts with `qwen` | `OllamaClient` | `settings.ollama_model` |
| Gemini API key available | `GeminiClient` | `settings.gemini_model` |
| No Gemini key | `OllamaClient` (fallback) | `settings.ollama_model` |

Both clients implement `LLMClient` ABC with `generate()` and `generate_with_tools()`. Tool-calling loops run up to 10 iterations before raising `LLMError`.

## Extraction Tools (TaskExtractor)

Defined in `backend/app/services/extractor.py`. The LLM calls these during task extraction:

| Tool | Parameters | Purpose |
|------|-----------|---------|
| `lookup_projects` | none | Returns all Vikunja projects (id, title, description) |
| `resolve_project` | `name: string` | Maps project name to Vikunja project_id (exact then partial match) |
| `check_existing_tasks` | `title: string` | Fuzzy-searches recent tasks to detect duplicates (returns top 5) |
| `get_label_descriptions` | none | Returns all labels with descriptions from SQLite |

## ChatAgent Modification Tools

Defined in `backend/app/services/agent.py`. Combined with extraction tools for the unified chat interface:

| Tool | Parameters | Behavior |
|------|-----------|----------|
| `search_tasks` | `query` | Search tasks by keyword, returns top 10 matches |
| `update_task` | `task_id`, `title?`, `description?`, `priority?`, `due_date?` | Returns pending confirmation |
| `complete_task` | `task_id` | Returns pending confirmation |
| `move_task` | `task_id`, `project_id` | Returns pending confirmation |
| `delete_task` | `task_id` | Returns pending confirmation (never deletes immediately) |
| `create_task` | `title`, `project_id`, `description?`, `priority?`, `due_date?`, `labels?` | Returns pending confirmation |

All modification tools return `pending_confirmation: true` -- the frontend must confirm before execution.

## Extraction Prompt

The system prompt (`EXTRACTION_SYSTEM_PROMPT`) instructs the LLM to:
- Extract actionable tasks for the user only (not tasks assigned to others)
- Start titles with a verb (Write, Email, Review, Submit)
- Resolve dates like "next Friday" to ISO format
- Call `lookup_projects` first, then `resolve_project` per task
- Output a JSON array of task objects with title, description, project_name, project_id, priority (1-5), due_date, estimated_minutes, labels

Configurable via `agent_config.base_prompt_override` (replaces entirely) and `agent_config.system_prompt_override` (appended).

## Error Handling

| Error | Retry | Behavior |
|-------|-------|----------|
| HTTP 429 (rate limit) | 3 attempts, exponential backoff (2^n seconds) | Raises `LLMError` after exhaustion |
| Timeout | 3 attempts (Gemini 60s, Ollama 120s) | Raises `LLMError` after exhaustion |
| Connection error | 3 attempts | Raises `LLMError` after exhaustion |
| Malformed JSON output | No retry | Falls back to regex extraction of JSON array |
| Tool loop > 10 iterations | N/A | Raises `LLMError` |

## FallbackClient

`FallbackClient(primary, fallback)` wraps two clients. If the primary raises `LLMError`, the fallback is tried. Both `generate()` and `generate_with_tools()` follow this pattern. Currently not wired by default in `get_llm_client()` but available for composition.

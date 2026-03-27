# API: Config & Models

## GET /api/config

Returns the singleton `agent_config` row.

```json
{
  "default_project_id": 5,
  "ollama_model": "qwen3:4b",
  "gemini_model": "gemini-3.1-flash-lite-preview",
  "gcal_calendar_id": "primary",
  "system_prompt_override": "Custom instructions appended to the base prompt",
  "base_prompt_override": "Full replacement for the default agent system prompt"
}
```

All fields are nullable. `system_prompt_override` is appended to the base prompt; `base_prompt_override` replaces it entirely.

## PUT /api/config

Partial update -- only provided fields are written. Returns the full updated config.

---

## GET /api/config/system-prompt

Returns the formatted agent system prompt with today's date interpolated. Uses `base_prompt_override` if set, otherwise the default `AGENT_SYSTEM_PROMPT`.

```json
{ "prompt": "You are a task management assistant..." }
```

## GET /api/config/tools

Returns the combined list of extraction and modification tool definitions.

```json
{ "tools": [{ "name": "search_tasks", "description": "...", "parameters": {...} }, ...] }
```

---

## GET /api/models

Public (no auth). Returns the available LLM model registry.

```json
[
  { "value": "gemini-flash", "model_id": "gemini-3.1-flash-lite-preview", "label": "Gemini 3.1 Flash Lite", "description": "Fast, good for most tasks", "provider": "gemini" },
  { "value": "gemini-3", "model_id": "gemini-3-flash-preview", "label": "Gemini 3.0", "description": "Higher quality, slower", "provider": "gemini" },
  { "value": "ollama-qwen", "model_id": "qwen3:4b", "label": "Qwen 3.x (Local)", "description": "Private, runs on your machine", "provider": "ollama" },
  { "value": "ollama-llama", "model_id": "ollama-llama", "label": "Llama 3.3 (Local)", "description": "Private, larger model", "provider": "ollama" }
]
```

The `value` field is what the frontend sends in `model` parameters. The backend resolves it to `model_id` via `get_model_id()`.

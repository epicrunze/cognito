# Cognito -- Overview

Cognito is a task-agent application. Users input freeform text (notes, meeting dumps, voice transcriptions), an LLM extracts structured tasks, and approved tasks sync to Vikunja -- a self-hosted, headless task manager.

## Architecture

```
+------------------+        +------------------+        +------------------+
|                  |  HTTP   |                  |  HTTP   |                  |
|    SvelteKit     | ------> |     FastAPI      | ------> |     Vikunja      |
|    Frontend      | <------ |     Backend      | <------ |   (task store)   |
|                  |         |                  |         |                  |
+------------------+         +--------+---------+         +------------------+
   Browser (SPA)             |        |
                             |  +-----+------+
                             |  |            |
                             v  v            v
                          Gemini API     Ollama
                          (cloud LLM)   (local LLM)
```

- The frontend never calls Vikunja directly. All requests go through the FastAPI backend, which injects the Vikunja API token server-side.
- The backend proxies task/project/label CRUD to Vikunja and stores its own metadata (proposals, conversations, config) in SQLite.
- LLM calls go to Gemini (primary, cloud) or Ollama with Qwen/Llama models (fallback, local).

## Tech Stack

| Layer          | Technology                                                        |
|----------------|-------------------------------------------------------------------|
| Frontend       | SvelteKit (Svelte 5), Tailwind CSS, TypeScript, IBM Plex Sans/Mono, svelte-dnd-action |
| Backend        | FastAPI (Python), sqlite3 (stdlib, autocommit), httpx, pydantic-settings |
| Task storage   | Vikunja v2.1+ (Docker, headless -- no UI, API only)               |
| Agent database | SQLite (proposals, config, conversations, revisions, label descriptions) |
| LLM            | Gemini API (cloud), Ollama with Qwen 3.x / Llama 3.3 (local)    |
| Auth           | Google OAuth 2.0 -> JWT HttpOnly cookie                           |

## Vikunja vs Cognito -- Responsibility Split

| Concern                  | Vikunja                        | Cognito                              |
|--------------------------|--------------------------------|--------------------------------------|
| Task CRUD                | Source of truth                 | Proxies all reads/writes             |
| Projects and labels      | Source of truth                 | Caches projects; stores label descriptions |
| Kanban buckets and views | Owns bucket/view data          | Proxies bucket ops, manages board UI |
| Task extraction from text| --                              | LLM-powered extraction pipeline      |
| Proposal queue           | --                              | SQLite: pending/approved/rejected    |
| Chat / agent mode        | --                              | Conversations + tool-calling agent   |
| Task revisions (undo)    | --                              | SQLite: before/after state tracking  |
| User auth                | Own auth (unused by Cognito)   | Google OAuth -> JWT                  |
| Scheduling / calendar    | Due dates, start/end dates     | Google Calendar link management      |
| Config / settings        | --                              | SQLite singleton (models, prompts)   |

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Cognito is a task-agent app: users input freeform text, an LLM extracts structured tasks, and approved tasks sync to Vikunja (self-hosted task manager). FastAPI backend + SvelteKit frontend + DuckDB.

## Commands

### Backend (from `backend/`)
```bash
uv sync                                          # install deps
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000  # dev server
uv run pytest tests/ -v                          # all tests (38)
uv run pytest tests/test_proposals.py -v         # single test file
uv run pytest tests/test_extractor.py::test_name -v  # single test
```

### Frontend (from `frontend/`)
```bash
npm install                  # install deps
npm run dev                  # dev server (port 5173, proxies /api to backend)
npm run build                # static build → ./build
npm run check                # svelte-check + TypeScript
```

### Docker
```bash
docker-compose up --build    # all services (vikunja:3456, backend:8000, frontend:80)
```

## Architecture

**Backend** (`backend/app/`): Layered FastAPI — routers → services → models → database.
- `main.py` — app entry, lifespan initializes DuckDB schema, mounts 4 routers
- `database.py` — DuckDB connection via `get_db()` context manager (used as FastAPI `Depends`)
- `config.py` — pydantic-settings, all env vars have defaults
- `services/extractor.py` — orchestrates LLM tool-calling loop to extract tasks from text
- `services/llm.py` — `LLMClient` ABC with `GeminiClient` impl; `generate_with_tools()` handles multi-turn tool dispatch
- `services/vikunja.py` — httpx-based REST client for Vikunja API
- `routers/proposals.py` — full CRUD + approve/reject lifecycle; approve creates Vikunja task
- `routers/ingest.py` — accepts text, returns proposals as JSON or SSE stream
- `auth/` — Google OAuth2 → JWT in HttpOnly cookie, `get_current_user` dependency

**Frontend** (`frontend/src/`): SvelteKit (Svelte 5) with static adapter, Tailwind CSS, TypeScript strict.
- Single page app: `routes/+page.svelte` (InputPanel + ProposalQueue)
- `lib/api.ts` — fetch wrapper with silent 401 refresh, SSE streaming support
- `lib/stores.svelte.ts` — Svelte 5 runes (`$state`, `$derived`) for reactivity

**Database**: DuckDB single file (`./data/agent.duckdb`). Tables: `users`, `task_proposals`, `vikunja_projects`, `agent_config`.

**Key flow**: User text → `POST /api/ingest` → TaskExtractor calls Gemini with tools (lookup_projects, resolve_project, check_existing_tasks) → proposals saved as pending → user approves → Vikunja task created.

## Testing Patterns

Tests use in-memory DuckDB, dependency overrides, and async mocking:
- Patch `get_db` with `make_mock_db(conn)` (yields same in-memory connection)
- Override `get_current_user` with lambda returning mock user
- `respx.mock` for httpx calls (Vikunja client tests)
- `AsyncMock` for async service methods
- `asyncio_mode = "auto"` in pyproject.toml — no `@pytest.mark.asyncio` needed

## Environment

All config in `.env` (see `.env.example`). Key vars: `VIKUNJA_API_TOKEN`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ALLOWED_EMAIL`, `JWT_SECRET`.

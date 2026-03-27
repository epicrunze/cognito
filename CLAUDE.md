# CLAUDE.md

## Project

Cognito is a task-agent app: freeform text → LLM extraction → structured tasks in Vikunja. FastAPI backend + SvelteKit frontend + SQLite.

Full spec: `docs/SPEC.md` (index) → `docs/spec/*.md`. Before UI/UX work, read `docs/DESIGN_PHILOSOPHY.md`.

## Commands

### Backend (from `backend/`)
```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uv run pytest tests/ -v
```

### Frontend (from `frontend/`)
```bash
npm install
npm run dev                  # port 5173, proxies /api to backend
npm run build                # static build → ./build
npm run check                # svelte-check + TypeScript
```

### Docker
```bash
docker-compose up --build    # vikunja:3456, backend:8000, frontend:80
```

## MCP Servers

**Svelte** (`sveltejs/mcp`): Run `svelte-autofixer` after editing any `.svelte` file. Use `get-documentation` before implementing SvelteKit patterns.

## Architecture

**Backend** (`backend/app/`): Layered — routers → services → models → database.
- 11 routers: auth, chat, config, ingest, labels, models, proposals, projects, revisions, schedule, tasks
- 7 services: agent (ChatAgent), extractor, llm (Gemini/Ollama), vikunja (httpx proxy), tagger, revisions, gcal
- Key patterns: Vikunja proxy injects API token server-side; ChatAgent has extraction + modification tools with revision tracking; all AI mutations create before/after snapshots for undo

**Frontend** (`frontend/src/`): SvelteKit (Svelte 5 runes), static adapter, Tailwind CSS, TypeScript strict.
- 20 stores in `lib/stores/` — task state, view modes, responsive breakpoints, chat, kanban, gantt, etc.
- 4 view modes: Bubbles (primary), Kanban (project), List, Gantt
- Mobile: bottom sheets, accordion kanban, masonry layout, swipe-to-complete, FAB quick-add

**Database**: SQLite (`./data/agent.db`). Tables: users, task_proposals, vikunja_projects, agent_config, label_descriptions, conversations, conversation_messages, task_revisions, task_calendar_links.

## Vikunja API — Key Gotchas

The frontend NEVER calls Vikunja directly — the backend proxy injects the API token.

- **PUT creates, POST updates** (opposite of REST) — applies to ALL resources.
- **`hex_color` has no `#` prefix.** Strip `#` before sending.
- **Buckets belong to views, not projects.** GET views → find view_kind=3 → GET buckets.
- **Filter syntax:** `done = false && priority >= 3`. **Search:** `s` param. **Dates:** ISO 8601.
- **Position:** float, view-dependent. Reorder via midpoint between neighbours.

## Testing

157 tests across 11 files. In-memory SQLite, dependency overrides, async mocking:
- Patch `get_db` with `make_mock_db(conn)` — `respx.mock` for httpx
- Override `get_current_user` with lambda returning mock user
- `asyncio_mode = "auto"` in pyproject.toml

## Deployment

3 Docker containers behind Cloudflare tunnels:
- `tasks.epicrunze.com` → vikunja — admin only
- `cognito.epicrunze.com` → frontend (nginx :80)
- `api-cognito.epicrunze.com` → backend (:8000)

Backend → Vikunja: internal Docker network (`http://vikunja:3456`). Frontend `PUBLIC_API_URL` is a build-time env var. CORS: `FRONTEND_URL` origin. Cookies: `COOKIE_DOMAIN=.epicrunze.com`.

## JaRVIS

Identity/memories loaded at session start via SessionStart hook. Run `/jarvis-reflect` after completing meaningful tasks. You MUST reflect before ending any session.

## Environment

All config in `.env` (see `.env.example`). Key vars: `VIKUNJA_API_TOKEN`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ALLOWED_EMAIL`, `JWT_SECRET`.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Cognito is a task-agent app: users input freeform text, an LLM extracts structured tasks, and approved tasks sync to Vikunja (self-hosted task manager). FastAPI backend + SvelteKit frontend + SQLite.

Full spec: `docs/SPEC.md`. Task queue: `TASKS.md`. Live component reference: `docs/cognito-design-system.jsx`. **Before any UI/UX work, read `docs/DESIGN_PHILOSOPHY.md` — it shapes how you approach design decisions and requires proposing changes before implementing.**

## Commands

### Backend (from `backend/`)
```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uv run pytest tests/ -v
uv run pytest tests/test_proposals.py -v
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

**Svelte** (`sveltejs/mcp`): Provides Svelte 5 docs lookup and code analysis.
- Run `svelte-autofixer` after writing or editing any `.svelte` file
- Use `get-documentation` before implementing SvelteKit patterns (load functions, form actions, routing)
- Use `list-sections` to find relevant docs when unsure about Svelte 5 syntax

## Architecture

**Backend** (`backend/app/`): Layered FastAPI — routers → services → models → database.
- `main.py` — app entry, lifespan inits SQLite schema
- `database.py` — SQLite via `get_db()` context manager (FastAPI Depends)
- `config.py` — Pydantic Settings, all env vars have defaults
- `services/extractor.py` — LLM tool-calling loop (lookup_projects, resolve_project, check_existing_tasks, get_label_descriptions)
- `services/llm.py` — LLMClient ABC with GeminiClient + OllamaClient; model selection per request
- `services/vikunja.py` — httpx REST client for Vikunja API
- `services/tagger.py` — auto-tagging via label descriptions + LLM
- `routers/ingest.py` — text → proposals (JSON or SSE), includes model + raw_response
- `routers/proposals.py` — CRUD + approve/reject; approve creates Vikunja task
- `auth/` — Google OAuth2 → JWT HttpOnly cookie, `get_current_user` dependency

**Frontend** (`frontend/src/`): SvelteKit (Svelte 5), static adapter, Tailwind CSS, TypeScript strict.
- `app.css` — dark theme design tokens as CSS custom properties
- `components/ui/` — primitives: Button, Input, Checkbox, Dropdown, Badge, Toast, SlideOver, Skeleton, Tip, etc.
- `lib/api.ts` — fetch wrapper with silent 401 refresh, SSE streaming
- `lib/stores.svelte.ts` — Svelte 5 runes ($state, $derived)

**Database**: SQLite (`./data/agent.db`). Tables: users, task_proposals, label_descriptions, vikunja_projects, agent_config.

## Vikunja API — Key Gotchas

The frontend NEVER calls Vikunja directly — the backend proxy injects the API token. Full reference in `docs/SPEC.md` Section 6.

- **PUT creates, POST updates** (opposite of REST) — applies to ALL resources (tasks, projects, labels).
- **`hex_color` has no `#` prefix.** Vikunja stores `A1A09A`, not `#A1A09A`. Strip `#` before sending.
- **Buckets belong to views, not projects.** Kanban: GET views → find view_kind=3 → GET buckets → tasks per bucket.
- **Filter syntax:** single `filter` param with expressions: `done = false && priority >= 3`.
- **Search:** `s` param, not `search`. **Pagination:** in response headers. **Dates:** ISO 8601.
- **Position:** float, view-dependent. Reorder via midpoint between neighbours.

## Design System

Dark theme. Tangerine accent (#E8772E) on warm dark neutrals. IBM Plex Sans. Full tokens in `docs/SPEC.md` Section 5.2. Live states in `docs/cognito-design-system.jsx`.

**Key patterns:**
- Optimistic updates on all mutations (update store → API → rollback on failure + toast)
- AI-tagged tasks: tangerine left border + inward glow, fades after viewing
- Collapsed sidebar: z-index 50, overflow visible, tooltips to the right outside the bar
- Top bar buttons: flexShrink 0, whiteSpace nowrap (never wrap to second line)
- Completed tasks: below "Completed (N)" divider, 0.65 opacity, collapsible
- Transitions: 150ms hover, 200ms panels, 300ms slide-overs (Svelte fly/fade/slide)
- Auto-save: 500ms debounce text, immediate toggles/selects

## Testing

In-memory SQLite, dependency overrides, async mocking:
- Patch `get_db` with `make_mock_db(conn)`
- Override `get_current_user` with lambda returning mock user
- `respx.mock` for httpx (Vikunja client)
- `asyncio_mode = "auto"` in pyproject.toml

## Deployment

3 Docker containers behind Cloudflare tunnels (no ports exposed):
- `tasks.epicrunze.com` → vikunja (:3456) — admin only, frontend never calls directly
- `cognito.epicrunze.com` → frontend (nginx :80)
- `api-cognito.epicrunze.com` → backend (:8000)

**Backend → Vikunja**: Internal Docker network only (`http://vikunja:3456`). Set via `VIKUNJA_URL`.

**Frontend API URL**: `PUBLIC_API_URL` is a SvelteKit build-time env var (baked in by static adapter). Pass as Docker build arg: `args: PUBLIC_API_URL: ${BACKEND_URL}`. In dev, leave unset — falls back to `/api` (Vite proxy).

**CORS**: `FRONTEND_URL` origin allowed with credentials in `main.py`.

**Cookies**: `COOKIE_DOMAIN=.epicrunze.com` covers both `cognito.` and `api-cognito.` subdomains.

## Environment

All config in `.env` (see `.env.example`). Key vars: `VIKUNJA_API_TOKEN`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ALLOWED_EMAIL`, `JWT_SECRET`.
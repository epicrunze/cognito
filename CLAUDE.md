# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Cognito is a task-agent app: users input freeform text, an LLM extracts structured tasks, and approved tasks sync to Vikunja (self-hosted task manager). FastAPI backend + SvelteKit frontend + SQLite.

The full technical spec is at `docs/SPEC.md` — read relevant sections before implementing features. The ordered task queue is in `TASKS.md`.

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
- `main.py` — app entry, lifespan initializes SQLite schema, mounts 4 routers
- `database.py` — SQLite connection via `get_db()` context manager (used as FastAPI `Depends`)
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
- `components/ui/` — primitive design system components (Button, Input, Checkbox, Toast, SlideOver, etc.)

**Database**: SQLite single file (`./data/agent.db`). Tables: `users`, `task_proposals`, `vikunja_projects`, `agent_config`.

**Key flow**: User text → `POST /api/ingest` → TaskExtractor calls Gemini with tools (lookup_projects, resolve_project, check_existing_tasks) → proposals saved as pending → user approves → Vikunja task created.

## Vikunja API — Critical Details

Vikunja is the headless task backend. The frontend NEVER calls it directly — all requests go through the FastAPI proxy which injects the API token.

- **PUT creates, POST updates.** This is the opposite of standard REST. Exception: label update also uses PUT. Double-check every endpoint.
- **Buckets belong to project views, not projects.** To show a kanban board: GET project views → find `view_kind=3` → GET its buckets → GET tasks per bucket.
- **Moving tasks between kanban columns:** POST to `/api/v1/projects/{id}/views/{viewId}/buckets/tasks` with `{task_id, bucket_id, position}`.
- **Filtering uses expression syntax** in a single `filter` param: `done = false && priority >= 3` (not individual query params).
- **Search uses `s` parameter**, not `search`.
- **Pagination** comes in response headers: `x-pagination-total-pages`, `x-pagination-result-count`.
- **Dates:** ISO 8601 with timezone: `2026-03-07T00:00:00Z`.
- **Task `position` is a float**, view-dependent. Reorder by calculating midpoint between neighbours.
- **Labels** added to tasks via PUT `/tasks/{id}/labels` with body `{"label_id": X}`.
- **Projects** can nest via `parent_project_id`. The `identifier` field (e.g. "PHD") builds human-readable task IDs like "PHD-12".
- Full API reference in `docs/SPEC.md` Section 6. Swagger docs at `http://localhost:3456/api/v1/docs`.

## Design System

Aesthetic: Linear meets Things 3. Warm neutral palette, high information density, instant interactions. Full token definitions in `docs/SPEC.md` Section 5.1.

**Palette** (defined as CSS custom properties in `app.css`):
- Backgrounds: `#FAFAF9` (base), `#FFFFFF` (surface), `#F5F5F4` (sidebar/hover)
- Text: `#1C1917` (primary), `#57534E` (secondary), `#A8A29E` (tertiary)
- Accent: `#6366F1` (indigo — primary actions), `#8B5CF6` (purple — AI features)
- Priority: urgent=`#EF4444`, high=`#F97316`, medium=`#EAB308`, low=`#22C55E`
- Borders: `#E7E5E4` (default), `#D6D3D1` (strong)

**Typography:** IBM Plex Sans (400/500/600) + IBM Plex Mono. Base size: 14px (0.875rem).

**Spacing:** 4/8/12/16/20/24/32/48px scale. Border radius: 6px containers, 4px inputs, 9999px pills.

**Interactions:**
- All mutations use optimistic updates — update store immediately, API in background, rollback + toast on failure.
- Transitions: 150ms (hover), 200ms (panels/cards), 300ms (slide-overs). Use Svelte `fly`, `fade`, `slide`.
- Auto-save: debounce 500ms for text fields, immediate for toggles/selects.

## Testing Patterns

Tests use in-memory SQLite, dependency overrides, and async mocking:
- Patch `get_db` with `make_mock_db(conn)` (yields same in-memory connection)
- Override `get_current_user` with lambda returning mock user
- `respx.mock` for httpx calls (Vikunja client tests)
- `AsyncMock` for async service methods
- `asyncio_mode = "auto"` in pyproject.toml — no `@pytest.mark.asyncio` needed

## Environment

All config in `.env` (see `.env.example`). Key vars: `VIKUNJA_API_TOKEN`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ALLOWED_EMAIL`, `JWT_SECRET`.
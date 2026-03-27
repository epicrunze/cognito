# Cognito — Technical Specification

**Task management + AI extraction powered by Vikunja (headless)**

Version 4.0 — March 2026

---

Cognito replaces Vikunja's frontend with a custom SvelteKit app while using Vikunja as a headless task database. Users paste unstructured text, an LLM extracts structured tasks with tool calling, and approved tasks sync to Vikunja. A conversational chat agent can also search, modify, and create tasks.

For design rationale, see [DESIGN_PHILOSOPHY.md](DESIGN_PHILOSOPHY.md).

## Specification Index

### Architecture & Data
- [Overview](spec/overview.md) — Architecture, tech stack, Vikunja vs Cognito responsibilities
- [Data Models](spec/data-models.md) — Vikunja entities, SQLite schema (9 tables), migrations

### Backend API
- [Auth](spec/api-auth.md) — Google OAuth → JWT cookie, token refresh
- [Tasks](spec/api-tasks.md) — Task CRUD proxy, attachments, subtasks, position, auto-tag
- [Projects](spec/api-projects.md) — Project/view/bucket CRUD, kanban, sync
- [Labels](spec/api-labels.md) — Label CRUD, descriptions, cleanup, stats, auto-generation
- [Extraction](spec/api-extraction.md) — Ingest (SSE), proposals (approve/reject)
- [Chat](spec/api-chat.md) — Conversational agent, modification tools, pending actions
- [Config](spec/api-config.md) — Agent config, model registry
- [Revisions](spec/api-revisions.md) — AI action history, undo/redo
- [Schedule](spec/api-schedule.md) — Google Calendar integration, LLM suggestions

### LLM
- [LLM Integration](spec/llm-integration.md) — Models, extraction tools, chat tools, prompts, error handling

### Frontend
- [Views](spec/frontend-views.md) — Routes, view modes (Bubbles/Kanban/List/Gantt), stores
- [Components](spec/frontend-components.md) — UI primitives, feature components
- [Mobile](spec/frontend-mobile.md) — Responsive breakpoints, bottom sheets, gestures, accordion kanban
- [Design System](spec/design-system.md) — Tokens, typography, shadows, animations

### Infrastructure
- [Vikunja API](spec/vikunja-api.md) — Vikunja REST reference, gotchas (PUT creates, POST updates)
- [Deployment](spec/deployment.md) — Docker, Cloudflare tunnels, env vars, CORS
- [Testing](spec/testing.md) — Test architecture, patterns, 157 tests

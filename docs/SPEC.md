# Cognito — Technical Specification v3

**Task management + AI extraction powered by Vikunja (headless)**

Version 3.0 — March 2026

---

## 1. Overview

Cognito replaces Vikunja's frontend with a custom SvelteKit app while using Vikunja as a headless task database. Users paste unstructured text (meeting notes, emails, ideas), an LLM extracts structured tasks with tool calling, and approved tasks sync to Vikunja. A single Google OAuth login gates all access.

### Architecture

```
SvelteKit Frontend (port 5173)
    ↕ JWT cookie
FastAPI Backend (port 8000)
    ├─→ Vikunja API (port 3456, headless)    # task storage
    ├─→ Gemini API                            # cloud LLM
    └─→ Ollama (port 11434)                   # local LLM
```

The frontend never calls Vikunja directly. The backend proxies all task/project/label CRUD, injecting the API token. The backend also manages AI extraction, the proposal queue (SQLite), and auto-tagging.

### Tech Stack

- **Frontend:** SvelteKit (Svelte 5), Tailwind CSS, IBM Plex Sans/Mono, svelte-dnd-action, date-fns
- **Backend:** FastAPI (Python), aiosqlite, httpx
- **Task storage:** Vikunja (Docker, headless, v2.1+)
- **Agent DB:** SQLite (proposals, label descriptions, config)
- **LLM:** Gemini API (cloud), Ollama with Qwen 3.x / Llama 3.3 (local/confidential)
- **Auth:** Google OAuth 2.0 → JWT HttpOnly cookie (reused from existing codebase)

### What Vikunja Handles vs Cognito

| Vikunja (headless) | Cognito |
|---|---|
| Task CRUD, storage, search | AI task extraction from text |
| Projects, labels, views, buckets | Proposal queue + approval flow |
| User/auth for API access | Google OAuth + JWT for users |
| CalDAV, webhooks, notifications | Auto-tagging with label descriptions |
| Attachments, comments | Model selection (Gemini/Ollama) |
| Kanban/list data model | All UI, filtering, interactions |

---

## 2. Data Models

### 2.1 Vikunja Data (via API)

**Task:** id, title, description (markdown), done, done_at, priority (0-5), due_date, start_date, end_date, project_id, labels[], assignees[], percent_done, hex_color, repeat_after, repeat_mode, index, identifier (e.g. "PHD-12"), uid, is_favorite, position (float, view-dependent), bucket_id (view-dependent), reminders[], attachments[], related_tasks, created_by, created, updated.

**Project:** id, title, description, identifier, hex_color, is_archived, is_favorite, parent_project_id, position, views[].

**Label:** id, title, hex_color.

**ProjectView:** id, title, project_id, view_kind (0=list, 1=gantt, 2=table, 3=kanban), filter, bucket_configuration_mode, default_bucket_id, done_bucket_id, position.

**Bucket:** id, title, position, limit (WIP), project_view_id, created_by, created, updated.

### 2.2 Agent Data (SQLite)

**TaskProposal:** id (UUID), source_id (UUID), title, description, project_name, project_id, priority (1-5), due_date, estimated_minutes, labels (JSON), source_type, source_text, confidential (bool), model_used (string), status (pending/approved/rejected/created), vikunja_task_id, auto_tag_reasons (JSON), created_at, reviewed_at.

**LabelDescription:** id, label_id (Vikunja), title, description (text describing what this label covers — used by AI for auto-tagging), created_at, updated_at.

**VikunjaProject (cache):** id, title, description, last_synced_at.

**AgentConfig (singleton):** default_project_id, default_model (string), ollama_model, gemini_model, gcal_calendar_id.

### 2.3 Schema

```sql
CREATE TABLE task_proposals (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    project_name TEXT,
    project_id INTEGER,
    priority INTEGER DEFAULT 3,
    due_date DATE,
    estimated_minutes INTEGER,
    labels TEXT DEFAULT '[]',
    source_type TEXT NOT NULL,
    source_text TEXT NOT NULL,
    confidential BOOLEAN DEFAULT FALSE,
    model_used TEXT,
    status TEXT DEFAULT 'pending',
    vikunja_task_id INTEGER,
    auto_tag_reasons TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP
);

CREATE TABLE label_descriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vikunja_projects (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    default_project_id INTEGER,
    default_model TEXT DEFAULT 'gemini-2.0-flash',
    ollama_model TEXT DEFAULT 'qwen3:4b',
    gemini_model TEXT DEFAULT 'gemini-2.0-flash',
    gcal_calendar_id TEXT
);
```

---

## 3. API Specification

### 3.1 Authentication

Reused from existing codebase.

| Endpoint | Method | Description |
|---|---|---|
| /api/auth/login | GET | Redirect to Google OAuth |
| /api/auth/callback | GET | OAuth callback → JWT cookie → redirect |
| /api/auth/me | GET | Current user info |
| /api/auth/logout | POST | Clear JWT cookie |

### 3.2 Vikunja Proxy Endpoints

All require JWT auth. The backend injects the Vikunja API token. **Vikunja uses PUT for creation, POST for updates** (opposite of REST). Label update uses PUT for both.

**Tasks:**

| Our endpoint | Method | Vikunja endpoint |
|---|---|---|
| /api/tasks | GET | GET /api/v1/tasks/all |
| /api/tasks/{id} | GET | GET /api/v1/tasks/{id} |
| /api/tasks/{id} | PUT | POST /api/v1/tasks/{id} |
| /api/tasks/{id} | DELETE | DELETE /api/v1/tasks/{id} |
| /api/projects/{id}/tasks | POST | PUT /api/v1/projects/{id}/tasks |
| /api/tasks/{id}/labels | POST | PUT /api/v1/tasks/{id}/labels |
| /api/tasks/{id}/labels/{labelId} | DELETE | DELETE /api/v1/tasks/{id}/labels/{labelId} |

**GET /api/tasks query params:** page, per_page, s (search), sort_by, order_by, filter (Vikunja expression syntax), filter_timezone, filter_include_nulls, expand.

**Filter syntax:** `done = false && priority >= 3`, `due_date < now+7d`, `labels in [1,2,3]`. Comparators: =, !=, >, >=, <, <=, like, in, not in. Combinators: && (AND), || (OR), parentheses. Date math: now, now+1d, now-1w.

**Projects & Views:**

| Our endpoint | Method | Vikunja endpoint |
|---|---|---|
| /api/projects | GET | GET /api/v1/projects |
| /api/projects/{id} | GET | GET /api/v1/projects/{id} |
| /api/projects | POST | PUT /api/v1/projects |
| /api/projects/{id} | PUT | POST /api/v1/projects/{id} |
| /api/projects/{id}/views | GET | GET /api/v1/projects/{id}/views |
| /api/projects/{id}/views/{viewId}/buckets | GET | GET /api/v1/projects/{id}/views/{viewId}/buckets |
| /api/projects/{id}/views/{viewId}/buckets | POST | PUT /api/v1/projects/{id}/views/{viewId}/buckets |
| /api/projects/{id}/views/{viewId}/buckets/tasks | POST | POST (move task between buckets) |

**Labels:**

| Our endpoint | Method | Vikunja endpoint |
|---|---|---|
| /api/labels | GET | GET /api/v1/labels |
| /api/labels | POST | PUT /api/v1/labels |
| /api/labels/{id} | PUT | PUT /api/v1/labels/{id} |
| /api/labels/{id} | DELETE | DELETE /api/v1/labels/{id} |

### 3.3 AI Extraction Endpoints

**POST /api/ingest** — Extract tasks from text. Supports SSE streaming.

```json
// Request
{
    "text": "Meeting notes...",
    "source_type": "notes",
    "model": "gemini-2.0-flash",
    "confidential": false,
    "project_hint": "PhD"
}
// Response (or SSE stream of individual proposals)
{
    "source_id": "uuid",
    "model_used": "gemini-2.0-flash",
    "proposals": [TaskProposal],
    "raw_response": { ... }  // full LLM response for debugging
}
```

**POST /api/chat** — Conversational extraction.

```json
// Request
{ "message": "...", "conversation_id": "uuid or null", "model": "gemini-2.0-flash" }
// Response
{ "reply": "...", "proposals": [TaskProposal], "conversation_id": "uuid" }
```

### 3.4 Proposal Endpoints

| Endpoint | Method | Description |
|---|---|---|
| /api/proposals | GET | List proposals (?status=pending) |
| /api/proposals/{id} | PUT | Edit proposal before approving |
| /api/proposals/{id}/approve | POST | Approve → create Vikunja task |
| /api/proposals/{id}/reject | POST | Reject proposal |
| /api/proposals/bulk | POST | Bulk approve/reject by ID list |
| /api/proposals/approve-all | POST | Approve all pending |

### 3.5 Auto-tagging Endpoints

| Endpoint | Method | Description |
|---|---|---|
| /api/labels/descriptions | GET | List all label descriptions |
| /api/labels/{id}/description | PUT | Set/update a label's description |
| /api/tasks/auto-tag | POST | Auto-tag existing tasks using label descriptions |
| /api/labels/stats | GET | Tag metrics: count, completion rate per label |

**POST /api/tasks/auto-tag** — Sends task titles + descriptions to the LLM along with label descriptions. Returns suggested label additions. Can target specific tasks or all untagged tasks.

```json
// Request
{ "task_ids": [1, 2, 3], "model": "gemini-2.0-flash" }
// or
{ "filter": "labels = []", "model": "gemini-2.0-flash" }
// Response
{ "suggestions": [{ "task_id": 1, "add_labels": [3, 5], "reasons": {"3": "matched 'writing'"} }] }
```

### 3.6 Scheduling (Phase 4)

| Endpoint | Method | Description |
|---|---|---|
| /api/schedule | POST | Create Google Calendar time blocks |
| /api/schedule/suggest | GET | LLM suggests schedule for a day |

---

## 4. LLM Integration

### 4.1 Model Selection

Users choose a model via a dropdown in the extraction UI. The backend routes accordingly.

Available models (configurable): Gemini 2.0 Flash (fast, cloud), Gemini 2.0 Pro (quality, cloud), Qwen 3.x (local via Ollama), Llama 3.3 (local via Ollama). The "Local" toggle forces Ollama routing regardless of selected model.

### 4.2 Tools

```python
tools = [
    {"name": "lookup_projects", "description": "Returns available Vikunja projects."},
    {"name": "resolve_project", "description": "Maps project name → Vikunja project ID."},
    {"name": "check_existing_tasks", "description": "Fuzzy-searches recent tasks to detect duplicates."},
    {"name": "get_label_descriptions", "description": "Returns all labels with their descriptions for auto-tagging."}
]
```

### 4.3 Extraction Prompt

```
You are a task extraction assistant. Given unstructured text, extract actionable tasks.

Use lookup_projects to get available projects. Use resolve_project for each task.
Use check_existing_tasks if a task might already exist.
Use get_label_descriptions to see available labels and auto-assign them based on their descriptions.

For each task, return JSON:
{
    "title": "Short, actionable (start with verb)",
    "description": "Brief context (1-2 sentences, nullable)",
    "project_name": "Matched project or 'Uncategorised'",
    "project_id": <from resolve_project>,
    "priority": 1-5, "due_date": "YYYY-MM-DD or null",
    "estimated_minutes": integer or null,
    "labels": ["matched_label_names"],
    "auto_tag_reasons": {"label_name": "why this label matches"}
}

Rules:
- Only extract actionable items for the USER
- Start titles with a verb
- Don't over-extract: "John will send the dataset" is NOT a user task
- Today's date is {today}
```

### 4.4 Error Handling

| Failure | Behaviour |
|---|---|
| Gemini rate limit | Fall back to Ollama if available; else error + retry |
| Gemini 5xx | Retry 3× with exponential backoff |
| Ollama unreachable | "Local model unavailable — check Ollama" |
| Ollama malformed JSON | Retry with JSON reminder; give up after 2 attempts |
| Vikunja down during tool call | Use cached project list; project_id = null |

---

## 5. Design System

### 5.1 Philosophy

**Dark theme, refined minimalism.** Inspired by Linear's density and Things 3's clarity. The app handles chaotic input and produces order — the UI is always composed. Tangerine accent on dark warm neutrals; no gradients, no decoration.

### 5.2 Tokens

```css
:root {
  /* Backgrounds */
  --bg-base: #111110;
  --bg-surface: #1A1A19;
  --bg-surface-hover: #222221;
  --bg-sidebar: #161615;
  --bg-elevated: #252524;
  --bg-overlay: rgba(0,0,0,0.6);

  /* Borders */
  --border-default: #2A2A28;
  --border-strong: #3A3A37;
  --border-subtle: #1F1F1E;

  /* Text */
  --text-primary: #EDEDEC;
  --text-secondary: #A1A09A;
  --text-tertiary: #6B6A65;
  --text-on-accent: #111110;

  /* Accent — tangerine */
  --accent: #E8772E;
  --accent-hover: #D4691F;
  --accent-subtle: rgba(232,119,46,0.1);
  --accent-glow: rgba(232,119,46,0.25);

  /* Priority */
  --priority-urgent: #EF5744;
  --priority-high: #E8772E;
  --priority-medium: #E2C541;
  --priority-low: #5BBC6E;
  --priority-none: #4A4A46;

  /* Semantic */
  --done: #5BBC6E;
  --overdue: #EF5744;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.5);

  /* Typography */
  --font-sans: 'IBM Plex Sans', -apple-system, sans-serif;
  --font-mono: 'IBM Plex Mono', 'Menlo', monospace;
  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.8125rem;  /* 13px */
  --text-base: 0.9375rem;/* 15px */
  --text-lg: 1rem;       /* 16px */
  --text-xl: 1.25rem;    /* 20px */

  /* Transitions */
  --transition-fast: 150ms ease-out;
  --transition-normal: 200ms ease-out;
  --transition-slow: 300ms ease-out;
}
```

**Spacing:** 4/8/12/16/20/24/32/48px. **Border radius:** 8px containers, 8px inputs, 6px inner elements, 9999px pills. **Component heights:** buttons 34px (sm) / 40px (md), inputs 40px (full) / 34px (in toolbars).

### 5.3 Primitives

Build these first in `components/ui/`. The live reference for all component states is in `docs/cognito-design-system.jsx`.

| Component | Key details |
|---|---|
| **Button** | Variants: accent, outline, ghost, danger, toggle. Sizes: sm/md. Loading spinner. `flexShrink: 0, whiteSpace: nowrap`. |
| **Input** | 40px height, accent focus ring + shadow. |
| **Textarea** | Auto-grow variant. Same focus ring as Input. |
| **Checkbox** | Circular (not square). Green fill + checkmark on done. 20px. |
| **PriorityIndicator** | 5 dots, filled/empty, colour-coded by level. Sizes: sm (7px) / md (8px). |
| **Badge** | Coloured pill from label hex_color. 24px height. |
| **DateDisplay** | Relative dates. Red if overdue. |
| **Kbd** | Monospace keyboard shortcut badge. 22px height. |
| **Dropdown** | Custom select with option descriptions, accent highlight, click-outside-to-close. |
| **Toast** | Bottom-right stack. Auto-dismiss 4s. Variants: success/error/info. Slide-up animation. |
| **SlideOver** | Right-side 480px panel. Backdrop. Escape to close. 200ms slide transition. |
| **Skeleton** | Pulsing rectangles matching content shape. |
| **Tooltip (Tip)** | Positions top or right (for collapsed sidebar). Arrow pointer. 100ms fade-in. |

### 5.4 Layout

```
┌──────────────┬────────────────────────────────────────────────┐
│              │  Page Title            Search  Filter  ◆  +New │
│   SIDEBAR    ├────────────────────────────────────────────────┤
│   240px      │  + Add task...                                 │
│   (56px      ├────────────────────────────────────────────────┤
│   collapsed) │                                                │
│              │  Task list / Kanban / Extraction page           │
│              │                                                │
│              │                     SlideOver detail panel →    │
└──────────────┴────────────────────────────────────────────────┘
```

**Sidebar:** Collapsible (240px → 56px icon rail). Tooltips appear to the RIGHT when collapsed, outside the sidebar boundary. Sidebar has `position: relative; z-index: 50; overflow: visible` when collapsed.

Contents: "cognito" wordmark + collapse toggle, nav links (All Tasks, Upcoming, Overdue) with counts, Projects section with colour dots, AI Extract button (accent border + subtle bg, prominent), Settings, user email.

**Top bar:** Fixed single row. Title left, actions right: search input (shrinks), Filter button, ◆ Extract button, + New button. All buttons have hover effects.

### 5.5 Task List View

Each row shows: circular checkbox, priority dots (5 dots), title (15px medium), description preview (13px tertiary, truncated, hidden when done), metadata row (project name, label badges with hover stats, attachment count icon with tooltip, subtask progress icon with tooltip), due date right-aligned (red if overdue), hover chevron.

**AI-tagged indicator:** Tasks auto-tagged by AI get a tangerine left border + inward glow (`box-shadow: inset 3px 0 8px -4px var(--accent-glow)`). This fades to default after the user views/opens the task.

**Sorting:** Smart default — overdue first, then by priority descending, then by due date ascending. User can override via Sort dropdown.

**Completed section:** Below a "Completed (N)" divider with toggle arrow. Completed tasks render at reduced opacity (0.65). Section is collapsible.

### 5.6 Kanban Board

Per-project. Fetch views → find view_kind=3 → fetch buckets → fetch tasks per bucket.

Cards show: priority dots, title, due date, first label. Drag with `svelte-dnd-action`. Position is midpoint between neighbours. Move API: POST to bucket/tasks endpoint.

### 5.7 Task Detail Panel (SlideOver)

480px, slides from right. All fields editable, auto-save (debounce 500ms text, immediate toggles). Fields: title (16px), done checkbox, project (Dropdown), priority (clickable dots), due date, labels (badges + add), description (textarea, markdown), estimated minutes, attachments section (images, files, links). Delete with confirmation. Created/updated timestamps at bottom.

### 5.8 AI Extraction Page

Route: `/extract`. Header: "◆ Extract Tasks" in accent. Model selector dropdown (Gemini Flash/Pro, Qwen, Llama). Local/Cloud toggle button with hover effect — when local, shows banner "Processing locally via Ollama — your data stays on this device."

Textarea input. Extract button with Ctrl+↵ hint. Collapsible "Raw AI Response" panel showing full JSON (tool calls, proposals, tokens, latency) for debugging.

Proposals stream in via SSE with fly transition + stagger. Each card has tangerine left border + glow, checkbox, priority, title, project, date, labels, edit button on hover. Approve All / Reject Selected actions.

### 5.9 Tag System

Each label can have a **description** (stored in agent DB) explaining what it covers. The AI extraction prompt includes these descriptions via the `get_label_descriptions` tool, enabling auto-tagging of new and existing tasks.

**Tag stats on hover:** Hovering any label badge shows a tooltip with: total tasks, completed, open, completion percentage.

**Auto-tag existing tasks:** POST /api/tasks/auto-tag sends untagged (or all) task titles to the LLM with label descriptions, returns suggestions. Applies silently; user can remove tags.

### 5.10 Interactions

**Optimistic updates** on all mutations. Pattern: update store → fire API → on failure: rollback + error toast.

**Keyboard shortcuts:** N (new), E (edit), X (toggle done), / (search), Ctrl+Enter (submit extraction), Esc (close panel/deselect), J/K (navigate list), Enter (open task), 1-5 (set priority), ? (shortcuts help).

**Transitions:** Svelte `fly`, `fade`, `slide`. 150ms hover, 200ms panels/cards, 300ms slide-overs.

### 5.11 Loading & Empty States

Skeleton screens matching content shape (not spinners). Empty states with helpful messages: "No tasks yet", "Paste meeting notes to extract tasks", "No search results."

### 5.12 Responsive

Desktop (>1024px): full sidebar + content + slide-over. Tablet (768-1024px): collapsed sidebar. Mobile (<768px): sidebar hidden, full-screen overlays, horizontal kanban scroll.

---

## 6. Vikunja API Reference

Auth: `Authorization: Bearer {VIKUNJA_API_TOKEN}` on all requests. **PUT creates, POST updates** (exception: label update uses PUT).

**Tasks:**
```
GET    /api/v1/tasks/all?page=1&per_page=50&s=search&sort_by=due_date&order_by=asc&filter=done%20%3D%20false
GET    /api/v1/tasks/{id}
POST   /api/v1/tasks/{id}                    # Update
DELETE /api/v1/tasks/{id}
PUT    /api/v1/projects/{projectId}/tasks     # Create
PUT    /api/v1/tasks/{id}/labels             # Add label: {"label_id": 1}
DELETE /api/v1/tasks/{id}/labels/{labelId}
```

**Projects:**
```
GET    /api/v1/projects
PUT    /api/v1/projects                       # Create
POST   /api/v1/projects/{id}                  # Update
```

**Views & Buckets (kanban):**
```
GET    /api/v1/projects/{id}/views
GET    /api/v1/projects/{id}/views/{viewId}/buckets
PUT    /api/v1/projects/{id}/views/{viewId}/buckets              # Create
POST   /api/v1/projects/{id}/views/{viewId}/buckets/{bucketId}   # Update
POST   /api/v1/projects/{id}/views/{viewId}/buckets/tasks        # Move: {"task_id":X,"bucket_id":Y,"position":Z}
```

**Labels:**
```
GET    /api/v1/labels
PUT    /api/v1/labels          # Create
PUT    /api/v1/labels/{id}     # Update (also PUT)
DELETE /api/v1/labels/{id}
```

**Key quirks:** position is float (midpoint for reorder), bucket_id is view-dependent, filter uses expression syntax, search uses `s` param, pagination in response headers (`x-pagination-total-pages`), dates ISO 8601 (`2026-03-07T00:00:00Z`), projects nest via `parent_project_id`.

---

## 7. Project Structure

```
cognito/
├── CLAUDE.md                    # Agent context (always loaded)
├── TASKS.md                     # Ordered implementation queue
├── docs/
│   ├── SPEC.md                  # This file
│   └── cognito-design-system.jsx  # Live component reference (React, for visual iteration)
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py, config.py, database.py
│   │   ├── auth/                # oauth.py, jwt.py, dependencies.py
│   │   ├── routers/             # auth, ingest, chat, proposals, tasks, projects, labels, schedule, auto_tag
│   │   ├── services/            # llm.py, extractor.py, vikunja.py, tagger.py, gcal.py
│   │   └── models/              # proposal.py, config.py, label_description.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app.css              # Design tokens
│   │   ├── routes/              # +layout.svelte, +page.svelte, project/[id]/, extract/
│   │   ├── lib/                 # api.ts, stores.svelte.ts, types.ts, optimistic.ts, shortcuts.ts
│   │   └── components/
│   │       ├── ui/              # Button, Input, Textarea, Checkbox, Dropdown, Badge, Toast, SlideOver, Skeleton, Tip, etc.
│   │       ├── Sidebar.svelte, TaskList.svelte, TaskRow.svelte, TaskDetail.svelte
│   │       ├── KanbanBoard.svelte, KanbanColumn.svelte, KanbanCard.svelte
│   │       ├── ExtractionPanel.svelte, ProposalCard.svelte, RawResponse.svelte
│   │       └── FilterBar.svelte
│   ├── package.json
│   └── svelte.config.js
```

---

## 8. Docker Compose

```yaml
services:
  vikunja:
    image: vikunja/vikunja:latest
    ports: ["3456:3456"]
    volumes: [./vikunja-data:/app/vikunja]
    environment:
      - VIKUNJA_SERVICE_JWTSECRET=${VIKUNJA_JWT_SECRET}
    restart: unless-stopped

  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: [./data:/app/data]
    environment:
      - VIKUNJA_URL=http://vikunja:3456
      - VIKUNJA_API_TOKEN=${VIKUNJA_API_TOKEN}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OLLAMA_URL=http://host.docker.internal:11434
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - JWT_SECRET=${JWT_SECRET}
      - ALLOWED_EMAIL=${ALLOWED_EMAIL}
      - DATABASE_URL=sqlite:///app/data/agent.db
    extra_hosts: ["host.docker.internal:host-gateway"]
    depends_on: [vikunja]
    restart: unless-stopped

  frontend:
    build: { context: ./frontend, target: production }
    ports: ["5173:80"]
    environment: [PUBLIC_API_URL=${BACKEND_URL}/api]
    depends_on: [backend]
    restart: unless-stopped
```

---

## 9. Environment Variables

```env
# Vikunja
VIKUNJA_URL=http://localhost:3456
VIKUNJA_API_TOKEN=your_vikunja_api_token
VIKUNJA_JWT_SECRET=random_secret_for_vikunja

# LLM
GEMINI_API_KEY=your_gemini_key
OLLAMA_URL=http://localhost:11434

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# App
JWT_SECRET=random_secret_for_jwt
ALLOWED_EMAIL=your@email.com
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
DATABASE_URL=sqlite:///./data/agent.db
```
# Cognito — Technical Specification v2

**A unified task management + AI extraction app powered by Vikunja (headless)**

Version 2.1 — March 2026 (API-verified against Vikunja v2.1+)

---

## 1. Overview

Cognito is a single SvelteKit application that combines task management with AI-powered task extraction. Vikunja runs as a **headless backend** — users never see Vikunja's UI. The SvelteKit frontend provides all task management views (list, kanban) plus an integrated AI extraction panel for turning unstructured text into tasks.

### 1.1 Core Architecture

```
┌─────────────────────────────────────────────────────────┐
│              COGNITO (SvelteKit)                         │
│                                                         │
│  ┌──────────┐ ┌───────────┐ ┌────────┐ ┌────────────┐  │
│  │ AI Input │ │ Task List │ │ Kanban │ │ Task Detail │  │
│  │ Panel    │ │ View      │ │ Board  │ │ Panel       │  │
│  └──────────┘ └───────────┘ └────────┘ └────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS (JWT cookie)
                        ▼
┌─────────────────────────────────────────────────────────┐
│              COGNITO BACKEND (FastAPI)                    │
│                                                          │
│  /api/auth       → Google OAuth + JWT                    │
│  /api/ingest     → LLM extraction → proposal queue       │
│  /api/chat       → Conversational extraction              │
│  /api/proposals  → CRUD + approve/reject                  │
│  /api/tasks      → Proxy to Vikunja task CRUD             │
│  /api/projects   → Proxy to Vikunja project CRUD          │
│  /api/labels     → Proxy to Vikunja label CRUD            │
│  /api/schedule   → Google Calendar (Phase 3)              │
│                                                          │
│  Services:                                               │
│    llm.py        → Gemini / Ollama router                │
│    extractor.py  → Tool-calling extraction pipeline      │
│    vikunja.py    → Vikunja REST API client (expanded)    │
│    gcal.py       → Google Calendar client (Phase 3)      │
└───────────────────────┬──────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────────┐
    │ Vikunja  │  │ Ollama   │  │ Google       │
    │ API      │  │ (local)  │  │ Calendar API │
    │ :3456    │  │ :11434   │  │ (Phase 3)    │
    └──────────┘  └──────────┘  └──────────────┘
```

### 1.2 Design Principles

- **Vikunja is the task database.** It runs headless — all task state lives there, but users never interact with its UI.
- **One app, one login.** Users log in once via Google OAuth. The backend handles all Vikunja API auth with a service token.
- **AI extraction is a first-class feature**, not a bolt-on. The extraction panel lives alongside the task views.
- **Build only what you use.** List view, kanban, task editing, labels. Skip features you don't need (Gantt, table view, sharing, teams).
- **Confidential data stays local.** Inputs flagged confidential route through Ollama, never to external APIs.
- **Optimised for a coding agent.** This spec is structured so each section can be handed to a coding agent as a self-contained task.

### 1.3 Technical Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend | SvelteKit (single app) | Familiar from prior project; handles all views |
| Backend | FastAPI (Python) | Familiar, async, good for LLM streaming |
| Task Storage | Vikunja (Docker, headless) | Mature task API, handles all PM data |
| LLM (general) | Gemini API | Best structured output + native function calling |
| LLM (confidential) | Ollama (localhost) | PHI-safe, no data leaves server — Qwen 3.x for tool calling |
| Calendar | Google Calendar API | Time-block scheduling (Phase 3) |
| Auth | Google OAuth 2.0 → JWT | Reused from existing codebase |
| Agent DB | SQLite | Proposal queue + config only |

### 1.4 What Vikunja Handles vs What Cognito Handles

| Concern | Handled by |
|---------|-----------|
| Task storage, projects, labels, priorities, due dates | Vikunja (headless API) |
| Task UI (list view, kanban, detail editing) | Cognito frontend |
| AI task extraction from unstructured text | Cognito backend (LLM + tools) |
| Proposal review & approval | Cognito frontend |
| Time-block scheduling | Cognito backend → Google Calendar (Phase 3) |
| Authentication | Cognito backend (Google OAuth → JWT) |

---

## 2. Data Models

Cognito has two data domains: **Vikunja data** (tasks, projects, labels — all stored in Vikunja, accessed via API) and **agent data** (proposals, config — stored in local SQLite).

### 2.1 Vikunja Data (accessed via API, not stored locally)

These are the Vikunja data structures the frontend needs to understand. The backend proxies these — the frontend never calls Vikunja directly.

#### Task (from Vikunja API)

The frontend renders and edits these fields:

| Field | Type | Used in UI |
|-------|------|-----------|
| id | integer | Internal reference |
| title | string | List view, kanban card, detail panel |
| description | string | Detail panel (markdown supported) |
| done | boolean | Checkbox in list/kanban |
| done_at | datetime | When marked done (system-controlled, read-only) |
| priority | integer | 0 (unset) to 5 (urgent) — star rating or colour |
| due_date | datetime | List view, detail panel, overdue highlighting |
| start_date | datetime | Detail panel (optional) |
| end_date | datetime | Detail panel (optional) |
| project_id | integer | Grouping, sidebar navigation |
| labels | array of Label | Coloured chips on cards |
| assignees | array of User | Detail panel (single-user setup, optional) |
| percent_done | float | Optional progress indicator (0.0–1.0) |
| hex_color | string | Task colour indicator (max 7 chars, e.g. "#ff0000") |
| repeat_after | integer | Repeat interval in seconds (0 = no repeat) |
| repeat_mode | integer | 0=default, 1=month, 2=from current date |
| index | integer | Task index within project (auto-assigned) |
| identifier | string | Human-readable ID e.g. "PHD-12" (computed, read-only) |
| uid | string | UUID for CalDAV (read-only) |
| is_favorite | boolean | Favorited by current user |
| position | float | Sort order (from task_positions, view-dependent) |
| bucket_id | integer | Kanban column (from task_buckets, view-dependent) |
| reminders | array | Task reminders (detail panel) |
| attachments | array | File attachments (detail panel) |
| related_tasks | object | Related task map by relation type |
| created_by | object | User who created the task (read-only) |
| created | datetime | Creation timestamp (read-only) |
| updated | datetime | Last update timestamp (read-only) |

#### Project (from Vikunja API)

| Field | Type | Used in UI |
|-------|------|-----------|
| id | integer | Internal reference |
| title | string | Sidebar, task grouping (required, 1-250 chars) |
| description | string | Optional subtitle |
| identifier | string | Short project identifier used in task IDs (e.g. "PHD") |
| hex_color | string | Project colour dot |
| is_archived | boolean | Hide from sidebar unless toggled |
| is_favorite | boolean | Show in favourites section |
| parent_project_id | integer | For nested project hierarchy |
| position | float | Project ordering in sidebar |
| views | array of ProjectView | Available views (list, kanban, etc.) |

#### Label (from Vikunja API)

| Field | Type | Used in UI |
|-------|------|-----------|
| id | integer | Internal reference |
| title | string | Label text |
| hex_color | string | Chip colour |

#### ProjectView (from Vikunja API)

Vikunja organises task display through "views" — each project can have multiple views (list, kanban, table, gantt). Kanban buckets belong to a specific view, not directly to a project. **This is a critical distinction from older Vikunja versions.**

| Field | Type | Used in UI |
|-------|------|-----------|
| id | integer | Internal reference |
| title | string | View tab label |
| project_id | integer | Parent project |
| view_kind | integer | 0=list, 1=gantt, 2=table, 3=kanban |
| filter | string | Default filter for this view |
| bucket_configuration_mode | integer | 0=none, 1=manual |
| default_bucket_id | integer | Default bucket for new tasks (kanban) |
| done_bucket_id | integer | Bucket for completed tasks (kanban) |
| position | float | View ordering |

#### Bucket (from Vikunja API — belongs to a ProjectView, not a Project)

| Field | Type | Used in UI |
|-------|------|-----------|
| id | integer | Column reference |
| title | string | Column header |
| position | float | Column order |
| limit | integer | WIP limit (optional, 0 = no limit) |
| project_view_id | integer | Which view this bucket belongs to |
| created_by | object | User who created the bucket |
| created | datetime | Creation timestamp |
| updated | datetime | Last update timestamp |

### 2.2 Agent Data (stored in local SQLite)

#### TaskProposal

| Field | Type | Description |
|-------|------|-------------|
| id | TEXT (UUID) | Primary key |
| source_id | TEXT (UUID) | Groups proposals from the same ingestion batch |
| title | TEXT | Task title (extracted by LLM) |
| description | TEXT | Task details/context (nullable) |
| project_name | TEXT | Suggested Vikunja project name |
| project_id | INTEGER | Vikunja project ID (resolved via tool call, nullable) |
| priority | INTEGER | 1–5, maps to Vikunja priority |
| due_date | DATE | Suggested deadline (nullable) |
| estimated_minutes | INTEGER | Time estimate for scheduling (nullable) |
| labels | JSON | Array of label strings (nullable) |
| source_type | TEXT | 'notes', 'email', 'idea', 'manual' |
| source_text | TEXT | Original input text |
| confidential | BOOLEAN | If true, was processed by Ollama |
| status | TEXT | 'pending', 'approved', 'rejected', 'created' |
| vikunja_task_id | INTEGER | Vikunja task ID after creation (nullable) |
| gcal_event_id | TEXT | Google Calendar event ID (nullable, Phase 3) |
| created_at | TIMESTAMP | Extraction time |
| reviewed_at | TIMESTAMP | Approval/rejection time (nullable) |

#### VikunjaProject (cached)

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Vikunja project ID |
| title | TEXT | Project name |
| description | TEXT | Project description |
| last_synced_at | TIMESTAMP | When last fetched |

#### AgentConfig (singleton)

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Always 1 |
| default_project_id | INTEGER | Fallback project for unmatched names |
| ollama_model | TEXT | Model for confidential tasks (e.g. 'qwen3:4b') |
| gemini_model | TEXT | Gemini model name |
| gcal_calendar_id | TEXT | Target calendar (Phase 3) |

### 2.3 SQLite Schema

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
    status TEXT DEFAULT 'pending',
    vikunja_task_id INTEGER,
    gcal_event_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP
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
    ollama_model TEXT DEFAULT 'qwen3:4b',
    gemini_model TEXT DEFAULT 'gemini-2.0-flash',
    gcal_calendar_id TEXT
);
```

---

## 3. API Specification

The backend serves two roles: (1) AI extraction + proposal management, and (2) proxy layer to Vikunja's API with a unified auth model.

### 3.1 Authentication

Reused from existing codebase. Single Google OAuth login gates all access.

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/auth/login | GET | Redirect to Google OAuth consent |
| /api/auth/callback | GET | OAuth callback → set JWT cookie → redirect to frontend |
| /api/auth/me | GET | Return current user info |
| /api/auth/logout | POST | Clear JWT cookie |

### 3.2 Task Proxy Endpoints

These proxy to Vikunja's REST API. The backend adds the Vikunja API token and translates responses as needed. The frontend never calls Vikunja directly.

#### Tasks

| Endpoint | Method | Description | Vikunja endpoint |
|----------|--------|-------------|-----------------|
| /api/tasks | GET | List all tasks (with query params for filtering) | GET /api/v1/tasks/all |
| /api/tasks/{id} | GET | Get single task | GET /api/v1/tasks/{id} |
| /api/tasks/{id} | PUT | Update task (title, description, done, priority, due_date, etc.) | POST /api/v1/tasks/{id} |
| /api/tasks/{id} | DELETE | Delete task | DELETE /api/v1/tasks/{id} |
| /api/projects/{id}/tasks | POST | Create task in project | PUT /api/v1/projects/{id}/tasks |
| /api/tasks/{id}/labels | POST | Add label to task | POST /api/v1/tasks/{id}/labels |
| /api/tasks/{id}/labels/{labelId} | DELETE | Remove label from task | DELETE /api/v1/tasks/{id}/labels/{labelId} |

**Query parameters for GET /api/tasks:**

| Param | Type | Description |
|-------|------|-------------|
| page | integer | Page number (pagination) |
| per_page | integer | Items per page (default 50) |
| s | string | Text search in title/description |
| sort_by | string | Comma-separated fields: 'due_date', 'priority', 'created', 'done', 'id' |
| order_by | string | 'asc' or 'desc' (matches sort_by order) |
| filter | string | Filter expression using Vikunja filter syntax (see below) |
| filter_timezone | string | Timezone for date comparisons in filter |
| filter_include_nulls | boolean | Include null values in filtered results |
| expand | string | Comma-separated: 'subtasks', 'buckets', 'comments' |

**Vikunja filter syntax examples:**
- `done = false` — incomplete tasks only
- `priority >= 3` — high priority tasks
- `due_date < now+7d` — due within 7 days
- `project_id = 1 && done = false` — incomplete tasks in project 1
- `labels in [1,2,3]` — tasks with specific label IDs
- Comparators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `in`, `not in`
- Combinators: `&&` (AND), `||` (OR), parentheses for grouping
- Date math: `now`, `now+1d`, `now-1w`, `now+1m`

#### Projects & Views

| Endpoint | Method | Description | Vikunja endpoint |
|----------|--------|-------------|-----------------|
| /api/projects | GET | List all projects | GET /api/v1/projects |
| /api/projects/{id} | GET | Get project (includes views) | GET /api/v1/projects/{id} |
| /api/projects | POST | Create project | PUT /api/v1/projects |
| /api/projects/{id} | PUT | Update project | POST /api/v1/projects/{id} |
| /api/projects/{id}/views | GET | List views for a project | GET /api/v1/projects/{id}/views |
| /api/projects/{id}/views | POST | Create a view | PUT /api/v1/projects/{id}/views |
| /api/projects/{id}/views/{viewId} | PUT | Update a view | POST /api/v1/projects/{id}/views/{viewId} |
| /api/projects/{id}/views/{viewId} | DELETE | Delete a view | DELETE /api/v1/projects/{id}/views/{viewId} |
| /api/projects/{id}/views/{viewId}/buckets | GET | List kanban buckets for a view | GET /api/v1/projects/{id}/views/{viewId}/buckets |
| /api/projects/{id}/views/{viewId}/buckets | POST | Create bucket in view | PUT /api/v1/projects/{id}/views/{viewId}/buckets |
| /api/projects/{id}/views/{viewId}/buckets/{bucketId} | PUT | Update bucket | POST /api/v1/projects/{id}/views/{viewId}/buckets/{bucketId} |
| /api/projects/{id}/views/{viewId}/buckets/{bucketId} | DELETE | Delete bucket | DELETE /api/v1/projects/{id}/views/{viewId}/buckets/{bucketId} |
| /api/projects/{id}/views/{viewId}/buckets/tasks | POST | Move task between buckets | POST /api/v1/projects/{id}/views/{viewId}/buckets/tasks |

#### Labels

| Endpoint | Method | Description | Vikunja endpoint |
|----------|--------|-------------|-----------------|
| /api/labels | GET | List all labels | GET /api/v1/labels |
| /api/labels | POST | Create label | PUT /api/v1/labels |
| /api/labels/{id} | PUT | Update label | PUT /api/v1/labels/{id} |
| /api/labels/{id} | DELETE | Delete label | DELETE /api/v1/labels/{id} |

### 3.3 AI Extraction Endpoints

These are Cognito-specific — no Vikunja equivalent.

#### POST /api/ingest

Accept unstructured text, extract tasks via LLM with tool calls, return proposals. Supports SSE streaming.

**Request:**
```json
{
    "text": "Meeting notes from today:\n- Need to submit ethics amendment by March 3\n- John will send the dataset, I need to preprocess it",
    "source_type": "notes",
    "confidential": false,
    "project_hint": "PhD"
}
```

**Response:**
```json
{
    "source_id": "uuid",
    "proposals": [
        {
            "id": "uuid",
            "title": "Submit ethics amendment",
            "project_name": "PhD",
            "project_id": 1,
            "priority": 4,
            "due_date": "2026-03-03",
            "estimated_minutes": 60,
            "labels": ["admin", "ethics"],
            "status": "pending"
        }
    ]
}
```

**SSE streaming:** If request includes `Accept: text/event-stream`, each proposal is emitted as a separate SSE event as it's extracted.

#### POST /api/chat

Conversational extraction — user describes tasks in natural language.

**Request:**
```json
{
    "message": "I had a meeting with my supervisor. We agreed I need to revise chapter 3 by next Friday.",
    "conversation_id": "uuid or null"
}
```

**Response:**
```json
{
    "reply": "I've extracted 1 task. Want me to break the chapter revision into sub-tasks?",
    "proposals": [TaskProposal],
    "conversation_id": "uuid"
}
```

### 3.4 Proposal Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/proposals | GET | List proposals (query: ?status=pending) |
| /api/proposals/{id} | PUT | Edit proposal before approving |
| /api/proposals/{id}/approve | POST | Approve → create task in Vikunja |
| /api/proposals/{id}/reject | POST | Reject proposal |
| /api/proposals/bulk | POST | Bulk approve/reject by ID list |
| /api/proposals/approve-all | POST | Approve all pending proposals |

**POST /api/proposals/{id}/approve response:**
```json
{
    "success": true,
    "vikunja_task_id": 142
}
```

**POST /api/proposals/bulk request:**
```json
{
    "approve": ["uuid1", "uuid2"],
    "reject": ["uuid3"]
}
```

### 3.5 Scheduling (Phase 3)

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/schedule | POST | Create Google Calendar time blocks from tasks |
| /api/schedule/suggest | GET | LLM suggests a schedule for a given day |

### 3.6 Sync

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/projects/sync | POST | Force refresh of Vikunja project cache |

---

## 4. LLM Integration

### 4.1 Router Logic

```python
def get_llm_client(confidential: bool):
    if confidential:
        return OllamaClient(model=config.ollama_model)  # must support tool calling
    else:
        return GeminiClient(model=config.gemini_model)
```

### 4.2 Tool-Assisted Extraction

Tools exposed to the LLM during extraction:

```python
tools = [
    {
        "name": "lookup_projects",
        "description": "Returns the list of available Vikunja projects.",
        "parameters": {}
    },
    {
        "name": "resolve_project",
        "description": "Maps a project name to its Vikunja project ID. Returns the default project if no match.",
        "parameters": {
            "name": {"type": "string", "description": "Project name to look up"}
        }
    },
    {
        "name": "check_existing_tasks",
        "description": "Fuzzy-searches recent Vikunja tasks by title to detect duplicates.",
        "parameters": {
            "title": {"type": "string", "description": "Task title to check"}
        }
    }
]
```

**Extraction flow:**
1. LLM receives unstructured input + tool definitions
2. LLM calls `lookup_projects()` to get real project names
3. For each task, LLM calls `resolve_project(name)` for actual `project_id`
4. Optionally calls `check_existing_tasks(title)` for duplicate detection
5. LLM returns structured JSON array of proposals

**Project resolution rules:**
- Match found → use its ID
- No match → use `default_project_id` from config
- No default configured → `project_id = null`, user assigns in proposal edit

### 4.3 Task Extraction Prompt

```
You are a task extraction assistant for a PhD student. Given unstructured
text (meeting notes, emails, or freeform ideas), extract actionable tasks.

Use the lookup_projects tool to get available projects before extracting.
Use resolve_project for each task to get the correct project ID.
Use check_existing_tasks if a task might already exist.

For each task, return JSON:
{
    "title": "Short, actionable title (start with verb)",
    "description": "Brief context (1-2 sentences, nullable)",
    "project_name": "Matching project from lookup_projects, or 'Uncategorised'",
    "project_id": <resolved via resolve_project>,
    "priority": 1-5 (1=low, 3=normal, 5=urgent),
    "due_date": "YYYY-MM-DD or null",
    "estimated_minutes": integer or null,
    "labels": ["relevant", "labels"]
}

Rules:
- Only extract actionable items for the USER (not tasks assigned to others)
- Start titles with a verb: "Write...", "Email...", "Review...", "Submit..."
- If a deadline is mentioned, include it. Calculate dates from relative references.
- Don't over-extract: "John will send the dataset" is NOT a user task
- Keep titles concise — task titles, not essays
- Today's date is {today}

Return a JSON array. If no actionable tasks found, return [].
```

### 4.4 Error Handling

| Failure | Behaviour |
|---------|-----------|
| Gemini rate limit / quota | Fall back to Ollama if available; else show error + retry button |
| Gemini 5xx | Retry up to 3× with exponential backoff (1s, 2s, 4s) |
| Ollama unreachable | Error: "Local model unavailable — check Ollama or switch to non-confidential" |
| Ollama malformed JSON | Retry with explicit JSON reminder; give up after 2 attempts |
| Vikunja down during tool call | Use cached project list; set `project_id = null` |

---

## 5. Design System & Frontend

### 5.0 Design Philosophy

**Aesthetic direction: Linear meets Things 3.** Clean, slightly warm neutral palette with sharp accent colours. High information density without clutter. Every interaction feels instant. The AI extraction feature should feel integrated and magical, not bolted on.

**Core principles:**
- Consistency over creativity — every element follows the same spacing, colour, and typography rules.
- Optimistic updates everywhere — UI responds immediately, API catches up in the background.
- Keyboard-first for power users, mouse-friendly for quick interactions.
- Motion communicates state changes, never decorates.

### 5.1 Design Tokens

These tokens should be defined as CSS custom properties (or Tailwind theme config) and used everywhere. The coding agent should build with these from the start.

#### Colour Palette

```css
:root {
  /* Background layers (light to dark surface hierarchy) */
  --bg-base: #FAFAF9;          /* Main background — warm off-white */
  --bg-surface: #FFFFFF;        /* Cards, panels, elevated surfaces */
  --bg-surface-hover: #F5F5F4;  /* Hover state on surface elements */
  --bg-sidebar: #F5F5F4;        /* Sidebar background — subtle distinction */
  --bg-overlay: rgba(0,0,0,0.4); /* Modal/slide-over backdrop */

  /* Borders */
  --border-default: #E7E5E4;    /* Standard borders */
  --border-strong: #D6D3D1;     /* Emphasis borders, active states */

  /* Text */
  --text-primary: #1C1917;      /* Headings, task titles */
  --text-secondary: #57534E;    /* Descriptions, metadata */
  --text-tertiary: #A8A29E;     /* Placeholders, timestamps */
  --text-on-accent: #FFFFFF;    /* Text on accent-coloured backgrounds */

  /* Accent — a warm indigo that feels professional but not corporate */
  --accent: #6366F1;            /* Primary actions, active nav items */
  --accent-hover: #4F46E5;      /* Hover on accent elements */
  --accent-subtle: #EEF2FF;     /* Accent tint for backgrounds (selected items) */

  /* Semantic */
  --priority-urgent: #EF4444;   /* Priority 5 */
  --priority-high: #F97316;     /* Priority 4 */
  --priority-medium: #EAB308;   /* Priority 3 */
  --priority-low: #22C55E;      /* Priority 2 */
  --priority-none: #A8A29E;     /* Priority 0-1 */
  --done: #22C55E;              /* Checkmarks, completed states */
  --overdue: #EF4444;           /* Overdue date highlighting */
  --ai-accent: #8B5CF6;         /* AI-specific elements — extraction, proposals */

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 25px rgba(0,0,0,0.1);
  --shadow-slide-over: -4px 0 25px rgba(0,0,0,0.1);
}
```

**Dark mode (future):** Invert the surface hierarchy. `--bg-base: #1C1917`, `--bg-surface: #292524`, etc. Design tokens make this a config swap, not a rewrite.

#### Typography

```css
:root {
  --font-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'IBM Plex Mono', 'Menlo', monospace;

  --text-xs: 0.75rem;    /* 12px — timestamps, badges */
  --text-sm: 0.8125rem;  /* 13px — metadata, labels */
  --text-base: 0.875rem; /* 14px — body text, task titles in list */
  --text-lg: 1rem;       /* 16px — section headers, task title in detail */
  --text-xl: 1.25rem;    /* 20px — page titles */

  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;

  --leading-tight: 1.3;
  --leading-normal: 1.5;
}
```

**Why IBM Plex Sans:** It's distinctive without being distracting, has excellent readability at small sizes (important for information-dense task lists), includes a matching mono variant, and is free/open source. Import via Google Fonts or self-host.

#### Spacing Scale

```
4px  — icon padding, tight gaps
8px  — inside small components (labels, badges)
12px — between related items within a group
16px — standard padding inside containers
20px — between groups/sections
24px — generous padding (cards, panels)
32px — section separation
48px — major layout gaps
```

#### Sizing

```
Sidebar width: 240px (desktop), 64px (collapsed/tablet), 0 (mobile)
Detail panel width: 480px
Kanban card min-width: 280px
Task row height: ~52px (compact enough for density, tall enough for two lines)
Border radius: 6px (cards/containers), 4px (inputs/badges), 9999px (pills)
```

#### Transitions

```css
--transition-fast: 150ms ease-out;   /* Hover states, toggles */
--transition-normal: 200ms ease-out; /* Panel opens, card moves */
--transition-slow: 300ms ease-out;   /* Page transitions, slide-overs */
```

### 5.2 Primitive Components

Build these first, before any features. Every other component inherits from these.

| Component | Purpose | Key details |
|-----------|---------|-------------|
| Button | Primary/secondary/ghost actions | Sizes: sm/md. Variants: accent, outline, ghost. Loading state with spinner. |
| Input | Text fields | Consistent height (36px), focus ring using --accent, placeholder using --text-tertiary. |
| Textarea | Multi-line input | Auto-grow variant for descriptions. |
| Select | Dropdowns | Custom styled, not native. Project selector, sort selector. |
| Checkbox | Task done toggle | Custom styled circle (not square). Animate fill on check. |
| Toast | Notifications | Bottom-right stack. Auto-dismiss 4s. Variants: success, error, info. |
| SlideOver | Detail panels | Right-side slide with backdrop. 480px width. Escape to close. |
| Skeleton | Loading states | Pulsing grey rectangles matching the shape of content they replace. |
| Badge | Labels, counts | Coloured pill with label text. Uses label hex_color as background. |
| PriorityIndicator | Priority display | Coloured dot or bar using semantic priority colours. Not stars — dots are more compact. |
| DateDisplay | Due date rendering | Shows relative dates ("Tomorrow", "Mar 7"). Red if overdue. |
| Kbd | Keyboard shortcut hints | Small monospace badge (e.g. "N" for new task). Shown on hover/focus. |

### 5.3 Interaction Patterns

#### Optimistic Updates

Every mutation follows this pattern:

```
1. User acts (check task, drag card, change priority)
2. UI updates immediately (Svelte store mutation)
3. API call fires in background
4. On success: do nothing (UI is already correct)
5. On failure: roll back store, show error toast with retry
```

Implement this as a reusable `optimisticUpdate(store, mutation, apiCall, rollback)` helper.

#### Keyboard Shortcuts

| Key | Context | Action |
|-----|---------|--------|
| `n` | Any view | Open quick-add task input |
| `e` | Task selected | Open task detail panel |
| `j` / `k` | Task list | Move selection down / up |
| `x` | Task selected | Toggle done |
| `1-5` | Task detail open | Set priority |
| `Escape` | Any panel open | Close panel |
| `/` | Any view | Focus search input |
| `Cmd+Enter` | AI extraction | Submit for extraction |

Register at the page layout level. Disable when an input/textarea is focused.

#### Transitions & Motion

| Element | Animation | Duration |
|---------|-----------|----------|
| SlideOver panel | Slide in from right + backdrop fade | 200ms ease-out |
| Toast notification | Fade + slide up from bottom-right | 150ms ease-out |
| Task completion | Checkbox fills with green, text fades slightly | 200ms |
| Kanban card drag | Card lifts with shadow, placeholder shows | Native drag feel |
| AI proposal appearing | Fade in + slide up, 50ms stagger between cards | 200ms per card |
| Task row hover | Background shifts to --bg-surface-hover | 100ms |

Use Svelte's built-in `fly`, `fade`, `slide` transitions. No external animation library needed.

### 5.4 Page Structure

```
┌──────┬──────────────────────────────────────────────────────┐
│      │  [/  Search...]                    [N  New]  [✨ AI] │
│  S   ├──────────────────────────────────────────────────────┤
│  I   │                                                      │
│  D   │   Main Content Area                                  │
│  E   │                                                      │
│  B   │   Routes:                                            │
│  A   │   /              → All tasks (list view)             │
│  R   │   /project/:id   → Project tasks (list)              │
│      │   /project/:id/kanban → Project kanban               │
│      │   /extract       → AI extraction panel               │
│      │                                                      │
│      │   Overlays:                                          │
│      │   Task Detail    → SlideOver from right (480px)      │
│      │                                                      │
└──────┴──────────────────────────────────────────────────────┘
```

### 5.5 Sidebar

Fixed left, 240px wide, `--bg-sidebar` background. Subtle right border.

```
┌─────────────────────────┐
│  ✨ Cognito             │  ← App name, --text-primary, --font-semibold
│                         │
│  All Tasks         (12) │  ← Active item gets --accent-subtle bg + --accent text
│  Upcoming           (5) │
│  Overdue            (2) │  ← --overdue colour for count badge
│                         │
│  ── Projects ────────── │  ← Section divider, --text-tertiary
│                         │
│  ● PhD              (8) │  ← Colour dot from project.hex_color
│  ● Admin            (3) │
│  ● Teaching         (1) │
│                         │
│                         │
│                         │
│  ✨ AI Extract          │  ← Uses --ai-accent, slightly prominent
│  ⚙ Settings            │
│                         │
│  ○ user@email.com       │  ← Avatar + truncated email
└─────────────────────────┘
```

### 5.6 Task List View

```
┌──────────────────────────────────────────────────────────────┐
│  PhD                                [List ▪] [Kanban]        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ + Add task...                                      ↵   │  │  ← Quick-add, --text-tertiary placeholder
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Filter: [All ▾]  [Any priority ▾]  [Any label ▾]     │  │  ← Filter chips, toggle on/off
│  │  Sort: [Due date ▾]                                    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ○  ●●●●○  Submit ethics amendment           Mar 3  →      │  ← Row: checkbox, priority dots, title, date, chevron
│            ethics · admin                                    │  ← Labels as small badges, --text-secondary
│                                                              │
│  ○  ●●●○○  Revise chapter 3                 Mar 7  →      │
│            writing · draft                                   │
│                                                              │
│  ○  ●●○○○  Prepare lab presentation         Mar 10 →      │
│            presentation                                      │
│                                                              │
│  ── Completed (3) ──────────────────────── [show ▾] ──────  │  ← Collapsed section
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Details:**
- Priority shown as filled/empty dots (compact, colour-coded). Not stars — dots scan faster.
- Due date right-aligned, turns `--overdue` colour if past due.
- Hover: row background shifts to `--bg-surface-hover`, subtle chevron appears on right.
- Click anywhere on row: open task detail slide-over.
- Checkbox click: optimistic toggle, animate the fill.
- Quick-add at top: always visible, type title + Enter to create. Tab to set project/priority before submitting.

### 5.7 Kanban Board View

```
┌──────────────────────────────────────────────────────────────────┐
│  PhD                                [List] [Kanban ▪]  [+ Col]  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ To Do (4) ──────┐  ┌─ In Progress (2) ┐  ┌─ Done ────────┐ │
│  │                   │  │                  │  │               │ │
│  │ ┌───────────────┐ │  │ ┌──────────────┐ │  │ ┌───────────┐ │ │
│  │ │●●●● Submit    │ │  │ │●●● Revise   │ │  │ │ ✓ Book    │ │ │
│  │ │     ethics    │ │  │ │    ch. 3     │ │  │ │   room    │ │ │
│  │ │ Mar 3 · ethics│ │  │ │ Mar 7 ·draft │ │  │ │           │ │ │
│  │ └───────────────┘ │  │ └──────────────┘ │  │ └───────────┘ │ │
│  │                   │  │                  │  │               │ │
│  │ ┌───────────────┐ │  │                  │  │               │ │
│  │ │●●● Prepare   │ │  │                  │  │               │ │
│  │ │    slides     │ │  │                  │  │               │ │
│  │ │ Mar 10       │ │  │                  │  │               │ │
│  │ └───────────────┘ │  │                  │  │               │ │
│  │                   │  │                  │  │               │ │
│  │ + Add task        │  │ + Add task       │  │ + Add task    │ │
│  └───────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Details:**
- Cards have `--bg-surface`, `--shadow-sm`, `--border-default`. Hover: `--shadow-md`.
- Priority dots in top-left of card. Due date and first label below title.
- Drag: card lifts (larger shadow), semi-transparent placeholder left behind.
- Drop: smooth animation to new position, optimistic update.
- Column header: title (editable on double-click), task count badge, optional WIP limit.
- Columns scroll independently if content overflows.
- Horizontal scroll for the board if many columns.

### 5.8 Task Detail Panel (SlideOver)

480px wide, slides from right. Shadow on left edge. Escape or click backdrop to close.

```
┌──────────────────────────────────────┐
│  [← Back]                    [🗑 Del] │
│                                       │
│  ○ Submit ethics amendment            │  ← Large checkbox + editable title (--text-lg)
│                                       │
│  Project    [PhD ▾]                   │  ← Dropdown selector
│  Priority   ●●●●○                    │  ← Clickable priority dots
│  Due date   [Mar 3, 2026  📅]        │  ← Date picker
│  Labels     [ethics] [admin] [+]     │  ← Badge chips, + to add
│  Estimate   [60 min]                 │  ← Input field
│                                       │
│  ── Description ──────────────────── │
│  ┌─────────────────────────────────┐ │
│  │ Ethics amendment submission —   │ │  ← Textarea, auto-save on blur
│  │ from meeting notes              │ │
│  └─────────────────────────────────┘ │
│                                       │
│  Created Mar 1 · Updated 2h ago      │  ← --text-tertiary, --text-xs
└──────────────────────────────────────┘
```

**All edits auto-save on blur/change.** Debounced 500ms for text fields, immediate for toggles/selects. No save button.

### 5.9 AI Extraction Panel

Dedicated route `/extract`. This is the signature feature — it should feel polished and slightly special. Uses `--ai-accent` as the theme colour for this panel.

```
┌──────────────────────────────────────────────────────────────┐
│  ✨ AI Task Extraction                                       │
│                                                              │
│  [💬 Chat] [📋 Paste]              [🔒 Confidential: Off]    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ I had a meeting with my supervisor today. We agreed  │   │  ← Textarea with generous padding
│  │ I need to revise chapter 3 by next Friday and she    │   │
│  │ wants me to present at the lab meeting on March 10.  │   │
│  │ Oh and I need to book a room for that.               │   │
│  └──────────────────────────────────────────────────────┘   │
│                              [Extract Tasks  ⌘↵] ──●        │  ← --ai-accent button, keyboard hint
│                                                              │
│  ── Extracted 3 tasks ─────────────────────────────────────  │
│                                                              │
│  ☑ ┌──────────────────────────────────────────────────────┐ │
│    │ ●●●●○  Revise chapter 3                              │ │  ← Proposal card, fades in with stagger
│    │ PhD · Mar 7 · 3h · writing                     [edit]│ │
│    └──────────────────────────────────────────────────────┘ │
│                                                              │
│  ☑ ┌──────────────────────────────────────────────────────┐ │
│    │ ●●●○○  Prepare lab meeting presentation              │ │
│    │ PhD · Mar 10 · 2h · presentation               [edit]│ │
│    └──────────────────────────────────────────────────────┘ │
│                                                              │
│  ☑ ┌──────────────────────────────────────────────────────┐ │
│    │ ●●○○○  Book room for lab meeting                     │ │
│    │ Admin · Mar 8 · 10m · booking                  [edit]│ │
│    └──────────────────────────────────────────────────────┘ │
│                                                              │
│  [✓ Approve All (3)]                     [✗ Reject Selected] │  ← Approve All is --ai-accent, prominent
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Details:**
- Proposals stream in one by one via SSE with a `fly` transition (slide up + fade, 50ms stagger).
- While extracting: show a subtle pulsing indicator on the "Extract Tasks" button.
- After approval: brief success animation (cards shrink away), toast with "3 tasks created" + link to view them.
- Edit mode: card expands inline to show editable fields (project dropdown, priority, due date, etc.).
- Confidential toggle: when on, show a visible `--ai-accent` banner "🔒 Processing locally via Ollama".

### 5.10 Loading & Empty States

**Loading:** Use skeleton screens that match the shape of actual content.
- Task list loading: 5 skeleton rows (grey pulsing rectangles for checkbox, title, date).
- Kanban loading: 3 skeleton columns with 2-3 skeleton cards each.
- Detail panel loading: skeleton blocks for title, fields, description.

**Empty states:** Friendly, not just "No tasks found."
- Empty project: "No tasks yet. Add one above or extract from notes."
- Empty extraction: "Paste meeting notes, an email, or just describe what you need to do."
- No search results: "No tasks match your search. Try different terms."

### 5.11 Responsive Behaviour

- **Desktop (>1024px):** Sidebar 240px, main content fills remaining width, detail panel is a 480px slide-over.
- **Tablet (768–1024px):** Sidebar collapses to 64px (icons only), expands on hover. Detail panel overlays full width.
- **Mobile (<768px):** Sidebar hidden (hamburger toggle). Full-width content. Detail panel is full-screen. Kanban scrolls horizontally.

---

## 6. Vikunja API Reference

Key Vikunja REST API endpoints the backend proxy layer needs to call. Full docs available at `{VIKUNJA_URL}/api/v1/docs`.

Auth: All requests include header `Authorization: Bearer {VIKUNJA_API_TOKEN}`.

**Critical: Vikunja uses PUT for creation and POST for updates.** This is the opposite of typical REST convention and applies to all endpoints below.

### 6.1 Tasks

```
GET    /api/v1/tasks/all?page=1&per_page=50&s=search&sort_by=due_date&order_by=asc&filter=done%20%3D%20false
GET    /api/v1/tasks/{id}
POST   /api/v1/tasks/{id}                    # Update task
DELETE /api/v1/tasks/{id}
PUT    /api/v1/projects/{projectId}/tasks     # Create task in project
```

**Task label operations:**
```
GET    /api/v1/tasks/{id}/labels             # List labels on task
PUT    /api/v1/tasks/{id}/labels             # Add label: body {"label_id": 1}
DELETE /api/v1/tasks/{id}/labels/{labelId}   # Remove label from task
```

**Important Vikunja API quirks:**
- Task `position` is a float stored per-view in `task_positions` table. To reorder, calculate midpoint between neighbours.
- `bucket_id` determines kanban column but is **view-dependent** — a task can be in different buckets in different views.
- The `filter` query param uses Vikunja's own filter expression syntax (e.g. `done = false && priority >= 3`).
- Pagination info is returned in response headers: `x-pagination-total-pages` and `x-pagination-result-count`.
- Date fields use ISO 8601 format: `2026-03-07T00:00:00Z`.
- Search uses the `s` query parameter, not `search`.

### 6.2 Projects

```
GET    /api/v1/projects?page=1&per_page=50&is_archived=false
GET    /api/v1/projects/{id}
PUT    /api/v1/projects                       # Create
POST   /api/v1/projects/{id}                  # Update
DELETE /api/v1/projects/{id}
```

### 6.3 Project Views

Each project has one or more views (list, kanban, table, gantt). **Buckets belong to views, not projects.**

```
GET    /api/v1/projects/{id}/views
PUT    /api/v1/projects/{id}/views            # Create view
POST   /api/v1/projects/{id}/views/{viewId}   # Update view
DELETE /api/v1/projects/{id}/views/{viewId}
```

**View kinds:** 0=list, 1=gantt, 2=table, 3=kanban

### 6.4 Buckets (Kanban Columns — scoped to a View)

**BREAKING CHANGE from older Vikunja:** Buckets are now accessed through project views, not directly through projects. The old `/projects/{id}/buckets` endpoint only returns bucket metadata — to get tasks in buckets, you must go through views.

```
GET    /api/v1/projects/{id}/views/{viewId}/buckets
PUT    /api/v1/projects/{id}/views/{viewId}/buckets              # Create bucket
POST   /api/v1/projects/{id}/views/{viewId}/buckets/{bucketId}   # Update bucket
DELETE /api/v1/projects/{id}/views/{viewId}/buckets/{bucketId}
```

**Moving tasks between buckets:**
```
POST   /api/v1/projects/{id}/views/{viewId}/buckets/tasks
Body:  {"task_id": 123, "bucket_id": 456, "position": 1234.5}
```

**Kanban task retrieval:** To get tasks grouped by bucket, query tasks with `bucket_id` in the filter or use the view's task collection endpoint. The frontend should query the view's buckets, then for each bucket query its tasks.

### 6.5 Labels

```
GET    /api/v1/labels?page=1&per_page=50&s=search
GET    /api/v1/labels/{id}
PUT    /api/v1/labels                         # Create
PUT    /api/v1/labels/{id}                    # Update (note: PUT for update too)
DELETE /api/v1/labels/{id}
```

**Note:** Label update uses PUT (not POST like other updates). This is an inconsistency in Vikunja's API.

---

## 7. Project Structure

```
cognito/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # Pydantic Settings
│   │   ├── database.py             # SQLite setup (aiosqlite)
│   │   ├── auth/                   # Reused from existing codebase
│   │   │   ├── oauth.py            # Google OAuth flow
│   │   │   ├── jwt.py              # JWT create/decode
│   │   │   └── dependencies.py     # FastAPI JWT cookie dependency
│   │   ├── routers/
│   │   │   ├── auth.py             # /api/auth/*
│   │   │   ├── ingest.py           # /api/ingest (SSE streaming)
│   │   │   ├── chat.py             # /api/chat
│   │   │   ├── proposals.py        # /api/proposals/*
│   │   │   ├── tasks.py            # /api/tasks/* (Vikunja proxy)
│   │   │   ├── projects.py         # /api/projects/* (Vikunja proxy, includes views + buckets)
│   │   │   ├── labels.py           # /api/labels/* (Vikunja proxy)
│   │   │   └── schedule.py         # /api/schedule/* (Phase 3)
│   │   ├── services/
│   │   │   ├── llm.py              # Gemini / Ollama router
│   │   │   ├── extractor.py        # Tool-calling extraction pipeline
│   │   │   ├── vikunja.py          # Vikunja REST API client (expanded)
│   │   │   └── gcal.py             # Google Calendar (Phase 3)
│   │   └── models/
│   │       ├── proposal.py         # TaskProposal model
│   │       └── config.py           # AgentConfig model
│   ├── tests/
│   │   ├── test_extractor.py
│   │   ├── test_vikunja.py
│   │   └── test_proposals.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +layout.svelte      # App shell: sidebar + main area
│   │   │   ├── +page.svelte        # Default: all tasks list view
│   │   │   ├── project/
│   │   │   │   └── [id]/
│   │   │   │       ├── +page.svelte     # Project task list
│   │   │   │       └── kanban/
│   │   │   │           └── +page.svelte # Project kanban view
│   │   │   └── extract/
│   │   │       └── +page.svelte    # AI extraction page
│   │   ├── lib/
│   │   │   ├── api.ts              # Backend API client (fetch wrapper + SSE)
│   │   │   ├── stores.ts           # Svelte stores: tasks, projects, proposals
│   │   │   └── types.ts            # TypeScript interfaces for all data models
│   │   └── components/
│   │       ├── Sidebar.svelte
│   │       ├── TaskList.svelte
│   │       ├── TaskRow.svelte
│   │       ├── TaskDetail.svelte   # Slide-over detail panel
│   │       ├── KanbanBoard.svelte
│   │       ├── KanbanColumn.svelte
│   │       ├── KanbanCard.svelte
│   │       ├── InputPanel.svelte   # AI extraction input
│   │       ├── ProposalCard.svelte
│   │       ├── ProposalQueue.svelte
│   │       ├── FilterBar.svelte
│   │       ├── PriorityStars.svelte
│   │       ├── LabelChip.svelte
│   │       └── DatePicker.svelte
│   ├── package.json
│   └── svelte.config.js
└── README.md
```

---

## 8. Docker Compose

```yaml
services:
  vikunja:
    image: vikunja/vikunja:latest
    ports:
      - "3456:3456"
    volumes:
      - ./vikunja-data:/app/vikunja
    environment:
      - VIKUNJA_SERVICE_JWTSECRET=${VIKUNJA_JWT_SECRET}
      - VIKUNJA_SERVICE_FRONTENDURL=http://localhost:3456
    restart: unless-stopped

  agent-backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - VIKUNJA_URL=http://vikunja:3456
      - VIKUNJA_API_TOKEN=${VIKUNJA_API_TOKEN}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OLLAMA_URL=http://host.docker.internal:11434
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - FRONTEND_URL=${FRONTEND_URL}
      - DATABASE_URL=sqlite:///app/data/agent.db
      - JWT_SECRET=${JWT_SECRET}
      - ALLOWED_EMAIL=${ALLOWED_EMAIL}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - vikunja
    restart: unless-stopped

  agent-frontend:
    build:
      context: ./frontend
      target: production
    ports:
      - "5173:80"
    environment:
      - PUBLIC_API_URL=${BACKEND_URL}/api
    depends_on:
      - agent-backend
    restart: unless-stopped
```

**Note:** Vikunja no longer needs `FRONTENDURL` pointing to a public address since users don't access its UI. It only needs to be reachable from the backend container.

---

## 9. Implementation Plan

### Phase 0: Design Foundation (Day 1 of Weekend 1)

**Goal:** Establish the design system so every component built afterwards is automatically cohesive.

1. Set up SvelteKit project with Tailwind (or plain CSS variables).
2. Define all design tokens (colours, typography, spacing, shadows, transitions) in CSS custom properties.
3. Import IBM Plex Sans + IBM Plex Mono fonts.
4. Build primitive components in `components/ui/`: Button, Input, Textarea, Checkbox, Toast, SlideOver, Skeleton, Badge, PriorityIndicator, DateDisplay, Kbd.
5. Build the app shell: sidebar layout + main content area + header bar.
6. Implement the Toast notification system (Svelte store + ToastContainer component).
7. Implement keyboard shortcut handler at the layout level.

**Milestone:** An app shell you can navigate, with all primitive components ready. No data yet, but the UI *looks* right.

### Phase 1: Backend + Data Views (Rest of Weekend 1)

**Goal:** Paste notes → proposals stream in → approve → tasks appear in Vikunja and are visible in the list view.

1. FastAPI skeleton: port auth from archive, set up SQLite schema.
2. Expanded Vikunja API client (`vikunja.py`): task CRUD, project listing, views listing, bucket listing, label CRUD.
3. Generic proxy layer for Vikunja endpoints (inject API token, forward, return).
4. Tool-calling extraction pipeline: `extractor.py` with `lookup_projects` / `resolve_project`.
5. `/api/ingest` endpoint with SSE streaming.
6. `/api/proposals` endpoints (CRUD + approve/reject).
7. Connect frontend: project list in sidebar (from API), task list view (read-only first).
8. Implement optimistic update helper function.
9. Task quick-add (create task from list view).
10. Task done toggle with optimistic update.
11. AI extraction page: text input, SSE streaming proposals, approve/reject.

**Milestone:** Working end-to-end flow. Can view tasks, create them, toggle done, and extract from text.

### Phase 2: Rich Task Management (Weekend 2)

**Goal:** The task views are polished enough to be your daily driver.

1. Task detail panel (SlideOver): all fields editable, auto-save on blur with debounce.
2. Filter bar using Vikunja filter syntax (`done = false`, `priority >= 3`, date math).
3. Sort options: due date, priority, created, position.
4. Completed tasks section (collapsed by default, show/hide toggle).
5. Kanban board: fetch project views → find kanban view (view_kind=3) → fetch buckets → fetch tasks per bucket.
6. Kanban drag-and-drop (`svelte-dnd-action`): POST to bucket/tasks endpoint on drop.
7. Kanban column management (create, rename, reorder, WIP limits).
8. Search functionality (/ shortcut, search input in header).
9. Skeleton loading states for list, kanban, and detail panel.
10. Empty states with helpful messages.
11. Keyboard shortcuts: j/k navigation, x to toggle, n for new, e for edit, 1-5 for priority.

**Milestone:** Comfortable daily driver for all task management. Never need Vikunja's UI.

### Phase 3: AI Polish + Chat (Weekend 3)

1. Confidential toggle + Ollama routing (Qwen 3.x with tool calling).
2. Chat endpoint for conversational extraction.
3. Chat mode in extraction panel (vs paste mode).
4. Streaming UX polish: staggered proposal card animations, pulsing extraction indicator.
5. Proposal editing (inline expand to edit fields before approving).
6. Bulk approve/reject + approve-all with success animation.
7. Proposal history (recently approved/rejected).
8. `check_existing_tasks` tool for duplicate detection.
9. Error handling: retry logic, error toasts, graceful degradation.
10. Prompt tuning based on real usage.

**Milestone:** AI extraction is reliable, feels polished, and handles all input types.

### Phase 4: Calendar + Mobile (Weekend 4)

1. Google Calendar OAuth (add `calendar` scope).
2. Fetch existing events, detect conflicts.
3. LLM schedule suggestion.
4. Schedule view in frontend.
5. Create/delete Google Calendar events.
6. Mobile-responsive layout (sidebar collapse, full-screen overlays).
7. Touch-friendly kanban (long-press to drag on mobile).

### Future

- Dark mode (token swap — minimal code change).
- Chrome extension for quick capture from any page.
- Email forwarding webhook for auto-ingestion.
- Recurring task management in the UI.
- Notification/reminder UI.

---

## 10. Environment Variables

```bash
# Vikunja
VIKUNJA_URL=http://localhost:3456
VIKUNJA_API_TOKEN=your-vikunja-api-token
VIKUNJA_JWT_SECRET=your-vikunja-jwt-secret

# LLM
GEMINI_API_KEY=your-gemini-key
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
GEMINI_MODEL=gemini-2.0-flash

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
ALLOWED_EMAIL=your.email@gmail.com

# Google Calendar (Phase 3)
GCAL_CALENDAR_ID=primary

# Database
DATABASE_URL=sqlite:///./data/agent.db

# Server
JWT_SECRET=your-jwt-secret
FRONTEND_URL=https://cognito.yourserver.com
BACKEND_URL=https://cognito.yourserver.com
```

---

## 11. Reused Code from Archive

| File | Changes needed |
|------|---------------|
| `auth/oauth.py` | None — pure Google OAuth |
| `auth/jwt.py` | None — generic JWT |
| `auth/dependencies.py` | Update import paths |
| `config.py` | Swap DuckDB → Vikunja/SQLite fields, add VIKUNJA_* vars |
| `services/llm.py` | Add tool-calling support to GeminiClient and OllamaClient |

---

## 12. Coding Agent Notes

This section contains guidance for a coding agent implementing this spec.

### General Approach

- **Reference Vikunja's API docs** at `{VIKUNJA_URL}/api/v1/docs` for exact request/response shapes.
- **Vikunja uses PUT for creation and POST for updates.** Exception: label update is PUT. Double-check every endpoint.
- **The backend proxy can be generic.** Instead of writing individual proxy functions for every Vikunja endpoint, consider a generic proxy that forwards requests to Vikunja with the API token injected. Only customise where you need to transform data (e.g., the proposal-to-task creation flow). This significantly reduces boilerplate.
- **Frontend state management:** Use Svelte stores. Keep a `tasks` store, `projects` store, `views` store, and `proposals` store. Invalidate/refetch after mutations.
- **Kanban needs the views model.** The frontend must: (1) fetch project views, (2) find the kanban view (view_kind=3), (3) fetch its buckets, (4) for each bucket, fetch its tasks. Consider caching the view ID per project.

### Vikunja API Gotchas

- **PUT creates, POST updates** (opposite of typical REST). Exception: label update uses PUT.
- **Buckets belong to views, not projects.** A project has views, each view can have buckets. The kanban view's buckets are at `/projects/{id}/views/{viewId}/buckets`. Moving tasks between buckets requires POSTing to `/projects/{id}/views/{viewId}/buckets/tasks`.
- **To show a kanban board:** First GET the project's views, find the one with `view_kind=3` (kanban), then GET its buckets, then GET tasks filtered by each bucket.
- Task `position` is a float stored per-view. When reordering, calculate midpoint between neighbours.
- `bucket_id` on a task is **view-dependent**. A task can be in different buckets in different views.
- Task search uses the `s` query parameter (not `search`).
- Filtering uses the `filter` query param with Vikunja's expression syntax: `done = false && priority >= 3`. Not individual params.
- Labels are added to tasks via PUT `/tasks/{id}/labels` with body `{"label_id": X}`.
- Vikunja returns paginated results with headers `x-pagination-total-pages` and `x-pagination-result-count`.
- Date fields use ISO 8601 with timezone: `2026-03-07T00:00:00Z`.
- Projects can be nested (via `parent_project_id`). The sidebar should handle hierarchy.
- Projects have an `identifier` field (e.g. "PHD") used to build human-readable task IDs like "PHD-12".

### Frontend Implementation Priority

Build in this order — design system first, then features:

**Phase 0 — Design foundation (build before any features):**
1. Design tokens (CSS custom properties for all colours, typography, spacing)
2. Primitive components: Button, Input, Textarea, Checkbox, Toast, SlideOver, Skeleton, Badge, PriorityIndicator, DateDisplay
3. App shell (sidebar + layout + header)
4. Toast notification system
5. Keyboard shortcut handler
6. Optimistic update helper function

**Phase 1 — Core views:**
1. Project list in sidebar (from API)
2. Task list view (read-only) → displays tasks from backend
3. Task quick-add → create tasks from the list view
4. Task done toggle with optimistic update → checkbox updates backend instantly
5. AI extraction page → the core differentiating feature

**Phase 2 — Rich interactions:**
1. Task detail panel (SlideOver) → click to edit all fields, auto-save
2. Filter/sort bar → refine the list view using Vikunja filter syntax
3. Kanban board → fetch views, find kanban view, render buckets + cards
4. Drag-and-drop → `svelte-dnd-action`, optimistic position updates
5. Skeleton loading states + empty states
6. Keyboard navigation (j/k/x/n/e/1-5)

### Libraries to Use

- `svelte-dnd-action` — drag and drop for kanban
- `date-fns` — date formatting and manipulation
- Standard `fetch` + `EventSource` for API calls and SSE
- Tailwind CSS recommended (define theme in config using the design tokens)
- IBM Plex Sans + IBM Plex Mono via Google Fonts or self-hosted
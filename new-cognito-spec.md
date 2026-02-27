# Task Agent — Technical Specification

**An AI integration layer for Vikunja project management**

Version 1.1 — February 2026

---

## 1. Overview

A lightweight service that sits between unstructured inputs (meeting notes, emails, ideas) and a self-hosted Vikunja instance. An LLM extracts structured task proposals using tool-assisted extraction, the user approves/rejects/edits them, and approved tasks are pushed to Vikunja. Optional Google Calendar time-blocking is planned for Phase 3.

### 1.1 Core Workflow

```
Unstructured Input (notes, emails, ideas)
        ↓
   LLM extracts structured task proposals
   (with tool calls: lookup_projects, resolve_project)
        ↓
   User reviews: approve / reject / edit
        ↓
   Vikunja API ← approved tasks created
        ↓
   Google Calendar ← optional time-block scheduling (Phase 3)
```

### 1.2 Design Principles

- **Vikunja is the PM tool.** The agent never duplicates PM functionality — no kanban, no project views, no task editing. Vikunja handles all of that.
- **The agent is a thin input layer.** It does one thing: turn messy inputs into clean tasks. Once a task is in Vikunja, the agent is done.
- **Confidential data stays local.** Any input flagged as confidential routes through Ollama (self-hosted LLM), never to external APIs.
- **Minimal UI.** A single page with a text input, a proposal queue, and a scheduling button.
- **Tool-assisted extraction.** The LLM uses function calling to look up real project data during extraction — no hallucinated project names.

### 1.3 Technical Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Backend | FastAPI (Python) | Already familiar, async, good for LLM streaming |
| Frontend | SvelteKit (single page) | Already familiar from journal project |
| PM Backend | Vikunja (Docker) | Self-hosted, good API, handles all PM features |
| LLM (general) | Gemini API | Best structured output + native function calling |
| LLM (confidential) | Ollama (localhost) | PHI-safe, no data leaves your server — requires tool-calling support (Qwen 3.x) |
| Calendar | Google Calendar API | Direct event creation for time-blocking (Phase 3) |
| Auth | Google OAuth 2.0 (on backend) | Reused from existing codebase — battle-tested |
| Database | SQLite | Only stores proposal queue — lightweight enough |

---

## 2. System Architecture

### 2.1 Component Diagram

```
┌──────────────────────────────────────────────────┐
│                  AGENT FRONTEND                    │
│         (SvelteKit — single page, static build)    │
│                                                    │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────┐  │
│  │ Input Panel  │ │ Proposal     │ │ Schedule   │  │
│  │ (text/paste) │ │ Queue        │ │ View       │  │
│  └─────────────┘ └──────────────┘ └────────────┘  │
└──────────────────────┬───────────────────────────┘
                       │ HTTPS (JWT cookie on all requests)
                       ▼
┌──────────────────────────────────────────────────┐
│              AGENT BACKEND (FastAPI)               │
│                                                    │
│  /api/auth  → Google OAuth + JWT (reused code)     │
│  /api/ingest    → LLM extraction → proposal queue  │
│  /api/proposals → CRUD + approve/reject            │
│  /api/schedule  → Google Calendar (Phase 3)        │
│  /api/projects  → proxy to Vikunja project list    │
│                                                    │
│  Services:                                         │
│    llm.py        → Gemini / Ollama router          │
│    extractor.py  → Prompt + tool-calling pipeline  │
│    vikunja.py    → Vikunja REST API client         │
│    gcal.py       → Google Calendar client (Phase 3)│
└──────────────────────┬───────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────────┐
    │ Vikunja  │ │ Ollama   │ │ Google       │
    │ API      │ │ (local)  │ │ Calendar API │
    │ :3456    │ │ :11434   │ │ (Phase 3)    │
    └──────────┘ └──────────┘ └──────────────┘
```

### 2.2 What Lives Where

| Concern | Handled by |
|---------|-----------|
| Task management (kanban, lists, projects, labels, due dates) | Vikunja |
| Task extraction from unstructured text | Agent backend (LLM + tool calling) |
| Proposal review & approval | Agent frontend |
| Time-block scheduling | Agent backend → Google Calendar (Phase 3) |
| Authentication | FastAPI backend — Google OAuth, JWT cookies (reused code) |
| Confidential data routing | Agent backend (LLM router) |

---

## 3. Data Models

The agent has a very small data footprint. The only persistent state is the proposal queue and some config. Everything else lives in Vikunja or Google Calendar.

### 3.1 TaskProposal

The core (and nearly only) data model.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| source_id | UUID | Groups proposals from the same ingestion batch |
| title | TEXT | Task title (extracted by LLM) |
| description | TEXT | Task details/context (nullable) |
| project_name | TEXT | Suggested Vikunja project name |
| project_id | INTEGER | Vikunja project ID (resolved via tool call during extraction, nullable) |
| priority | INTEGER | 1 (low) to 5 (urgent) — maps to Vikunja priority |
| due_date | DATE | Suggested deadline (nullable) |
| estimated_minutes | INTEGER | Time estimate for scheduling (nullable) |
| labels | JSON | Array of label strings (nullable) |
| source_type | TEXT | 'notes', 'email', 'idea', 'manual' |
| source_text | TEXT | The original input text this was extracted from |
| confidential | BOOLEAN | If true, was processed by Ollama |
| status | TEXT | 'pending', 'approved', 'rejected', 'created' |
| vikunja_task_id | INTEGER | Vikunja task ID after creation (nullable) |
| gcal_event_id | TEXT | Google Calendar event ID if scheduled (nullable) |
| created_at | TIMESTAMP | Extraction time |
| reviewed_at | TIMESTAMP | Approval/rejection time (nullable) |

### 3.2 VikunjaProject (cached)

Local cache of Vikunja projects so the LLM can map tasks to existing projects without calling Vikunja on every extraction.

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Vikunja project ID |
| title | TEXT | Project name |
| description | TEXT | Project description |
| last_synced_at | TIMESTAMP | When this was fetched from Vikunja |

### 3.3 AgentConfig (singleton)

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Always 1 |
| default_project_id | INTEGER | Fallback Vikunja project for unmatched names |
| ollama_model | TEXT | Model name for confidential tasks — must support tool calling (e.g. 'qwen3:4b') |
| gemini_model | TEXT | Gemini model name |
| gcal_calendar_id | TEXT | Target Google Calendar ID (Phase 3) |

### 3.4 SQLite Schema

```sql
CREATE TABLE task_proposals (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,        -- groups proposals from same ingestion
    title TEXT NOT NULL,
    description TEXT,
    project_name TEXT,
    project_id INTEGER,
    priority INTEGER DEFAULT 3,
    due_date DATE,
    estimated_minutes INTEGER,
    labels TEXT DEFAULT '[]',  -- JSON array
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

## 4. API Specification

### 4.1 Authentication

Reused from the existing codebase with minimal changes.

#### GET /api/auth/login

Redirects to Google's OAuth consent screen.

**Response:** 302 Redirect to accounts.google.com

#### GET /api/auth/callback

OAuth callback. Exchanges code for tokens, validates email against allowlist, sets JWT as HttpOnly cookie.

**Response:** 302 Redirect to frontend

#### GET /api/auth/me

Returns current user info.

**Response:** `{ "email": "string", "name": "string", "picture": "url" }`

#### POST /api/auth/logout

Clears the JWT cookie.

**Response:** `{ "success": true }`

### 4.2 Ingestion

#### POST /api/ingest

Accept unstructured text, extract tasks via LLM (with tool calls), return proposals. Supports SSE streaming so proposals appear as they're extracted rather than all at once.

**Request:**
```json
{
    "text": "Meeting notes from today:\n- Need to submit ethics amendment by March 3\n- John will send the dataset, I need to preprocess it\n- Follow up with supervisor about conference paper deadline",
    "source_type": "notes",
    "confidential": false,
    "project_hint": "PhD"
}
```

**Response (standard):**
```json
{
    "source_id": "uuid",
    "proposals": [
        {
            "id": "uuid",
            "source_id": "uuid",
            "title": "Submit ethics amendment",
            "description": "Ethics amendment submission — from meeting notes",
            "project_name": "PhD",
            "project_id": 1,
            "priority": 4,
            "due_date": "2026-03-03",
            "estimated_minutes": 60,
            "labels": ["admin", "ethics"],
            "source_type": "notes",
            "confidential": false,
            "status": "pending"
        }
    ]
}
```

**SSE streaming (optional, via `Accept: text/event-stream`):**
Each proposal is emitted as a separate event as extraction completes, allowing the UI to render proposals in real time.

### 4.3 Proposals

#### GET /api/proposals?status=pending

Fetch proposals filtered by status.

**Response:**
```json
{
    "proposals": [TaskProposal],
    "count": 3
}
```

#### PUT /api/proposals/{id}

Edit a proposal before approving (change title, project, due date, etc).

**Request:** Partial TaskProposal fields.

**Response:** Updated TaskProposal.

#### POST /api/proposals/{id}/approve

Approve a proposal → creates task in Vikunja.

**Response:**
```json
{
    "success": true,
    "vikunja_task_id": 142,
    "vikunja_url": "https://vikunja.yourserver.com/tasks/142"
}
```

#### POST /api/proposals/{id}/reject

Reject a proposal. Marks as rejected, no further action.

#### POST /api/proposals/bulk

Bulk approve/reject by explicit ID list.

**Request:**
```json
{
    "approve": ["uuid1", "uuid2"],
    "reject": ["uuid3"]
}
```

**Response:**
```json
{
    "approved": 2,
    "rejected": 1,
    "errors": []
}
```

#### POST /api/proposals/approve-all

Approve all currently pending proposals in one click.

**Response:**
```json
{
    "approved": 5,
    "errors": []
}
```

### 4.4 Scheduling (Phase 3)

#### POST /api/schedule

Take a list of Vikunja tasks and create Google Calendar time blocks.

**Request:**
```json
{
    "date": "2026-02-27",
    "task_ids": [142, 143, 145],
    "auto_arrange": true,
    "work_hours": {"start": "09:00", "end": "17:00"},
    "break_minutes": 15
}
```

If `auto_arrange` is true, the LLM suggests an order and time allocation based on priorities, estimated durations, and any existing calendar events.

**Response:**
```json
{
    "events": [
        {
            "task_title": "Submit ethics amendment",
            "start": "2026-02-27T09:00:00",
            "end": "2026-02-27T10:00:00",
            "gcal_event_id": "abc123"
        }
    ]
}
```

#### GET /api/schedule/suggest?date=2026-02-27

Ask the LLM to suggest a schedule for a given day. Returns a draft — user confirms before events are created.

**Response:** Same as above but with `"draft": true`.

### 4.5 Projects

#### GET /api/projects

Proxy to Vikunja — returns cached project list. Refreshes cache if stale (>1 hour).

**Response:**
```json
{
    "projects": [
        {"id": 1, "title": "PhD", "description": "Main research"},
        {"id": 2, "title": "Admin", "description": "University admin tasks"},
        {"id": 3, "title": "Teaching", "description": "TA responsibilities"}
    ]
}
```

#### POST /api/projects/sync

Force a refresh of the Vikunja project cache.

**Response:** `{ "synced": 5 }`

### 4.6 Chat (Conversational Ingest)

#### POST /api/chat

For a conversational flow — the user describes what they need to do in natural language, and the agent extracts tasks interactively.

**Request:**
```json
{
    "message": "I had a meeting with my supervisor today. We agreed I need to revise chapter 3 by next Friday and she wants me to present at the lab meeting on March 10th. Oh and I need to book a room for that.",
    "conversation_id": "uuid or null"
}
```

**Response:**
```json
{
    "reply": "I've extracted 3 tasks from that. The chapter revision sounds like the big one — do you want me to break that into smaller sub-tasks, or keep it as one item?",
    "proposals": [TaskProposal, TaskProposal, TaskProposal],
    "conversation_id": "uuid"
}
```

The chat endpoint is a convenience wrapper — it still produces proposals that go through the same approval flow.

---

## 5. LLM Integration

### 5.1 Router Logic

```python
def get_llm_client(confidential: bool):
    if confidential:
        return OllamaClient(model=config.ollama_model)  # must support tool calling
    else:
        return GeminiClient(model=config.gemini_model)
```

Reuses the existing `LLMClient` abstract base class pattern from the previous codebase, with extensions for tool/function calling.

### 5.2 Tool-Assisted Extraction

Instead of asking the LLM to guess project names and IDs, we expose tools the LLM can call during extraction. This prevents hallucinated project names and produces accurate `project_id` values directly.

**Tools exposed to the LLM:**

```python
tools = [
    {
        "name": "lookup_projects",
        "description": "Returns the list of available Vikunja projects.",
        "parameters": {}
    },
    {
        "name": "resolve_project",
        "description": "Maps a project name to its Vikunja project ID. Returns the default project if no match found.",
        "parameters": {
            "name": {"type": "string", "description": "Project name to look up"}
        }
    },
    {
        "name": "check_existing_tasks",
        "description": "Fuzzy-searches recent Vikunja tasks by title to detect duplicates.",
        "parameters": {
            "title": {"type": "string", "description": "Task title to check for duplicates"}
        }
    }
]
```

**Extraction flow:**
1. LLM receives the unstructured input text + tool definitions
2. LLM calls `lookup_projects()` to get real project names
3. For each extracted task, LLM calls `resolve_project(name)` to get the actual `project_id`
4. Optionally calls `check_existing_tasks(title)` if a task sounds like it might be a duplicate
5. LLM returns final structured JSON array of proposals

**Project resolution rules:**
- If the LLM suggests a project name that exists in Vikunja → resolve to its ID
- If no match → route to `default_project_id` from `AgentConfig`
- If no `default_project_id` configured → `project_id = null`, user must assign in proposal edit

**Tool calling model requirements:**
- Gemini: native function calling support — no changes needed
- Ollama: model must support tool use. Use Qwen 3.x (e.g. `qwen3:4b`) which has strong tool-calling support. Avoid smaller models that produce unreliable JSON.

### 5.3 Task Extraction Prompt

```
You are a task extraction assistant for a PhD student. Given unstructured
text (meeting notes, emails, or freeform ideas), extract actionable tasks.

Use the lookup_projects tool to get available projects before extracting tasks.
Use resolve_project for each task to get the correct project ID.
Use check_existing_tasks if a task might already exist in Vikunja.

For each task, return JSON:
{
    "title": "Short, actionable task title (start with verb)",
    "description": "Brief context or details (1-2 sentences max, nullable)",
    "project_name": "Best matching project from lookup_projects result, or 'Uncategorised'",
    "project_id": <resolved via resolve_project tool>,
    "priority": 1-5 (1=low, 3=normal, 5=urgent),
    "due_date": "YYYY-MM-DD or null if not mentioned/inferrable",
    "estimated_minutes": estimated time to complete (integer, null if unclear),
    "labels": ["relevant", "labels"]
}

Rules:
- Only extract genuinely actionable items for the USER (not tasks for others)
- Start titles with a verb: "Write...", "Email...", "Review...", "Submit..."
- If a deadline is mentioned, include it. If "next Friday" etc., calculate the date
- Don't over-extract: "John will send the dataset" is NOT a task for the user,
  but "Preprocess dataset once John sends it" IS
- If something is vague, make your best guess and note uncertainty in description
- Keep it concise — these are task titles, not essays
- Today's date is {today}

Return a JSON array of tasks. If no actionable tasks found, return [].
```

### 5.4 Schedule Suggestion Prompt (Phase 3)

```
You are a daily schedule planner for a PhD student.

Tasks to schedule today:
{tasks_with_priorities_and_estimates}

Existing calendar events today:
{existing_events}

Work hours: {start} to {end}
Break between tasks: {break_minutes} minutes

Create a realistic schedule. Rules:
- Don't overlap with existing events
- Put high-priority and cognitively demanding tasks earlier in the day
- Group related tasks together
- Include breaks
- If there's not enough time for all tasks, flag which ones to defer
- Be realistic about estimates (pad 20% for context switching)

Return JSON array of scheduled blocks.
```

### 5.5 Error Handling Strategy

External LLM calls are unreliable. The following strategy applies:

| Failure | Behaviour |
|---------|-----------|
| Gemini API rate limit / quota | Fall back to Ollama if available; otherwise surface error with retry button |
| Gemini API error (5xx) | Retry up to 3 times with exponential backoff (1s, 2s, 4s) |
| Ollama unreachable | Clear error message: "Local model unavailable — switch to non-confidential mode or check Ollama" |
| Ollama returns malformed JSON | Retry with explicit JSON reminder in prompt; give up after 2 attempts |
| Tool call fails (Vikunja down during extraction) | Use cached project list; fall back to `project_id = null` |

---

## 6. External Integrations

### 6.1 Vikunja API

Vikunja exposes a REST API (documented at `/api/v1/docs` on your instance).

Key endpoints used:

| Action | Vikunja Endpoint |
|--------|-----------------|
| List projects | GET /api/v1/projects |
| Create task | PUT /api/v1/projects/{id}/tasks |
| Add label to task | POST /api/v1/tasks/{id}/labels |
| Get task details | GET /api/v1/tasks/{id} |
| List tasks (for scheduling) | GET /api/v1/tasks/all |

Authentication: API token (generated in Vikunja settings). Store as `VIKUNJA_API_TOKEN` env var.

**Resilience:** If Vikunja is down when approving a task, the proposal status remains `approved` (not `created`) and a background retry is attempted. The user sees a toast notification and can manually retry from the proposal history.

### 6.2 Google Calendar API (Phase 3)

Used for time-block scheduling only.

| Action | Google Calendar Endpoint |
|--------|------------------------|
| List events (check conflicts) | GET /calendars/{id}/events |
| Create event (time block) | POST /calendars/{id}/events |
| Delete event | DELETE /calendars/{id}/events/{eventId} |

Authentication: OAuth 2.0, reuse existing Google OAuth with additional `calendar` scope.

### 6.3 Gmail Integration (Future — Phase 4)

Not in MVP. When added:
- Option A: Gmail API (OAuth) — poll for new emails, extract tasks
- Option B: Email forwarding — set up a forwarding rule for specific emails to a webhook endpoint
- Option B is simpler and avoids Gmail API complexity. Recommended.

---

## 7. Frontend Design

### 7.1 Single Page Layout

The entire agent UI is one page with three panels/sections:

```
┌─────────────────────────────────────────────────────────────────┐
│  Task Agent                          [Vikunja ↗]  [Settings ⚙]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ Input ─────────────────────────────────────────────────────┐ │
│  │ [💬 Chat] [📋 Paste Notes] [📧 Email]     [🔒 Confidential] │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │ I had a meeting with my supervisor today. We agreed  │   │ │
│  │  │ I need to revise chapter 3 by next Friday...         │   │ │
│  │  └──────────────────────────────────────────────────────┘   │ │
│  │                                         [Extract Tasks →]   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Proposals (3 pending) ─────────────────────────────────────┐ │
│  │                                                              │ │
│  │  ☑ Revise chapter 3                              ★★★★☆     │ │
│  │    📁 PhD  ·  📅 Mar 7  ·  ⏱ 3h  ·  draft, writing        │ │
│  │    [edit]                                                    │ │
│  │                                                              │ │
│  │  ☑ Prepare lab meeting presentation              ★★★☆☆     │ │
│  │    📁 PhD  ·  📅 Mar 10  ·  ⏱ 2h  ·  presentation         │ │
│  │    [edit]                                                    │ │
│  │                                                              │ │
│  │  ☑ Book room for lab meeting                     ★★☆☆☆     │ │
│  │    📁 Admin  ·  📅 Mar 8  ·  ⏱ 10m  ·  booking            │ │
│  │    [edit]                                                    │ │
│  │                                                              │ │
│  │  [✓ Approve All]  [✓ Approve Selected]  [✗ Reject Selected] │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ Schedule Tomorrow ─────────────────────────────────────────┐ │
│  │  (Phase 3 — Google Calendar integration)                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Interaction Details

**Input Panel:**
- Toggle between chat mode (conversational) and paste mode (bulk text)
- Confidential toggle routes to Ollama — show a visible indicator (🔒) so you always know
- Source type selector helps the LLM adjust extraction strategy
- "Extract Tasks" sends to `/api/ingest` or `/api/chat`
- Proposals stream in via SSE — each proposal card appears as it's extracted

**Proposal Queue:**
- Proposals appear as they stream in after extraction
- Each proposal is a card with: title, project, due date, time estimate, priority (editable stars), labels
- Click "edit" to inline-edit any field before approving
- **"Approve All"** button: approve all pending in one click
- Checkbox select for partial bulk approve/reject
- Approved proposals disappear from queue (move to 'created' status)
- A small "history" link shows recently approved/rejected proposals

**Schedule Panel (Phase 3):**
- Appears when there are tasks with due dates approaching
- "Suggest schedule" calls the LLM with current tasks + existing calendar events
- Shows proposed time blocks — user can remove or adjust
- "Push to Google Calendar" creates the events

### 7.3 Responsive Behaviour

Desktop: all three panels visible, stacked vertically.
Mobile: collapsible accordion — input open by default, proposals and schedule collapsed with badge counts.

---

## 8. Project Structure

```
task-agent/
├── docker-compose.yml          # Agent + Vikunja + Ollama
├── .env.example                # Environment variable template
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app
│   │   ├── config.py           # Pydantic Settings (adapted from existing)
│   │   ├── database.py         # SQLite setup (aiosqlite)
│   │   ├── auth/               # Reused from existing codebase
│   │   │   ├── oauth.py        # Google OAuth flow (httpx-based)
│   │   │   ├── jwt.py          # JWT create/decode (python-jose)
│   │   │   └── dependencies.py # FastAPI JWT cookie dependency
│   │   ├── routers/
│   │   │   ├── auth.py         # GET /api/auth/* (reused)
│   │   │   ├── ingest.py       # POST /api/ingest (SSE streaming)
│   │   │   ├── chat.py         # POST /api/chat
│   │   │   ├── proposals.py    # Proposal CRUD + approve/reject/approve-all
│   │   │   ├── schedule.py     # Calendar scheduling (Phase 3)
│   │   │   └── projects.py     # Vikunja project proxy + sync
│   │   ├── services/
│   │   │   ├── llm.py          # GeminiClient / OllamaClient / LLMRouter (adapted)
│   │   │   ├── extractor.py    # Tool-calling extraction pipeline
│   │   │   ├── vikunja.py      # Vikunja REST API client
│   │   │   └── gcal.py         # Google Calendar client (Phase 3)
│   │   └── models/
│   │       ├── proposal.py     # TaskProposal model
│   │       └── config.py       # AgentConfig model
│   ├── tests/
│   │   ├── test_extractor.py   # LLM extraction with mocked tool calls
│   │   ├── test_vikunja.py     # Vikunja client tests
│   │   └── test_proposals.py   # Proposal lifecycle tests
│   └── pyproject.toml          # uv-managed dependencies
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +layout.svelte
│   │   │   └── +page.svelte    # The single page
│   │   ├── lib/
│   │   │   ├── api.ts          # Agent API client (with SSE support)
│   │   │   └── stores.ts       # Proposals, schedule state
│   │   └── components/
│   │       ├── InputPanel.svelte
│   │       ├── ProposalCard.svelte
│   │       ├── ProposalQueue.svelte
│   │       └── ScheduleView.svelte  # Phase 3
│   ├── package.json
│   └── svelte.config.js
└── README.md
```

> **Note:** `auth/` is ported directly from the `archive/thought-journal` branch with minimal changes (swap DuckDB references → SQLite, adjust environment variable names).

---

## 9. Docker Compose

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
      - VIKUNJA_SERVICE_FRONTENDURL=https://vikunja.yourserver.com
    restart: unless-stopped

  agent-backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data          # SQLite database
    environment:
      - VIKUNJA_URL=http://vikunja:3456
      - VIKUNJA_API_TOKEN=${VIKUNJA_API_TOKEN}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OLLAMA_URL=http://host.docker.internal:11434   # see note below
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - FRONTEND_URL=https://agent.yourserver.com
      - DATABASE_URL=sqlite:///app/data/agent.db
      - JWT_SECRET=${JWT_SECRET}
      - ALLOWED_EMAIL=${ALLOWED_EMAIL}
    extra_hosts:
      - "host.docker.internal:host-gateway"   # Linux fix: makes host accessible
    depends_on:
      - vikunja
    restart: unless-stopped

  agent-frontend:
    build:
      context: ./frontend
      target: production    # multi-stage build: node build → nginx serve
    ports:
      - "5173:80"           # nginx on 80 internally
    environment:
      - PUBLIC_API_URL=https://agent.yourserver.com/api
    depends_on:
      - agent-backend
    restart: unless-stopped
```

> **Linux networking note:** `host.docker.internal` is a macOS/Windows Docker Desktop convenience. On Linux (your server), `extra_hosts: ["host.docker.internal:host-gateway"]` makes it work identically. This allows the containerised backend to reach Ollama running on the host.

---

## 10. Implementation Plan

### Phase 1: Foundation (Weekend 1)

1. Archive old codebase → `archive/thought-journal` branch
2. Set up Vikunja via Docker, create projects, generate API token
3. FastAPI skeleton: port `auth/` from archive, new config + SQLite schema
4. Vikunja API client — list projects, create task — test with hardcoded data
5. Tool-calling extraction pipeline: `extractor.py` with `lookup_projects` / `resolve_project` tools
6. `/api/ingest` endpoint — text in, proposals out (with SSE streaming)
7. Minimal SvelteKit frontend: text area + extract button + proposal cards

**Milestone:** Paste meeting notes → proposals stream in with real project IDs → approve → tasks appear in Vikunja.

### Phase 2: Polish the Core (Weekend 2)

1. Proposal editing (inline edit title, project, due date, priority)
2. Bulk approve/reject + approve-all
3. Confidential toggle + Ollama routing (Qwen 3.x with tool calling)
4. Chat endpoint for conversational input
5. Proposal history (view recently approved/rejected)
6. Error handling: retry logic, user-facing error messages
7. Improve extraction prompt based on real usage

**Milestone:** Comfortable daily-driver for task capture from any input.

### Phase 3: Calendar Integration (Weekend 3)

1. Google Calendar OAuth setup (add `calendar` scope to existing OAuth)
2. Fetch existing events for a given day
3. LLM schedule suggestion (tasks + existing events → proposed time blocks)
4. Schedule view in frontend
5. Create Google Calendar events from approved schedule
6. Delete/reschedule support

**Milestone:** Can plan tomorrow's time blocks from the agent UI.

### Phase 4: Quality of Life (Ongoing)

- Email forwarding webhook (auto-ingest forwarded emails)
- Mobile-responsive layout
- Keyboard shortcuts for fast approval
- `check_existing_tasks` tool refinement (smarter deduplication)
- Prompt tuning based on what you find yourself editing most

---

## 11. Environment Variables

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

# Google OAuth (reused from existing setup)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
ALLOWED_EMAIL=your.email@gmail.com

# Google Calendar (Phase 3)
GCAL_CALENDAR_ID=primary

# Database
DATABASE_URL=sqlite:///./data/agent.db

# Server
JWT_SECRET=your-jwt-secret
FRONTEND_URL=https://agent.yourserver.com
BACKEND_URL=https://agent.yourserver.com
```

---

## 12. Reused Code from Archive

These modules will be ported from the `archive/thought-journal` branch with minimal modifications:

| File | What changes |
|------|-------------|
| `backend/app/auth/oauth.py` | Nothing — pure Google OAuth, no journal-specific logic |
| `backend/app/auth/jwt.py` | Nothing — generic JWT create/decode |
| `backend/app/auth/dependencies.py` | Minor: update import paths |
| `backend/app/config.py` | Swap DuckDB fields → Vikunja/SQLite fields; add `VIKUNJA_*` vars |
| `backend/app/services/llm.py` | Add tool-calling support to `GeminiClient` and `OllamaClient` |

---

## 13. Key Differences from Journal Spec

For reference, here's what was deliberately cut or simplified:

| Journal Spec | Task Agent | Why |
|-------------|-----------|-----|
| DuckDB | SQLite | Only storing a proposal queue — SQLite is simpler |
| Offline-first with IndexedDB + sync engine | Online only | Single user, always on your server, no sync conflicts |
| Code-based diff + conflict resolution | Not needed | No version conflicts in a proposal queue |
| Self-modifying code system | Not needed | Use a TODO.md in the repo |
| Push notifications with VAPID | Not needed (Phase 4 at most) | You'll check the agent when you have notes to process |
| 8 data models | 3 data models | Vikunja handles the complexity |
| 7-9 weeks estimated | 3 weekends | Standing on Vikunja's shoulders |
| Service worker + background sync | Static SvelteKit build + nginx | No offline requirement |
| Entry version history | Not needed | Proposals are ephemeral — approve and forget |
| Plain JSON extraction | Tool-assisted extraction | Real project IDs, duplicate detection, no hallucinated names |
# Cognito -- Data Models

## Vikunja Data Models (API)

These models live entirely in Vikunja. Cognito reads and writes them via the REST API. The backend never stores tasks locally.

### Task

Returned by `GET /api/v1/tasks/{id}`. Key fields:

| Field           | Type     | Notes                                      |
|-----------------|----------|--------------------------------------------|
| `id`            | integer  | Vikunja-assigned                           |
| `title`         | string   | Required                                   |
| `description`   | string   | Markdown                                   |
| `done`          | boolean  |                                            |
| `priority`      | integer  | 0 (unset) to 5 (urgent)                   |
| `due_date`      | string   | ISO 8601 datetime                          |
| `start_date`    | string   | ISO 8601 datetime                          |
| `end_date`      | string   | ISO 8601 datetime                          |
| `project_id`    | integer  |                                            |
| `labels`        | array    | Array of Label objects                     |
| `position`      | float    | View-dependent ordering                    |
| `related_tasks` | object   | Keyed by relation kind (e.g. `"subtask"`)  |

### Project

| Field         | Type    | Notes                            |
|---------------|---------|----------------------------------|
| `id`          | integer |                                  |
| `title`       | string  |                                  |
| `description` | string  |                                  |
| `hex_color`   | string  | No `#` prefix (e.g. `"A1A09A"`) |
| `is_archived` | boolean |                                  |
| `position`    | float   |                                  |

### Label

| Field       | Type    | Notes                            |
|-------------|---------|----------------------------------|
| `id`        | integer |                                  |
| `title`     | string  |                                  |
| `hex_color` | string  | No `#` prefix in Vikunja storage |

### ProjectView

| Field                       | Type    | Notes                               |
|-----------------------------|---------|---------------------------------------|
| `id`                        | integer |                                       |
| `title`                     | string  |                                       |
| `view_kind`                 | string  | `"list"`, `"kanban"`, `"gantt"`, etc. |
| `bucket_configuration_mode` | string  | `"manual"` for user-managed buckets   |

### Bucket

Buckets belong to views, not projects.

| Field      | Type    | Notes                        |
|------------|---------|------------------------------|
| `id`       | integer |                              |
| `title`    | string  |                              |
| `limit`    | integer | WIP limit (0 = unlimited)    |
| `position` | float   |                              |

**Vikunja API convention:** PUT creates, POST updates. This applies to all resources.

---

## SQLite Schema (Cognito Agent Database)

All tables are defined in `backend/app/database.py` via `init_schema()`. The database file lives at `./data/agent.db`. All timestamps use `strftime('%Y-%m-%dT%H:%M:%S', 'now')`.

### users

Authentication records from Google OAuth.

```sql
CREATE TABLE IF NOT EXISTS users (
    id                       TEXT PRIMARY KEY,
    email                    TEXT UNIQUE NOT NULL,
    name                     TEXT,
    picture                  TEXT,
    refresh_token            TEXT,
    refresh_token_expires_at TEXT,
    created_at               TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    last_login_at            TEXT
)
```

### task_proposals

Proposal queue for LLM-extracted tasks. Status transitions: `pending` -> `approved` | `rejected`.

```sql
CREATE TABLE IF NOT EXISTS task_proposals (
    id                TEXT PRIMARY KEY,
    source_id         TEXT NOT NULL,
    title             TEXT NOT NULL,
    description       TEXT,
    project_name      TEXT,
    project_id        INTEGER,
    priority          INTEGER DEFAULT 3,
    due_date          TEXT,
    estimated_minutes INTEGER,
    labels            TEXT DEFAULT '[]',
    source_type       TEXT NOT NULL DEFAULT 'notes',
    source_text       TEXT NOT NULL DEFAULT '',
    confidential      INTEGER DEFAULT 0,
    status            TEXT DEFAULT 'pending',
    vikunja_task_id   INTEGER,
    gcal_event_id     TEXT,
    created_at        TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    reviewed_at       TEXT
)
```

### vikunja_projects

Local cache of Vikunja projects. Synced periodically.

```sql
CREATE TABLE IF NOT EXISTS vikunja_projects (
    id             INTEGER PRIMARY KEY,
    title          TEXT NOT NULL,
    description    TEXT,
    last_synced_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
)
```

**Migrations** (added to existing databases):

```sql
ALTER TABLE vikunja_projects ADD COLUMN hex_color TEXT DEFAULT '';
ALTER TABLE vikunja_projects ADD COLUMN is_archived INTEGER DEFAULT 0;
ALTER TABLE vikunja_projects ADD COLUMN position REAL DEFAULT 0;
```

### agent_config

Singleton row (always `id = 1`). Seeded automatically on startup.

```sql
CREATE TABLE IF NOT EXISTS agent_config (
    id                      INTEGER PRIMARY KEY,
    default_project_id      INTEGER,
    ollama_model            TEXT DEFAULT 'qwen3:4b',
    gemini_model            TEXT DEFAULT 'gemini-3.1-flash-lite-preview',
    gcal_calendar_id        TEXT,
    system_prompt_override  TEXT
)
```

**Migrations:**

```sql
ALTER TABLE agent_config ADD COLUMN system_prompt_override TEXT;
ALTER TABLE agent_config ADD COLUMN base_prompt_override TEXT;
```

### label_descriptions

Rich descriptions for Vikunja labels, used by the auto-tagger to understand label semantics.

```sql
CREATE TABLE IF NOT EXISTS label_descriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label_id    INTEGER NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
)
```

### conversations

Chat sessions between the user and the AI agent.

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
)
```

### conversation_messages

Individual messages within a conversation. Stores both user and assistant messages, with optional proposal and action payloads.

```sql
CREATE TABLE IF NOT EXISTS conversation_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    proposals_json  TEXT,
    actions_json    TEXT,
    created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
)
```

**Migration:**

```sql
ALTER TABLE conversation_messages ADD COLUMN actions_json TEXT;
```

### task_revisions

Tracks before/after state for AI-initiated task modifications, enabling undo.

```sql
CREATE TABLE IF NOT EXISTS task_revisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         INTEGER NOT NULL,
    action_type     TEXT NOT NULL,
    source          TEXT NOT NULL,
    before_state    TEXT,
    after_state     TEXT,
    changes         TEXT,
    conversation_id TEXT,
    proposal_id     TEXT,
    undone          INTEGER DEFAULT 0,
    undone_at       TEXT,
    created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
)
```

### task_calendar_links

Maps Vikunja tasks to Google Calendar events.

```sql
CREATE TABLE IF NOT EXISTS task_calendar_links (
    task_id        INTEGER PRIMARY KEY,
    gcal_event_id  TEXT NOT NULL,
    calendar_id    TEXT NOT NULL DEFAULT 'primary',
    created_at     TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
)
```

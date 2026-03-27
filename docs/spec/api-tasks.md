# Tasks API — `/api/tasks`

Proxies task CRUD to Vikunja. The backend injects the Vikunja API token server-side. All endpoints require authentication.

## Endpoints

| Method | Endpoint | Description | Vikunja Method |
|--------|----------|-------------|----------------|
| GET | `/api/tasks` | List tasks (filtered, paginated) | GET /api/v1/tasks |
| GET | `/api/tasks/{id}` | Get single task | GET /api/v1/tasks/{id} |
| PUT | `/api/tasks` | Create task | PUT /api/v1/projects/{id}/tasks |
| POST | `/api/tasks/{id}` | Update task | POST /api/v1/tasks/{id} |
| DELETE | `/api/tasks/{id}` | Delete task | DELETE /api/v1/tasks/{id} |
| POST | `/api/tasks/{id}/position` | Update position in a view | POST /api/v1/tasks/{id}/position |
| PUT | `/api/tasks/{id}/labels` | Add label to task | PUT /api/v1/tasks/{id}/labels |
| DELETE | `/api/tasks/{id}/labels/{lid}` | Remove label from task | DELETE /api/v1/tasks/{id}/labels/{lid} |
| POST | `/api/tasks/auto-tag` | Auto-tag tasks via LLM | (composite) |
| GET | `/api/tasks/{id}/attachments` | List attachments | GET /api/v1/tasks/{id}/attachments |
| PUT | `/api/tasks/{id}/attachments` | Upload attachment (max 20MB) | PUT /api/v1/tasks/{id}/attachments |
| GET | `/api/tasks/{id}/attachments/{aid}` | Download attachment | GET /api/v1/tasks/{id}/attachments/{aid} |
| DELETE | `/api/tasks/{id}/attachments/{aid}` | Delete attachment | DELETE /api/v1/tasks/{id}/attachments/{aid} |
| GET | `/api/tasks/{id}/subtasks` | List subtasks | (via related_tasks) |
| PUT | `/api/tasks/{id}/subtasks` | Create subtask | PUT + relation |
| POST | `/api/tasks/{id}/subtasks/{sid}` | Update subtask | POST /api/v1/tasks/{sid} |
| DELETE | `/api/tasks/{id}/subtasks/{sid}` | Delete subtask + relation | DELETE task + relation |

## Query Params: `GET /api/tasks`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `project_id` | int | null | Filter by project |
| `view_id` | int | null | Filter by view |
| `s` | string | null | Search term (Vikunja uses `s`, not `search`) |
| `filter` | string | null | Vikunja filter expression (see below) |
| `sort_by` | string | null | Field to sort by |
| `order_by` | string | null | `asc` or `desc` |
| `page` | int | 1 | Page number (min 1) |
| `per_page` | int | 50 | Items per page (1-500) |

## Vikunja Filter Syntax

The `filter` param accepts expressions like:
- `done = false` — open tasks only
- `priority >= 3` — high priority
- `done = false && priority >= 3` — combinable with `&&` / `||`

## Create Task: `PUT /api/tasks`

```json
{
  "project_id": 1,
  "title": "Fix the bug",
  "description": "Optional details",
  "priority": 3,
  "due_date": "2026-04-01",
  "start_date": "2026-03-27T09:00:00Z",
  "end_date": "2026-03-27T17:00:00Z",
  "labels": ["bug", "urgent"]
}
```

## Auto-Tag: `POST /api/tasks/auto-tag`

```json
{ "task_ids": [1, 2, 3], "model": "gemini-flash" }
```

Both fields optional. If `task_ids` is omitted, tags all unlabeled open tasks. Requires label descriptions to be configured in Settings > Labels.

## Gotchas

- **Subtasks are filtered out** of `GET /api/tasks` responses (tasks with a `parenttask` relation are excluded).
- **Subtask counts** are enriched onto parent tasks as `subtask_total` and `subtask_done`.
- **Date normalization:** Update converts bare dates (`2026-04-01`) to RFC3339 (`2026-04-01T00:00:00Z`).
- **Revisions:** All create/update/delete/auto-tag operations record revisions in SQLite for history tracking.
- **Position:** `position` is a float. Reorder by computing the midpoint between neighbours. Requires `project_view_id`.

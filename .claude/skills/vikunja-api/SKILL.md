---
name: vikunja-api
description: >
  Vikunja REST API reference (v2.1.0). Use when working with the Vikunja client,
  proxy routes, task/project/label CRUD, kanban/bucket operations, API debugging,
  or test mocking for Vikunja endpoints.
triggers:
  - vikunja
  - task CRUD
  - proxy route
  - kanban bucket
  - label API
  - project API
  - 502 bad gateway
  - task update
  - task create
  - due_date
  - API error
---

# Vikunja API Reference

Vikunja v2.1.0 | Base path: `/api/v1` | Auth: `Authorization: Bearer <token>`

Source: `docs/vikunja-swagger.json` (OpenAPI 2.0 / Swagger)

**Important:** Do not assume Vikunja is running on localhost. It may be behind a
reverse proxy, on a Docker network, or hosted publicly. When running scripts or
debugging, always ask the user where their Vikunja instance and backend are hosted.

---

## 1. The Cardinal Rule: HTTP Method Inversion

Vikunja uses **inverted HTTP methods** compared to standard REST conventions:

| Operation | Standard REST | Vikunja   |
|-----------|--------------|-----------|
| Create    | POST         | **PUT**   |
| Update    | PUT/PATCH    | **POST**  |
| Read      | GET          | GET       |
| Delete    | DELETE       | DELETE    |

**Label exception:** `PUT /labels` creates, `PUT /labels/{id}` updates (PUT for both).

### Wrong vs Right

```python
# WRONG: POST to create a task
await client.post(f"/projects/{pid}/tasks", json=payload)

# RIGHT: PUT to create a task
await client.put(f"/projects/{pid}/tasks", json=payload)
```

```python
# WRONG: PUT to update a task
await client.put(f"/tasks/{tid}", json=payload)

# RIGHT: POST to update a task
await client.post(f"/tasks/{tid}", json=payload)
```

```python
# WRONG: POST to create a label
await client.post("/labels", json=payload)

# RIGHT: PUT to create a label (and PUT /labels/{id} to update)
await client.put("/labels", json=payload)
```

---

## 2. Common Mistakes

### Search param is `s`, not `search`
```python
# WRONG
params = {"search": "groceries"}
# RIGHT
params = {"s": "groceries"}
```

### Buckets go through views, not projects directly
```python
# WRONG
GET /projects/{id}/buckets
# RIGHT
GET /projects/{id}/views/{view}/buckets
```

### Listing project tasks requires a view
```python
# WRONG — PUT /projects/{id}/tasks is for CREATION only
GET /projects/{id}/tasks
# RIGHT — list tasks through a view
GET /projects/{id}/views/{view}/tasks
```

### Use single `filter` param with expression syntax
```python
# WRONG — individual filter params
params = {"done": "false", "priority_gte": 3}
# RIGHT — single filter expression
params = {"filter": "done = false && priority >= 3"}
```

### Pagination is in response HEADERS, not body
```python
# WRONG
total = response.json()["total_pages"]
# RIGHT
total = int(response.headers["x-pagination-total-pages"])
count = int(response.headers["x-pagination-result-count"])
```

### Global task list is `/tasks`, not `/tasks/all`
```python
# WRONG (undocumented, may work but not in spec)
GET /tasks/all
# RIGHT (per spec)
GET /tasks
```

---

## 3. Endpoint Quick Reference

### Tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List all tasks (paginated, filterable) |
| GET | `/tasks/{id}` | Get one task |
| POST | `/tasks/{id}` | Update a task |
| DELETE | `/tasks/{id}` | Delete a task |
| PUT | `/projects/{id}/tasks` | Create a task in project |
| POST | `/tasks/bulk` | Bulk update tasks |
| POST | `/tasks/{id}/position` | Update task position |
| POST | `/tasks/{id}/read` | Mark task as read |

### Projects

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects` | List all projects |
| GET | `/projects/{id}` | Get one project |
| PUT | `/projects` | Create a project |
| POST | `/projects/{id}` | Update a project |
| DELETE | `/projects/{id}` | Delete a project |

### Labels

| Method | Path | Description |
|--------|------|-------------|
| GET | `/labels` | List all labels |
| GET | `/labels/{id}` | Get one label |
| PUT | `/labels` | Create a label |
| PUT | `/labels/{id}` | Update a label |
| DELETE | `/labels/{id}` | Delete a label |

### Task Labels

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks/{task}/labels` | Get labels on a task |
| PUT | `/tasks/{task}/labels` | Add a label to a task |
| DELETE | `/tasks/{task}/labels/{label}` | Remove a label from a task |
| POST | `/tasks/{taskID}/labels/bulk` | Replace all labels on a task |

### Views

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{project}/views` | List project views |
| GET | `/projects/{project}/views/{id}` | Get one view |
| PUT | `/projects/{project}/views` | Create a view |
| POST | `/projects/{project}/views/{id}` | Update a view |
| DELETE | `/projects/{project}/views/{id}` | Delete a view |

### Buckets (Kanban)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{id}/views/{view}/buckets` | List buckets |
| PUT | `/projects/{id}/views/{view}/buckets` | Create a bucket |
| POST | `/projects/{id}/views/{view}/buckets/{bucket}` | Update a bucket |
| DELETE | `/projects/{id}/views/{view}/buckets/{bucket}` | Delete a bucket |
| POST | `/projects/{project}/views/{view}/buckets/{bucket}/tasks` | Move task to bucket |

### View Tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{id}/views/{view}/tasks` | List tasks in a view (kanban views return buckets with tasks) |

### Other

| Method | Path | Description |
|--------|------|-------------|
| GET/PUT/DELETE | `/tasks/{taskID}/assignees[/{userID}]` | Assignee management |
| POST | `/tasks/{taskID}/assignees/bulk` | Bulk assign |
| GET/PUT/POST/DELETE | `/tasks/{taskID}/comments[/{commentID}]` | Comments |
| GET/PUT/DELETE | `/tasks/{id}/attachments[/{attachmentID}]` | Attachments |
| PUT/DELETE | `/tasks/{taskID}/relations[/{relationKind}/{otherTaskID}]` | Relations |

---

## 4. Kanban Workflow

1. **Get views:** `GET /projects/{id}/views` -> find one where `view_kind = "kanban"`
2. **Get buckets:** `GET /projects/{id}/views/{view}/buckets` -> returns `[Bucket]`
3. **Get tasks:** `GET /projects/{id}/views/{view}/tasks` -> for kanban views returns buckets with tasks nested
4. **Move task:** `POST /projects/{project}/views/{view}/buckets/{bucket}/tasks` with body `{"task_id": N}`
5. **Reposition:** `POST /tasks/{id}/position` with body `{"position": 1234.5, "project_view_id": N}`

---

## 5. Search & Filtering

**Search:** `?s=query` on GET `/tasks`, GET `/labels`, GET `/projects`

**Filter:** `?filter=done = false && priority >= 3`

- Comparators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `in`, `not in`
- Combinators: `&&` (AND), `||` (OR), parentheses for grouping
- Date math: `now`, `now+1d`, `now-1w`, `now+1m`
- Extra params: `filter_timezone`, `filter_include_nulls`

See [references/filter-syntax.md](references/filter-syntax.md) for full docs.

---

## 6. Pagination

**Query params:** `page` (1-indexed), `per_page`

**Response headers (not body):**
- `x-pagination-total-pages` — total available pages
- `x-pagination-result-count` — items in this response

**Permission header** (single-item endpoints):
- `x-max-permission` — `0`=Read, `1`=Write, `2`=Admin

---

## 7. Data Models (Creation Payloads)

### Task (PUT /projects/{id}/tasks)
- `title` (string, required, min 1)
- `description` (string)
- `priority` (integer)
- `due_date` (string, RFC 3339: `2026-03-10T00:00:00Z`)
- `hex_color` (string, max 7)
- `percent_done` (number, 0-1)
- `start_date`, `end_date` (string, RFC 3339)
- `repeat_after` (integer, seconds)
- `repeat_mode` (0=default, 1=from-current-date, 2=monthly)
- `reminders` (array of TaskReminder)

### Project (PUT /projects)
- `title` (string, required, max 250, min 1)
- `description` (string)
- `hex_color` (string, max 7)
- `identifier` (string, max 10)
- `parent_project_id` (integer)

### Label (PUT /labels)
- `title` (string, required, max 250, min 1)
- `description` (string)
- `hex_color` (string, max 7)

### Bucket (PUT /projects/{id}/views/{view}/buckets)
- `title` (string, required, min 1)
- `limit` (integer, min 0)

See [references/data-models.md](references/data-models.md) for complete schemas.

---

## 8. Testing with Mocks

```python
import httpx
import respx

# PUT for create, POST for update
respx.put("http://vikunja:3456/api/v1/projects/1/tasks").mock(
    return_value=httpx.Response(201, json={"id": 1, "title": "Test"})
)
respx.post("http://vikunja:3456/api/v1/tasks/1").mock(
    return_value=httpx.Response(200, json={"id": 1, "title": "Updated"})
)

# Label create (PUT), label update (also PUT)
respx.put("http://vikunja:3456/api/v1/labels").mock(
    return_value=httpx.Response(201, json={"id": 1, "title": "urgent"})
)
respx.put("http://vikunja:3456/api/v1/labels/1").mock(
    return_value=httpx.Response(200, json={"id": 1, "title": "critical"})
)

# Add label to task (PUT)
respx.put("http://vikunja:3456/api/v1/tasks/1/labels").mock(
    return_value=httpx.Response(201, json={"label_id": 1})
)

# Delete (standard DELETE)
respx.delete("http://vikunja:3456/api/v1/tasks/1").mock(
    return_value=httpx.Response(200, json={"message": "Successfully deleted."})
)
```

---

## 9. Cognito Project Integration

**Architecture:** Frontend -> FastAPI proxy -> Vikunja (backend injects API token)

**Key files:**
- `backend/app/services/vikunja.py` — `VikunjaClient` with `_request()` base method
- `backend/app/routers/tasks.py` — Task CRUD proxy
- `backend/app/routers/labels.py` — Label CRUD proxy
- `backend/app/routers/projects.py` — Project list with SQLite cache (1hr TTL)

**Known deviations from spec:**
1. `vikunja.py:89` — Uses `/projects/{id}/tasks` for listing (spec only has PUT there; should use view-based endpoint)
2. `vikunja.py:91,222` — Uses `/tasks/all` (not in spec; spec has `GET /tasks`)
3. `vikunja.py:207` — `move_task_to_bucket` posts to `.../buckets/tasks` not `.../buckets/{bucket}/tasks`
4. `routers/tasks.py:66` — Wraps response in `{"tasks": [...]}` (Vikunja returns bare array)
5. `routers/labels.py:33` — Wraps response in `{"labels": [...]}` (Vikunja returns bare array)
6. `routers/projects.py:52` — Wraps response in `{"projects": [...]}` and strips most fields
7. `routers/labels.py` — Missing `PUT /{id}` (update label) proxy route
8. `routers/tasks.py` — Missing `GET /tasks/{task}/labels` (list task labels) proxy route

See [references/proxy-mapping.md](references/proxy-mapping.md) for full mapping.

---

## 10. Reference File Index

| File | When to consult |
|------|----------------|
| [references/endpoints.md](references/endpoints.md) | Full request/response schemas for any endpoint |
| [references/data-models.md](references/data-models.md) | Complete field definitions for all models |
| [references/filter-syntax.md](references/filter-syntax.md) | Building filter queries |
| [references/proxy-mapping.md](references/proxy-mapping.md) | Debugging or adding Cognito proxy routes |

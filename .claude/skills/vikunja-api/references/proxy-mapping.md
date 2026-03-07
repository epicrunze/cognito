# Cognito Proxy -> Vikunja API Mapping

How our FastAPI proxy routes map to Vikunja's REST API.

## Architecture

```
Frontend (SvelteKit)
  -> FastAPI proxy (injects Bearer token)
    -> Vikunja (http://vikunja:3456/api/v1/...)
```

- Auth injection: `services/vikunja.py:32-36` adds `Authorization: Bearer` header
- Error handling: `VikunjaError` -> HTTP 502 Bad Gateway in all routers
- Response wrapping: Our proxy wraps bare arrays in `{"tasks": [...]}`, `{"labels": [...]}`, `{"projects": [...]}`

## Route Mapping

### Tasks (`routers/tasks.py`)

| Our Method | Our Path | Vikunja Method | Vikunja Path | Status | Notes |
|------------|----------|---------------|--------------|--------|-------|
| GET | `/api/tasks` | GET | `/tasks/all` or `/projects/{id}/tasks` | Bug | Should use `GET /tasks` (not `/tasks/all`) for cross-project; should use `GET /projects/{id}/views/{view}/tasks` for per-project |
| GET | `/api/tasks/{id}` | GET | `/tasks/{id}` | Correct | |
| PUT | `/api/tasks` | PUT | `/projects/{id}/tasks` | Correct | Extracts `project_id` from body |
| POST | `/api/tasks/{id}` | POST | `/tasks/{id}` | Correct | |
| DELETE | `/api/tasks/{id}` | DELETE | `/tasks/{id}` | Correct | Returns `{"success": true}` instead of Vikunja's `{"message": "..."}` |
| PUT | `/api/tasks/{id}/labels` | PUT | `/tasks/{id}/labels` | Correct | |
| DELETE | `/api/tasks/{id}/labels/{label_id}` | DELETE | `/tasks/{id}/labels/{label_id}` | Correct | Returns `{"success": true}` |

### Labels (`routers/labels.py`)

| Our Method | Our Path | Vikunja Method | Vikunja Path | Status | Notes |
|------------|----------|---------------|--------------|--------|-------|
| GET | `/api/labels` | GET | `/labels` | Correct | Wraps in `{"labels": [...]}` |
| PUT | `/api/labels` | PUT | `/labels` | Correct | |
| DELETE | `/api/labels/{id}` | DELETE | `/labels/{id}` | Correct | Returns `{"success": true}` |
| — | — | PUT | `/labels/{id}` | Not implemented | Update label endpoint missing |
| — | — | GET | `/labels/{id}` | Not implemented | Get single label missing |

### Projects (`routers/projects.py`)

| Our Method | Our Path | Vikunja Method | Vikunja Path | Status | Notes |
|------------|----------|---------------|--------------|--------|-------|
| GET | `/api/projects` | GET | `/projects` | Correct | Returns from SQLite cache (1hr TTL), auto-refreshes. Strips to `{id, title, description}` only |
| POST | `/api/projects/sync` | GET | `/projects` | Correct | Force-refresh cache. Not a standard Vikunja endpoint — our custom sync trigger |

### Not Implemented

These Vikunja endpoints have no proxy route:

| Vikunja Method | Vikunja Path | Category |
|---------------|--------------|----------|
| PUT | `/projects` | Create project |
| POST | `/projects/{id}` | Update project |
| DELETE | `/projects/{id}` | Delete project |
| GET | `/projects/{project}/views` | List views |
| PUT/POST/DELETE | `/projects/{project}/views[/{id}]` | View CRUD |
| GET/PUT/POST/DELETE | `/projects/{id}/views/{view}/buckets[/{bucket}]` | Bucket CRUD |
| POST | `/projects/{project}/views/{view}/buckets/{bucket}/tasks` | Move task to bucket |
| POST | `/tasks/{id}/position` | Update task position |
| POST | `/tasks/bulk` | Bulk update tasks |
| POST | `/tasks/{taskID}/labels/bulk` | Bulk update task labels |
| GET | `/tasks/{task}/labels` | List task labels |
| GET/PUT/DELETE | `/tasks/{taskID}/assignees[/{userID}]` | Assignee management |
| GET/PUT/POST/DELETE | `/tasks/{taskID}/comments[/{commentID}]` | Comment management |
| GET/PUT/DELETE | `/tasks/{id}/attachments[/{attachmentID}]` | Attachment management |

## Known Deviations

1. **`vikunja.py:89`** — `list_tasks()` uses `GET /projects/{id}/tasks` for per-project listing. The spec only defines `PUT` (create) on that path. Should use `GET /projects/{id}/views/{view}/tasks`.

2. **`vikunja.py:91,222`** — Uses `GET /tasks/all` for cross-project listing. The spec defines `GET /tasks` (no `/all` suffix).

3. **`vikunja.py:207`** — `move_task_to_bucket()` posts to `/projects/{id}/views/{view}/buckets/tasks`. The spec path is `/projects/{project}/views/{view}/buckets/{bucket}/tasks` (bucket ID in path, not just body).

4. **`routers/tasks.py:66`** — `list_tasks` wraps response in `{"tasks": [...]}`. Vikunja returns a bare JSON array.

5. **`routers/labels.py:33`** — `list_labels` wraps response in `{"labels": [...]}`. Vikunja returns a bare JSON array.

6. **`routers/projects.py:52`** — Returns only `{id, title, description}` from SQLite cache, stripping Vikunja fields like `hex_color`, `identifier`, `is_archived`, `position`, `views`, etc.

7. **`routers/labels.py`** — No `PUT /api/labels/{id}` route for updating labels. The Vikunja spec has `PUT /labels/{id}` for updates.

8. **`routers/tasks.py`** — No `GET /api/tasks/{task}/labels` route for listing labels on a task.

## Project Cache

- Cache table: `vikunja_projects` in SQLite
- TTL: 1 hour (`CACHE_TTL_HOURS = 1`)
- Auto-refresh: on `GET /api/projects` if cache is stale
- Force-refresh: `POST /api/projects/sync`
- Graceful degradation: returns stale cache if Vikunja is unreachable

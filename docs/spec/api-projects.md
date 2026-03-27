# Projects API — `/api/projects`

Proxies project CRUD to Vikunja with a local SQLite cache (1-hour TTL). Also manages kanban views and buckets. All endpoints require authentication.

## Project Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List projects (from cache, auto-refreshes if stale) |
| POST | `/api/projects` | Create project |
| POST | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |
| POST | `/api/projects/sync` | Force-refresh project cache |

## View & Bucket Endpoints (Kanban)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{pid}/views` | List views for a project |
| PUT | `/api/projects/{pid}/views` | Create a view |
| GET | `/api/projects/{pid}/views/{vid}/buckets` | List buckets in a kanban view |
| PUT | `/api/projects/{pid}/views/{vid}/buckets` | Create a bucket |
| POST | `/api/projects/{pid}/views/{vid}/buckets/{bid}` | Update a bucket |
| DELETE | `/api/projects/{pid}/views/{vid}/buckets/{bid}` | Delete a bucket |
| GET | `/api/projects/{pid}/views/{vid}/tasks` | List tasks in a view (kanban: buckets with nested tasks) |
| POST | `/api/projects/{pid}/views/{vid}/buckets/{bid}/tasks` | Move task to bucket |

## Query Params: `GET /api/projects`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `include_archived` | bool | false | Include archived projects |

## Create Project: `POST /api/projects`

```json
{ "title": "My Project", "description": "", "hex_color": "#E8772E" }
```

## Update Project: `POST /api/projects/{id}`

```json
{ "title": "New Name", "hex_color": "#A1A09A", "is_archived": false, "position": 1.5 }
```

All fields optional (only non-null fields are sent to Vikunja).

## Move Task to Bucket: `POST /api/projects/{pid}/views/{vid}/buckets/{bid}/tasks`

```json
{ "task_id": 42 }
```

## Gotchas

- **Cache:** Project list is served from SQLite cache. Auto-refreshes when older than 1 hour. Use `POST /api/projects/sync` to force refresh.
- **`hex_color` normalization:** Colors are stored with `#` prefix in the cache (Vikunja stores them without). The API normalizes both directions.
- **Subtask filtering:** `GET .../views/{vid}/tasks` filters out subtasks (tasks with `parenttask` relations) from kanban bucket results.
- **Buckets belong to views, not projects.** You must first find the kanban view (`view_kind=3`) before working with buckets.
- **Stale cache fallback:** If Vikunja is unreachable during cache refresh, stale cached data is returned rather than an error.

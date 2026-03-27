# Vikunja API Reference

Backend proxy: `backend/app/services/vikunja.py`. The frontend never calls Vikunja directly.

## Authentication

All requests use `Authorization: Bearer {VIKUNJA_API_TOKEN}` injected server-side.

## Method Convention (Critical)

**PUT creates, POST updates** for ALL resources. This is the opposite of standard REST.

| Operation | Method |
|-----------|--------|
| Create task/project/label | `PUT` |
| Update task/project/label | `POST` |
| Delete | `DELETE` |
| Read | `GET` |

## Color Format

`hex_color` has **no `#` prefix**. Vikunja stores `A1A09A`, not `#A1A09A`. Always strip `#` before sending.

## Tasks

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/projects/{id}/tasks` | `GET` | List tasks in project |
| `/api/v1/projects/{id}/tasks` | `PUT` | Create task in project |
| `/api/v1/tasks/{id}` | `POST` | Update task |
| `/api/v1/tasks/{id}` | `DELETE` | Delete task |
| `/api/v1/tasks/{id}` | `GET` | Get single task |
| `/api/v1/tasks/all` | `GET` | List all tasks (with filters) |

## Projects

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/projects` | `GET` | List all projects |
| `/api/v1/projects` | `PUT` | Create project |
| `/api/v1/projects/{id}` | `POST` | Update project |
| `/api/v1/projects/{id}` | `DELETE` | Delete project |

## Views & Buckets (Kanban)

Buckets belong to **views**, not projects.

1. `GET /api/v1/projects/{id}/views` -- get views for project
2. Find view with `view_kind: 3` (kanban)
3. `GET /api/v1/projects/{id}/views/{viewId}/buckets` -- get buckets
4. Tasks are accessed per-bucket

## Labels

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/labels` | `GET` | List all labels |
| `/api/v1/labels` | `PUT` | Create label |
| `/api/v1/labels/{id}` | `POST` | Update label |
| `/api/v1/labels/{id}` | `DELETE` | Delete label |
| `/api/v1/tasks/{id}/labels` | `PUT` | Add label to task |
| `/api/v1/tasks/{id}/labels/{labelId}` | `DELETE` | Remove label from task |

## Query Parameters

| Feature | Parameter | Notes |
|---------|-----------|-------|
| **Filter** | `filter` | Expression syntax: `done = false && priority >= 3` |
| **Search** | `s` | Not `search` |
| **Pagination** | Response headers | Page info in HTTP headers |
| **Sort** | `sort_by`, `order_by` | Field name + `asc`/`desc` |
| **Dates** | ISO 8601 | All date fields |

## Position

Task position is a **float**, view-dependent. Reorder by computing midpoint between neighboring tasks' positions.

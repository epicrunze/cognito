# Vikunja Data Models

Complete field definitions from `docs/vikunja-swagger.json` `#/definitions/*`.

All dates are RFC 3339 format: `2026-03-10T00:00:00Z`

---

## Task (`models.Task`)

| Field | Type | Constraints | Writable | Description |
|-------|------|-------------|----------|-------------|
| `id` | integer | | read-only | Unique numeric ID |
| `title` | string | min: 1 | create/update | The task text |
| `description` | string | | create/update | Task description |
| `done` | boolean | | create/update | Whether the task is done |
| `done_at` | string | | read-only | When marked done (system-controlled) |
| `due_date` | string | RFC 3339 | create/update | When the task is due |
| `start_date` | string | RFC 3339 | create/update | When the task starts |
| `end_date` | string | RFC 3339 | create/update | When the task ends |
| `priority` | integer | | create/update | Task priority (sortable) |
| `percent_done` | number | 0-1 | create/update | Completion percentage |
| `hex_color` | string | max: 7 | create/update | Color in hex format |
| `repeat_after` | integer | seconds | create/update | Repeat interval in seconds |
| `repeat_mode` | integer | 0,1,2 | create/update | 0=default, 1=from-current-date, 2=monthly |
| `project_id` | integer | | create | Project this task belongs to |
| `bucket_id` | integer | | read-only | Bucket ID (only via view with buckets) |
| `index` | integer | | read-only | Task index within project |
| `identifier` | string | | read-only | Human-readable ID (e.g., `PROJ-42`) |
| `position` | number | float | update | Position for sorting (view-dependent) |
| `is_favorite` | boolean | | create/update | Show in Favorites project |
| `cover_image_attachment_id` | integer | | create/update | Attachment ID for cover image |
| `created` | string | RFC 3339 | read-only | Creation timestamp |
| `updated` | string | RFC 3339 | read-only | Last update timestamp |
| `created_by` | User | | read-only | User who created the task |
| `labels` | [Label] | | read-only | Associated labels (use label endpoints to modify) |
| `assignees` | [User] | | read-only | Assigned users (use assignee endpoints) |
| `attachments` | [TaskAttachment] | | read-only | Attached files (use attachment endpoints) |
| `reminders` | [TaskReminder] | | create/update | Reminder configurations |
| `related_tasks` | RelatedTaskMap | | read-only | Related tasks by relation kind |
| `comments` | [TaskComment] | | read-only | Only with `expand=comments` |
| `comment_count` | integer | | read-only | Only with `expand=comments` |
| `buckets` | [TaskBucket] | | read-only | Only with `expand=buckets` |
| `reactions` | ReactionMap | | read-only | Reactions on this task |
| `subscription` | Subscription | | read-only | User's subscription status |
| `is_unread` | boolean | | read-only | Unread status |

### Creation payload (PUT /projects/{id}/tasks)
Required: `title`
```json
{
  "title": "Buy groceries",
  "description": "Milk, eggs, bread",
  "priority": 3,
  "due_date": "2026-03-10T00:00:00Z",
  "hex_color": "#E8772E",
  "labels": [],
  "reminders": [{"reminder": "2026-03-10T09:00:00Z"}]
}
```

### Update payload (POST /tasks/{id})
Only include fields to change:
```json
{
  "done": true,
  "priority": 5
}
```

---

## Project (`models.Project`)

| Field | Type | Constraints | Writable | Description |
|-------|------|-------------|----------|-------------|
| `id` | integer | | read-only | Unique numeric ID |
| `title` | string | min: 1, max: 250 | create/update | Project title |
| `description` | string | | create/update | Project description |
| `hex_color` | string | max: 7 | create/update | Color in hex |
| `identifier` | string | max: 10 | create/update | Short identifier for task IDs |
| `parent_project_id` | integer | | create/update | Parent project for nesting |
| `is_archived` | boolean | | create/update | Archive status |
| `is_favorite` | boolean | | create/update | Favorite status |
| `position` | number | float | update | Sort position |
| `created` | string | RFC 3339 | read-only | Creation timestamp |
| `updated` | string | RFC 3339 | read-only | Last update timestamp |
| `owner` | User | | read-only | Creator |
| `views` | [ProjectView] | | read-only | Associated views |
| `background_blur_hash` | string | | read-only | Blur hash for background preview |
| `background_information` | object | | read-only | Background provider metadata |

### Creation payload (PUT /projects)
```json
{
  "title": "My Project",
  "description": "Project description",
  "hex_color": "#E8772E",
  "identifier": "MYPROJ"
}
```

---

## Label (`models.Label`)

| Field | Type | Constraints | Writable | Description |
|-------|------|-------------|----------|-------------|
| `id` | integer | | read-only | Unique numeric ID |
| `title` | string | min: 1, max: 250 | create/update | Label title |
| `description` | string | | create/update | Label description |
| `hex_color` | string | max: 7 | create/update | Color in hex |
| `created` | string | RFC 3339 | read-only | Creation timestamp |
| `updated` | string | RFC 3339 | read-only | Last update timestamp |
| `created_by` | User | | read-only | Creator |

### Creation payload (PUT /labels)
```json
{
  "title": "urgent",
  "hex_color": "#ff0000",
  "description": "High urgency items"
}
```

### Update payload (PUT /labels/{id})
```json
{
  "title": "critical",
  "hex_color": "#cc0000"
}
```

---

## ProjectView (`models.ProjectView`)

| Field | Type | Constraints | Writable | Description |
|-------|------|-------------|----------|-------------|
| `id` | integer | | read-only | Unique numeric ID |
| `title` | string | | create/update | View title |
| `view_kind` | string | enum: `list`, `gantt`, `table`, `kanban` | create/update | View type |
| `project_id` | integer | | read-only | Parent project |
| `position` | number | float | update | Sort position |
| `filter` | object | | create/update | Filter query for this view |
| `default_bucket_id` | integer | | create/update | Bucket for new tasks (kanban) |
| `done_bucket_id` | integer | | create/update | Bucket for completed tasks |
| `bucket_configuration_mode` | string | enum: `none`, `manual`, `filter` | create/update | How buckets are configured |
| `bucket_configuration` | [BucketConfig] | | create/update | Bucket config options (non-manual modes) |
| `created` | string | RFC 3339 | read-only | Creation timestamp |
| `updated` | string | RFC 3339 | read-only | Last update timestamp |

---

## Bucket (`models.Bucket`)

| Field | Type | Constraints | Writable | Description |
|-------|------|-------------|----------|-------------|
| `id` | integer | | read-only | Unique numeric ID |
| `title` | string | min: 1 | create/update | Bucket title |
| `limit` | integer | min: 0 | create/update | Max concurrent tasks (0 = unlimited) |
| `position` | number | float | update | Sort position |
| `project_view_id` | integer | | read-only | Parent view |
| `count` | integer | | read-only | Current task count |
| `tasks` | [Task] | | read-only | Tasks in this bucket |
| `created` | string | RFC 3339 | read-only | Creation timestamp |
| `updated` | string | RFC 3339 | read-only | Last update timestamp |
| `created_by` | User | | read-only | Creator |

### Creation payload (PUT /projects/{id}/views/{view}/buckets)
```json
{
  "title": "In Progress",
  "limit": 5
}
```

---

## TaskBucket (`models.TaskBucket`)

Used for moving tasks between buckets.

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | integer | Task to move |
| `bucket_id` | integer | Target bucket |
| `project_view_id` | integer | View this bucket belongs to |
| `task` | Task | read-only, populated in response |
| `bucket` | Bucket | read-only, populated in response |

**Note:** Position is managed separately via `POST /tasks/{id}/position`.

### Move payload (POST /projects/{project}/views/{view}/buckets/{bucket}/tasks)
```json
{"task_id": 42}
```

---

## TaskPosition (`models.TaskPosition`)

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | integer | Task ID |
| `position` | number | Float position value |
| `project_view_id` | integer | View context for this position |

### Payload (POST /tasks/{id}/position)
```json
{
  "position": 1234.5,
  "project_view_id": 1
}
```

---

## TaskComment (`models.TaskComment`)

| Field | Type | Writable | Description |
|-------|------|----------|-------------|
| `id` | integer | read-only | Comment ID |
| `comment` | string | create/update | Comment text |
| `author` | User | read-only | Comment author |
| `reactions` | ReactionMap | read-only | Reactions |
| `created` | string | read-only | Creation timestamp |
| `updated` | string | read-only | Last update timestamp |

---

## TaskAttachment (`models.TaskAttachment`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Attachment ID |
| `task_id` | integer | Parent task |
| `file` | File | File metadata (name, size, mime, etc.) |
| `created` | string | Creation timestamp |
| `created_by` | User | Uploader |

---

## TaskReminder (`models.TaskReminder`)

| Field | Type | Description |
|-------|------|-------------|
| `reminder` | string | Absolute reminder time (RFC 3339) |
| `relative_period` | integer | Seconds relative to `relative_to` (negative = before) |
| `relative_to` | string | Date field name to anchor relative reminder |

---

## LabelTask (`models.LabelTask`)

| Field | Type | Description |
|-------|------|-------------|
| `label_id` | integer | Label ID to associate with a task |
| `created` | string | read-only, creation timestamp |

---

## LabelTaskBulk (`models.LabelTaskBulk`)

| Field | Type | Description |
|-------|------|-------------|
| `labels` | [Label] | All labels to set on the task (replaces existing) |

---

## TaskCollection (`models.TaskCollection`)

Query parameters for listing tasks (used internally).

| Field | Type | Description |
|-------|------|-------------|
| `s` | string | Search query |
| `filter` | string | Filter expression |
| `filter_include_nulls` | boolean | Include null values |
| `sort_by` | [string] | Fields to sort by |
| `order_by` | [string] | `asc` or `desc` per sort field |

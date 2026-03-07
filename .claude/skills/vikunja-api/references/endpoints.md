# Vikunja API Endpoints Reference

Full endpoint catalog derived from `docs/vikunja-swagger.json` (v2.1.0).

Base path: `/api/v1` | Auth: `Authorization: Bearer <token>`

**Reminder:** PUT creates, POST updates (except labels: PUT for both create and update).

---

## Tasks

### GET /tasks
List all tasks the user has access to.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `page` | integer | Page number (1-indexed) |
| `per_page` | integer | Items per page |
| `s` | string | Search query |
| `sort_by` | string | Field to sort by (e.g., `due_date`, `priority`, `done`) |
| `order_by` | string | `asc` or `desc` |
| `filter` | string | Filter expression (see filter-syntax.md) |
| `filter_timezone` | string | Timezone for date filters |
| `filter_include_nulls` | string | Include nulls in filter results |
| `expand` | array | Expand related data (e.g., `comments`, `buckets`) |

**Response 200:** `[Task]`
**Headers:** `x-pagination-total-pages`, `x-pagination-result-count`

### GET /tasks/{id}
Get a single task.

**Path params:** `id` (integer, required)
**Query params:** `expand` (array)

**Response 200:** `Task` | **404:** not found
**Headers:** `x-max-permission`

### POST /tasks/{id}
Update a task.

**Path params:** `id` (integer, required)
**Body:** `Task` (fields to update)

**Response 200:** `Task` | **400:** validation | **403:** forbidden

### DELETE /tasks/{id}
Delete a task.

**Path params:** `id` (integer, required)

**Response 200:** `{"message": "Successfully deleted."}` | **400/403:** error

### PUT /projects/{id}/tasks
Create a task in a project.

**Path params:** `id` (integer, required — project ID)
**Body:** `Task` (at minimum `{"title": "..."}`)

**Response 201:** `Task` | **400:** validation | **403:** forbidden

### POST /tasks/bulk
Update multiple tasks at once.

**Body:** `BulkTask`
```json
{
  "task_ids": [1, 2, 3],
  "fields": ["done"],
  "values": {"done": true}
}
```

**Response 200:** `[Task]`

### POST /tasks/{id}/position
Update a task's position within a view.

**Path params:** `id` (integer, required)
**Body:** `TaskPosition`
```json
{
  "position": 1234.5,
  "project_view_id": 1
}
```

**Response 200:** `TaskPosition`

### POST /tasks/{id}/read
Mark a task as read for the current user.

**Path params:** `id` (integer, required — uses `projecttask` in spec)

**Response 200:** `Task`

---

## Projects

### GET /projects
List all projects.

**Query params:** `page`, `per_page`, `s`, `is_archived` (boolean), `expand` (string)

**Response 200:** `[Project]`

### GET /projects/{id}
Get one project.

**Path params:** `id` (integer, required)

**Response 200:** `Project`
**Headers:** `x-max-permission`

### PUT /projects
Create a new project.

**Body:** `Project` (at minimum `{"title": "..."}`)

**Response 201:** `Project`

### POST /projects/{id}
Update a project.

**Path params:** `id` (integer, required)
**Body:** `Project` (fields to update)

**Response 200:** `Project`

### DELETE /projects/{id}
Delete a project and all its tasks.

**Path params:** `id` (integer, required)

**Response 200:** `{"message": "Successfully deleted."}`

### PUT /projects/{projectID}/duplicate
Duplicate a project with all tasks.

**Path params:** `projectID` (integer, required)
**Body:** `ProjectDuplicate` (`{"parent_project_id": N}`)

**Response 201:** `ProjectDuplicate`

---

## Labels

### GET /labels
List all labels the user has access to.

**Query params:** `page`, `per_page`, `s`

**Response 200:** `[Label]`

### GET /labels/{id}
Get one label.

**Path params:** `id` (integer, required)

**Response 200:** `Label`

### PUT /labels
Create a label.

**Body:** `Label` (at minimum `{"title": "..."}`)

**Response 201:** `Label`

### PUT /labels/{id}
Update a label. **Note:** Uses PUT, not POST (unlike other update endpoints).

**Path params:** `id` (integer, required)
**Body:** `Label` (fields to update)

**Response 200:** `Label`

### DELETE /labels/{id}
Delete a label.

**Path params:** `id` (integer, required)

**Response 200:** `Label`

---

## Task Labels

### GET /tasks/{task}/labels
Get all labels on a task.

**Path params:** `task` (integer, required)
**Query params:** `page`, `per_page`, `s`

**Response 200:** `[Label]`

### PUT /tasks/{task}/labels
Add a label to a task.

**Path params:** `task` (integer, required)
**Body:** `LabelTask`
```json
{"label_id": 1}
```

**Response 201:** `LabelTask`

### DELETE /tasks/{task}/labels/{label}
Remove a label from a task.

**Path params:** `task` (integer), `label` (integer)

**Response 200:** `{"message": "Successfully deleted."}`

### POST /tasks/{taskID}/labels/bulk
Replace all labels on a task.

**Path params:** `taskID` (integer, required)
**Body:** `LabelTaskBulk`
```json
{"labels": [{"id": 1}, {"id": 2}]}
```

**Response 201:** `LabelTaskBulk`

---

## Views

### GET /projects/{project}/views
List all views for a project.

**Path params:** `project` (integer, required)

**Response 200:** `[ProjectView]`

### GET /projects/{project}/views/{id}
Get one view.

**Path params:** `project` (integer), `id` (integer)

**Response 200:** `ProjectView`

### PUT /projects/{project}/views
Create a view.

**Path params:** `project` (integer, required)
**Body:** `ProjectView`

**Response 200:** `ProjectView`

### POST /projects/{project}/views/{id}
Update a view.

**Path params:** `project` (integer), `id` (integer)
**Body:** `ProjectView`

**Response 200:** `ProjectView`

### DELETE /projects/{project}/views/{id}
Delete a view.

**Path params:** `project` (integer), `id` (integer)

**Response 200:** `{"message": "Successfully deleted."}`

---

## Buckets (Kanban)

### GET /projects/{id}/views/{view}/buckets
List all buckets in a kanban view.

**Path params:** `id` (integer — project), `view` (integer — view ID)

**Response 200:** `[Bucket]` (each bucket may contain `tasks` array)

### PUT /projects/{id}/views/{view}/buckets
Create a new bucket.

**Path params:** `id` (integer), `view` (integer)
**Body:** `Bucket` (at minimum `{"title": "..."}`)

**Response 200:** `Bucket`

### POST /projects/{projectID}/views/{view}/buckets/{bucketID}
Update a bucket.

**Path params:** `projectID`, `view`, `bucketID` (all integer)
**Body:** `Bucket` (fields to update)

**Response 200:** `Bucket`

### DELETE /projects/{projectID}/views/{view}/buckets/{bucketID}
Delete a bucket. Tasks in it are moved to the default bucket.

**Path params:** `projectID`, `view`, `bucketID` (all integer)

**Response 200:** `{"message": "Successfully deleted."}`

---

## View Tasks

### GET /projects/{id}/views/{view}/tasks
Get tasks in a project through a specific view.

**Path params:** `id` (integer — project), `view` (integer — view ID)

**Query params:** Same as `GET /tasks` — `page`, `per_page`, `s`, `sort_by`, `order_by`, `filter`, `filter_timezone`, `filter_include_nulls`, `expand`

**Response 200:** `[Task]`
- For **kanban views**, the response structure includes buckets with nested tasks
- For **list/table/gantt views**, returns a flat `[Task]` array

**Headers:** `x-pagination-total-pages`, `x-pagination-result-count`

---

## Move Task to Bucket

### POST /projects/{project}/views/{view}/buckets/{bucket}/tasks
Move a task to a specific bucket in a kanban view.

**Path params:** `project`, `view`, `bucket` (all integer)
**Body:** `TaskBucket`
```json
{"task_id": 1}
```

**Response 200:** `TaskBucket`

---

## Assignees

### GET /tasks/{taskID}/assignees
List all assignees for a task.

**Response 200:** `[User]`

### PUT /tasks/{taskID}/assignees
Add an assignee to a task.

**Body:** `{"user_id": N}`

**Response 201:** `TaskAssignee`

### POST /tasks/{taskID}/assignees/bulk
Bulk assign users to a task.

**Body:** `BulkAssignees` — `{"assignees": [{"id": N}, ...]}`

**Response 201:** `BulkAssignees`

### DELETE /tasks/{taskID}/assignees/{userID}
Remove an assignee from a task.

**Response 200:** `{"message": "Successfully deleted."}`

---

## Comments

### GET /tasks/{taskID}/comments
List all comments on a task.

**Response 200:** `[TaskComment]`

### PUT /tasks/{taskID}/comments
Create a comment.

**Body:** `TaskComment` — `{"comment": "text"}`

**Response 201:** `TaskComment`

### GET /tasks/{taskID}/comments/{commentID}
Get one comment.

**Response 200:** `TaskComment`

### POST /tasks/{taskID}/comments/{commentID}
Update a comment.

**Body:** `TaskComment`

**Response 200:** `TaskComment`

### DELETE /tasks/{taskID}/comments/{commentID}
Delete a comment.

**Response 200:** `{"message": "Successfully deleted."}`

---

## Attachments

### GET /tasks/{id}/attachments
List all attachments on a task.

**Response 200:** `[TaskAttachment]`

### PUT /tasks/{id}/attachments
Upload an attachment (multipart/form-data).

**Body:** file upload

**Response 201:** `TaskAttachment`

### GET /tasks/{id}/attachments/{attachmentID}
Download an attachment.

**Response 200:** file stream

### DELETE /tasks/{id}/attachments/{attachmentID}
Delete an attachment.

**Response 200:** `{"message": "Successfully deleted."}`

---

## Relations

### PUT /tasks/{taskID}/relations
Create a relation between two tasks.

**Body:** `TaskRelation`
```json
{
  "other_task_id": 2,
  "relation_kind": "related"
}
```

Relation kinds: `unknown`, `subtask`, `parenttask`, `related`, `duplicateof`, `duplicates`, `blocking`, `blocked`, `precedes`, `follows`, `copiedfrom`, `copiedto`

**Response 201:** `TaskRelation`

### DELETE /tasks/{taskID}/relations/{relationKind}/{otherTaskID}
Remove a relation.

**Response 200:** `{"message": "Successfully deleted."}`

---

## Reactions

### GET /{kind}/{id}/reactions
Get reactions on an entity. `kind` is `tasks` or `comments`.

**Response 200:** `ReactionMap`

### PUT /{kind}/{id}/reactions
Add a reaction.

**Body:** `{"value": "emoji"}`

**Response 200:** `Reaction`

### POST /{kind}/{id}/reactions/delete
Remove your reaction.

**Body:** `{"value": "emoji"}`

**Response 200:** `{"message": "..."}`

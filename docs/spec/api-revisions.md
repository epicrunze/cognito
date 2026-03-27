# API: Revisions (Undo/Redo)

Every AI-initiated task mutation is recorded as a revision with before/after state snapshots. This enables full undo/redo of chat actions and proposal approvals.

## What triggers a revision

| Source       | Action types                              |
|--------------|-------------------------------------------|
| `chat`       | create, update, complete, move, delete    |
| `proposal`   | create (on approve)                       |
| `auto_tag`   | auto_tag (label additions)                |

Each revision stores: `task_id`, `action_type`, `source`, `before_state` (full Vikunja task JSON), `after_state`, `changes`, and optional `conversation_id` / `proposal_id`.

---

## GET /api/revisions?limit=50

List recent revisions, newest first. `limit` range: 1-200 (default 50).

```json
{
  "revisions": [
    {
      "id": 7, "task_id": 42, "action_type": "update", "source": "chat",
      "before_state": {...}, "after_state": {...}, "changes": {"title": "New"},
      "conversation_id": "uuid", "proposal_id": null,
      "undone": false, "undone_at": null, "created_at": "2026-03-27T..."
    }
  ]
}
```

## GET /api/revisions/{id}

Get a single revision by ID. Returns 404 if not found.

## POST /api/revisions/{id}/undo?force=false

Undo a revision. Before applying, the service checks for conflicts (the task may have been modified since the revision was recorded). If conflicts are detected:

```json
{
  "conflict": true,
  "conflict_fields": ["title", "priority"],
  "current_state": {...},
  "expected_state": {...}
}
```

Pass `?force=true` to skip the conflict check and apply the undo regardless.

Undo behavior by action type:
- **create** -- deletes the created task
- **update / complete / move** -- restores `before_state` fields (title, description, priority, due_date, done, project_id)
- **delete** -- re-creates the task from `before_state`
- **auto_tag** -- removes the labels that were added

Returns `{"success": true, "revision_id": 7, "action_type": "update"}` on success.

## POST /api/revisions/{id}/redo

Re-apply a previously undone revision. Only works if the revision is currently marked as undone. Mirrors the original action using `after_state`.

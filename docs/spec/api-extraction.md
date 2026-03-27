# API: Extraction & Proposals

## POST /api/ingest

Extract task proposals from unstructured text via LLM tool-calling.

### Request

```json
{
  "text": "string (required)",
  "source_type": "notes | email | idea | manual (default: notes)",
  "confidential": false,
  "project_hint": "string | null",
  "model": "gemini-flash (default)"
}
```

### Response (JSON) — default

```json
{
  "source_id": "uuid",
  "proposals": [TaskProposal],
  "conversation_id": "uuid"
}
```

### Response (SSE) — when `Accept: text/event-stream`

Events are emitted in order:

| Event      | Data                                        |
|------------|---------------------------------------------|
| `proposal` | Single `TaskProposal` JSON                  |
| `done`     | `{"count": N, "conversation_id": "uuid"}`   |
| `error`    | `{"detail": "error message"}`               |

Each ingest interaction is persisted as a conversation (visible in chat history).

---

## GET /api/proposals

List proposals. Optional query param `?status=pending|created|rejected`.

```json
{ "proposals": [TaskProposal], "count": 5 }
```

## PUT /api/proposals/{id}

Edit a proposal before approving. Body is a partial `TaskProposalUpdate` (any subset of title, description, project_name, project_id, priority, due_date, estimated_minutes, labels). Returns the updated `TaskProposal`.

## POST /api/proposals/{id}/approve

Approve a proposal — creates the task in Vikunja. If no `project_id` is set, the endpoint creates the project from `project_name` or falls back to `default_project_id` from agent config.

```json
{
  "success": true,
  "vikunja_task_id": 42,
  "vikunja_url": "https://...",
  "new_project_created": false,
  "revision_id": 7
}
```

## POST /api/proposals/{id}/reject

Mark a proposal as rejected. Returns `{"success": true}`.

## POST /api/proposals/approve-all

Batch-approve pending proposals. Optionally pass `{"ids": ["id1", "id2"]}` to limit scope; otherwise approves all pending.

```json
{
  "approved": 3,
  "errors": [{"id": "...", "title": "...", "error": "..."}],
  "new_projects": ["Project Name"],
  "task_ids": [42, 43, 44]
}
```

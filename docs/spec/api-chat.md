# API: Chat (ChatAgent)

The ChatAgent combines task extraction with task modification in a conversational interface. It auto-detects whether the user is pasting text for extraction or issuing a command to modify existing tasks.

## Tools

### Extraction tools (from TaskExtractor)
- `lookup_projects` — list available Vikunja projects
- `resolve_project` — fuzzy-match a project name to an ID
- `check_existing_tasks` — deduplicate against existing tasks
- `get_label_descriptions` — fetch label metadata for tagging

### Modification tools
- `search_tasks(query)` — keyword search, returns up to 10 matches (id, title, done, project_id)
- `update_task(task_id, title?, description?, priority?, due_date?)` — update fields (pending confirmation)
- `complete_task(task_id)` — mark done (pending confirmation)
- `move_task(task_id, project_id)` — move to another project (pending confirmation)
- `delete_task(task_id)` — request deletion (pending confirmation)
- `create_task(title, project_id, description?, priority?, due_date?, labels?)` — create directly (pending confirmation)

All modification tools except `search_tasks` return `pending_actions` that require user approval via the execute-action endpoint.

---

## POST /api/chat

Send a message. Creates a new conversation if `conversation_id` is omitted. Keeps the last 10 messages as context.

### Request
```json
{
  "message": "string (required)",
  "conversation_id": "string | null",
  "model": "gemini-flash (default)"
}
```

### Response
```json
{
  "reply": "AI response text",
  "proposals": [TaskProposal],
  "actions": [],
  "pending_actions": [
    { "type": "delete", "task_id": 42, "task_title": "Old task" }
  ],
  "conversation_id": "uuid"
}
```

## POST /api/chat/execute-action

Confirm and execute a pending action after user approval. Records a revision for undo.

### Request
```json
{
  "type": "create | update | complete | move | delete",
  "task_id": 42,
  "changes": { "title": "New title" },
  "project_id": 5
}
```

- `changes` required for `create` and `update`
- `project_id` required for `move` and `create`

### Response
```json
{ "success": true, "revision_id": 7 }
```
For `create`, also returns `task` (full Vikunja object) and `vikunja_task_id`.

## GET /api/chat/history

List recent conversations (up to 50, newest first).

```json
{
  "conversations": [
    { "id": "uuid", "snippet": "first 100 chars...", "created_at": "...", "message_count": 4 }
  ]
}
```

## GET /api/chat/{id}

Load a conversation with full message history.

```json
{
  "conversation_id": "uuid",
  "messages": [
    { "role": "user", "content": "...", "created_at": "..." },
    { "role": "assistant", "content": "...", "proposals": [...], "actions": [...], "created_at": "..." }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

## DELETE /api/chat/{id}

Delete a conversation and all its messages. Returns `{"success": true}`.

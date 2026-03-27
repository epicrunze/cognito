# Labels API — `/api/labels`

Proxies label CRUD to Vikunja and manages label descriptions in local SQLite (used by auto-tagger). All endpoints require authentication.

## Label Endpoints (Vikunja Proxy)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/labels` | List all labels |
| PUT | `/api/labels` | Create a label |
| PUT | `/api/labels/{id}` | Update a label |
| DELETE | `/api/labels/{id}` | Delete a label |
| POST | `/api/labels/cleanup` | Delete all labels with 0 tasks |

## Description Endpoints (SQLite)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/labels/descriptions` | List all label descriptions |
| PUT | `/api/labels/{id}/description` | Upsert a label description |
| DELETE | `/api/labels/{id}/description` | Delete a label description |

## Other Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/labels/stats` | Per-label task counts (total, done, open) |
| POST | `/api/labels/{id}/generate-description` | LLM-generate a description from the label's tasks |

## Create Label: `PUT /api/labels`

```json
{ "title": "bug", "hex_color": "E8772E", "description": "Software defects" }
```

## Upsert Description: `PUT /api/labels/{id}/description`

```json
{ "title": "bug", "description": "Apply to tasks that track software defects or broken behavior." }
```

Descriptions are stored in SQLite (not Vikunja) and power the auto-tagger. The `title` field is denormalized for display purposes.

## Stats Response: `GET /api/labels/stats`

```json
{
  "stats": {
    "1": { "total": 12, "done": 5, "open": 7 },
    "2": { "total": 3, "done": 0, "open": 3 }
  }
}
```

Keys are label IDs (as strings in JSON). Computed by scanning all tasks (up to 500).

## Generate Description: `POST /api/labels/{id}/generate-description`

No request body. Fetches all tasks with this label, sends them to Gemini Flash, and saves the generated description. Returns 400 if no tasks use the label.

## Gotchas

- **Label updates use PUT** (not POST), matching Vikunja's convention where PUT is used for both create and update on labels.
- **`hex_color` has no `#` prefix** when sent to Vikunja. Send `E8772E`, not `#E8772E`.
- **Cleanup side effect:** `POST /api/labels/cleanup` also removes SQLite descriptions for any deleted labels.
- **Stats are computed on-the-fly** by scanning up to 500 tasks. Not cached.
- **Descriptions vs. Vikunja descriptions:** Vikunja labels have their own `description` field. The `/descriptions` endpoints manage a *separate* SQLite table used specifically by the auto-tagger, not the Vikunja field.

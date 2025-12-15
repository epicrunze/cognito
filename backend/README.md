# Cognito Backend

FastAPI backend for Cognito PWA - Conversational Thought Journaling.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

```bash
# Install dependencies
uv sync
```

## Development

```bash
# Start development server with hot reload
uv run uvicorn app.main:app --reload

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

## Configuration

Create a `.env` file in the backend directory:

```bash
### Database
DATABASE_URL=duckdb:///./data/journal.duckdb

### Authentication (Google OAuth)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
JWT_SECRET=change-this-to-a-secure-random-string
JWT_EXPIRY_HOURS=24
ALLOWED_EMAIL=your.google.email@gmail.com
COOKIE_SECURE=True  # Set to False for localhost development

### Application
FRONTEND_URL=http://localhost:5173

### LLM Integration
GEMINI_API_KEY=your-gemini-key
OLLAMA_URL=http://localhost:11434
```

## Security & Authentication

The backend uses Google OAuth 2.0 for authentication and JWT tokens for session management.

1. **Setup Google OAuth:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and configure OAuth consent screen
   - Create OAuth 2.0 Client credentials (Web application)
   - Add authorized redirect URI: `http://localhost:5173/auth/callback` (and production URL)
   - Copy Client ID and Secret to `.env`

2. **Login Flow:**
   - Frontend redirects to `/api/auth/login`
   - User authenticates with Google
   - Server validates email against `ALLOWED_EMAIL`
   - Server sets HttpOnly `cognito_auth` cookie with JWT
   - Redirects back to frontend

3. **Protection:**
   - JWT tokens are signed and valid for `JWT_EXPIRY_HOURS`
   - Cookies are HttpOnly, Secure, and SameSite=Strict
   - Only the configured `ALLOWED_EMAIL` can log in

## API Endpoints

### Authentication

All Entry API endpoints require authentication via the `cognito_auth` cookie.

**Endpoints:**
- `GET /api/auth/login` - Initiate Google OAuth flow
- `GET /api/auth/callback` - OAuth callback handler
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Clear auth cookie

### Entries

Manage journal entries with conversation history and version tracking.

#### List Entries

```http
GET /api/entries?status=active&limit=20&offset=0&order_by=date:desc
```

**Query Parameters:**
- `status` (optional): Filter by status (`active` or `archived`)
- `after_date` (optional): Filter entries after date (YYYY-MM-DD)
- `before_date` (optional): Filter entries before date (YYYY-MM-DD)
- `limit` (optional): Max entries to return (1-100, default: 50)
- `offset` (optional): Skip entries for pagination (default: 0)
- `order_by` (optional): Sort order, format `field:direction` (default: `date:desc`)

**Response:**
```json
{
  "entries": [
    {
      "id": "uuid",
      "date": "2024-12-10",
      "conversations": [
        {
          "id": "uuid",
          "started_at": "2024-12-10T10:00:00Z",
          "messages": [
            {
              "role": "user",
              "content": "Today I realized...",
              "timestamp": "2024-12-10T10:00:00Z"
            }
          ],
          "prompt_source": "user",
          "notification_id": null
        }
      ],
      "refined_output": "Reflection on...",
      "relevance_score": 1.0,
      "last_interacted_at": "2024-12-10T10:05:00Z",
      "interaction_count": 2,
      "status": "active",
      "version": 1,
      "created_at": "2024-12-10T10:00:00Z",
      "updated_at": "2024-12-10T10:00:00Z"
    }
  ],
  "total": 42
}
```

#### Get Single Entry

```http
GET /api/entries/{entry_id}
```

Updates `last_interacted_at` timestamp on access.

**Response:** Single entry object (see structure above)

**Errors:**
- `401` - Not authenticated
- `404` - Entry not found or not owned by user

#### Create Entry

```http
POST /api/entries
Content-Type: application/json

{
  "date": "2024-12-10",
  "conversations": [
    {
      "id": "uuid",
      "started_at": "2024-12-10T10:00:00Z",
      "messages": [
        {
          "role": "user",
          "content": "Message text",
          "timestamp": "2024-12-10T10:00:00Z"
        }
      ],
      "prompt_source": "user",
      "notification_id": null
    }
  ],
  "refined_output": "Initial reflection"
}
```

**Behavior:**
- Returns existing entry if one exists for the given date (date uniqueness)
- Auto-creates user account on first request if needed

**Response:** Created or existing entry object (HTTP 201)

#### Update Entry

```http
PUT /api/entries/{entry_id}
Content-Type: application/json

{
  "refined_output": "Updated reflection",
  "status": "archived"
}
```

All fields are optional (partial update).

**Behavior:**
- Creates version snapshot before update
- Increments `version` number
- Updates `updated_at` timestamp

**Available fields:**
- `conversations` - Full conversation replacement
- `refined_output` - Updated reflection text
- `relevance_score` - Score 0.0-1.0
- `status` - `active` or `archived`

**Response:** Updated entry object

**Errors:**
- `404` - Entry not found or not owned by user

#### Get Version History

```http
GET /api/entries/{entry_id}/versions
```

Retrieve snapshots of previous `refined_output` values.

**Response:**
```json
{
  "versions": [
    {
      "id": "uuid",
      "entry_id": "uuid",
      "version": 3,
      "content_snapshot": "Previous reflection text",
      "created_at": "2024-12-10T10:00:00Z"
    },
    {
      "id": "uuid",
      "entry_id": "uuid",
      "version": 2,
      "content_snapshot": "Even older text",
      "created_at": "2024-12-09T15:00:00Z"
    }
  ]
}
```

Versions are ordered newest first.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app, CORS, middleware
│   ├── config.py         # Settings, environment variables
│   ├── database.py       # DuckDB connection, schema
│   ├── models/           # Pydantic models
│   │   ├── user.py       # User model
│   │   └── entry.py      # Entry, Conversation models
│   ├── routers/          # API route handlers
│   │   ├── auth.py       # Authentication endpoints
│   │   └── entries.py    # Entry CRUD endpoints
│   ├── repositories/     # Data access layer
│   │   └── entry_repo.py # Entry database operations
│   ├── services/         # Business logic
│   ├── jobs/             # Scheduled jobs
│   └── auth/             # Authentication
│       └── dependencies.py
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_auth.py      # Auth tests
│   ├── test_entries.py   # Entry CRUD tests
│   └── test_entry_versions.py  # Version snapshot tests
└── data/                 # DuckDB database files
```

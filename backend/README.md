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

### Local Development (Without Docker)

```bash
# Start development server with hot reload
uv run uvicorn app.main:app --reload

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Docker Development

See the [Docker Deployment](#docker-deployment) section below for running the backend in Docker.

## Docker Deployment

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0+)
- The `cognito-network` Docker network must exist

### Quick Start

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create environment file from example
cp .env.docker.example .env.docker

# 3. Edit .env.docker with your actual configuration
# At minimum, set: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, JWT_SECRET, ALLOWED_EMAIL

# 4. Build and start the container
docker-compose up -d

# 5. View logs
docker-compose logs -f

# 6. Verify health
curl http://localhost:8000/health
```

### Environment Configuration for Docker

Edit `.env.docker` with your configuration:

```bash
# Required: Database (uses Docker volume)
DATABASE_URL=duckdb:///./data/journal.duckdb

# Required: Google OAuth credentials
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Required: JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET=your-secure-random-string

# Required: Allowed user email
ALLOWED_EMAIL=your.email@gmail.com

# Frontend URL (update for production)
FRONTEND_URL=http://localhost:5173

# Cookie security (False for local HTTP, True for production HTTPS)
COOKIE_SECURE=False

# Optional: LLM integration
GEMINI_API_KEY=your-gemini-key
OLLAMA_URL=http://localhost:11434  # or http://ollama:11434 if on cognito-network
```

### Network Configuration

The backend connects to the existing `cognito-network` Docker bridge network. This allows other services on the same network to communicate with the backend using the service name:

```bash
# From another container on cognito-network:
http://cognito-backend:8000
```

If the network doesn't exist, create it:

```bash
docker network create cognito-network
```

### Data Persistence

The DuckDB database is stored in a Docker volume named `cognito-data`, which persists across container restarts:

```bash
# View volume details
docker volume inspect cognito-data

# Backup the database
docker cp cognito-backend:/app/data/journal.duckdb ./backup.duckdb

# Restore the database
docker cp ./backup.duckdb cognito-backend:/app/data/journal.duckdb
```

### Docker Management Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose stop

# Restart services
docker-compose restart

# View logs (all)
docker-compose logs -f

# View logs (last 100 lines)
docker-compose logs --tail=100 -f

# Execute commands in container
docker-compose exec cognito-backend /bin/bash

# Stop and remove containers (keeps volumes)
docker-compose down

# Stop and remove containers AND volumes (deletes data!)
docker-compose down -v

# Rebuild image after code changes
docker-compose build
docker-compose up -d
```

### Health Checks

The container includes automatic health checks that monitor the `/health` endpoint:

```bash
# Check container health status
docker-compose ps

# Manual health check
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# Check from another container on cognito-network
docker run --rm --network cognito-network curlimages/curl:latest \
  curl http://cognito-backend:8000/health
```

### Troubleshooting

#### Container won't start

```bash
# Check logs for errors
docker-compose logs

# Verify environment file exists
ls -la .env.docker

# Validate docker-compose configuration
docker-compose config
```

#### Database permission errors

```bash
# The container runs as non-root user (uid 1000)
# If you have permission issues, check volume permissions:
docker-compose exec cognito-backend ls -la /app/data/
```

#### Network connectivity issues

```bash
# Verify container is on cognito-network
docker network inspect cognito-network

# Should show cognito-backend in Containers section

# If network doesn't exist:
docker network create cognito-network
# Then restart container:
docker-compose down && docker-compose up -d
```

#### OAuth redirect URI issues

When running in Docker, ensure your Google OAuth redirect URIs include:
- Development: `http://localhost:5173/auth/callback`
- Production: `https://your-domain.com/auth/callback`

#### Port conflicts

If port 8000 is already in use:

```bash
# Option 1: Stop the conflicting service
sudo lsof -i :8000

# Option 2: Change the port in docker-compose.yml
# Edit ports section: "8001:8000" (maps host 8001 to container 8000)
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

**Response:** Created or existing entry object (HTTP 201)

**Errors:**
- `401` - Not authenticated

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
- `401` - Not authenticated
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

**Errors:**
- `401` - Not authenticated

### Chat

Conversational journaling with LLM integration. Supports both Gemini API and local Ollama.

#### Send Message

```http
POST /api/chat
Content-Type: application/json

{
  "entry_id": "uuid",
  "conversation_id": "uuid",  // Optional - omit to start new conversation
  "message": "I had a great day today",
  "use_local_model": false    // Optional - use Ollama instead of Gemini
}
```

**Behavior:**
- Creates new conversation if `conversation_id` is not provided
- Stores user message and assistant response in the entry
- Uses Gemini API by default, or Ollama if `use_local_model` is true

**Response:**
```json
{
  "response": "That's wonderful! What made it great?",
  "conversation_id": "uuid",
  "entry_id": "uuid"
}
```

**Errors:**
- `401` - Not authenticated
- `404` - Entry or conversation not found
- `503` - LLM service unavailable

#### Refine Entry

```http
POST /api/chat/refine
Content-Type: application/json

{
  "entry_id": "uuid",
  "use_local_model": false  // Optional
}
```

Synthesizes all conversations in an entry into a coherent journal summary.

**Response:**
```json
{
  "refined_output": "# Today's Reflection\n\nI had a productive day...",
  "entry_id": "uuid"
}
```

**Errors:**
- `401` - Not authenticated
- `400` - No conversations to refine
- `404` - Entry not found
- `503` - LLM service unavailable

#### LLM Configuration

Set the following environment variables:

```bash
# Gemini API (primary)
GEMINI_API_KEY=your-gemini-api-key

# Ollama (local fallback)
OLLAMA_URL=http://localhost:11434  # Default model: llama3.2
```

**System Prompts:**

The LLM uses two system prompts defined in `app/services/llm.py`:

- `CHAT_SYSTEM_PROMPT`: Guides the LLM to be a thoughtful journaling companion that asks follow-up questions
- `REFINE_SYSTEM_PROMPT`: Instructs the LLM to synthesize conversations into a coherent first-person journal entry

To customize the prompts, edit the constants in `app/services/llm.py`.

### Goals

Manage user-defined objectives that guide notification generation.

#### List Goals

```http
GET /api/goals?active=true
```

**Query Parameters:**
- `active` (optional): Filter by active status (`true` or `false`, omit for all)

**Response:**
```json
{
  "goals": [
    {
      "id": "uuid",
      "category": "health",
      "description": "Exercise 3x per week",
      "active": true,
      "created_at": "2024-12-15T10:00:00Z",
      "updated_at": "2024-12-15T10:00:00Z"
    }
  ]
}
```

**Errors:**
- `401` - Not authenticated

#### Get Single Goal

```http
GET /api/goals/{goal_id}
```

**Response:** Single goal object (see structure above)

**Errors:**
- `401` - Not authenticated
- `404` - Goal not found or not owned by user

#### Create Goal

```http
POST /api/goals
Content-Type: application/json

{
  "category": "health",
  "description": "Exercise 3x per week"
}
```

**Category examples:** `health`, `productivity`, `skills`, or any custom string

**Response:** Created goal object (HTTP 201)

**Errors:**
- `401` - Not authenticated

#### Update Goal

```http
PUT /api/goals/{goal_id}
Content-Type: application/json

{
  "description": "Exercise 5x per week",
  "active": false
}
```

All fields are optional (partial update).

**Available fields:**
- `category` - Goal category
- `description` - Goal description  
- `active` - Whether goal is active (true/false)

**Response:** Updated goal object

**Errors:**
- `401` - Not authenticated
- `404` - Goal not found or not owned by user

#### Delete Goal

```http
DELETE /api/goals/{goal_id}
```

Performs soft delete (sets `active=false`). Goal remains in database but is marked inactive.

**Response:**
```json
{
  "success": true
}
```

**Errors:**
- `401` - Not authenticated
- `404` - Goal not found or not owned by user

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
│   │   ├── entry.py      # Entry, Conversation models
│   │   └── goal.py       # Goal models
│   ├── routers/          # API route handlers
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── entries.py    # Entry CRUD endpoints
│   │   └── goals.py      # Goal CRUD endpoints
│   ├── repositories/     # Data access layer
│   │   ├── entry_repo.py # Entry database operations
│   │   ├── goal_repo.py  # Goal database operations
│   │   └── user_repo.py  # User database operations
│   ├── services/         # Business logic
│   ├── jobs/             # Scheduled jobs
│   └── auth/             # Authentication
│       └── dependencies.py
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_auth.py      # Auth tests
│   ├── test_entries.py   # Entry CRUD tests
│   ├── test_entry_versions.py  # Version snapshot tests
│   ├── test_goals.py     # Goal CRUD tests
│   └── test_user_repo.py # User repository tests
└── data/                 # DuckDB database files
```


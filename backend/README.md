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

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app, CORS, middleware
│   ├── config.py         # Settings, environment variables
│   ├── database.py       # DuckDB connection, schema
│   ├── models/           # Pydantic models
│   ├── routers/          # API route handlers
│   ├── services/         # Business logic
│   ├── jobs/             # Scheduled jobs
│   └── auth/             # Authentication
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_config.py    # Config tests
│   └── test_database.py  # Database tests
└── data/                 # DuckDB database files
```

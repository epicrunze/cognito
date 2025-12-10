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
DATABASE_URL=duckdb:///./data/journal.duckdb
JWT_SECRET=your-secret-key-here
JWT_EXPIRY_HOURS=24
ALLOWED_EMAIL=your.email@gmail.com
FRONTEND_URL=http://localhost:5173
GEMINI_API_KEY=your-gemini-key
OLLAMA_URL=http://localhost:11434
```

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

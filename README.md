# cognito
AI powered thought journals

## Overview

A Progressive Web Application for conversational thought journaling with LLM integration. The system combines personal knowledge management with AI augmentation, featuring autonomous maintenance and proactive prompting.

## Project Structure

- **backend/** - FastAPI backend API with DuckDB database
- **frontend/** - SvelteKit PWA client application

## Quick Start

### Backend (Docker)

The backend can be run in Docker for easy deployment:

```bash
cd backend

# Copy and configure environment
cp .env.docker.example .env.docker
# Edit .env.docker with your settings

# Start with Docker Compose
docker-compose up -d
```

See [backend/README.md](backend/README.md) for detailed deployment instructions, including Docker setup, environment configuration, and troubleshooting.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

See [frontend/README.md](frontend/README.md) for frontend-specific documentation.

## Documentation

- [Backend README](backend/README.md) - API documentation, Docker deployment, authentication
- [Frontend README](frontend/README.md) - PWA setup, offline functionality
- [Technical Specification](thought-journal-pwa-spec.md) - Complete system design and architecture
- [Coding Agent Prompts](coding-agent-prompts.md) - Implementation plan breakdown

## Features

- **Conversational Journaling** - Chat with LLM to capture thoughts naturally
- **Google OAuth Authentication** - Secure login with your Google account
- **Offline-First PWA** - Works without internet connection
- **Docker Deployment** - Easy containerized deployment on cognito-network
- **Goal Tracking** - Set and track personal objectives
- **Version History** - Track changes to journal entries over time

## Tech Stack

- **Backend**: FastAPI, DuckDB, Python 3.11+
- **Frontend**: SvelteKit, TypeScript, IndexedDB
- **LLM**: Gemini API, Ollama (optional)
- **Deployment**: Docker, Docker Compose
- **Authentication**: Google OAuth 2.0, JWT

## License

Private project - All rights reserved

"""
Cognito PWA FastAPI Application.

Main entry point for the backend API server.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import get_connection, init_schema
from app.routers.auth import router as auth_router
from app.routers.entries import router as entries_router
from app.routers.goals import router as goals_router
from app.routers.chat import router as chat_router
from app.routers.sync import router as sync_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan handler.

    Initializes the database schema on startup.
    """
    # Startup: Initialize database schema
    conn = get_connection()
    try:
        init_schema(conn)
    finally:
        conn.close()

    yield

    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="Cognito API",
    description="Backend API for Cognito PWA - Conversational Thought Journaling",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
allowed_origins = [settings.frontend_url]
if settings.frontend_url != "http://localhost:5173":
    # Also allow localhost for development
    allowed_origins.append("http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(entries_router)
app.include_router(goals_router)
app.include_router(chat_router)
app.include_router(sync_router)



@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns a simple status to verify the API is running.
    """
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict:
    """
    Root endpoint.

    Returns basic API information.
    """
    return {
        "name": "Cognito API",
        "version": "0.1.0",
        "docs": "/docs",
    }

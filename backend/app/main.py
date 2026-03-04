"""
Cognito Task Agent — FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import get_connection, init_schema
from app.routers.auth import router as auth_router
from app.routers.ingest import router as ingest_router
from app.routers.proposals import router as proposals_router
from app.routers.projects import router as projects_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise DuckDB schema on startup."""
    conn = get_connection()
    try:
        init_schema(conn)
    finally:
        conn.close()
    yield


app = FastAPI(
    title="Cognito Task Agent API",
    description="AI integration layer for Vikunja — turns messy inputs into clean tasks.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
allowed_origins = [settings.frontend_url]
if "localhost" not in settings.frontend_url:
    allowed_origins.append("http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(ingest_router)
app.include_router(proposals_router)
app.include_router(projects_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root() -> dict:
    return {"name": "Cognito Task Agent API", "version": "1.0.0", "docs": "/docs"}

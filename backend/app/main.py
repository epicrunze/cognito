"""
Cognito Task Agent — FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import get_connection, init_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.config import router as config_router
from app.routers.ingest import router as ingest_router
from app.routers.labels import router as labels_router
from app.routers.proposals import router as proposals_router
from app.routers.projects import router as projects_router
from app.routers.models import router as models_router
from app.routers.revisions import router as revisions_router
from app.routers.tasks import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise SQLite schema on startup."""
    conn = get_connection()
    try:
        init_schema(conn)
    finally:
        conn.close()
    logger.info("Backend started — FRONTEND_URL=%r VIKUNJA_URL=%r GEMINI_MODEL=%r",
        settings.frontend_url, settings.vikunja_url, settings.gemini_model)
    yield


app = FastAPI(
    title="Cognito Task Agent API",
    description="AI integration layer for Vikunja — turns messy inputs into clean tasks.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
allowed_origins = [settings.frontend_url.rstrip("/")]
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
app.include_router(chat_router)
app.include_router(config_router)
app.include_router(ingest_router)
app.include_router(labels_router)
app.include_router(models_router)
app.include_router(proposals_router)
app.include_router(projects_router)
app.include_router(revisions_router)
app.include_router(tasks_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "version": "1.0.0", "cors_origins": allowed_origins}


@app.get("/")
async def root() -> dict:
    return {"name": "Cognito Task Agent API", "version": "1.0.0", "docs": "/docs"}

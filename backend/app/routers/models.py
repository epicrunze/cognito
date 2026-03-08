"""
Model registry endpoint — serves available models to the frontend.
"""

from fastapi import APIRouter

from app.models_registry import AVAILABLE_MODELS

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models")
async def list_models():
    return AVAILABLE_MODELS

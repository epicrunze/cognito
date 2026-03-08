"""
Centralized model registry.

Single source of truth for all available LLM models.
The frontend fetches this list via /api/models instead of hardcoding.
"""

AVAILABLE_MODELS = [
    {
        "value": "gemini-flash",
        "model_id": "gemini-3.1-flash-lite-preview",
        "label": "Gemini 3.1 Flash Lite",
        "description": "Fast, good for most tasks",
        "provider": "gemini",
    },
    {
        "value": "gemini-3",
        "model_id": "gemini-3-flash-preview",
        "label": "Gemini 3.0",
        "description": "Higher quality, slower",
        "provider": "gemini",
    },
    {
        "value": "ollama-qwen",
        "model_id": "qwen3:4b",
        "label": "Qwen 3.x (Local)",
        "description": "Private, runs on your machine",
        "provider": "ollama",
    },
    {
        "value": "ollama-llama",
        "model_id": "ollama-llama",
        "label": "Llama 3.3 (Local)",
        "description": "Private, larger model",
        "provider": "ollama",
    },
]

DEFAULT_MODEL = "gemini-flash"


def get_model_id(value: str) -> str:
    """Map frontend value to actual model ID."""
    for m in AVAILABLE_MODELS:
        if m["value"] == value:
            return m["model_id"]
    return value

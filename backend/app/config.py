"""
Configuration management using Pydantic Settings.

Loads all settings from environment variables (or .env file).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./data/agent.db"

    # ── JWT Authentication ────────────────────────────────────────────────────
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_expiry_hours: int = 168  # 7 days

    # ── Google OAuth ──────────────────────────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""

    # ── User Authorization ────────────────────────────────────────────────────
    allowed_email: str = ""

    # ── Cookie Settings ───────────────────────────────────────────────────────
    cookie_secure: bool = True
    cookie_domain: str = ""
    cookie_samesite: str = "lax"

    # ── URLs ──────────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # ── Vikunja ───────────────────────────────────────────────────────────────
    vikunja_url: str = "http://localhost:3456"
    vikunja_api_token: str = ""

    # ── LLM — Phase 1: Gemini only ────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ── LLM — Phase 2: Ollama ─────────────────────────────────────────────────
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"

    # ── Google Calendar — Phase 3 ─────────────────────────────────────────────
    gcal_calendar_id: str = "primary"

    def get_database_path(self) -> str:
        """Extract the file path from the database URL."""
        if self.database_url.startswith("sqlite:///"):
            return self.database_url[len("sqlite:///"):]
        return self.database_url


# Global settings instance
settings = Settings()

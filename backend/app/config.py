"""
Configuration management using Pydantic Settings.

Loads configuration from environment variables with validation and defaults.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "duckdb:///./data/journal.duckdb"

    # JWT Authentication
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_expiry_hours: int = 168  # 7 days for offline-first support

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Cookie Settings
    cookie_secure: bool = True  # Set to False for localhost development
    cookie_domain: str = ""  # Set to ".epicrunze.com" for subdomain cookie sharing
    cookie_samesite: str = "lax"  # Use "none" for cross-subdomain requests

    # User Authorization
    allowed_email: str = ""

    # Frontend URL for CORS and redirects
    frontend_url: str = "http://localhost:5173"

    # Backend URL for OAuth callback (Google redirects here, not frontend)
    backend_url: str = "http://localhost:8000"

    # LLM Configuration
    gemini_api_key: str = ""
    ollama_url: str = "http://localhost:11434"

    def get_database_path(self) -> str:
        """Extract the file path from the database URL."""
        if self.database_url.startswith("duckdb:///"):
            return self.database_url.replace("duckdb:///", "")
        return self.database_url


# Global settings instance
settings = Settings()

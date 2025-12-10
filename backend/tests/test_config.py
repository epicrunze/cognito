"""
Tests for configuration loading.
"""

import os
import pytest


class TestConfigDefaults:
    """Tests for default configuration values."""

    def test_config_defaults(self) -> None:
        """Verify default values load correctly."""
        # Import fresh to get defaults
        from app.config import Settings
        
        settings = Settings(
            _env_file=None,  # Don't load .env file
        )
        
        assert settings.database_url == "duckdb:///./data/journal.duckdb"
        assert settings.jwt_expiry_hours == 24
        assert settings.frontend_url == "http://localhost:5173"
        assert settings.ollama_url == "http://localhost:11434"

    def test_get_database_path(self) -> None:
        """Verify database path extraction works."""
        from app.config import Settings
        
        settings = Settings(
            database_url="duckdb:///./data/test.duckdb",
            _env_file=None,
        )
        
        assert settings.get_database_path() == "./data/test.duckdb"


class TestConfigFromEnv:
    """Tests for configuration from environment variables."""

    def test_config_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify environment variable override works."""
        # Set environment variables
        monkeypatch.setenv("DATABASE_URL", "duckdb:///./test/custom.duckdb")
        monkeypatch.setenv("JWT_SECRET", "test-secret-key")
        monkeypatch.setenv("JWT_EXPIRY_HOURS", "48")
        monkeypatch.setenv("ALLOWED_EMAIL", "user@example.com")
        monkeypatch.setenv("FRONTEND_URL", "https://myapp.com")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        monkeypatch.setenv("OLLAMA_URL", "http://custom-ollama:11434")
        
        # Import fresh settings
        from app.config import Settings
        settings = Settings(_env_file=None)
        
        assert settings.database_url == "duckdb:///./test/custom.duckdb"
        assert settings.jwt_secret == "test-secret-key"
        assert settings.jwt_expiry_hours == 48
        assert settings.allowed_email == "user@example.com"
        assert settings.frontend_url == "https://myapp.com"
        assert settings.gemini_api_key == "test-gemini-key"
        assert settings.ollama_url == "http://custom-ollama:11434"

    def test_jwt_expiry_as_integer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify JWT expiry is properly converted to integer."""
        monkeypatch.setenv("JWT_EXPIRY_HOURS", "12")
        
        from app.config import Settings
        settings = Settings(_env_file=None)
        
        assert isinstance(settings.jwt_expiry_hours, int)
        assert settings.jwt_expiry_hours == 12


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_extra_fields_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify extra environment variables don't cause errors."""
        monkeypatch.setenv("UNKNOWN_CONFIG_OPTION", "some-value")
        
        from app.config import Settings
        
        # Should not raise an error
        settings = Settings(_env_file=None)
        assert settings is not None

    def test_database_path_variations(self) -> None:
        """Verify different database URL formats are handled."""
        from app.config import Settings
        
        # Standard format
        settings1 = Settings(
            database_url="duckdb:///./data/journal.duckdb",
            _env_file=None,
        )
        assert settings1.get_database_path() == "./data/journal.duckdb"
        
        # Absolute path
        settings2 = Settings(
            database_url="duckdb:////var/data/journal.duckdb",
            _env_file=None,
        )
        assert settings2.get_database_path() == "/var/data/journal.duckdb"
        
        # Plain path (fallback)
        settings3 = Settings(
            database_url="/tmp/test.duckdb",
            _env_file=None,
        )
        assert settings3.get_database_path() == "/tmp/test.duckdb"

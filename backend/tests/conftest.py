"""
Pytest configuration and fixtures for test suite.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
import duckdb


@pytest.fixture
def test_db_path() -> Generator[str, None, None]:
    """
    Provide a temporary database path for testing.
    
    Creates a unique path and ensures cleanup after test.
    Note: We don't create the file - DuckDB needs to create it fresh.
    """
    temp_path = tempfile.mktemp(suffix=".duckdb")
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)
    # DuckDB creates .wal files
    wal_path = temp_path + ".wal"
    if os.path.exists(wal_path):
        os.unlink(wal_path)


@pytest.fixture
def test_db_connection(test_db_path: str) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Provide a DuckDB connection to a temporary test database.
    """
    conn = duckdb.connect(test_db_path)
    yield conn
    conn.close()


@pytest.fixture
def env_override(monkeypatch: pytest.MonkeyPatch):
    """
    Fixture to help override environment variables for config testing.
    """
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key.upper(), str(value))
    return _set_env

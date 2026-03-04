"""Shared fixtures for the test suite."""

from contextlib import contextmanager

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import init_schema
from app.main import app
from app.models.user import User


@pytest.fixture
def in_memory_db():
    """Fresh in-memory DuckDB with schema initialised."""
    conn = duckdb.connect(":memory:")
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def mock_user() -> User:
    return User(email="test@example.com", name="Test User")


def make_mock_db(conn):
    """Return a drop-in replacement for get_db() that always yields *conn*."""

    @contextmanager
    def _mock(database_path=None):
        yield conn

    return _mock

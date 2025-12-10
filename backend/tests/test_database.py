"""
Tests for database connection and schema management.
"""

import duckdb
import pytest

from app.database import get_connection, init_schema, get_tables, get_db


class TestDatabaseConnection:
    """Tests for database connection handling."""

    def test_database_connection(self, test_db_path: str) -> None:
        """Verify DuckDB connection works correctly."""
        conn = get_connection(test_db_path)
        assert conn is not None
        
        # Verify we can execute a simple query
        result = conn.execute("SELECT 1 as test").fetchone()
        assert result == (1,)
        
        conn.close()

    def test_connection_context_manager(self, test_db_path: str) -> None:
        """Verify the context manager properly handles connections."""
        with get_db(test_db_path) as conn:
            result = conn.execute("SELECT 42 as answer").fetchone()
            assert result == (42,)
        
        # Connection should be closed after context manager exits
        # Creating a new connection should work
        with get_db(test_db_path) as conn2:
            result = conn2.execute("SELECT 1").fetchone()
            assert result == (1,)


class TestSchemaCreation:
    """Tests for database schema initialization."""

    def test_schema_creation(self, test_db_path: str) -> None:
        """Verify all tables are created correctly."""
        conn = get_connection(test_db_path)
        init_schema(conn)
        
        tables = get_tables(conn)
        
        expected_tables = [
            "users",
            "entries",
            "entry_versions",
            "goals",
            "proposals",
            "code_specs",
            "scheduled_notifications",
            "notification_config",
            "push_subscriptions",
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table '{table}' not found in database"
        
        conn.close()

    def test_schema_idempotent(self, test_db_path: str) -> None:
        """Verify running init_schema multiple times doesn't error."""
        conn = get_connection(test_db_path)
        
        # Run schema init twice
        init_schema(conn)
        tables_after_first = get_tables(conn)
        
        init_schema(conn)
        tables_after_second = get_tables(conn)
        
        # Should have same tables both times
        assert set(tables_after_first) == set(tables_after_second)
        assert len(tables_after_first) == 9
        
        conn.close()

    def test_users_table_structure(self, test_db_path: str) -> None:
        """Verify users table has correct columns."""
        conn = get_connection(test_db_path)
        init_schema(conn)
        
        # Get column info for users table
        result = conn.execute("DESCRIBE users").fetchall()
        columns = {row[0]: row[1] for row in result}
        
        assert "id" in columns
        assert "email" in columns
        assert "name" in columns
        assert "picture" in columns
        assert "created_at" in columns
        assert "last_login_at" in columns
        
        conn.close()

    def test_entries_table_structure(self, test_db_path: str) -> None:
        """Verify entries table has correct columns."""
        conn = get_connection(test_db_path)
        init_schema(conn)
        
        result = conn.execute("DESCRIBE entries").fetchall()
        columns = {row[0]: row[1] for row in result}
        
        assert "id" in columns
        assert "user_id" in columns
        assert "date" in columns
        assert "conversations" in columns
        assert "refined_output" in columns
        assert "relevance_score" in columns
        assert "status" in columns
        assert "version" in columns
        
        conn.close()

    def test_insert_and_query_user(self, test_db_path: str) -> None:
        """Verify we can insert and query data."""
        conn = get_connection(test_db_path)
        init_schema(conn)
        
        # Insert a user
        conn.execute("""
            INSERT INTO users (email, name)
            VALUES ('test@example.com', 'Test User')
        """)
        
        # Query the user
        result = conn.execute(
            "SELECT email, name FROM users WHERE email = 'test@example.com'"
        ).fetchone()
        
        assert result is not None
        assert result[0] == "test@example.com"
        assert result[1] == "Test User"
        
        conn.close()

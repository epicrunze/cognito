"""Schema tests for the OKF knowledge layer tables."""

import sqlite3

from app.database import init_schema, get_tables


def _db():
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(conn)
    return conn


def test_knowledge_tables_created():
    conn = _db()
    tables = get_tables(conn)
    for t in ("knowledge_concepts", "concepts", "concept_links",
              "concepts_fts", "knowledge_meta"):
        assert t in tables, f"missing table {t}"


def test_concepts_fts_is_searchable():
    conn = _db()
    conn.execute(
        "INSERT INTO concepts (concept_id, source, type, title, body) "
        "VALUES ('knowledge/x', 'native', 'Note', 'Hello', 'world body')"
    )
    conn.execute(
        "INSERT INTO concepts_fts (concept_id, title, description, tags, body) "
        "VALUES ('knowledge/x', 'Hello', '', '', 'world body')"
    )
    rows = conn.execute(
        "SELECT concept_id FROM concepts_fts WHERE concepts_fts MATCH 'world'"
    ).fetchall()
    assert rows == [("knowledge/x",)]


def test_native_type_required():
    conn = _db()
    try:
        conn.execute(
            "INSERT INTO knowledge_concepts (concept_id, type) VALUES ('knowledge/y', '')"
        )
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised, "empty type should violate CHECK"

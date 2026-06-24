import json
import sqlite3

import pytest

from app.database import init_schema
from app.services.knowledge.adapters.base import Concept, FieldCaps
from app.services.knowledge.adapters.native import NativeConceptAdapter


def test_concept_defaults():
    c = Concept(concept_id="knowledge/x", type="Note", source="native")
    assert c.tags == []
    assert c.frontmatter == {}
    assert c.body == ""


def test_fieldcaps_shape():
    fc = FieldCaps(writable={"title": "native"}, readonly=["concept_id"])
    assert fc.writable["title"] == "native"
    assert "concept_id" in fc.readonly


def _db():
    conn = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
    init_schema(conn)
    return conn


async def test_native_adapter_lists_and_gets():
    conn = _db()
    conn.execute(
        "INSERT INTO knowledge_concepts (concept_id, type, title, description, tags, frontmatter, body) "
        "VALUES (?,?,?,?,?,?,?)",
        ("knowledge/auth", "Design Note", "Auth", "How auth works",
         json.dumps(["security"]), json.dumps({"type": "Design Note", "owner": "me"}),
         "Body links to [task](/tasks/3.md)."),
    )
    adapter = NativeConceptAdapter(conn)
    listed = await adapter.list_concepts()
    assert len(listed) == 1
    c = listed[0]
    assert c.concept_id == "knowledge/auth"
    assert c.source == "native"
    assert c.tags == ["security"]
    assert c.frontmatter["owner"] == "me"

    got = await adapter.get_concept("knowledge/auth")
    assert got.title == "Auth"
    assert await adapter.get_concept("knowledge/missing") is None
    assert adapter.owns("knowledge/auth") is True
    assert adapter.owns("tasks/3") is False

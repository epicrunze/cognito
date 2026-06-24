import json
import sqlite3
from unittest.mock import AsyncMock

import pytest

from app.database import init_schema
from app.services.knowledge.adapters.base import Concept, FieldCaps
from app.services.knowledge.adapters.native import NativeConceptAdapter
from app.services.knowledge.adapters.vikunja_tasks import VikunjaTaskAdapter
from app.services.knowledge.adapters.vikunja_projects import VikunjaProjectAdapter


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


def _task(**over):
    base = {
        "id": 42, "title": "Ship it", "description": "Do the thing",
        "done": False, "priority": 3, "due_date": "2026-07-01T00:00:00Z",
        "project_id": 7, "labels": [{"title": "urgent"}], "percent_done": 0.5,
        "identifier": "PRJ-42", "updated": "2026-06-18T10:00:00Z",
    }
    base.update(over)
    return base


async def test_vikunja_task_adapter_projects_task():
    vik = AsyncMock()
    vik.list_tasks.return_value = [_task()]
    adapter = VikunjaTaskAdapter(vik)

    concepts = await adapter.list_concepts()
    assert len(concepts) == 1
    c = concepts[0]
    assert c.concept_id == "tasks/42"
    assert c.type == "Task"
    assert c.source == "vikunja"
    assert c.title == "Ship it"
    assert c.tags == ["urgent"]
    assert "/projects/7.md" in c.body          # parent link present
    assert "Do the thing" in c.body
    assert adapter.owns("tasks/42") is True
    assert adapter.owns("projects/7") is False

    caps = adapter.field_capabilities(c)
    assert "title" in caps.writable
    assert "identifier" in caps.readonly
    assert "percent_done" in caps.readonly


async def test_vikunja_task_adapter_get_single():
    vik = AsyncMock()
    vik.get_task.return_value = _task(id=9, title="One")
    adapter = VikunjaTaskAdapter(vik)
    c = await adapter.get_concept("tasks/9")
    assert c.title == "One"
    vik.get_task.assert_awaited_once_with(9)
    assert await adapter.get_concept("projects/1") is None


async def test_vikunja_project_adapter():
    vik = AsyncMock()
    vik.list_projects.return_value = [
        {"id": 7, "title": "Roadmap", "description": "Big plans"}
    ]
    adapter = VikunjaProjectAdapter(vik)
    concepts = await adapter.list_concepts()
    assert len(concepts) == 1
    c = concepts[0]
    assert c.concept_id == "projects/7"
    assert c.type == "Project"
    assert c.title == "Roadmap"
    assert "/projects/7/notes.md" in c.body     # links to its notes concept
    assert adapter.owns("projects/7") is True
    assert adapter.owns("projects/7/notes") is False   # notes owned by NotesAdapter

    vik.get_project.return_value = {"id": 3, "title": "Solo", "description": ""}
    one = await adapter.get_concept("projects/3")
    assert one.title == "Solo"

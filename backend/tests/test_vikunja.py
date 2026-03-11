"""Tests for VikunjaClient — httpx calls intercepted by respx."""

import json

import httpx
import pytest
import respx

from app.services.vikunja import VikunjaClient, VikunjaError

BASE_URL = "http://vikunja.test"
TOKEN = "test-token"


@pytest.fixture
def vc():
    return VikunjaClient(base_url=BASE_URL, api_token=TOKEN)


# ── list_projects ─────────────────────────────────────────────────────────────

@respx.mock
async def test_list_projects_success(vc):
    respx.get(f"{BASE_URL}/api/v1/projects").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "title": "PhD Research"}])
    )
    result = await vc.list_projects()
    assert result == [{"id": 1, "title": "PhD Research"}]


@respx.mock
async def test_list_projects_error(vc):
    respx.get(f"{BASE_URL}/api/v1/projects").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    with pytest.raises(VikunjaError):
        await vc.list_projects()


@respx.mock
async def test_list_projects_empty_on_non_list(vc):
    """Vikunja occasionally returns a dict on edge-cases — normalise to []."""
    respx.get(f"{BASE_URL}/api/v1/projects").mock(
        return_value=httpx.Response(200, json={})
    )
    result = await vc.list_projects()
    assert result == []


# ── create_task ───────────────────────────────────────────────────────────────

@respx.mock
async def test_create_task_success(vc):
    respx.put(f"{BASE_URL}/api/v1/projects/1/tasks").mock(
        return_value=httpx.Response(201, json={"id": 42, "title": "Write paper"})
    )
    result = await vc.create_task(
        project_id=1,
        title="Write paper",
        priority=5,
        due_date="2026-03-10",
    )
    assert result["id"] == 42

    # Verify request body
    body = json.loads(respx.calls.last.request.content)
    assert body["title"] == "Write paper"
    assert body["priority"] == 5
    assert body["due_date"] == "2026-03-10T00:00:00Z"


@respx.mock
async def test_create_task_no_labels(vc):
    """labels=None → only one API call (no label endpoint hit)."""
    respx.put(f"{BASE_URL}/api/v1/projects/1/tasks").mock(
        return_value=httpx.Response(201, json={"id": 1, "title": "T"})
    )
    await vc.create_task(project_id=1, title="T", labels=None)
    assert respx.calls.call_count == 1


@respx.mock
async def test_create_task_error(vc):
    respx.put(f"{BASE_URL}/api/v1/projects/1/tasks").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    with pytest.raises(VikunjaError):
        await vc.create_task(project_id=1, title="T")


# ── get_task ──────────────────────────────────────────────────────────────────

@respx.mock
async def test_get_task_success(vc):
    respx.get(f"{BASE_URL}/api/v1/tasks/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "title": "My task"})
    )
    result = await vc.get_task(42)
    assert result["id"] == 42
    assert result["title"] == "My task"


@respx.mock
async def test_get_task_error(vc):
    respx.get(f"{BASE_URL}/api/v1/tasks/42").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    with pytest.raises(VikunjaError):
        await vc.get_task(42)


# ── search_tasks ──────────────────────────────────────────────────────────────

@respx.mock
async def test_search_tasks_success(vc):
    tasks = [{"id": i, "title": f"Task {i}"} for i in range(3)]
    respx.get(f"{BASE_URL}/api/v1/tasks").mock(
        return_value=httpx.Response(200, json=tasks)
    )
    result = await vc.search_tasks("Task")
    assert len(result) == 3
    assert result[0]["id"] == 0


# ── create_project ────────────────────────────────────────────────────────────

@respx.mock
async def test_create_project_success(vc):
    respx.put(f"{BASE_URL}/api/v1/projects").mock(
        return_value=httpx.Response(200, json={"id": 10, "title": "New Project", "description": ""})
    )
    result = await vc.create_project("New Project")
    assert result["id"] == 10
    assert result["title"] == "New Project"

    body = json.loads(respx.calls.last.request.content)
    assert body["title"] == "New Project"


@respx.mock
async def test_create_project_error(vc):
    respx.put(f"{BASE_URL}/api/v1/projects").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    with pytest.raises(VikunjaError):
        await vc.create_project("Bad Project")


# ── get_label ──────────────────────────────────────────────────────────────────

@respx.mock
async def test_get_label_normalizes_hex(vc):
    """get_label adds '#' prefix to bare hex_color from Vikunja."""
    respx.get(f"{BASE_URL}/api/v1/labels/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "title": "Bug", "hex_color": "ff0000"})
    )
    result = await vc.get_label(5)
    assert result["id"] == 5
    assert result["hex_color"] == "#ff0000"


@respx.mock
async def test_get_label_error(vc):
    respx.get(f"{BASE_URL}/api/v1/labels/999").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    with pytest.raises(VikunjaError):
        await vc.get_label(999)


# ── list_labels ──────────────────────────────────────────────────────────────

@respx.mock
async def test_list_labels_normalizes_hex(vc):
    """list_labels adds '#' prefix to all bare hex_color values."""
    respx.get(f"{BASE_URL}/api/v1/labels").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "title": "Bug", "hex_color": "ff0000"},
            {"id": 2, "title": "Feature", "hex_color": "00ff00"},
            {"id": 3, "title": "NoColor", "hex_color": ""},
        ])
    )
    result = await vc.list_labels()
    assert result[0]["hex_color"] == "#ff0000"
    assert result[1]["hex_color"] == "#00ff00"
    assert result[2]["hex_color"] == ""  # empty stays empty


# ── create_label ─────────────────────────────────────────────────────────────

@respx.mock
async def test_create_label_strips_hash(vc):
    """create_label strips '#' from hex_color before sending to Vikunja."""
    respx.put(f"{BASE_URL}/api/v1/labels").mock(
        return_value=httpx.Response(200, json={"id": 10, "title": "New", "hex_color": "ff5500"})
    )
    result = await vc.create_label({"title": "New", "hex_color": "#ff5500"})
    # Sent without '#'
    body = json.loads(respx.calls.last.request.content)
    assert body["hex_color"] == "ff5500"
    # Returned with '#' (normalized for frontend)
    assert result["hex_color"] == "#ff5500"


# ── update_label ─────────────────────────────────────────────────────────────

@respx.mock
async def test_update_label_uses_post(vc):
    """update_label uses POST (not PUT), strips '#', and normalizes response."""
    current = {"id": 5, "title": "Bug", "hex_color": "ff0000", "description": "", "created_by": {"id": 1}}
    updated = {**current, "hex_color": "00ff00"}
    respx.get(f"{BASE_URL}/api/v1/labels/5").mock(
        return_value=httpx.Response(200, json=current)
    )
    respx.post(f"{BASE_URL}/api/v1/labels/5").mock(
        return_value=httpx.Response(200, json=updated)
    )
    result = await vc.update_label(5, {"hex_color": "#00ff00"})
    # Response normalized with '#' for frontend
    assert result["hex_color"] == "#00ff00"

    # Verify POST was used (not PUT) and '#' was stripped
    body = json.loads(respx.calls.last.request.content)
    assert body["hex_color"] == "00ff00"


@respx.mock
async def test_search_tasks_error(vc):
    """500 from Vikunja → raises VikunjaError."""
    respx.get(f"{BASE_URL}/api/v1/tasks").mock(
        return_value=httpx.Response(500, text="Error")
    )
    with pytest.raises(VikunjaError):
        await vc.search_tasks("query")

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


@respx.mock
async def test_search_tasks_error(vc):
    """500 from Vikunja → raises VikunjaError."""
    respx.get(f"{BASE_URL}/api/v1/tasks").mock(
        return_value=httpx.Response(500, text="Error")
    )
    with pytest.raises(VikunjaError):
        await vc.search_tasks("query")

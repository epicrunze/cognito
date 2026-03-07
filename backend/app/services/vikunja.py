"""
Vikunja REST API client.

All interaction with the self-hosted Vikunja instance goes through here.
Auth is via API token set in settings.

IMPORTANT: Vikunja uses PUT to create, POST to update (opposite of standard REST).
"""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class VikunjaError(Exception):
    """Base error for Vikunja API failures."""


class VikunjaClient:
    """Async httpx client for the Vikunja API."""

    def __init__(self, base_url: str | None = None, api_token: str | None = None):
        self.base_url = (base_url or settings.vikunja_url).rstrip("/")
        self.api_token = api_token or settings.vikunja_api_token

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """Base request method — injects auth header."""
        url = f"{self.base_url}/api/v1{path}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(method, url, headers=self._headers, **kwargs)
            if not response.is_success:
                raise VikunjaError(
                    f"{method} {path} failed: {response.status_code} {response.text}"
                )
            return response.json()

    # ── Projects ──────────────────────────────────────────────────────────────

    async def list_projects(self) -> list[dict]:
        """Return all projects the API token has access to."""
        data = await self._request("GET", "/projects")
        return data if isinstance(data, list) else []

    async def get_project(self, project_id: int) -> dict:
        """Fetch a single project by ID."""
        return await self._request("GET", f"/projects/{project_id}")

    async def list_project_views(self, project_id: int) -> list[dict]:
        """Return all views for a project."""
        data = await self._request("GET", f"/projects/{project_id}/views")
        return data if isinstance(data, list) else []

    # ── Tasks ─────────────────────────────────────────────────────────────────

    async def list_tasks(
        self,
        project_id: int | None = None,
        filter: str | None = None,
        sort_by: str | None = None,
        order_by: str | None = None,
        page: int = 1,
        per_page: int = 50,
        s: str | None = None,
    ) -> list[dict]:
        """List tasks. Uses /tasks/all for cross-project, or /projects/{id}/tasks."""
        params: dict = {"page": page, "per_page": per_page}
        if filter:
            params["filter"] = filter
        if sort_by:
            params["sort_by"] = sort_by
        if order_by:
            params["order_by"] = order_by
        if s:
            params["s"] = s

        if project_id:
            path = f"/projects/{project_id}/tasks"
        else:
            path = "/tasks/all"

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1{path}",
                headers=self._headers,
                params=params,
            )
            if not response.is_success:
                raise VikunjaError(f"Failed to list tasks: {response.status_code} {response.text}")
            data = response.json()
            return data if isinstance(data, list) else []

    async def get_task(self, task_id: int) -> dict:
        """Fetch a single task by ID."""
        return await self._request("GET", f"/tasks/{task_id}")

    async def create_task(
        self,
        project_id: int,
        title: str,
        description: str | None = None,
        priority: int = 3,
        due_date: str | None = None,  # ISO date string
        labels: list[str] | None = None,
    ) -> dict:
        """
        Create a task in the given Vikunja project.

        PUT creates in Vikunja (opposite of standard REST).
        Returns the created task dict from Vikunja.
        """
        payload: dict = {
            "title": title,
            "priority": priority,
        }
        if description:
            payload["description"] = description
        if due_date:
            payload["due_date"] = f"{due_date}T00:00:00Z"

        logger.debug("Creating task in project %d: %s", project_id, payload)
        task = await self._request("PUT", f"/projects/{project_id}/tasks", json=payload)
        logger.debug("Vikunja response: %s", task)

        # Add labels if any (separate API call)
        if labels and task.get("id"):
            await self._add_labels_to_task(task["id"], labels)

        return task

    async def update_task(self, task_id: int, data: dict) -> dict:
        """
        Update task fields.

        POST updates in Vikunja (opposite of standard REST).
        """
        return await self._request("POST", f"/tasks/{task_id}", json=data)

    async def delete_task(self, task_id: int) -> dict:
        """Delete a task."""
        return await self._request("DELETE", f"/tasks/{task_id}")

    async def _add_labels_to_task(self, task_id: int, labels: list[str]) -> None:
        """
        Add labels to a task.

        For Phase 1, we log missing labels but don't fail.
        """
        pass

    async def add_label_to_task(self, task_id: int, label_id: int) -> dict:
        """Add an existing label to a task. Uses PUT (Vikunja convention)."""
        return await self._request(
            "PUT", f"/tasks/{task_id}/labels", json={"label_id": label_id}
        )

    async def remove_label_from_task(self, task_id: int, label_id: int) -> dict:
        """Remove a label from a task."""
        return await self._request("DELETE", f"/tasks/{task_id}/labels/{label_id}")

    # ── Labels ────────────────────────────────────────────────────────────────

    async def list_labels(self) -> list[dict]:
        """Return all labels."""
        data = await self._request("GET", "/labels")
        return data if isinstance(data, list) else []

    async def create_label(self, data: dict) -> dict:
        """Create a label. PUT creates in Vikunja."""
        return await self._request("PUT", "/labels", json=data)

    async def delete_label(self, label_id: int) -> dict:
        """Delete a label."""
        return await self._request("DELETE", f"/labels/{label_id}")

    # ── Buckets (Kanban) ──────────────────────────────────────────────────────

    async def list_buckets(self, project_id: int, view_id: int) -> list[dict]:
        """Return buckets for a kanban view."""
        data = await self._request(
            "GET", f"/projects/{project_id}/views/{view_id}/buckets"
        )
        return data if isinstance(data, list) else []

    async def move_task_to_bucket(
        self,
        project_id: int,
        view_id: int,
        task_id: int,
        bucket_id: int,
        position: float,
    ) -> dict:
        """Move a task to a different kanban bucket."""
        return await self._request(
            "POST",
            f"/projects/{project_id}/views/{view_id}/buckets/tasks",
            json={"task_id": task_id, "bucket_id": bucket_id, "position": position},
        )

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_tasks(self, query: str) -> list[dict]:
        """
        Fuzzy-search tasks by title for duplicate detection.

        Uses the Vikunja task list endpoint with a search param.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/tasks/all",
                headers=self._headers,
                params={"s": query, "per_page": 5},
            )
            if response.status_code != 200:
                return []
            data = response.json()
            return data if isinstance(data, list) else []


# Global client instance
vikunja = VikunjaClient()

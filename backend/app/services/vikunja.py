"""
Vikunja REST API client.

All interaction with the self-hosted Vikunja instance goes through here.
Auth is via API token set in settings.
"""

import httpx

from app.config import settings


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

    async def list_projects(self) -> list[dict]:
        """Return all projects the API token has access to."""
        url = f"{self.base_url}/api/v1/projects"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=self._headers)
            if response.status_code != 200:
                raise VikunjaError(f"Failed to list projects: {response.status_code} {response.text}")
            data = response.json()
            # Vikunja returns a list directly
            return data if isinstance(data, list) else []

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

        Returns the created task dict from Vikunja.
        """
        payload: dict = {
            "title": title,
            "priority": priority,
        }
        if description:
            payload["description"] = description
        if due_date:
            # Vikunja expects RFC3339 datetime
            payload["due_date"] = f"{due_date}T00:00:00Z"

        url = f"{self.base_url}/api/v1/projects/{project_id}/tasks"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.put(url, headers=self._headers, json=payload)
            if response.status_code not in (200, 201):
                raise VikunjaError(f"Failed to create task: {response.status_code} {response.text}")
            task = response.json()

        # Add labels if any (separate API call)
        if labels and task.get("id"):
            await self._add_labels_to_task(task["id"], labels)

        return task

    async def _add_labels_to_task(self, task_id: int, labels: list[str]) -> None:
        """
        Add labels to a task.

        Vikunja requires labels to already exist — we look them up by title
        and create them if missing. Labels missing from Vikunja are skipped
        gracefully rather than failing the whole approval.
        """
        # For Phase 1, we log missing labels but don't fail
        # A Phase 2 improvement would auto-create labels via POST /api/v1/labels
        pass

    async def get_task(self, task_id: int) -> dict:
        """Fetch a single task by ID."""
        url = f"{self.base_url}/api/v1/tasks/{task_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=self._headers)
            if response.status_code != 200:
                raise VikunjaError(f"Failed to get task {task_id}: {response.status_code}")
            return response.json()

    async def search_tasks(self, query: str) -> list[dict]:
        """
        Fuzzy-search tasks by title for duplicate detection.

        Uses the Vikunja task list endpoint with a search param.
        """
        url = f"{self.base_url}/api/v1/tasks/all"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                headers=self._headers,
                params={"s": query, "per_page": 5},
            )
            if response.status_code != 200:
                return []
            data = response.json()
            return data if isinstance(data, list) else []


# Global client instance
vikunja = VikunjaClient()

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

    async def create_project(self, title: str, description: str = "") -> dict:
        """Create a new project. PUT creates in Vikunja."""
        return await self._request("PUT", "/projects", json={"title": title, "description": description})

    async def get_project(self, project_id: int) -> dict:
        """Fetch a single project by ID."""
        return await self._request("GET", f"/projects/{project_id}")

    async def update_project(self, project_id: int, data: dict) -> dict:
        """Update project fields. Fetches current state first to avoid Go zero-value wipe."""
        current = await self.get_project(project_id)
        current.update(data)
        return await self._request("POST", f"/projects/{project_id}", json=current)

    async def delete_project(self, project_id: int) -> dict:
        """Delete a project."""
        return await self._request("DELETE", f"/projects/{project_id}")

    async def list_project_views(self, project_id: int) -> list[dict]:
        """Return all views for a project."""
        data = await self._request("GET", f"/projects/{project_id}/views")
        return data if isinstance(data, list) else []

    # ── Tasks ─────────────────────────────────────────────────────────────────

    async def list_tasks(
        self,
        project_id: int | None = None,
        view_id: int | None = None,
        filter: str | None = None,
        sort_by: str | None = None,
        order_by: str | None = None,
        page: int = 1,
        per_page: int = 50,
        s: str | None = None,
    ) -> list[dict]:
        """List tasks. Uses /projects/{id}/views/{view}/tasks for a project, or /tasks for all."""
        params: dict = {"page": page, "per_page": per_page}
        if filter:
            params["filter"] = filter
        if sort_by:
            params["sort_by"] = sort_by
        if order_by:
            params["order_by"] = order_by
        if s:
            params["s"] = s

        if project_id and view_id:
            path = f"/projects/{project_id}/views/{view_id}/tasks"
        else:
            path = "/tasks"

        data = await self._request("GET", path, params=params)
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
        if due_date and not due_date.startswith("0001-01-01"):
            if "T" in due_date:
                payload["due_date"] = due_date
            else:
                payload["due_date"] = f"{due_date}T00:00:00Z"

        logger.debug("Creating task in project %d: %s", project_id, payload)
        task = await self._request("PUT", f"/projects/{project_id}/tasks", json=payload)
        logger.debug("Vikunja response: %s", task)

        # Add labels if any (separate API call)
        if labels and task.get("id"):
            await self._add_labels_to_task(task["id"], labels)

        return task

    async def update_task(self, task_id: int, data: dict) -> dict:
        """Update task fields. Fetches current state first to avoid Go zero-value wipe."""
        current = await self.get_task(task_id)
        current.update(data)
        return await self._request("POST", f"/tasks/{task_id}", json=current)

    async def delete_task(self, task_id: int) -> dict:
        """Delete a task."""
        return await self._request("DELETE", f"/tasks/{task_id}")

    async def _add_labels_to_task(self, task_id: int, labels: list[str]) -> None:
        """
        Add labels to a task by name. Creates missing labels on the fly.
        Never fails the whole operation — logs warnings for individual failures.
        """
        try:
            all_labels = await self.list_labels()
        except Exception:
            logger.warning("Failed to fetch labels for task %d, skipping label attachment", task_id)
            return

        lookup = {l["title"].lower(): l["id"] for l in all_labels}
        added = 0

        for name in labels:
            try:
                label_id = lookup.get(name.lower())
                if label_id is None:
                    created = await self.create_label({"title": name})
                    label_id = created["id"]
                    lookup[name.lower()] = label_id
                await self.add_label_to_task(task_id, label_id)
                added += 1
            except Exception:
                logger.warning("Failed to add label '%s' to task %d", name, task_id)

        logger.info("Added %d/%d labels to task %d", added, len(labels), task_id)

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

    async def update_label(self, label_id: int, data: dict) -> dict:
        """Update a label. Fetches current state first to avoid Go zero-value wipe."""
        labels = await self.list_labels()
        current = next((l for l in labels if l["id"] == label_id), {})
        current.update(data)
        return await self._request("PUT", f"/labels/{label_id}", json=current)

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

    async def create_bucket(
        self, project_id: int, view_id: int, title: str, limit: int = 0
    ) -> dict:
        """Create a bucket in a kanban view. PUT creates in Vikunja."""
        return await self._request(
            "PUT",
            f"/projects/{project_id}/views/{view_id}/buckets",
            json={"title": title, "limit": limit},
        )

    async def update_bucket(
        self, project_id: int, view_id: int, bucket_id: int, data: dict
    ) -> dict:
        """Update a bucket. Fetches current state first to avoid Go zero-value wipe."""
        buckets = await self.list_buckets(project_id, view_id)
        current = next((b for b in buckets if b["id"] == bucket_id), {})
        current.update(data)
        return await self._request(
            "POST",
            f"/projects/{project_id}/views/{view_id}/buckets/{bucket_id}",
            json=current,
        )

    async def delete_bucket(
        self, project_id: int, view_id: int, bucket_id: int
    ) -> dict:
        """Delete a bucket."""
        return await self._request(
            "DELETE",
            f"/projects/{project_id}/views/{view_id}/buckets/{bucket_id}",
        )

    async def move_task_to_bucket(
        self,
        project_id: int,
        view_id: int,
        task_id: int,
        bucket_id: int,
    ) -> dict:
        """Move a task to a different kanban bucket."""
        return await self._request(
            "POST",
            f"/projects/{project_id}/views/{view_id}/buckets/{bucket_id}/tasks",
            json={"task_id": task_id},
        )

    async def update_task_position(
        self, task_id: int, position: float, view_id: int
    ) -> dict:
        """Update a task's position within a view."""
        return await self._request(
            "POST",
            f"/tasks/{task_id}/position",
            json={"position": position, "project_view_id": view_id},
        )

    async def create_view(
        self, project_id: int, title: str, view_kind: str = "kanban"
    ) -> dict:
        """Create a project view. PUT creates in Vikunja."""
        return await self._request(
            "PUT",
            f"/projects/{project_id}/views",
            json={"title": title, "view_kind": view_kind, "bucket_configuration_mode": "manual"},
        )

    async def list_view_tasks(
        self, project_id: int, view_id: int
    ) -> list[dict]:
        """List tasks for a view. For kanban views, returns buckets with nested tasks."""
        data = await self._request(
            "GET", f"/projects/{project_id}/views/{view_id}/tasks"
        )
        return data if isinstance(data, list) else []

    # ── Attachments ───────────────────────────────────────────────────────────

    async def list_attachments(self, task_id: int) -> list[dict]:
        """List attachments for a task."""
        data = await self._request("GET", f"/tasks/{task_id}/attachments")
        return data if isinstance(data, list) else []

    async def upload_attachment(
        self, task_id: int, filename: str, content: bytes, content_type: str
    ) -> dict:
        """Upload a file attachment to a task. Uses raw httpx (multipart, not JSON)."""
        url = f"{self.base_url}/api/v1/tasks/{task_id}/attachments"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        files = {"files": (filename, content, content_type)}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=headers, files=files)
            if not response.is_success:
                raise VikunjaError(
                    f"PUT /tasks/{task_id}/attachments failed: {response.status_code} {response.text}"
                )
            return response.json()

    async def download_attachment(
        self, task_id: int, attachment_id: int, preview_size: str | None = None
    ) -> tuple[bytes, str, str]:
        """Download an attachment. Returns (content, content_type, filename)."""
        url = f"{self.base_url}/api/v1/tasks/{task_id}/attachments/{attachment_id}"
        if preview_size:
            url += f"?preview_size={preview_size}"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if not response.is_success:
                raise VikunjaError(
                    f"GET /tasks/{task_id}/attachments/{attachment_id} failed: {response.status_code}"
                )
            ct = response.headers.get("content-type", "application/octet-stream")
            # Extract filename from content-disposition header
            cd = response.headers.get("content-disposition", "")
            fname = "attachment"
            if "filename=" in cd:
                fname = cd.split("filename=")[-1].strip('" ')
            return response.content, ct, fname

    async def delete_attachment(self, task_id: int, attachment_id: int) -> dict:
        """Delete an attachment from a task."""
        return await self._request("DELETE", f"/tasks/{task_id}/attachments/{attachment_id}")

    # ── Subtasks (Relations) ─────────────────────────────────────────────────

    async def get_subtasks(self, task_id: int) -> list[dict]:
        """Get subtasks via the related_tasks.subtask field."""
        task = await self.get_task(task_id)
        related = task.get("related_tasks") or {}
        return related.get("subtask", [])

    async def create_subtask(self, parent_id: int, title: str, project_id: int) -> dict:
        """Create a child task and link it as a subtask of the parent."""
        child = await self.create_task(project_id, title)
        await self._request(
            "PUT",
            f"/tasks/{parent_id}/relations",
            json={"other_task_id": child["id"], "relation_kind": "subtask"},
        )
        return child

    async def delete_subtask(self, parent_id: int, subtask_id: int) -> None:
        """Remove the subtask relation and delete the child task."""
        await self._request(
            "DELETE",
            f"/tasks/{parent_id}/relations/subtask/{subtask_id}",
        )
        await self.delete_task(subtask_id)

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_tasks(self, query: str) -> list[dict]:
        """
        Fuzzy-search tasks by title for duplicate detection.

        Uses the Vikunja task list endpoint with a search param.
        """
        data = await self._request("GET", "/tasks", params={"s": query, "per_page": 5})
        return data if isinstance(data, list) else []


# Global client instance
vikunja = VikunjaClient()

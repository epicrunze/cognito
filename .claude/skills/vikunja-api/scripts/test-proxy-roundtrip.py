#!/usr/bin/env python3
"""End-to-end roundtrip test: Cognito proxy -> Vikunja -> verify.

Requires a running backend + Vikunja instance.

Usage:
    uv run scripts/test-proxy-roundtrip.py
    BACKEND_URL=https://api-cognito.epicrunze.com uv run scripts/test-proxy-roundtrip.py

Environment:
    BACKEND_URL       - Cognito backend (required — ask user; no default assumed)
    VIKUNJA_URL       - Vikunja direct URL (required — ask user; no default assumed)
    VIKUNJA_API_TOKEN - Vikunja API token (required)

NOTE: Do not assume localhost. Vikunja may be behind a reverse proxy,
      on a Docker network, or hosted publicly. Always ask the user.
"""

import os
import sys
import json
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx required. Install with: uv add httpx", file=sys.stderr)
    sys.exit(1)

# Load .env
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

BACKEND_URL = os.environ.get("BACKEND_URL", "").rstrip("/")
VIKUNJA_URL = os.environ.get("VIKUNJA_URL", "").rstrip("/")
VIKUNJA_TOKEN = os.environ.get("VIKUNJA_API_TOKEN", "")

missing = []
if not BACKEND_URL:
    missing.append("BACKEND_URL")
if not VIKUNJA_URL:
    missing.append("VIKUNJA_URL")
if not VIKUNJA_TOKEN:
    missing.append("VIKUNJA_API_TOKEN")
if missing:
    print(f"ERROR: Required env vars not set: {', '.join(missing)}", file=sys.stderr)
    print("Set them in .env or environment. Ask the user for their endpoint URLs.", file=sys.stderr)
    sys.exit(1)


class RoundtripTest:
    def __init__(self):
        self.client = httpx.Client(timeout=15.0)
        self.vikunja_headers = {
            "Authorization": f"Bearer {VIKUNJA_TOKEN}",
            "Content-Type": "application/json",
        }
        self.results: list[tuple[str, bool, str]] = []
        self.task_id: int | None = None
        self.label_id: int | None = None
        self.project_id: int | None = None

    def step(self, name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        self.results.append((name, passed, detail))
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    def proxy_get(self, path: str) -> httpx.Response:
        return self.client.get(f"{BACKEND_URL}{path}")

    def proxy_put(self, path: str, json_data: dict) -> httpx.Response:
        return self.client.put(f"{BACKEND_URL}{path}", json=json_data)

    def proxy_post(self, path: str, json_data: dict) -> httpx.Response:
        return self.client.post(f"{BACKEND_URL}{path}", json=json_data)

    def proxy_delete(self, path: str) -> httpx.Response:
        return self.client.delete(f"{BACKEND_URL}{path}")

    def vikunja_get(self, path: str) -> httpx.Response:
        return self.client.get(
            f"{VIKUNJA_URL}/api/v1{path}", headers=self.vikunja_headers
        )

    def run_task_roundtrip(self):
        print("\n=== Task Roundtrip ===\n")

        # 1. Get projects
        resp = self.proxy_get("/api/projects")
        if resp.status_code == 200:
            projects = resp.json().get("projects", [])
            if projects:
                self.project_id = projects[0]["id"]
                self.step("List projects", True, f"found {len(projects)}, using id={self.project_id}")
            else:
                self.step("List projects", False, "no projects found")
                return
        else:
            self.step("List projects", False, f"HTTP {resp.status_code}")
            return

        # 2. Create task via proxy (PUT)
        resp = self.proxy_put("/api/tasks", {
            "project_id": self.project_id,
            "title": "[TEST] Roundtrip test task",
            "priority": 2,
        })
        if resp.status_code == 200 and resp.json().get("id"):
            self.task_id = resp.json()["id"]
            self.step("Create task (PUT)", True, f"id={self.task_id}")
        else:
            self.step("Create task (PUT)", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
            return

        # 3. Read via proxy
        resp = self.proxy_get(f"/api/tasks/{self.task_id}")
        if resp.status_code == 200 and resp.json().get("title") == "[TEST] Roundtrip test task":
            self.step("Read task (proxy)", True)
        else:
            self.step("Read task (proxy)", False, f"HTTP {resp.status_code}")

        # 4. Read directly from Vikunja
        resp = self.vikunja_get(f"/tasks/{self.task_id}")
        if resp.status_code == 200 and resp.json().get("title") == "[TEST] Roundtrip test task":
            self.step("Read task (direct Vikunja)", True)
        else:
            self.step("Read task (direct Vikunja)", False, f"HTTP {resp.status_code}")

        # 5. Update via proxy (POST)
        resp = self.proxy_post(f"/api/tasks/{self.task_id}", {
            "title": "[TEST] Updated roundtrip task",
        })
        if resp.status_code == 200:
            self.step("Update task (POST)", True)
        else:
            self.step("Update task (POST)", False, f"HTTP {resp.status_code}")

        # 6. Verify update
        resp = self.proxy_get(f"/api/tasks/{self.task_id}")
        if resp.status_code == 200 and "Updated" in resp.json().get("title", ""):
            self.step("Verify update", True)
        else:
            self.step("Verify update", False)

        # 7. Delete via proxy
        resp = self.proxy_delete(f"/api/tasks/{self.task_id}")
        if resp.status_code == 200:
            self.step("Delete task", True)
            self.task_id = None
        else:
            self.step("Delete task", False, f"HTTP {resp.status_code}")

    def run_label_roundtrip(self):
        print("\n=== Label Roundtrip ===\n")

        # 1. Create label
        resp = self.proxy_put("/api/labels", {
            "title": "[TEST] Roundtrip label",
            "hex_color": "#ff0000",
        })
        if resp.status_code == 200 and resp.json().get("id"):
            self.label_id = resp.json()["id"]
            self.step("Create label (PUT)", True, f"id={self.label_id}")
        else:
            self.step("Create label (PUT)", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
            return

        # 2. List labels
        resp = self.proxy_get("/api/labels")
        if resp.status_code == 200:
            labels = resp.json().get("labels", [])
            found = any(l["id"] == self.label_id for l in labels)
            self.step("List labels", found, f"found={found} in {len(labels)} labels")
        else:
            self.step("List labels", False, f"HTTP {resp.status_code}")

        # 3. If we have a task, attach/detach label
        if self.project_id:
            # Create a temp task
            resp = self.proxy_put("/api/tasks", {
                "project_id": self.project_id,
                "title": "[TEST] Label attach test",
            })
            if resp.status_code == 200 and resp.json().get("id"):
                temp_task_id = resp.json()["id"]

                # Attach label
                resp = self.proxy_put(f"/api/tasks/{temp_task_id}/labels", {
                    "label_id": self.label_id,
                })
                self.step("Attach label to task", resp.status_code in (200, 201))

                # Detach label
                resp = self.proxy_delete(f"/api/tasks/{temp_task_id}/labels/{self.label_id}")
                self.step("Detach label from task", resp.status_code == 200)

                # Cleanup temp task
                self.proxy_delete(f"/api/tasks/{temp_task_id}")

        # 4. Delete label
        resp = self.proxy_delete(f"/api/labels/{self.label_id}")
        if resp.status_code == 200:
            self.step("Delete label", True)
            self.label_id = None
        else:
            self.step("Delete label", False, f"HTTP {resp.status_code}")

    def cleanup(self):
        """Best-effort cleanup of any resources created during testing."""
        print("\n=== Cleanup ===\n")
        cleaned = False
        if self.task_id:
            resp = self.proxy_delete(f"/api/tasks/{self.task_id}")
            print(f"  Cleaned up task {self.task_id}: HTTP {resp.status_code}")
            cleaned = True
        if self.label_id:
            resp = self.proxy_delete(f"/api/labels/{self.label_id}")
            print(f"  Cleaned up label {self.label_id}: HTTP {resp.status_code}")
            cleaned = True
        if not cleaned:
            print("  Nothing to clean up")

    def summary(self):
        print("\n=== Summary ===\n")
        passed = sum(1 for _, p, _ in self.results if p)
        failed = sum(1 for _, p, _ in self.results if not p)
        total = len(self.results)
        print(f"  {passed}/{total} passed, {failed} failed")
        if failed:
            print("\n  Failed steps:")
            for name, p, detail in self.results:
                if not p:
                    print(f"    - {name}" + (f": {detail}" if detail else ""))
        return 0 if failed == 0 else 1


def main():
    print(f"Backend:  {BACKEND_URL}")
    print(f"Vikunja:  {VIKUNJA_URL}")
    print(f"Token:    {'set' if VIKUNJA_TOKEN else 'NOT SET'}")

    test = RoundtripTest()
    try:
        test.run_task_roundtrip()
        test.run_label_roundtrip()
    except Exception as e:
        print(f"\n  FATAL: {e}")
    finally:
        test.cleanup()

    sys.exit(test.summary())


if __name__ == "__main__":
    main()

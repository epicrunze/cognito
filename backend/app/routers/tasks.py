"""
Router: /api/tasks

Vikunja task proxy (Spec §3.2).
Proxies task CRUD operations to Vikunja, injecting the API token server-side
so the frontend never needs direct Vikunja access.

NOTE: Vikunja uses PUT to create and POST to update (opposite of standard REST).

TODO:
- GET /api/tasks — list tasks (supports filter expression, pagination)
- GET /api/tasks/{id} — get single task
- PUT /api/tasks — create task (Vikunja: PUT creates)
- POST /api/tasks/{id} — update task (Vikunja: POST updates)
- DELETE /api/tasks/{id} — delete task
- POST /api/tasks/{id}/labels — add label to task
- GET /api/tasks/{id}/comments — list comments
- PUT /api/tasks/{id}/comments — add comment
"""

# TODO: Implement tasks proxy router

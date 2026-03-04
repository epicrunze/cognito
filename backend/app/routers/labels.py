"""
Router: /api/labels

Vikunja label proxy (Spec §3.2).
Proxies label management to Vikunja, injecting the API token server-side.

NOTE: Label updates use PUT (same as task creation — Vikunja convention).

TODO:
- GET /api/labels — list all labels
- GET /api/labels/{id} — get single label
- PUT /api/labels — create label
- POST /api/labels/{id} — update label
- DELETE /api/labels/{id} — delete label
- PUT /api/tasks/{id}/labels — assign label to task (via tasks router or here)
"""

# TODO: Implement labels proxy router

# Cognito — Implementation Tasks

Work through in order. Check boxes when complete.
Before each task, read the referenced spec sections in `docs/SPEC.md`.

## Phase 5: Calendar + Mobile

### T-031: Google Calendar
- [ ] Add calendar scope to OAuth
- [ ] `services/gcal.py` — list events, create, delete
- [ ] POST /api/schedule, GET /api/schedule/suggest
- [ ] Schedule view in frontend

### T-032: Mobile responsive
Read: Section 5.14
- [ ] Sidebar hidden on mobile, hamburger toggle
- [ ] Detail panel full-screen on mobile
- [ ] Kanban horizontal scroll, touch-friendly
- [ ] Test 375px, 768px, 1024px+

---

## Additional items completed (not in original plan)

- `ui/DatePicker.svelte` — full calendar picker component
- `routers/models.py` + `models_registry.py` — GET /api/models endpoint for model selection
- `/upcoming` and `/overdue` routes with filtered task views
- `lib/stores/search.svelte.ts` — search store with 300ms debounce
- TaskPanel supports `proposal` mode (edit proposals before approval inline)
- Backend tests expanded to 42 passing (up from 38)
- `ShortcutsModal.svelte` — `?` key opens slide-over with full keyboard shortcuts reference (Navigation, Actions, Global sections)
- Bottom hint bar in TaskList — dismissible shortcut hints, persists dismiss state in localStorage
- `lib/stores/filter.svelte.ts` + `FilterBar.svelte` — client-side filtering by status, priority, labels with active count badge
- `lib/stores/kanban.svelte.ts` — kanbanStore with full board management, bucket CRUD, DnD, bucket name lookup for list view
- `lib/api.ts` kanbanApi — views, buckets, moveTask, position endpoints
- `lib/stores/taskMutations.ts` — unified update/toggleDone/delete that syncs both tasksStore and kanbanStore with optimistic updates + rollback
- Backend kanban endpoints: views, buckets, move task, view tasks, task position (in projects.py + tasks.py)
- `services/vikunja.py` expanded: create_bucket, update_bucket, delete_bucket, move_task_to_bucket, update_task_position, create_view, list_view_tasks
- `proposals.py` approve-all returns `task_ids` array for AI glow tracking

---

## Notes

- **Read the referenced spec section before starting each task.**
- **Use the design tokens.** Never hardcode colours or spacing.
- **Test each task before moving on** — does it render? Does the API work? Does optimistic rollback work?
- **Vikunja swagger docs** at `http://tasks.epicrunze.com/api/v1/docs`.

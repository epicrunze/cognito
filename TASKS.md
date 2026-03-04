# Cognito — Implementation Tasks

Work through these tasks in order. Check the box when complete.
Before starting any task, read the referenced spec sections in `docs/SPEC.md`.

---

## Phase 0: Design Foundation

### T-001: Project scaffolding ✅
- [x] Create backend stub files: `routers/chat.py`, `routers/tasks.py`, `routers/labels.py`, `routers/schedule.py`, `models/config.py`, `services/gcal.py`
- [x] Create frontend stub files: `lib/types.ts`, route pages (`/project/[id]`, `/project/[id]/kanban`, `/extract`), feature components (`Sidebar`, `TaskList`, `TaskRow`, `TaskDetail`, `KanbanBoard`, `KanbanColumn`, `KanbanCard`, `FilterBar`, `PriorityStars`, `LabelChip`, `DatePicker`), UI primitives (`Button`, `Input`, `Textarea`, `Checkbox`, `Select`, `Badge`, `PriorityIndicator`, `DateDisplay`, `Skeleton`, `Kbd`, `SlideOver`, `Toast`, `ToastContainer`)
- [x] Update `.env.example` with `DATABASE_URL` entry
- [x] All 38 backend tests still pass

### T-002: Design tokens and global styles ✅
Read: `docs/SPEC.md` Section 5.1 (Design Tokens)
- [x] Install and configure Tailwind CSS in the SvelteKit project
- [x] Define all CSS custom properties (colours, typography, spacing, shadows, transitions) in `frontend/src/app.css`
- [x] Import IBM Plex Sans and IBM Plex Mono (Google Fonts link in app.html or self-host)
- [x] Configure Tailwind theme to reference the CSS custom properties
- [x] Set base styles: font-family, font-size, background colour, text colour

### T-003: Primitive UI components — Part 1 ✅
Read: `docs/SPEC.md` Section 5.2 (Primitive Components)
- [x] Create `frontend/src/components/ui/Button.svelte` — variants: accent, outline, ghost. Sizes: sm, md. Loading state with spinner.
- [x] Create `frontend/src/components/ui/Input.svelte` — consistent 36px height, focus ring using --accent
- [x] Create `frontend/src/components/ui/Textarea.svelte` — auto-grow variant for descriptions
- [x] Create `frontend/src/components/ui/Checkbox.svelte` — custom circle style (not square), animate fill on check using --done colour
- [x] Create `frontend/src/components/ui/Select.svelte` — custom styled dropdown, not native
- [x] Create `frontend/src/components/ui/Badge.svelte` — coloured pill, accepts hex_color prop for dynamic label colours

### T-004: Primitive UI components — Part 2 ✅
Read: `docs/SPEC.md` Sections 5.2, 5.1
- [x] Create `frontend/src/components/ui/PriorityIndicator.svelte` — 5 dots, filled/empty, colour-coded per priority level
- [x] Create `frontend/src/components/ui/DateDisplay.svelte` — relative dates ("Tomorrow", "Mar 7"), red if overdue
- [x] Create `frontend/src/components/ui/Skeleton.svelte` — pulsing grey rectangle, accepts width/height props
- [x] Create `frontend/src/components/ui/Kbd.svelte` — small monospace keyboard shortcut badge
- [x] Create `frontend/src/components/ui/SlideOver.svelte` — right-side panel, 480px, backdrop, escape to close, slide transition 200ms
- [x] Create `frontend/src/components/ui/Toast.svelte` + `ToastContainer.svelte` — bottom-right stack, auto-dismiss 4s, variants: success/error/info

### T-005: Toast notification system ✅
- [x] Create a toast Svelte store in `frontend/src/lib/stores/toast.ts`
- [x] Export `addToast(message, variant, duration?)` function
- [x] `ToastContainer` reads from the store, renders toasts with `fly` transition
- [x] Auto-remove after duration (default 4000ms)
- [x] Test: import and call `addToast` from a page, verify it appears and auto-dismisses

### T-006: App shell layout ✅
Read: `docs/SPEC.md` Sections 5.4, 5.5
- [x] Create `frontend/src/routes/+layout.svelte` with sidebar + main content area
- [x] Sidebar: 240px wide, --bg-sidebar background, right border
- [x] Sidebar content: app name at top, navigation links (All Tasks, Upcoming, Overdue), project list section, AI Extract button, settings icon, user info at bottom
- [x] Navigation links are placeholder — just show text, no data yet
- [x] Main content area: header bar with search input + "New" button + "AI" button, then `<slot />`
- [x] Create `frontend/src/routes/+page.svelte` — placeholder "All Tasks" page

### T-007: TypeScript types ✅
Read: `docs/SPEC.md` Section 2.1 (Vikunja Data), Section 2.2 (Agent Data)
- [x] Create `frontend/src/lib/types.ts` with interfaces for: Task, Project, ProjectView, Bucket, Label, TaskProposal
- [x] Match field names and types exactly to the Vikunja API response shapes (snake_case JSON)
- [x] Include nullable fields as `field: type | null`

### T-008: Keyboard shortcut handler ✅
Read: `docs/SPEC.md` Section 5.3 (Keyboard Shortcuts table)
- [x] Create `frontend/src/lib/shortcuts.ts` — a keyboard event handler that maps keys to actions
- [x] Register at the layout level (keydown listener on window)
- [x] Disable shortcuts when an input, textarea, or contenteditable is focused
- [x] Implement placeholder actions for: n (new task), / (focus search), Escape (close panel)
- [x] Other shortcuts (j/k/x/e/1-5) will be wired up when their features are built

### T-009: Optimistic update helper ✅
Read: `docs/SPEC.md` Section 5.3 (Optimistic Updates)
- [x] Create `frontend/src/lib/optimistic.ts`
- [x] Export `optimisticUpdate<T>({ apply, apiCall, rollback, errorMessage? })` — caller-controlled apply/rollback
- [x] Pattern: update store immediately → fire apiCall → on failure: rollback store + show error toast

---

## Phase 1: Backend + Core Data Flow

### T-010: FastAPI skeleton and auth (partial)
Read: `docs/SPEC.md` Sections 3.1, 11
- [x] FastAPI app in `backend/app/main.py` with CORS middleware
- [x] Auth module: Google OAuth2 → JWT HttpOnly cookie (`auth/oauth.py`, `auth/jwt.py`, `auth/dependencies.py`)
- [x] `config.py` — Pydantic Settings with all env vars
- [ ] Migrate database from DuckDB to SQLite with aiosqlite (schema from Section 2.3)
- [ ] Update tests to use in-memory SQLite instead of in-memory DuckDB

### T-011: Vikunja API client
Read: `docs/SPEC.md` Section 6 (entire section — critical API details)
- [ ] Create `backend/app/services/vikunja.py` — async httpx client
- [ ] Base method: `_request(method, path, **kwargs)` that adds `Authorization: Bearer {token}` header
- [ ] Implement: `list_projects()`, `get_project(id)`, `list_project_views(project_id)`
- [ ] Implement: `list_tasks(filter, sort_by, order_by, page, per_page, s)`, `get_task(id)`, `create_task(project_id, data)`, `update_task(id, data)`, `delete_task(id)`
- [ ] Implement: `list_labels()`, `create_label(data)`, `add_label_to_task(task_id, label_id)`, `remove_label_from_task(task_id, label_id)`
- [ ] Implement: `list_buckets(project_id, view_id)`, `move_task_to_bucket(project_id, view_id, task_id, bucket_id, position)`
- [ ] Handle pagination headers (`x-pagination-total-pages`, `x-pagination-result-count`)
- [ ] Remember: PUT creates, POST updates. Label update uses PUT.

### T-012: Generic Vikunja proxy router
Read: `docs/SPEC.md` Section 3.2
- [ ] Create `backend/app/routers/tasks.py` — proxy endpoints for task CRUD
- [ ] Create `backend/app/routers/projects.py` — proxy endpoints for projects, views, buckets
- [ ] Create `backend/app/routers/labels.py` — proxy endpoints for labels
- [ ] All endpoints require the JWT auth dependency
- [ ] Consider a generic proxy function that forwards request to Vikunja with token injection, reducing boilerplate
- [ ] Test with curl/httpie: CRUD operations via the proxy match direct Vikunja API calls

### T-013: LLM extraction pipeline
Read: `docs/SPEC.md` Sections 4.1–4.3
- [ ] Create `backend/app/services/llm.py` — GeminiClient and OllamaClient with tool-calling support
- [ ] Create `backend/app/services/extractor.py` — the extraction pipeline
- [ ] Define tools: `lookup_projects`, `resolve_project`, `check_existing_tasks`
- [ ] Tool implementations call the Vikunja client
- [ ] Implement the extraction prompt from Section 4.3
- [ ] Return structured TaskProposal objects
- [ ] Test: send sample meeting notes text, verify reasonable proposals come back with real project IDs

### T-014: Ingest and proposals API
Read: `docs/SPEC.md` Sections 3.3, 3.4
- [ ] Create `backend/app/routers/ingest.py` — POST `/api/ingest` with SSE streaming support
- [ ] Create `backend/app/routers/proposals.py` — GET (list), PUT (edit), POST approve/reject, bulk operations
- [ ] Approve flow: take proposal → create task in Vikunja via client → update proposal status to 'created' → store vikunja_task_id
- [ ] Test full flow: ingest text → get proposals → approve → verify task exists in Vikunja

### T-015: Frontend API client
- [ ] Create `frontend/src/lib/api.ts` — fetch wrapper with JWT cookie (credentials: 'include')
- [ ] Methods for all backend endpoints: tasks, projects, labels, proposals, ingest
- [ ] SSE support: `extractTasks(text, opts)` returns an async iterator yielding proposals
- [ ] Error handling: throw on non-2xx, include response body in error
- [ ] Pagination helper: auto-follow pages or return pagination metadata

### T-016: Svelte stores
- [ ] Create `frontend/src/lib/stores/tasks.ts` — writable store, methods: fetchAll, fetchByProject, create, update, toggleDone, delete
- [ ] Create `frontend/src/lib/stores/projects.ts` — writable store, methods: fetchAll (includes views)
- [ ] Create `frontend/src/lib/stores/proposals.ts` — writable store, methods: fetchPending, approve, reject, approveAll
- [ ] Create `frontend/src/lib/stores/labels.ts` — writable store, methods: fetchAll
- [ ] All mutation methods use the optimistic update pattern from T-009

### T-017: Sidebar with live data
- [ ] Update `+layout.svelte` sidebar to fetch projects on mount and display them
- [ ] Show project colour dots using `hex_color`
- [ ] Show task counts next to each project (fetch task counts from API)
- [ ] Active navigation item highlighted with --accent-subtle background + --accent text
- [ ] "All Tasks", "Upcoming", "Overdue" links route to `/`, `/upcoming`, `/overdue`

### T-018: Task list view (read-only)
Read: `docs/SPEC.md` Section 5.6
- [ ] Create `frontend/src/components/TaskList.svelte` and `TaskRow.svelte`
- [ ] TaskRow: checkbox (Checkbox component), priority dots (PriorityIndicator), title, due date (DateDisplay), label badges
- [ ] Fetch tasks on mount, display in list
- [ ] Show skeleton loading state while fetching (Skeleton component)
- [ ] Show empty state if no tasks
- [ ] Hover: row background shifts to --bg-surface-hover

### T-019: Task quick-add
- [ ] Add an always-visible input at the top of the task list: "Add task..." placeholder
- [ ] On Enter: create task in current project with the typed title via API
- [ ] Optimistic: add task to store immediately, roll back on API failure
- [ ] Clear input after successful creation
- [ ] Focus input when user presses `n` (keyboard shortcut from T-008)

### T-020: Task done toggle
- [ ] Wire up Checkbox click in TaskRow to toggle `done` status
- [ ] Use optimistic update: checkbox fills immediately, API call in background
- [ ] Animate the checkbox fill (200ms transition)
- [ ] On failure: roll back checkbox state, show error toast
- [ ] Completed tasks move to a "Completed" section at the bottom (collapsed by default)

### T-021: AI extraction page
Read: `docs/SPEC.md` Section 5.9
- [ ] Create `frontend/src/routes/extract/+page.svelte`
- [ ] Textarea for input with generous padding
- [ ] "Extract Tasks" button using --ai-accent colour, shows ⌘↵ hint
- [ ] On submit: call `/api/ingest` with SSE, render ProposalCard components as they stream in
- [ ] Each ProposalCard: checkbox, priority dots, title, project, due date, labels, edit button
- [ ] Cards appear with `fly` transition, 50ms stagger between cards
- [ ] "Approve All" button (--ai-accent), "Reject Selected" button
- [ ] On approve: call bulk approve API, show success toast "N tasks created", cards animate away
- [ ] Confidential toggle in header area

---

## Phase 2: Rich Task Management

### T-022: Task detail panel
Read: `docs/SPEC.md` Section 5.8
- [ ] Create `frontend/src/components/TaskDetail.svelte` using SlideOver
- [ ] Open when clicking any task row (store the selected task ID)
- [ ] Editable fields: title (large text), done checkbox, project (Select), priority (PriorityIndicator, clickable), due date (date input), labels (Badge chips + add button), description (Textarea, auto-grow), estimated minutes
- [ ] Auto-save: debounce 500ms for text fields, immediate for toggles/selects/priority
- [ ] Show created/updated timestamps at bottom in --text-tertiary
- [ ] Delete button with confirmation
- [ ] Close on Escape or backdrop click

### T-023: Filter and sort bar
Read: `docs/SPEC.md` Section 5.6, Section 3.2 (filter syntax)
- [ ] Create `frontend/src/components/FilterBar.svelte`
- [ ] Filter chips: done status (All/Active/Completed), priority (Any/High/Urgent), label selector
- [ ] Sort dropdown: Due date, Priority, Created, Position
- [ ] Translate UI filter selections into Vikunja filter syntax strings
- [ ] Re-fetch tasks when filters change
- [ ] Show active filter count on the filter button

### T-024: Kanban board view
Read: `docs/SPEC.md` Sections 5.7, 6.3, 6.4
- [ ] Create route: `frontend/src/routes/project/[id]/kanban/+page.svelte`
- [ ] Create `frontend/src/components/KanbanBoard.svelte`, `KanbanColumn.svelte`, `KanbanCard.svelte`
- [ ] On mount: fetch project views → find view with `view_kind === 3` → fetch its buckets → for each bucket, fetch tasks
- [ ] Display columns with bucket title, task count, optional WIP limit
- [ ] Cards show: priority dots, title, due date, first label
- [ ] Card hover: shadow increases (--shadow-sm → --shadow-md)
- [ ] Click card: open TaskDetail slide-over
- [ ] "+ Add task" at bottom of each column
- [ ] "+ Column" button to create new buckets
- [ ] View toggle buttons [List] [Kanban] in page header to switch between views

### T-025: Kanban drag and drop
- [ ] Install and configure `svelte-dnd-action`
- [ ] Enable drag between columns (changes bucket_id) and within columns (changes position)
- [ ] On drop: calculate new position (midpoint between neighbours), optimistically update store
- [ ] API call: POST to `/api/projects/{id}/views/{viewId}/buckets/tasks` with {task_id, bucket_id, position}
- [ ] On failure: roll back to original position, show error toast
- [ ] Drag visual: card lifts with larger shadow, semi-transparent placeholder in original spot

### T-026: Loading and empty states
Read: `docs/SPEC.md` Section 5.10
- [ ] Task list: show 5 skeleton rows while loading
- [ ] Kanban: show 3 skeleton columns with 2-3 skeleton cards each
- [ ] Detail panel: skeleton blocks for title, fields, description
- [ ] Empty project: "No tasks yet. Add one above or extract from notes."
- [ ] Empty extraction: "Paste meeting notes, an email, or just describe what you need to do."
- [ ] No search results: "No tasks match your search."

### T-027: Keyboard navigation
Read: `docs/SPEC.md` Section 5.3 (Keyboard Shortcuts)
- [ ] j/k: move selection up/down in task list (highlight selected row)
- [ ] Enter: open detail panel for selected task
- [ ] x: toggle done on selected task
- [ ] e: open detail panel in edit mode
- [ ] 1-5: set priority (when detail panel is open)
- [ ] /: focus search input in header
- [ ] Visual: show subtle selection highlight on currently selected row

### T-028: Search
- [ ] Wire up the search input in the header bar
- [ ] On type (debounced 300ms): fetch tasks with `s` query parameter
- [ ] Show results in the main task list area
- [ ] Clear search with Escape or X button
- [ ] `/` keyboard shortcut focuses the search input

---

## Phase 3: AI Polish

### T-029: Chat mode for extraction
Read: `docs/SPEC.md` Section 3.3 (POST /api/chat)
- [ ] Add chat mode toggle to the extraction page ([Chat] [Paste] tabs)
- [ ] Chat mode: conversational input, agent replies with extracted tasks + follow-up questions
- [ ] Maintain conversation_id for multi-turn conversations
- [ ] Display agent replies above the proposal cards

### T-030: Proposal editing
- [ ] "Edit" button on each proposal card expands it inline
- [ ] Show editable fields: title, project (Select dropdown from project store), priority, due date, labels, estimated minutes
- [ ] Save edits via PUT `/api/proposals/{id}`
- [ ] Collapse edit on save or clicking edit again

### T-031: Confidential mode + Ollama routing
Read: `docs/SPEC.md` Sections 4.1, 4.4
- [ ] Confidential toggle on extraction page routes to Ollama backend
- [ ] Show visible banner: "🔒 Processing locally via Ollama"
- [ ] Backend: route confidential=true requests to OllamaClient
- [ ] Handle Ollama-specific errors (unreachable, malformed JSON) with clear messages

### T-032: Extraction UX polish
- [ ] Pulsing indicator on "Extract Tasks" button while extraction is running
- [ ] Staggered fly-in animation for proposal cards (50ms delay between each)
- [ ] Success animation on approve: cards shrink/fade away
- [ ] Toast on approve: "3 tasks created" with link to view them in the project
- [ ] Error retry: if extraction fails, show retry button with the same input preserved

### T-033: Proposal history
- [ ] Add a "History" section/link on the extraction page
- [ ] Show recently approved and rejected proposals (last 50)
- [ ] Each shows: title, project, status (approved/rejected), timestamp
- [ ] Can click an approved proposal to view the created task

### T-034: Error handling and retry
Read: `docs/SPEC.md` Section 4.4
- [ ] Backend: implement retry logic for Gemini (3x exponential backoff) and Ollama (2x)
- [ ] Backend: fall back to Ollama if Gemini rate-limited (if Ollama available)
- [ ] Frontend: all API errors show toast notifications, never silent failures
- [ ] Frontend: retry buttons on failed operations
- [ ] Vikunja down during approve: keep status as 'approved', show toast, manual retry option

---

## Phase 4: Calendar + Mobile (Future)

### T-035: Google Calendar integration
Read: `docs/SPEC.md` Sections 3.5, 1.3
- [ ] Add `calendar` scope to Google OAuth flow
- [ ] Backend: `gcal.py` service — list events, create event, delete event
- [ ] Backend: POST `/api/schedule` and GET `/api/schedule/suggest`
- [ ] Frontend: schedule view showing proposed time blocks
- [ ] Push to calendar flow with confirmation

### T-036: Mobile responsive layout
Read: `docs/SPEC.md` Section 5.11
- [ ] Sidebar: hidden on mobile, hamburger menu toggle
- [ ] Task detail: full-screen overlay on mobile
- [ ] Kanban: horizontal scroll, touch-friendly card sizing
- [ ] Test at 375px, 768px, 1024px+ breakpoints

---

## Notes for Claude Code

- **Always read the referenced spec section before starting a task.** The spec is at `docs/SPEC.md`.
- **Test each task before moving on.** At minimum: does it render? Does the API call work? Does the optimistic update roll back correctly?
- **Use the design tokens.** Never hardcode colours, spacing, or font sizes. Use the CSS custom properties.
- **Vikunja API is running at `http://localhost:3456`.** Make sure Docker is up before testing backend tasks.
- **When in doubt about Vikunja's API behaviour**, check `docs/SPEC.md` Section 6 or hit the Vikunja swagger docs at `http://localhost:3456/api/v1/docs`.
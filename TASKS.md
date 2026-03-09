# Cognito — Implementation Tasks

Work through in order. Check boxes when complete.
Before each task, read the referenced spec sections in `docs/SPEC.md`.

---

## Phase 0: Design Foundation

### T-001: Scaffolding
- [x] Create project structure per `docs/SPEC.md` Section 7
- [x] Init SvelteKit in `frontend/` with TypeScript
- [x] Init FastAPI in `backend/` with pyproject.toml
- [x] Create `docker-compose.yml` per Section 8
- [x] Create `.env.example` per Section 9

### T-002: Design tokens
Read: Section 5.2
- [x] Configure Tailwind in SvelteKit
- [x] Define all CSS custom properties in `app.css` (dark theme tokens)
- [x] Import IBM Plex Sans + IBM Plex Mono
- [x] Set base styles: bg-base background, text-primary color, font-sans

### T-003: Primitive components — inputs
Read: Section 5.3, reference `docs/cognito-design-system.jsx`
- [x] `ui/Button.svelte` — variants: accent, outline, ghost, danger, toggle. Sizes: sm/md. Loading state. `flexShrink:0, whiteSpace:nowrap`
- [x] `ui/Input.svelte` — 40px height (34px in toolbars), accent focus ring + shadow
- [x] `ui/Textarea.svelte` — auto-grow, same focus ring
- [x] `ui/Checkbox.svelte` — circular, green fill + checkmark, 20px
- [x] `ui/Dropdown.svelte` — custom select, option descriptions, accent highlight, click-outside-close

### T-004: Primitive components — display
Read: Section 5.3
- [x] `ui/PriorityIndicator.svelte` — 5 dots, colour-coded. Sizes: sm (7px) / md (8px)
- [x] `ui/Badge.svelte` — pill with hex_color bg. 24px height
- [x] `ui/DateDisplay.svelte` — relative dates, red if overdue
- [x] `ui/Kbd.svelte` — monospace shortcut badge, 22px height
- [x] `ui/Skeleton.svelte` — pulsing rectangle, width/height/radius props
- [x] `ui/Tip.svelte` — tooltip, `side` prop: "top" (default) or "right" (for collapsed sidebar). Arrow pointer

### T-005: Primitive components — overlay
Read: Section 5.3
- [x] `ui/Toast.svelte` + `ToastContainer.svelte` — bottom-right stack, auto-dismiss 4s, success/error/info, slide-up
- [x] `ui/SlideOver.svelte` — right-side 480px, backdrop, escape to close, 200ms slide
- [x] Toast store in `lib/stores/toast.ts` with `addToast(message, variant, duration?)`

### T-006: App shell
Read: Sections 5.4, 5.5
- [x] `+layout.svelte` — sidebar (240px) + main content + header bar
- [x] Sidebar: collapsible to 56px icon rail with toggle
- [x] When collapsed: `overflow: visible`, `z-index: 50`, tooltips appear to RIGHT
- [x] Sidebar contents: wordmark, nav links with counts, project list with colour dots, AI Extract button (accent border), settings, user email
- [x] Header bar: page title (left, margin-right auto), search input (shrinks), Filter, Extract, + New (all buttons with hover effects, single row, no wrapping)
- [x] All sidebar items have hover effects

### T-007: Types and keyboard shortcuts
Read: Sections 2.1, 2.2, 5.12
- [x] `lib/types.ts` — Task, Project, ProjectView, Bucket, Label, TaskProposal, LabelDescription
- [x] `lib/shortcuts.ts` — page-level keydown handler, disabled when input focused
- [x] Wire N, /, Escape initially; others when features built
- [x] `lib/optimistic.ts` — `optimisticUpdate(store, mutation, apiCall, rollback)`

---

## Phase 1: Backend + Core Data

### T-008: FastAPI skeleton + auth
Read: Sections 3.1, 9
- [x] FastAPI app with CORS middleware
- [x] Port auth module from archive (oauth.py, jwt.py, dependencies.py)
- [x] Config via Pydantic Settings with all env vars
- [x] SQLite schema init on startup (Section 2.3, including label_descriptions table)

### T-009: Vikunja API client
Read: Section 6 (critical — read entirely)
- [x] `services/vikunja.py` — async httpx client with `_request(method, path)` adding auth header
- [x] Methods: list_projects, get_project, list_project_views, list_tasks, get_task, create_task, update_task, delete_task, list_labels, create_label, add_label_to_task, remove_label_from_task, list_buckets, move_task_to_bucket
- [x] Handle pagination headers
- [x] Remember: PUT creates, POST updates (label update is PUT for both)

### T-010: Proxy routers
Read: Section 3.2
- [x] `routers/tasks.py`, `routers/projects.py`, `routers/labels.py`
- [x] All require JWT auth dependency
- [x] Generic proxy where possible (inject token, forward, return)

### T-011: LLM extraction pipeline
Read: Sections 4.1–4.3
- [x] `services/llm.py` — GeminiClient + OllamaClient, both support tool calling
- [x] `services/extractor.py` — extraction pipeline with tools: lookup_projects, resolve_project, check_existing_tasks, get_label_descriptions
- [x] Model selection: accept model name in request, route to appropriate client
- [x] Return raw LLM response alongside proposals (for debugging UI)

### T-012: Ingest + proposals API
Read: Sections 3.3, 3.4
- [x] `routers/ingest.py` — POST /api/ingest with SSE streaming. Include `model` field in request
- [x] `routers/proposals.py` — CRUD, approve (creates Vikunja task + applies labels), reject, bulk
- [x] Store model_used and auto_tag_reasons in proposal record

### T-013: Frontend API client + stores
- [x] `lib/api.ts` — fetch wrapper with JWT cookie, SSE support
- [x] `lib/stores/tasks.ts` — fetchAll, fetchByProject, create, update, toggleDone, delete (all optimistic)
- [x] `lib/stores/projects.ts` — fetchAll (includes views)
- [x] `lib/stores/proposals.ts` — fetchPending, approve, reject, approveAll
- [x] `lib/stores/labels.ts` — fetchAll, fetchDescriptions

### T-014: Sidebar with live data
- [x] Fetch projects on mount, show with colour dots + counts
- [x] Active item: accent-subtle bg + accent text
- [x] Collapsed state: icon rail with right-side tooltips showing label + count
- [x] AI Extract button prominent with accent border

### T-015: Task list view
Read: Section 5.5
- [x] `TaskList.svelte` + `TaskRow.svelte`
- [x] Row: checkbox, priority dots, title, description preview (truncated), project name, label badges, due date (red if overdue), hover chevron
- [x] Quick-add at top: "+ Add task..." placeholder, Enter to create
- [x] Checkbox: optimistic toggle with animation
- [x] Skeleton loading (5 rows matching content shape)
- [x] Empty state

### T-016: Completed tasks section
Read: Section 5.5
- [x] "Completed (N)" divider with toggle arrow below active tasks
- [x] Completed tasks render below divider at 0.65 opacity
- [x] Collapsible (click divider to show/hide)

### T-017: Smart sort
- [x] Default: overdue first, then priority desc, then due date asc
- [x] Sort dropdown (Dropdown component): priority, due date, created, alphabetical
- [x] Translate to Vikunja sort_by + order_by params (via filterStore.vikunjaSort)

### T-018: AI extraction page
Read: Section 5.10
- [x] Route: `/extract`
- [x] Header: "Extract Tasks" in accent colour
- [x] Model selector (Dropdown): Gemini Flash, Gemini Pro, Qwen (Local), Llama (Local)
- [x] Local/Cloud toggle (Button variant="toggle"), hover effect. When local: accent-tinted bg + banner
- [x] Textarea input with generous padding
- [x] Extract button + Ctrl+Enter Kbd hint
- [x] Collapsible RawResponse panel (shows full JSON: tool calls, proposals, tokens, latency)
- [x] Proposal cards stream in via SSE with fly transition + 50ms stagger
- [x] Cards: tangerine left border + glow, checkbox, priority, title, project, date, labels
- [x] Approve All / Reject Selected actions. Success toast "N tasks created"

---

## Phase 2: Rich Task Management

### T-019: Task detail panel
Read: Section 5.9
- [x] SlideOver, opens on task row click
- [x] Editable: title (16px), done, project (Dropdown + inline create), priority (clickable dots), due date (DatePicker), labels (badges + add picker), description (textarea), estimated minutes
- [x] Attachments section (list files/images, upload area) — uses Vikunja attachments API
- [x] Auto-save: debounce 500ms text, immediate toggles/selects
- [x] Clear AI-tagged glow when task is opened (mark as viewed via filterStore.markViewed)
- [x] Delete button + confirmation. Created/updated timestamps

### T-020: Filter bar
Read: Section 5.6
- [x] FilterBar.svelte with chips: status (All/Active/Completed), priority, label
- [x] Translate to Vikunja filter syntax (via filterStore.vikunjaFilter)
- [x] Filter button in header shows active filter count

### T-021: Kanban board
Read: Section 5.8
- [x] Route: `/project/[id]/kanban`
- [x] Fetch views -> find view_kind=kanban -> buckets -> tasks per bucket (auto-creates kanban view if missing)
- [x] Cards: priority, title, date, first label. Hover shadow
- [x] View toggle [List] [Kanban] in header
- [x] "+ Add task" per column. "+ Column" to create buckets
- [x] KanbanBoard, KanbanColumn, KanbanCard components
- [x] kanbanStore with fetchBoard, moveTask, createBucket, createTaskInBucket
- [x] Bucket name badges on list view TaskRows (via fetchBucketMap)

### T-022: Kanban drag-and-drop
- [x] `svelte-dnd-action` for between-column and within-column
- [x] Position = midpoint between neighbours
- [x] POST to bucket/tasks endpoint (moveTaskToBucket + updateTaskPosition)
- [x] Optimistic update with rollback

### T-023: Search + keyboard navigation
Read: Section 5.12
- [x] Search input in header, debounced 300ms, uses `s` param
- [x] J/K navigate list (highlight selected row with accent-subtle + 2px accent left border)
- [x] Enter opens detail, X toggles done, E opens edit, 1-5 sets priority
- [x] / focuses search
- [x] `?` opens keyboard shortcuts help slide-over
- [x] Bottom hint bar in TaskList for shortcut discoverability (dismissible, persists in localStorage)

---

## Phase 3: Auto-tagging + AI Polish

### T-024: Label descriptions
Read: Section 5.11
- [x] Backend: label_descriptions CRUD endpoints (Section 3.5)
- [x] `services/tagger.py` — auto-tag logic using LLM + label descriptions
- [x] UI: in label management (settings or inline), let user write description per label
- [x] New tool: get_label_descriptions for extraction pipeline

### T-025: Auto-tag existing tasks
- [x] POST /api/tasks/auto-tag endpoint
- [x] Sends task titles to LLM with label descriptions, returns suggested labels
- [x] UI: button in settings or per-project to "Auto-tag untagged tasks"
- [x] Apply silently, user can remove. Show AI-tagged glow on newly tagged

### T-026: Tag stats
- [x] GET /api/labels/stats — count + completion per label
- [x] Badge hover tooltip: total, done, open, completion %
- [x] Frontend: fetch stats, pass to Badge components

### T-027: Chat mode
Read: Section 3.3
- [x] POST /api/chat endpoint with conversation_id
- [x] Chat/Paste toggle tabs on extraction page
- [x] Chat: conversational input, agent replies + proposals
- [x] Multi-turn via conversation_id

### T-028: Proposal editing
- [x] Edit button on proposal card expands inline
- [x] Editable: title, project (Dropdown), priority, due date, labels, estimate
- [x] Save via PUT /api/proposals/{id}

### T-029: Extraction UX polish
- [x] Pulsing indicator on Extract button while running
- [x] Staggered fly-in for proposal cards
- [x] Success animation on approve (cards shrink away)
- [x] Error retry with preserved input

### T-030: Error handling
Read: Section 4.4
- [x] Backend: retry logic (Gemini 3x, Ollama 2x)
- [x] Backend: Gemini -> Ollama fallback on rate limit
- [x] Frontend: all errors -> toast, retry buttons, no silent failures

---

## Phase 4: Bubble View Migration

Read `docs/DESIGN_PHILOSOPHY.md` before starting. Reference `docs/cognito-design-system.jsx` for the visual prototype (React — translate to Svelte). Read `docs/MIGRATION_PLAN.md` for implementation details.

### T-033: ThoughtBubble component — collapsed & hover
Read: Section 5.5
- [x] `components/features/ThoughtBubble.svelte` — collapsed state: title only (2-3 lines, -webkit-line-clamp), ~200px wide, 90px min-height, 10px border-radius, `--bg-surface` background
- [x] Project corner triangle: CSS border trick in top-right using project `hex_color`, 0.3 opacity
- [x] Priority-as-presence: opacity scaling (p5=100%, p4=100%, p3=85%, p2=65%, p1=55%), title colour brightness by priority, shadow weight by priority
- [x] Hover state: card lifts 1px (translateY), shadow increases, metadata fades in (due date, first label, attachment count, subtask count) in pre-allocated space — NO size change, 100ms fade
- [x] AI-tagged state: tangerine border + inset glow (reuse existing pattern)
- [x] `kanban` prop: full column width, reduced padding, 2-line title clamp
- [x] Test with mock data in isolation before wiring to stores

### T-034: ThoughtBubble — expanded state
Read: Sections 5.5, 5.9
- [x] Click toggles expanded: card grows to ~360px, pushes neighbours aside (CSS Grid transitions or manual FLIP layout)
- [x] Expanded fields: title (editable, 16px), description (textarea, auto-grow), priority dots (clickable), due date picker, project name (with colour), label badges + add picker, attachments, done/edit buttons
- [x] Global `expandedTaskId` state: only one bubble expanded at a time
- [x] Click outside or Escape collapses expanded bubble
- [x] Auto-save: 500ms debounce for text fields, immediate for toggles/selects
- [x] Created/updated timestamps at bottom
- [x] Delete button with confirmation

### T-035: BubbleCluster component
Read: Section 5.5
- [x] `components/features/BubbleCluster.svelte` — props: project, tasks
- [x] Muted project label (uppercase, small, `--text-tertiary`) + colour dot + task count
- [x] Flex-wrap layout with 12px gap, tasks sorted by priority descending
- [x] Collapsible: click project label to collapse/expand the cluster
- [x] Completed tasks: "N completed" toggle at bottom, reduced opacity when shown
- [x] 44px bottom margin between clusters

### T-036: BubbleCanvas + home page route
Read: Section 5.5
- [x] `components/features/BubbleCanvas.svelte` — groups all tasks by project, renders BubbleCluster per project
- [x] Add `tasksByProject` derived grouping to tasks store
- [x] Update `/` route to render BubbleCanvas instead of TaskList
- [x] Global expandedTaskId state; only one bubble expanded across all clusters
- [x] Skeleton loading state (placeholder bubble shapes)

### T-037: KanbanBoard with ThoughtBubble + same-route toggle
Read: Section 5.8
- [x] Replace KanbanCard with ThoughtBubble (kanban=true) in KanbanBoard
- [x] Same-route view toggle at `/project/[id]`: Bubbles (cluster) | Kanban | List — kanban is default
- [x] Remove separate `/project/[id]/kanban` route (views are now modes on the same route)
- [x] Kanban entrance animation: columns fade in with 80ms stagger, cards appear with 50ms stagger per card (CSS transitions on opacity + transform)

### T-038: Extraction with ThoughtBubble
Read: Section 5.10
- [x] Update `/extract` to render proposals as ThoughtBubble (aiTagged=true) instead of ProposalCard
- [x] Bubble entrance animation (scale + translateY, 280ms with 100ms stagger)
- [x] Expanded proposal shows editable fields (same as T-034)
- [x] Approve All / Reject actions remain; success toast on approve

### T-039: View transition animations
Read: Section 5.7
- [x] Uses View Transitions API with custom snapshot/flight animations (native browser API, more performant than Svelte crossfade)
- [x] Shared transition keys based on task ID via `view-transition-name`
- [x] Bubble → kanban: cards animate between positions via browser view transitions
- [x] Kanban → bubble: cards release from columns, settle into cluster layout
- [x] Total animation: 300-400ms with stagger. Speed > spectacle

### T-040: Compact list view for projects
Read: Section 5.6
- [x] List mode in same-route toggle at `/project/[id]`
- [x] Compact rows: priority dots + title + first label + due date, hover highlight
- [x] Click opens SlideOver (list rows don't expand in-place)
- [x] Sort dropdown and filter bar functional
- [x] ThoughtBubble `compact` mode replaces TaskRow, keyboard nav preserved

### T-041: Cleanup deprecated components
- [x] Remove KanbanCard.svelte (replaced by ThoughtBubble kanban mode)
- [x] Remove ProposalCard.svelte (replaced by ThoughtBubble aiTagged mode)
- [x] Remove TaskRow.svelte (replaced by ThoughtBubble compact mode)
- [x] `/project/[id]/kanban` route already removed (views are modes on same route)
- [x] Verified no dead imports or references remain

---

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
- **Reference `docs/cognito-design-system.jsx`** for visual component states.
- **Test each task before moving on** — does it render? Does the API work? Does optimistic rollback work?
- **Vikunja swagger docs** at `http://tasks.epicrunze.com/api/v1/docs`.

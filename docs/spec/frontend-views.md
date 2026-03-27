# Frontend Views

## Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | `+page.svelte` | All tasks (default: bubbles view) |
| `/login` | `login/+page.svelte` | Google OAuth login |
| `/upcoming` | `upcoming/+page.svelte` | Tasks with upcoming due dates |
| `/overdue` | `overdue/+page.svelte` | Overdue tasks |
| `/project/[id]` | `project/[id]/+page.svelte` | Project tasks (default: kanban view) |
| `/project/[id]/kanban` | `project/[id]/kanban/+page.svelte` | Project kanban board |
| `/settings` | `settings/+page.svelte` | App settings |
| `/settings/labels` | `settings/labels/+page.svelte` | Label management |
| `/extract` | `extract/+page.svelte` | Task extraction interface |

## View Modes

Five view modes, toggled via `ViewOrchestrator`:

### Bubbles (default for non-project routes)
- **BubbleCanvas**: Physics-based layout container with collision detection
- **BubbleCluster**: Groups bubbles by project, handles drag-and-drop
- **ThoughtBubble**: Unified card component (renders in bubble, kanban, or compact/list mode)
- **SeedBubble**: Entry point bubble for creating new tasks

### Kanban (default for project routes)
- **KanbanBoard**: Board container with bucket management and drag-and-drop
- **KanbanColumn**: Individual bucket column with task cards

### List
- **TaskList**: Sortable list view with smart sorting, completed tasks divider

### Gantt
- **GanttChart**: Main orchestrator (drag, zoom, project grouping, today line)
- **GanttTimeline**: Sticky two-tier date header
- **GanttBar**: Task bars with drag-to-move/resize, priority coloring
- **GanttUnscheduled**: Collapsible sidebar for unscheduled tasks, drag-to-timeline

### Calendar
- **CalendarView**: Calendar-based task display

## ViewOrchestrator

`ViewOrchestrator.svelte` manages view switching:

1. Derives view mode from route: project routes default to `kanban`, others to `bubbles`
2. View mode state: `'bubbles' | 'kanban' | 'list' | 'gantt' | 'calendar'`
3. Uses buffered `displayProjectId` / `displayFilterMode` values -- updated inside `startViewTransition` callback so the browser captures old DOM before swapping
4. Syncs view mode to `viewModeStore` via `$effect`
5. Imports `snapshotCards`, `diffSnapshots`, `animateFlights` from `viewTransitionAnimator` for FLIP-style transitions

## View Transitions API

Defined in `app.css`:
- `::view-transition-group(*)`: 250ms duration, `cubic-bezier(0.22, 1, 0.36, 1)` easing
- `prefers-reduced-motion`: reduces transition duration to 0.01ms
- Custom FLIP animation via `viewTransitionAnimator.ts` for card position changes

## Stores

| Store | File | Purpose |
|-------|------|---------|
| `authStore` | `auth.svelte.ts` | Authentication state, check/login/logout |
| `bubbleStore` | `bubble.svelte.ts` | Bubble view layout and physics state |
| `calendarStore` | `calendar.svelte.ts` | Calendar view state |
| `chatStore` | `chat.svelte.ts` | AI chat messages, actions, pending actions |
| `confirmDialogStore` | `confirmDialog.svelte.ts` | Promise-based confirmation dialog |
| `filterStore` | `filter.svelte.ts` | Active filter criteria |
| `ganttStore` | `gantt.svelte.ts` | Gantt zoom, scroll, drag, sidebar collapse |
| `kanbanStore` | `kanban.svelte.ts` | Kanban board, bucket CRUD, drag-and-drop |
| `labelsStore` | `labels.svelte.ts` | Label data and stats |
| `projectIdentifiers` | `projectIdentifiers.svelte.ts` | Project icon/color identifiers |
| `projectsStore` | `projects.svelte.ts` | Project data and CRUD |
| `proposalsStore` | `proposals.svelte.ts` | Task proposal queue |
| `responsiveStore` | `responsive.svelte.ts` | Breakpoint detection (mobile/tablet/desktop) |
| `revisionsStore` | `revisions.svelte.ts` | Task revision history |
| `searchStore` | `search.svelte.ts` | Search query state |
| `sidebarRectsStore` | `sidebarRects.svelte.ts` | Sidebar element bounding rects |
| `taskDetailStore` | `taskDetail.svelte.ts` | Task detail panel open/close state |
| `tasksStore` | `tasks.svelte.ts` | Task data and CRUD |
| `toastStore` | `toast.svelte.ts` | Toast notification queue |
| `viewModeStore` | `viewMode.svelte.ts` | Current view mode state |

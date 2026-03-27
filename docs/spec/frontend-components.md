# Frontend Components

## UI Primitives (`components/ui/`)

| Component | Description |
|-----------|-------------|
| `Badge` | Colored label/status badge |
| `BottomSheet` | Mobile bottom sheet with snap points and drag gestures |
| `Button` | Standard button with variants |
| `Checkbox` | Toggle checkbox |
| `ClockPicker` | Analog/digital time picker |
| `ColorPicker` | Color selection widget |
| `ConfirmDialog` | Promise-based confirmation dialog (use `showConfirmDialog()`) |
| `DateDisplay` | Formatted date rendering with relative dates |
| `DatePicker` | Calendar date selector |
| `Dropdown` | Single-select dropdown menu |
| `Input` | Text input field |
| `Kbd` | Keyboard shortcut badge |
| `MultiSelectDropdown` | Multi-select dropdown with checkboxes |
| `PriorityIndicator` | Priority level visual indicator (1-5 scale) |
| `ScheduleDisplay` | Read-only schedule rendering |
| `SchedulePicker` | Schedule editor with ClockPicker integration |
| `Skeleton` | Loading placeholder with pulse animation |
| `SlideOver` | Desktop slide-over panel (300ms transition) |
| `Textarea` | Multi-line text input |
| `Tip` | Contextual help tooltip |
| `Toast` | Individual toast notification |
| `ToastContainer` | Toast notification stack manager |

## Feature Components (`components/features/`)

| Component | Description |
|-----------|-------------|
| `BubbleCanvas` | Physics-based bubble layout with collision detection |
| `BubbleCluster` | Project-grouped bubble container with DnD |
| `CalendarView` | Calendar-based task display |
| `FilterBar` | Filter controls (project, priority, labels, date) |
| `GanttBar` | Draggable/resizable task bar with priority colors |
| `GanttChart` | Gantt orchestrator (zoom, drag, project grouping, today line) |
| `GanttTimeline` | Sticky two-tier date header |
| `GanttUnscheduled` | Collapsible sidebar for unscheduled tasks |
| `KanbanBoard` | Kanban board with bucket management and DnD |
| `KanbanColumn` | Individual kanban bucket column |
| `MobileQuickAdd` | FAB quick-add button for mobile |
| `ProjectContextMenu` | Right-click context menu for projects |
| `SeedBubble` | Entry point bubble for new task creation |
| `ShortcutsModal` | Keyboard shortcuts reference modal |
| `Sidebar` | Navigation sidebar (64px collapsed, diamond button for AI chat) |
| `TaskDetail` | Task detail panel (SlideOver on desktop, BottomSheet on mobile) |
| `TaskDetailContent` | Shared task detail form content |
| `TaskList` | Sortable list view with completed-tasks divider |
| `TaskPanel` | Task editing panel |
| `ThinkingMargin` | Slide-out AI chat panel (via `E` hotkey or sidebar diamond) |
| `ThoughtBubble` | Unified task card (bubble, kanban, compact modes) |
| `ViewOrchestrator` | View mode switching with View Transitions API |

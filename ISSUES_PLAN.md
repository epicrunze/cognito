# Cognito Issues — Implementation Plan

## Overview
33 issues from `ISSUES.md`, organized into 9 batches by dependency. Each batch ends with testing.

---

## Batch 1: Quick Fixes & UI Polish
*No dependencies. All parallelizable.*

| # | Issue | Status |
|---|-------|--------|
| 10 | Native delete task popup | DONE |
| 18 | Seed bubble project accent | DONE |
| 24 | Completed button hover effect | DONE |
| 28 | Remove card highlight/selection | DONE |
| 33 | Updated timestamp stale | DONE |

### Issue 10 — Native delete task popup
**Problem:** Browser `confirm()` dialog is jarring and doesn't match the app's dark theme.
**Solution:** Create `ConfirmDialog.svelte` in `ui/` — centered modal, dark backdrop, red confirm button. Export a programmatic `showConfirmDialog({ title, message, confirmLabel, destructive })` from a store (similar pattern to `addToast`). Replace all `confirm()` calls in ThoughtBubble and TaskDetailContent.
**Files:** `ThoughtBubble.svelte`, `TaskDetailContent.svelte`, new `components/ui/ConfirmDialog.svelte`, new `lib/stores/confirmDialog.svelte.ts`

### Issue 18 — Seed bubble project accent
**Problem:** Seed bubble has generic border, no visual connection to its project.
**Solution:** Accept `projectColor` prop from BubbleCluster. Use it for hover border-color at ~30% opacity. In editing mode, use project color at ~50% opacity for the border. Subtle connection to the project without being loud.
**Files:** `SeedBubble.svelte`, `BubbleCluster.svelte`

### Issue 24 — Completed button hover effect
**Problem:** "Completed (N)" toggle in BubbleCluster has no hover feedback — user can't tell it's clickable.
**Solution:** Add CSS hover state: `opacity: 0.8` (up from 0.5), subtle background `var(--bg-surface-hover)` with rounded padding, and smooth transition. Already has `cursor: pointer`.
**Files:** `BubbleCluster.svelte`

### Issue 28 — Remove card highlight/selection
**Problem:** Selected card styling (accent border) breaks visual flow in card view.
**Solution:** Remove the `selected` visual styling (accent border + accent-subtle background) from ThoughtBubble's collapsed/compact state. Keep the `selected` prop for functional task-detail sync but eliminate the visual distinction that breaks flow. The task detail side panel already indicates which task is being viewed.
**Files:** `ThoughtBubble.svelte`

### Issue 33 — Updated timestamp stale
**Problem:** Task `updated` field only refreshes on page reload.
**Solution:** After any `updateTask` API call succeeds, patch the local task's `updated` field with the current ISO timestamp (or from the API response if it returns the updated task). In `taskMutations.ts`, after the optimistic update API call resolves, update the `updated` field in the store.
**Files:** `taskMutations.ts`

**Test after batch:** `npm run check`

---

## Batch 2: Confirmation Dialogs & Delete Flows
*Depends on ConfirmDialog from Batch 1.*

| # | Issue | Status |
|---|-------|--------|
| 11 | Project delete confirmation | DONE |
| 14 | Delete labels + auto-cleanup | DONE |
| 19 | Project drag-drop indicator | DONE (CSS implemented) |

### Issue 11 — Project delete more involved
**Problem:** Project deletion is too easy to trigger accidentally — big destructive change needs more friction.
**Solution:** GitHub-style type-to-confirm: a modal (using ConfirmDialog from Batch 1) that shows "Delete [project name]?" with a warning about deleting all tasks. A text input requires typing the exact project name before the Delete button enables (red, disabled until match). Cancel button always available.
**Files:** `ProjectContextMenu.svelte`, `ConfirmDialog.svelte`

### Issue 14 — Delete labels + auto-cleanup
**Problem:** No UI to delete labels. Unused labels accumulate.
**Solution:**
- **Frontend:** Add a delete button (trash icon) per label in the labels settings page. Use ConfirmDialog from Batch 1 for confirmation.
- **Backend:** Add `POST /api/labels/cleanup` endpoint that fetches all label stats, identifies labels with 0 tasks, and deletes them via Vikunja API. Frontend gets a "Clean up unused labels" button that calls this endpoint.
- **Auto-delete:** Optionally run cleanup automatically on a schedule or when navigating to labels settings.
**Files:** Backend `routers/labels.py`, frontend `settings/labels/+page.svelte`

### Issue 19 — Project drag-drop indicator
**Problem:** When dragging projects in sidebar, it's unclear where the project will land.
**Solution:** Render a 2px accent-colored horizontal line at the `dragOverIdx` position between sidebar project items during drag. Standard drop indicator pattern.
**Files:** `Sidebar.svelte`

**Test after batch:** `npm run check` + `uv run pytest tests/ -v`

---

## Batch 3: Filter System Overhaul
*After Batch 1. Can run parallel with Batches 4 and 5.*

| # | Issue | Status |
|---|-------|--------|
| 12 | Filter button positioning | TODO |
| 13 | Label filter → dropdown | TODO |
| 15 | Multi-filter UX (dates, subtasks) | TODO |
| 22 | Kanban filtering + density | TODO |

### Issue 12 — Filter button persistent everywhere
**Problem:** Filter button shows on all pages including settings where it does nothing.
**Solution:** Integrate search and filter into the top bar. Search input is always present (for global search). Filter toggle button is only rendered on task routes (All Tasks, project views, upcoming, overdue) — hidden on settings. The FilterBar dropdown still slides down below top bar when toggled, but the trigger lives in the top bar. This saves vertical space vs a separate sub-bar.
**Files:** `+layout.svelte`, `FilterBar.svelte`

### Issue 13 — Label filter condensed
**Problem:** Too many labels overflow horizontally as inline pills — unusable with many labels.
**Solution:** Replace inline label pills with a `MultiSelectDropdown.svelte` component. Button shows "Labels (N)" with count of selected. Opens a scrollable dropdown with checkboxes per label, colored dots, and a search/filter input at the top. Selected labels shown as small chips below the button.
**Files:** `FilterBar.svelte`, new `components/ui/MultiSelectDropdown.svelte`

### Issue 15 — Multi-filter UX
**Problem:** No multi-select labels, no due date or subtask filters.
**Solution:** Redesigned filter bar as dropdown-based controls:
- **Status:** dropdown (All / Active / Completed)
- **Priority:** dropdown with checkboxes (multi-select 1-5)
- **Labels:** MultiSelectDropdown (from #13)
- **Due date:** dropdown with presets: Any, Overdue, Today, This week, This month, No due date, Custom range (opens date range picker)
- **Has subtasks:** checkbox toggle
Extend `filterStore` with `dueDateFilter` (preset string or `{ from, to }` range) and `hasSubtasks: boolean | null`. Apply filters in BubbleCanvas and Kanban.
**Files:** `filterStore`, `FilterBar.svelte`

### Issue 22 — Kanban filtering + density
**Problem:** No filtering per kanban column. Cards are too large for kanban.
**Solution:** Two changes:
1. **Apply global filters to kanban:** filterStore filters (status, priority, labels, due date) apply to kanban tasks too — currently they bypass filtering.
2. **Density toggle:** A compact/full toggle in the kanban view bar. Compact mode: smaller padding (8px), smaller font (13px), title clamped to 2 lines, no icon row — just title + top-border color. Full mode: current size. Store preference in localStorage.
**Files:** `KanbanBoard.svelte`, `KanbanColumn.svelte`, `ThoughtBubble.svelte`

**Test after batch:** `npm run check`

---

## Batch 4: Card Enhancements
*After Batch 1. Can run parallel with Batches 3 and 5.*

| # | Issue | Status |
|---|-------|--------|
| 1 | Task sidebar field sync | DONE |
| 16 | Attachment/subtask indicators | DONE |
| 17 | Cards too minimalistic + overdue | DONE |
| 23 | Kanban column indicators | DONE |
| 3 | Sidebar project readability | DONE |

### Issue 1 — Task sidebar editor field sync
**Problem:** Side editor doesn't always update when task is edited from the expanded card.
**Solution:** Add a secondary `$effect` in `TaskDetailContent.svelte` that watches `task.updated` timestamp. When it changes (and the user hasn't changed `editKey`), selectively sync fields that the user isn't actively editing. Track which fields have focus/dirty state to avoid clobbering user input. Fields to sync: title, description, priority, due_date, labels, done status.
**Files:** `TaskDetailContent.svelte`

### Issue 16 — Attachment/subtask icon indicators
**Problem:** No visual indication of attachments or subtasks on collapsed cards.
**Solution:** Small muted icons always visible below the title on collapsed cards: paperclip + count for attachments, checkbox + progress (e.g. "1/4") for subtasks, red dot for overdue. These are passive — 11-12px, tertiary color, no interaction needed.
**Files:** `ThoughtBubble.svelte`

### Issue 17 — Cards too minimalistic + overdue highlighting
**Problem:** Cards show only title. No hover affordances. No overdue visual signal.
**Solution:** Three layers of info density:
1. **Default (no hover):** Title + small icon row (attachments, subtasks, overdue dot) — always visible.
2. **Hover:** Due date and first label fade in below icons. A quick-complete circle/checkbox appears in the top-left corner — clicking it toggles done without expanding.
3. **Expanded:** Full detail (description, all labels, priority dots, dates, edit controls).
Overdue tasks also get a subtle warm 2px left-border (`var(--overdue)` color) that's always visible.
**Files:** `ThoughtBubble.svelte`

### Issue 23 — Kanban column indicators
**Problem:** Cards look identical regardless of which kanban column they're in.
**Solution:** Subtle 2px top-border color per column: To-Do (neutral/default border), Doing (accent blue), Done (green `var(--done)`). Done column cards also get checkmark icon. When a task is dragged to the Done bucket, automatically mark it as complete via `toggleDone`. Column colors defined as a config map in KanbanBoard.
**Files:** `KanbanColumn.svelte`, `KanbanBoard.svelte`

### Issue 3 — Sidebar project readability
**Problem:** Project abbreviations are illegible. No way to tell which project is which at a glance.
**Solution:** Replace micro-cluster dots with auto-generated emoji based on project name (e.g. "PhD" -> graduation cap). User can override via project settings/context menu. Full name shows on hover tooltip (reuse `Tip` component pattern). Since native emojis can't be CSS-styled to match the theme, use a curated set of SVG icons or apply CSS `grayscale()`+`brightness()` filter to emojis to keep them muted and consistent with the dark theme. Task count dots remain beside each icon.
**Files:** `Sidebar.svelte`, `ProjectContextMenu.svelte`

**Test after batch:** `npm run check`

---

## Batch 5: Animation & Transition Fixes
*After Batch 1. Can run parallel with Batches 3 and 4.*

| # | Issue | Status |
|---|-------|--------|
| 2 | View transition stuttering | TODO |
| 21 | List→bubble animation wrong | TODO |
| 20 | Kanban task opening broken | TODO |

### Issue 2 — View transition animations stutter
**Problem:** Switching views and opening/closing bubbles sometimes stutters.
**Solution:** **Needs deeper investigation before changes.** Build a testbed environment first to isolate and reproduce stuttering. Then systematically test fixes: reduce `MAX_ANIMATED`, add `will-change` hints, use `requestAnimationFrame` scheduling, test with different card counts. If View Transitions API remains unreliable, evaluate simpler CSS-based fallback. Do not change production code until testbed validates the approach.
**Files:** `viewTransitionAnimator.ts`, `ViewOrchestrator.svelte`

### Issue 21 — Cards display big then shrink
**Problem:** When switching from list to bubbles/kanban, cards render large then shrink — looks trippy.
**Solution:** Same testbed as Issue #2. Root cause: entering cards render at full size before flight animation applies scale-down. Fix: set entering cards to `opacity: 0` initially, animate opacity+transform together so cards are invisible until the flight animation starts. Test in testbed first.
**Files:** `viewTransitionAnimator.ts`

### Issue 20 — Kanban task opening broken
**Problem:** Clicking a kanban card tries to expand inline instead of opening the side viewer. Side viewer also competes for screen space with kanban columns.
**Solution:** Two fixes:
1. Pass `kanban={true}` to ThoughtBubble in KanbanColumn — disable inline expand, only call `taskDetailStore.open(taskId)` on click.
2. In kanban mode, TaskDetail renders as a **draggable overlay panel** (absolute positioned, z-index above kanban) rather than taking flex space. Kanban columns stay full width underneath. Panel can be repositioned by dragging its header bar. Click outside or Esc to close. Store last position in localStorage so it remembers between sessions.
**Files:** `KanbanColumn.svelte`, `ThoughtBubble.svelte`, `TaskDetail.svelte`

**Test after batch:** `npm run check`, manual visual verification

---

## Batch 6: Settings Redesign + Labels
*After Batches 2 and 3.*

| # | Issue | Status |
|---|-------|--------|
| 7 | Settings page redesign | TODO |
| 8 | Label colors + AI descriptions | TODO |
| 9 | More color options | TODO |
| 31 | AI behavior tab enhancements | TODO |
| 32 | Label statistics | TODO |

### Issue 7 — Settings not organized
**Problem:** Settings is a flat list of cards — hard to navigate.
**Solution:** Tabbed sidebar layout within the settings page. Left tab list: Account, AI & Agent, Labels, History. Each tab shows its content in the right panel. Keeps everything on one route but organized by category. Active tab highlighted with accent.
**Files:** `settings/+page.svelte`

### Issue 8 — Label colors + AI descriptions
**Problem:** Can't change label colors. No way to auto-generate descriptions.
**Solution:**
- **Color editing:** Add a color swatch row per label in the labels settings page (reuse ColorPicker from Issue #9). Changing color calls Vikunja's label update API.
- **AI description generation:** New backend endpoint `POST /api/labels/{id}/generate-description` that fetches tasks with that label, sends them to the LLM with a prompt asking "Based on these tasks, describe what this label category means in 1-2 sentences." Frontend gets a "Generate" button per label that calls this endpoint and populates the description textarea.
**Files:** Backend `routers/labels.py`, `services/tagger.py`, frontend `settings/labels/+page.svelte`

### Issue 9 — More color options
**Problem:** Only 8 colors available for projects/labels.
**Solution:** Custom HSL picker matching the dark theme. Keep 8 preset swatches as quick options. Below presets, a "Custom..." button opens an inline HSL picker: hue strip + saturation/brightness square, hex input field. Fully themed with dark background. Reusable `ColorPicker.svelte` component used by both project creation and label settings.
**Files:** New `components/ui/ColorPicker.svelte`

### Issue 31 — AI behavior tab
**Problem:** AI settings only shows a prompt override textarea. Need full system prompt, tool descriptions, chat history.
**Solution:** In the "AI & Agent" settings tab:
1. **Full system prompt** (read-only collapsible) — fetch default prompt from new `GET /api/config/system-prompt` endpoint.
2. **Override textarea** — existing editable override with auto-save.
3. **Available tools** — collapsible list of all tools (extraction + modification) with descriptions. Hardcode or fetch from new `GET /api/config/tools` endpoint.
4. **Chat history** — link to dedicated `/settings/chat-history` route. Full conversation replay showing all messages, tool calls, proposals, and actions returned. Like a debug log for AI interactions.
Backend: new `GET /api/chat/history` endpoint listing all conversations with pagination. New `GET /api/chat/{id}/messages` endpoint for full conversation messages.
**Files:** `settings/+page.svelte`, new `settings/chat-history/+page.svelte`, backend `routers/config.py`, `routers/chat.py`

### Issue 32 — Label statistics
**Problem:** Label stats exist in backend but aren't displayed.
**Solution:** In the labels settings section, show per-label stats inline: "N tasks (M open / K done)". Display as a small horizontal bar (label color) showing open/done ratio. Use existing `GET /api/labels/stats` endpoint. Fetch stats on mount and after any label change.
**Files:** `settings/labels/+page.svelte`, `labelsStore`

**Test after batch:** `npm run check` + `uv run pytest tests/ -v`

---

## Batch 7: Smart Sorting & Task Density
*After Batch 3 (filter system).*

| # | Issue | Status |
|---|-------|--------|
| 27 | Smart sorting algorithm | TODO |
| 26 | Max cards / focus mode | TODO |
| 25 | AI extract positioning | TODO |

### Issue 27 — Smart sorting
**Problem:** No intelligent sorting that considers due date, priority, and task urgency together.
**Solution:** Composite score algorithm:
```
score = 0.5 * urgency + 0.35 * priority + 0.15 * recency

urgency:
  overdue by N days: 1.0 + 0.02*N (capped 1.5)
  due today: 0.9
  due in 1-3 days: 0.7
  due this week: 0.5
  due this month: 0.3
  no due date: 0.15

priority: p/5 (linear 0.2-1.0)
recency: based on updated_at (higher = more recently touched)
```
Sort descending by composite score. Create `lib/smartSort.ts` utility. Use as default sort in BubbleCanvas and All Tasks view. Within each cluster, sort by score instead of raw priority.
**Files:** New `lib/smartSort.ts`, `BubbleCanvas.svelte`

### Issue 26 — Max cards / focus mode
**Problem:** All tasks render at once. No way to focus on what's most important.
**Solution:** A "Focus" toggle in the top view bar (next to view mode switcher). When active, shows only the top ~8 most important tasks across all projects, sorted by the composite score from Issue #27. Clean, minimal layout — "what do I work on now?" Toggle off to see everything. Focus mode works with the smart sort algorithm.
**Files:** `+layout.svelte` or `ViewOrchestrator.svelte`, `BubbleCanvas.svelte`

### Issue 25 — AI extract positioning
**Problem:** Current sidebar position may not be ideal. Maybe top or floating button?
**Solution:** Replace the sidebar diamond trigger with a **floating action button** (bottom-right corner). The diamond button expands into a chat overlay panel that grows upward. Always accessible from any view. Remove the diamond from the sidebar. Keep `E` hotkey as a toggle. The panel should be similar to Intercom/chat widgets — floating, non-intrusive, doesn't push content.
**Files:** `Sidebar.svelte`, `+layout.svelte`, `ThinkingMargin.svelte`

**Test after batch:** `npm run check`

---

## Batch 8: Celebration & Polish
*After Batch 4 (card enhancements).*

| # | Issue | Status |
|---|-------|--------|
| 4 | Project creation visual weight | TODO |
| 5 | Task completion celebration | TODO |
| 29 | Side window + new task snap | DONE |
| 30 | Auto-label in editor | TODO |

### Issue 4 — Project creation lackluster
**Problem:** Creating a project doesn't feel like a significant moment.
**Solution:** Enhance the existing sidebar inline creation: add color picker + icon picker to the pop-out panel. After creation, the new project item does a scale-up animation with a project-color glow that fades over 1.5s. The canvas shows a welcoming empty state for the new project (e.g. "Your first thought goes here..." with a subtle animation pointing to the seed bubble).
**Files:** `Sidebar.svelte`

### Issue 5 — Task completion celebration
**Problem:** Checking off a task has no celebration — should be a moment of satisfaction.
**Solution:** Subtle particle burst animation:
1. Hover checkbox (from Issue #17) fills with checkmark (scale pulse).
2. 3-5 small dots in the task's project color radiate outward from the checkbox and fade over 400ms.
3. Card smoothly transitions to 0.65 opacity (completed state).
Total ~500ms. Create a `celebrate()` utility that injects temporary DOM elements for particles. Fire from ThoughtBubble's done toggle handler.
**Files:** `ThoughtBubble.svelte`, `taskMutations.ts`, new `lib/celebrate.ts`

### Issue 29 — New task snap with side window
**Problem:** Creating a task while side panel is open doesn't navigate to the new task.
**Solution:** In `SeedBubble.svelte`'s `submit()` function, after creating a task, check if `taskDetailStore.isOpen`. If so, call `taskDetailStore.open(created.id)` to snap the side panel to the new task. This way the user immediately sees the full editor for their new task.
**Files:** `SeedBubble.svelte`

### Issue 30 — Auto-label in editor
**Problem:** No auto-label option when adding labels in the task editor.
**Solution:** Add a small "Auto" button next to the "+ Add label" section in `TaskDetailContent.svelte`. When clicked, call existing `POST /api/tasks/auto-tag` for that single task. Show suggested labels as a preview (pills with "Accept" / "Dismiss" actions) before applying. Accepted labels get added via the label API.
**Files:** `TaskDetailContent.svelte`

**Test after batch:** `npm run check`

---

## Batch 9: Undo/Redo Extension
*After all other batches.*

| # | Issue | Status |
|---|-------|--------|
| 6 | Undo/redo for non-AI edits | TODO |

### Issue 6 — Undo/redo for manual edits
**Problem:** Undo/redo only works for AI-originated changes, not manual edits.
**Solution:** Track all manual field changes (title, description, priority, due date, labels, done toggle) as revisions with `source='manual'`.
- **Backend:** Add `source='manual'` support to `RevisionService.record()`. New endpoint `POST /api/tasks/{id}/revision` that accepts before/after state.
- **Frontend:** In `taskMutations.ts`, before calling `updateTask`, snapshot current task state. After API succeeds, POST the revision with `source='manual'`. The existing undo/redo buttons pick up manual revisions in the stack.
- Per the original issue: manual revisions do NOT need to appear in the settings revision log (filter by source != 'manual' in settings display).
**Files:** Backend `services/revisions.py`, frontend `taskMutations.ts`, `revisionsStore`

**Test after batch:** `npm run check` + `uv run pytest tests/ -v`

---

## Batch Dependency Graph

```
Batch 1 (Quick fixes)
  ├── Batch 2 (Delete flows) ─── Batch 6 (Settings + Labels)
  ├── Batch 3 (Filters) ──────── Batch 7 (Sorting)
  ├── Batch 4 (Cards) ─────────── Batch 8 (Celebrations)
  └── Batch 5 (Animations)

Batch 9 (Undo/redo) — after all other batches
```

**Parallel opportunities:**
- Batches 3, 4, 5 can all run in parallel after Batch 2
- Batches 6, 7 can run in parallel after Batch 3
- Batch 8 after Batch 4

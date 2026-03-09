# Cognito Frontend Migration Plan: List → Bubble View

This document describes how to migrate the existing list-based task UI to the new "thought bubble" paradigm. Read `docs/DESIGN_PHILOSOPHY.md` for the full design vision. Reference `cognito-design-system.jsx` for the visual prototype (React — translate to Svelte).

## Summary of Changes

The app is shifting from a Linear-style task list to a Google Keep-style spatial layout. Tasks are "thought bubbles" that cluster by project, communicate priority through visual weight (not explicit indicators), and expand in-place when clicked. The task list still exists as a secondary view within projects.

## What's Changing

### Home Page (All Thoughts)
**Before:** Task list with rows — checkbox, priority dots, title, metadata, date.
**After:** Bubble clusters grouped by project. Each cluster has a muted label and a masonry-wrapped collection of small cards. Priority determines visual presence (opacity, text brightness, shadow weight), not position. High priority = prominent. Low priority = faded.

### Project View
**Before:** Same task list, filtered to one project. Kanban as a secondary view.
**After:** Kanban is the DEFAULT view when clicking a project. List is the secondary view (compact Linear-style rows for sorting/filtering).

### Task Detail
**Before:** SlideOver panel from the right (480px).
**After:** Expand in-place. Clicking a bubble causes it to grow, pushing neighbours aside. Expanded state shows all fields (title editable, description, priority dots, due date, labels, attachments, done/edit buttons). Click outside or Escape to collapse.

### AI Extraction
**Before:** Proposals stream in as list items with tangerine borders.
**After:** Proposals stream in as bubble-shaped cards (same ThoughtBubble component). On approve, they conceptually "fly" to their project cluster (or show success toast).

### Kanban Transition
**Before:** Page switch to kanban view.
**After:** When entering a project kanban, cards should animate into their columns. In the real Svelte implementation, use `animate:flip` from `svelte/animate` and `crossfade` from `svelte/transition` with `send`/`receive` to make the same DOM elements move between layouts. The kanban columns should fade in first, then cards animate to their positions.

Reference for Svelte FLIP: https://svelte.dev/tutorial/svelte/animations
Reference for crossfade between containers: https://svelte.dev/tutorial/svelte/deferred-transitions

## New Components

### ThoughtBubble.svelte (CORE — replaces TaskRow)
The most important component in the app. This is both the bubble and the expanded detail view.

**Props:** task, expanded, onToggle, kanban (boolean — adjusts sizing for kanban layout)

**Default state (collapsed):**
- Fixed minimum height (~90px) so hover info has room without resizing
- Title only, 2-3 lines max, clipped with -webkit-line-clamp
- No priority dots, no labels, no dates visible at rest
- Priority expressed through: opacity (p5=100%, p3=85%, p2=65%, p1=45%), title text colour (brighter = higher), shadow weight
- Project corner colour: small CSS triangle in top-right corner using the project's hex_color
- AI-tagged: tangerine border + inset glow
- Width: ~200px. Border-radius: 10px. Background: --bg-surface.

**Hover state (NO size change):**
- Card lifts 1px (translateY), shadow increases
- Below the title (in the existing empty space), show: due date, first label, attachment count, subtask count
- These fade in (100ms) and fade out on mouse leave
- The card does NOT grow. The hover info fits in pre-allocated space.

**Expanded state (click to toggle):**
- Card grows to ~360px wide. Neighbours push aside (use Svelte animate:flip or CSS grid transitions)
- Shows: title (editable, 16px), description (textarea, auto-grow), priority dots (now visible, clickable), due date picker, project name (with colour), labels (badges + add), attachments, subtasks, done/edit buttons
- Created/updated timestamps at bottom
- Auto-save: 500ms debounce text, immediate toggles

**Collapse:** Click outside or Escape. Animate back to default size.

### BubbleCluster.svelte (replaces TaskList for home page)
Groups ThoughtBubbles by project.

**Props:** project, tasks

**Layout:**
- Muted project label (uppercase, small, tertiary colour) + colour dot + task count
- Masonry-like flex-wrap layout with 12px gap
- Tasks sorted by priority descending within the cluster
- Completed tasks: "N completed" toggle at bottom, reduced opacity when shown
- Generous bottom margin (44px) between clusters

### BubbleCanvas.svelte (new — home page)
Renders all BubbleClusters.

**Props:** tasks (all), projects

Fetches all tasks, groups by project, renders a BubbleCluster for each. Handles the global expanded state (only one bubble expanded at a time — click outside to collapse).

### KanbanBoard.svelte (modified)
Now the default project view. Same data fetching (views → buckets → tasks) but uses ThoughtBubble in kanban mode instead of KanbanCard.

**Animation on enter:** Columns fade in with stagger (80ms per column). Cards within each column appear with stagger (50ms per card within a column, offset by column delay). Use CSS transitions on opacity + transform for the entrance.

**FLIP transition from bubbles:** When navigating from All Thoughts → Project kanban, capture bubble positions before the route change, then use Svelte's `crossfade` with `send`/`receive` to animate cards from bubble positions to kanban positions. This requires the ThoughtBubble to use keyed each blocks and shared transition keys.

### TaskList.svelte (simplified — secondary view)
Compact Linear-style list. Only used within a project as an alternative to kanban.
Priority dots + title + first label + due date. One tight row per task. Hover highlight. Click to expand (could open a slide-over here since list rows don't expand well in-place).

## Components to Remove/Replace

| Old Component | Replacement |
|---|---|
| TaskRow.svelte | ThoughtBubble.svelte (collapsed state) |
| TaskDetail.svelte (SlideOver) | ThoughtBubble.svelte (expanded state) |
| KanbanCard.svelte | ThoughtBubble.svelte (kanban=true) |
| ProposalCard.svelte | ThoughtBubble.svelte (with aiTagged=true) |
| TaskList.svelte (as home page) | BubbleCanvas.svelte + BubbleCluster.svelte |

## Routes Change

| Route | Before | After |
|---|---|---|
| `/` | Task list (all tasks) | BubbleCanvas (all clusters) |
| `/project/[id]` | Task list (filtered) | KanbanBoard (default) |
| `/project/[id]/kanban` | Kanban board | Remove — kanban is now the default at `/project/[id]` |
| `/project/[id]/list` | N/A | ListView (secondary) |
| `/extract` | Extraction panel | Same, but proposals use ThoughtBubble |

## Stores Change

The task store needs a new method for grouping:

```typescript
// New derived store
const tasksByProject = $derived(
  Object.groupBy($tasks, task => task.project_id)
);
```

The expanded state should be global (one bubble expanded at a time):
```typescript
let expandedTaskId = $state<number | null>(null);
```

## CSS / Design Token Updates

No token changes needed — same dark theme, same tangerine accent. New CSS needed:

```css
/* Bubble fixed height for hover info space */
.thought-bubble { min-height: 90px; display: flex; flex-direction: column; }
.thought-bubble .title { /* title at top */ }
.thought-bubble .spacer { flex: 1; } /* pushes hover info to bottom */
.thought-bubble .hover-info { min-height: 20px; } /* reserved space */

/* Project corner triangle */
.thought-bubble .project-corner {
  position: absolute; top: 0; right: 0;
  width: 0; height: 0;
  border-left: 18px solid transparent;
  border-top: 18px solid var(--project-color);
  border-top-right-radius: 9px;
  opacity: 0.3;
}

/* Priority as presence */
.thought-bubble[data-priority="5"] { opacity: 1; }
.thought-bubble[data-priority="3"] { opacity: 0.85; }
.thought-bubble[data-priority="2"] { opacity: 0.65; }
.thought-bubble[data-priority="1"] { opacity: 0.45; }
```

## Implementation Order

1. **ThoughtBubble.svelte** — build this first. It replaces 4 components. Get the collapsed/hover/expanded states right before anything else. Test with mock data.

2. **BubbleCluster.svelte** — wrap ThoughtBubbles in project groups. Test the masonry layout, priority sorting, completed toggle.

3. **BubbleCanvas.svelte + route change** — make `/` render the bubble canvas instead of the task list. Wire to real data.

4. **KanbanBoard modification** — switch to ThoughtBubble in kanban mode. Make kanban the default project view. Add entrance animation (columns fade, cards stagger).

5. **Extraction update** — swap ProposalCard for ThoughtBubble with aiTagged.

6. **FLIP animation** — add crossfade/send/receive between bubble canvas and kanban. This is the polish step — get everything working without animation first, then add it.

7. **List view** — build the compact secondary list view for projects.

## Key Technical Notes

- **One expanded bubble at a time.** Global state. Clicking a bubble sets `expandedTaskId`. Clicking outside (or Escape) sets it to null. Don't allow multiple expanded simultaneously.

- **Hover info must NOT resize the card.** The card has a fixed `min-height` and uses `flex-direction: column` with a spacer so the hover info renders in pre-allocated space at the bottom.

- **The FLIP animation is the hardest part.** Svelte's `animate:flip` works within a single `{#each}` block. Moving cards between the bubble layout and kanban layout requires `crossfade` with `send`/`receive` across different `{#each}` blocks. Study the Svelte deferred transitions tutorial before implementing. Consider using the View Transitions API as a fallback if crossfade proves difficult across route changes.

- **Kanban entrance is simpler than FLIP.** Columns and cards can use CSS transitions on opacity + transform with staggered `transition-delay`. No Svelte animation primitives needed — just conditional CSS classes.

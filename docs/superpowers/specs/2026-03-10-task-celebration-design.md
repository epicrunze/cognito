# Task Completion Celebration System — Design Spec

## Context

Completing a task in Cognito currently has a minimal animation: a 200ms button pulse + 4-5 tiny confetti dots that travel ~25px and fade in 400ms. This only fires in 2 of 6 completion paths (bubble quick-complete and expanded Done button). The result is unsatisfying — completing a task should feel triumphant and rewarding, especially for high-priority items.

## Requirements

- **Triumphant, bold celebrations** that make completing tasks feel like winning
- **Priority-scaled intensity** — P1 urgent gets full fireworks, P0/none gets a modest but satisfying burst
- **All 6 completion paths** must celebrate (currently only 2 do)
- **Three effect layers:** confetti shower, sparkle trails, card transformation
- **Optional sound effects** — off by default, toggle in settings
- **Performance** — smooth 60fps even with 100 particles

## Architecture

### Canvas Particle System (`celebrate.ts`)

Replace the current DOM-based approach with a singleton canvas overlay.

**`CelebrationCanvas`** — singleton class:
- Lazily creates a fixed, full-viewport `<canvas>` with `pointer-events: none; z-index: 9999`
- `requestAnimationFrame` loop that auto-starts/stops based on active particle count
- Manages two particle types: confetti and sparkles

**Public API:**
```ts
celebrate(origin: {x: number, y: number}, tier: CelebrationTier, color: string): void
getTier(priority: number): CelebrationTier
```

**Particle types:**
- **Confetti** — small colored rectangles/circles that burst upward from origin, then fall with gravity + horizontal drift + rotation. Colors: mix of project color, accent (#E8772E), done green (#5BBC6E), and white.
- **Sparkles** — bright dots that arc outward from origin following curved paths, leaving fading trail segments. Color: golden/tangerine gradient.

### Celebration Tiers

| Priority | Tier | Confetti Count | Spread | Sparkle Arcs | Duration |
|----------|------|---------------|--------|--------------|----------|
| P1 Urgent (5) | `epic` | 80-100 | Full viewport | 6-8 | 1200ms |
| P2 High (4) | `grand` | 50-60 | Wide | 4-5 | 1000ms |
| P3 Medium (3) | `standard` | 25-35 | Moderate | 2-3 | 800ms |
| P4 Low (2) | `modest` | 10-15 | Localized | 1 | 600ms |
| P0 None (0/1) | `minimal` | 5-8 | Tight | 0 | 400ms |

### Card Transformation (CSS/Svelte)

On completion, the task's visual element participates:
1. **Checkbox animation** — animated checkmark (SVG stroke draw-on, 300ms)
2. **Green flash** — brief `--color-done` glow/border flash on the card/row
3. **Scale pulse** — subtle scale(1 → 1.05 → 1) on the card
4. **Fade to completed state** — card transitions to 0.65 opacity / completed styling

Card transformation is CSS-driven and works independently from the canvas effects.

### Centralized Triggering

**Element Registry** (`celebrationRegistry` in `celebrate.ts`):
- Components register their completion trigger element: `registerCelebrationElement(taskId, element)`
- Cleanup on unmount: `unregisterCelebrationElement(taskId)`

**Triggering in `toggleDone()`** (`taskMutations.ts`):
- When marking done (not undoing), look up the task's priority and registered element
- Get element bounding rect for origin coordinates
- Call `celebrate(origin, getTier(priority), projectColor)`
- Fallback: if no element registered, use viewport center

This centralizes all celebration logic — individual components only need to register their element.

### Sound Effects

- Tiny audio files as base64 data URIs embedded in code (~2-5KB each)
- 5 sounds matching tiers: triumphant chime → gentle tick
- **Off by default** — `localStorage` key `cognito-celebration-sounds`
- Settings toggle: "Celebration sounds" checkbox in settings page
- Played via `AudioContext` for low latency

### Completion Paths

All 6 paths trigger celebration through centralized `toggleDone()`:

1. **ThoughtBubble collapsed** — quick-complete button registers itself
2. **ThoughtBubble expanded** — "Done" button registers itself
3. **ThoughtBubble compact/list** — checkbox registers itself
4. **TaskList keyboard 'x'** — uses selected row's registered checkbox
5. **TaskDetailContent side panel** — checkbox registers itself
6. **KanbanColumn drag-to-done** — card element registers itself

## Files Modified

- `frontend/src/lib/celebrate.ts` — full rewrite: canvas particle system + registry
- `frontend/src/lib/stores/taskMutations.ts` — add celebration call in `toggleDone()`
- `frontend/src/components/features/ThoughtBubble.svelte` — register elements, add card transformation CSS, remove old `celebrate()` calls
- `frontend/src/components/features/TaskDetailContent.svelte` — register checkbox element
- `frontend/src/components/features/TaskList.svelte` — register row elements
- `frontend/src/components/features/KanbanColumn.svelte` — register card elements
- `frontend/src/routes/settings/+page.svelte` — add celebration sounds toggle
- `frontend/src/app.css` — add card transformation keyframes

## Verification

1. Complete a task via each of the 6 paths — all should show celebration
2. Complete tasks of different priorities — visual intensity should scale
3. Enable celebration sounds in settings — verify audio plays
4. Verify 60fps during epic-tier celebration (DevTools Performance tab)
5. Verify canvas is cleaned up (removed/hidden) when no particles active
6. Run `npm run check` — no TypeScript errors

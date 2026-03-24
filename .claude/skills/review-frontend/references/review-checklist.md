# Frontend Review Checklist

Structured criteria for visual and code analysis, derived from `docs/DESIGN_PHILOSOPHY.md`.

---

## Visual Criteria

### 1. Metaphor Alignment
- [ ] The app feels like a "thinking space", not a task manager
- [ ] Bubbles feel like thoughts floating on a surface, not rows in a table
- [ ] Closer to Google Keep energy than Linear energy
- [ ] Each thought has its own presence as a spatial object

### 2. Color Restraint
- [ ] Tangerine (#E8772E) used ONLY for actions and AI features
- [ ] Bubble surfaces are neutral (not colored by project)
- [ ] Overdue tasks: subtle warmth (faint red-shifted border or dot), not alarming
- [ ] No excessive use of accent color

### 3. Information Density
- [ ] Default bubble: title + subtle indicator row only
- [ ] Indicators (overdue dot, subtask progress, attachment count) at 0.55 opacity, 11px
- [ ] Labels, dates, description appear on HOVER, not by default
- [ ] Priority communicated through position/weight, not explicit indicators at rest

### 4. Visual Hierarchy
- [ ] High priority items positioned top-left of cluster
- [ ] Low priority items drift down-right, genuinely fading
- [ ] Urgent items have more visual weight (slightly more visible border, full primary color title)
- [ ] No explicit priority indicators visible at rest (dots only on expand)

### 5. Spacing & Breathing Room
- [ ] Clusters separated by generous whitespace, not borders or dividers
- [ ] No internal borders within cards
- [ ] Content flows naturally within cards
- [ ] Organic masonry layout, not uniform grid

### 6. Typography
- [ ] IBM Plex Sans used consistently
- [ ] Correct weights: 400 (body), 500 (medium), 600 (semibold)
- [ ] Size scale: xs (0.75rem), sm (0.875rem), base (1rem), lg (1.125rem), xl (1.25rem)
- [ ] Line heights: tight (1.25), normal (1.5), relaxed (1.625)

### 7. Dark Theme
- [ ] Dark background functions as "surface of thought"
- [ ] Bubbles are lighter surfaces floating on dark ground
- [ ] Light-on-dark inversion creates "thoughts emerging from background"
- [ ] Shadows use rgba(0,0,0) with appropriate opacity per token

### 8. Interactions (check from screenshots + code)
- [ ] Hover: subtle lift (shadow increase), due date + first label fade in, quick-complete circle appears
- [ ] Expanded bubble: pushes neighbours aside organically
- [ ] Bubble→kanban transition: same cards animate into columns (not page transition)
- [ ] All animations are 150ms (hover), 200ms (panels), 300ms (slide-overs)

### 9. Anti-Patterns (should NOT be present)
- [ ] No uniform grid layout (masonry is correct)
- [ ] No too-dense default bubbles (title + indicators only)
- [ ] No page transitions between views (cards should move, not rebuild)
- [ ] No dominating sidebar (thin, quiet, minimal)
- [ ] No decorative animation (every motion communicates state change)
- [ ] No treating this like a todo app (thinking space language and interactions)

---

## Code Criteria

### Component Size
- [ ] No component exceeds 500 LOC without justification
- [ ] Large components have clear decomposition path identified
- [ ] Related logic is co-located, not spread across files

### Design Token Usage
Check `frontend/src/app.css` tokens are used via `var(--token)`:
- [ ] Colors: `--bg-base`, `--bg-surface`, `--accent`, `--text-primary`, etc.
- [ ] Shadows: `--shadow-sm`, `--shadow-md`, `--shadow-lift`, `--shadow-lg`
- [ ] Transitions: `--transition-fast` (150ms), `--transition-normal` (200ms), `--transition-slow` (300ms)
- [ ] Typography: `--font-sans`, `--font-mono`, size/weight tokens
- [ ] No hardcoded color values, shadow values, or transition durations

### Accessibility
- [ ] All interactive elements have accessible names (aria-label or visible text)
- [ ] Keyboard navigation works for all major flows
- [ ] Focus management correct in modals and slide-overs
- [ ] Color contrast meets WCAG AA against dark theme
- [ ] Screen reader experience is coherent

### Pattern Consistency
- [ ] Optimistic updates used for all mutations
- [ ] Toast notifications for errors follow consistent pattern
- [ ] Svelte 5 runes used consistently ($state, $derived, $effect)
- [ ] Event handling uses Svelte 5 `oneventname` syntax (not `on:eventname`)

### Store Architecture
- [ ] No state duplication across stores
- [ ] $effect patterns include proper guards (especially for DnD)
- [ ] Store boundaries align with domain concepts
- [ ] Mutations go through designated mutation functions

---

## Feature Opportunity Prompts

When analyzing, consider:
- What interaction would make this feel MORE like a thinking space?
- Is there a moment where the app feels "dead" or static that could use subtle life?
- Are there Google Keep / Are.na / Muse interactions that would fit?
- What completion, transition, or feedback moment could be more satisfying?
- Is there a natural feature that users would expect but is missing?

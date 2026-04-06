# Cognito — Implementation Tasks

Work through in order. Check boxes when complete.
Before each task, read the referenced spec sections in `docs/SPEC.md`.

## Phase 5: Calendar + Mobile

### T-031: Google Calendar
- [x] Add calendar scope to OAuth
- [x] `services/gcal.py` — list events, create, update, delete, free/busy
- [x] POST /api/schedule, GET /api/schedule, DELETE /api/schedule/{id}, GET /api/schedule/suggest
- [x] Schedule view in frontend (CalendarView — daily agenda with time grid)
- [x] Task ↔ Calendar event linking (task_calendar_links table)
- [x] LLM schedule suggestions (suggest endpoint + accept/dismiss UI)
- [x] Backend tests (11 tests in test_schedule.py)

### T-032: Mobile responsive (Phase 1 — layout)
Read: Section 5.14
- [x] Sidebar hidden on mobile, hamburger toggle
- [x] Detail panel full-screen on mobile
- [x] Kanban horizontal scroll, touch-friendly
- [x] Test 375px, 768px, 1024px+

### T-032b: Mobile UX redesign (Phase 2 — interactions)
- [x] BottomSheet.svelte — reusable draggable bottom sheet with snap points
- [x] 2-column masonry bubble layout on mobile (CSS columns)
- [x] Tap bubble → bottom sheet preview (not inline expand)
- [x] Filter chips: [All] [Upcoming] [Overdue] inline below top bar
- [x] Simplified sidebar: projects-only + settings, 280px, MD3 pill active state
- [x] Swipe-to-complete gesture on bubbles (direction-locked, 30% threshold)
- [x] FAB quick-add bottom sheet with AI auto-sort + chat input
- [x] Polish: filter chips moved to top bar title area, BottomSheet viewport fix (100dvh + visualViewport), full-surface drag, body scroll lock, scrollbar cleanup, sidebar alignment fix, MobileQuickAdd layout fix
- [x] Simplified view toggle: Bubbles + Focus only on mobile (removed List/Gantt)
- [x] Hide empty projects on mobile All Tasks view
- [x] Mobile kanban: stacked accordion layout replacing horizontal scroll

---

## Phase 6: Frontend Review Fixes

From the 2026-03-24 visual + code review. Screenshots in `/tmp/cognito-review/`.

### T-033: Quick fixes
- [ ] Reduce overdue left-border opacity (soften the red indicator)
- [ ] Add `<main>` landmark in `+layout.svelte`
- [ ] Bump `.card-indicator` opacity from 0.55 to ~0.65 for contrast
- [ ] Add `sr-only` text to sidebar nav links (fix aria label mismatch)

### T-034: UI improvements
- [ ] Hide "Focus" toggle button when in Gantt view (it only applies to other views)
- [ ] Add a subtle animation to ThinkingMargin empty state
- [ ] Improve empty states (Upcoming page "No tasks" → warmer copy)

### T-035: Design token consolidation
- [ ] Add missing tokens to `app.css`: `--danger`, `--accent-blue`, accent opacity variants
- [ ] Replace ~40 hardcoded hex colors across components with `var()` references
- [ ] Key files: Button, Input, Textarea, DatePicker, ProjectContextMenu, TaskDetailContent, Sidebar, GanttBar, GanttChart, ThoughtBubble, ColorPicker, ConfirmDialog, AIBehaviorTab

### T-036: Organic bubble layout
- [ ] Redesign bubble layout algorithm: variable card sizes based on content/priority
- [x] Masonry layout within clusters (mobile — CSS columns, 2-column)
- [ ] Masonry layout on desktop (wider viewports, 3+ columns)
- [ ] Priority-driven positioning (urgent top-left, low priority drifts down-right)

---

## Phase 7: AI Suggestion UX Polish

From the 2026-04-04 systematic AI feature testing session.

### T-037: AI suggestion UX improvements
- [ ] Hide ThinkingMargin empty state when conversation has content or input has text
- [ ] Fix card description textarea: auto-resize and scrollable
- [ ] Consolidate ThinkingMargin messaging (subtle "no tasks found" → styled empty-state card)
- [ ] Strengthen "done" signal after Approve All (make orange glow more visible, add summary toast)
- [ ] Add save feedback indicator for label description textarea edits
- [ ] Surface raw error messages in all catch blocks (user is sole user, wants debuggable errors)

### T-038: Schedule preferences settings tab
- [ ] New "Schedule" tab in settings (or extend Calendars tab)
- [ ] Configurable work hours (start/end time, per weekday/weekend)
- [ ] Weekend toggle (different hours or "no suggestions")
- [ ] Feed preferences into LLM schedule suggest prompt

### T-039: Async extraction with cancel (architectural)
- [ ] Background extraction jobs (not blocking SSE connection)
- [ ] Progress indicator for multi-step tool-calling
- [ ] Cancel button to abort extraction mid-flight
- [ ] Handle disconnection gracefully (resume or discard)

### T-040: Auto-tag button redesign
- [ ] Make "Tag" button more discoverable (tooltip, fuller label, or surface elsewhere)
- [ ] Consider auto-tag onboarding for first-time use

---

## Notes

- **Read the referenced spec section before starting each task.**
- **Use the design tokens.** Never hardcode colours or spacing.
- **Test each task before moving on** — does it render? Does the API work? Does optimistic rollback work?
- **Vikunja swagger docs** at `http://tasks.epicrunze.com/api/v1/docs`.

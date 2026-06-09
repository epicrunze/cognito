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
- [x] Add `<main>` landmark in `+layout.svelte`
- [ ] Bump `.card-indicator` opacity from 0.55 to ~0.65 for contrast
- [x] Add `sr-only` text to sidebar nav links (fix aria label mismatch)

### T-034: UI improvements
- [x] Hide "Focus" toggle button when in Gantt view (it only applies to other views)
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
- [x] New "Schedule" tab in settings (or extend Calendars tab)
- [x] Configurable work hours (start/end time, per weekday/weekend)
- [x] Weekend toggle (different hours or "no suggestions")
- [x] Feed preferences into LLM schedule suggest prompt

### T-039: Async extraction with cancel (architectural)
- [ ] Background extraction jobs (not blocking SSE connection)
- [ ] Progress indicator for multi-step tool-calling
- [ ] Cancel button to abort extraction mid-flight
- [ ] Handle disconnection gracefully (resume or discard)

### T-040: Auto-tag button redesign
- [ ] Make "Tag" button more discoverable (tooltip, fuller label, or surface elsewhere)
- [ ] Consider auto-tag onboarding for first-time use

---

## Phase 8: Frontend Review 2026-04-18

From the 2026-04-18 review session. Full findings catalogued during the session.

### T-041: Quick correctness fixes
- [x] **F-2**: Calendar toggle on All Tasks "did nothing" — root cause was not view-transition but the schedule API returning 401, which the api wrapper interpreted as session expiry and bounced through `/login` → `/`. Fixed by changing `routers/schedule.py` to return 403 (semantically correct: user *is* authenticated, just lacks Google Calendar grant) so the api wrapper leaves it alone and `CalendarView` renders its existing error banner. See T-046 for the deeper refresh_token fix this exposed.
- [x] **F-3**: Sidebar showed "(0 tasks)" on `/settings` because tasksStore was only fetched lazily by view components. Added `tasksStore.fetchAll()` to the layout `onMount` so counts are correct on every route.
- [x] **F-5**: Main FAB aria-label was "AI Extract" but opens ThinkingMargin. Now toggles between "Open thinking margin" / "Close thinking margin" based on state.
- [x] **F-6**: BubbleCanvas `handleTaskClick` now calls `bubbleStore.collapseImmediate()` before opening TaskDetail, so the inline expansion no longer lingers behind the side panel.

### T-042: Desktop bubble masonry
- [ ] **F-1 / T-036 restated**: Desktop BubbleCanvas is a uniform row-grid — flagged anti-pattern in DESIGN_PHILOSOPHY.md. Mobile already uses CSS columns; port to desktop with 3+ columns for a real organic layout.

### T-043: Orphan cleanup
- [ ] **F-4**: Decide fate of `frontend/src/routes/extract/+page.svelte` — currently orphaned (AI Extract FAB opens ThinkingMargin, not this route). Delete or rewire.

### T-044: Empty-state polish
- [ ] **F-7**: Upcoming/Overdue empty states — context-aware warmer copy ("Nothing coming up this week — nice").
- [ ] **F-9**: Hide `new thought…` placeholder on filtered views (Upcoming/Overdue) where a new task wouldn't match the filter.

### T-045: Smaller UX items
- [ ] **F-8**: Single-letter sidebar projects at narrow widths — add hover-expand rail or persistent labels.
- [ ] **F-11**: List-view keyboard legend is cryptic. Move to a `?` cheat-sheet overlay.
- [ ] **F-12**: TaskDetail side-panel IA — reorder so notes/subtasks come before the large attachment drop zone.

### T-046: OAuth refresh_token loss across logout/login (uncovered while debugging F-2)
- [x] `/api/auth/logout` no longer wipes the Google refresh_token — was the source of a permanent dead state where users couldn't reach Calendar after any logout cycle (Google won't re-issue a refresh_token without `prompt=consent`). Logout is now a cookie-only operation.
- [x] `/api/auth/login` self-heals: if the configured user has no refresh_token in DB (or no row yet), it auto-appends `prompt=consent` so Google issues a fresh one on the next consent.
- [x] `/api/auth/login?reconnect=true` query param + "Reconnect Google" button in the calendar error banner — fallback for the one edge case auto-fix can't detect (user revokes the grant at myaccount.google.com).
- [x] 6 new tests in `backend/tests/test_auth.py` covering force-consent variants, the reconnect override, and the logout-doesn't-clear invariant. Total 27/27 auth+schedule tests pass.

---

## Notes

- **Read the referenced spec section before starting each task.**
- **Use the design tokens.** Never hardcode colours or spacing.
- **Test each task before moving on** — does it render? Does the API work? Does optimistic rollback work?
- **Vikunja swagger docs** at `http://tasks.epicrunze.com/api/v1/docs`.

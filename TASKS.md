# Cognito — Implementation Tasks

Work through in order. Check boxes when complete.
Before each task, read the referenced spec sections in `docs/SPEC.md`.
Before any UI/UX task, read `docs/DESIGN_PHILOSOPHY.md`.

> **2026-06-18 refresh.** Reviewed against the 2026-06-14 Claude Design System
> overhaul (whisper-rail bubbles, masonry, project workspace, mobile TabBar,
> motion module). Tasks the overhaul already solved or contradicted are struck
> through with a reason. Landed-but-untracked work is captured in Phases 9–10.

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

> Note: the mobile hamburger + top filter chips were **superseded** by the
> 2026-06-14 bottom `TabBar` + `LensTabs` (see T-051). The interactions above
> still apply; the chrome around them changed.

---

## Phase 6: Frontend Review Fixes

From the 2026-03-24 visual + code review. Screenshots in `/tmp/cognito-review/`.

### T-033: Quick fixes
- [x] ~~Reduce overdue left-border opacity~~ — **obsolete.** The colored left border was
      replaced by the `.priority-rail` whisper rail (3px, 45%→full on hover; overdue
      forces `--urgent`). The "soften the red" goal is satisfied by the rest-state opacity.
- [x] Add `<main>` landmark in `+layout.svelte`
- [x] ~~Bump `.card-indicator` opacity 0.55 → 0.65~~ — **obsolete.** `.card-indicator` no
      longer exists; the bubble was rewritten to the whisper-rail anatomy.
- [x] Add `sr-only` text to sidebar nav links (fix aria label mismatch)

### T-034: UI improvements
- [x] Hide "Focus" toggle button when in Gantt view (it only applies to other views)
- [ ] Add a subtle (reduced-motion-aware) animation to the ThinkingMargin empty state
      — use a `lib/transitions.ts` factory, not raw Svelte easing.
- [→] Improve empty states (warmer copy) — **moved to T-044** (consolidated with F-7).

### T-035: Design token consolidation
> The 2026-06-14 overhaul reconciled the token set into `app.css` (`--surface-*`,
> `--shadow-*`, `--t-*`, `--ease-*`, `--type-*`, spacing/radius scales). Hardcoded
> hex is down from ~40 to **~13 across 8 files** — this task is nearly done.
- [ ] Audit & replace the remaining ~13 hardcoded hex values with `var()` references.
      Worst offenders: **TaskDetailContent.svelte (4)**, **ProjectContextMenu.svelte (2)**,
      **KanbanBoard.svelte (2)**; remainder scattered one-per-file.
- [x] ~~Add `--danger` / `--accent-blue` / accent-opacity tokens~~ — verify against the
      reconciled token set before adding; most needs are already covered by `--urgent`,
      `--accent`, and the `--surface-*` ramp.

### T-036: Organic bubble layout → **merged into T-042**
- [x] ~~Variable card sizes based on content/priority~~ — **obsolete / anti-philosophy.**
      The design system expresses priority via *position, weight, and opacity — not size*
      (`DESIGN_PHILOSOPHY.md` → Visual Language). Size-scaling was deliberately dropped.
- [x] Masonry layout within clusters (mobile — CSS columns, 2-column)
- [→] Desktop masonry + priority-driven ordering — **moved to T-042** (the remaining
      live work; desktop is no longer a uniform grid but is flex-wrap, not true masonry).

---

## Phase 7: AI Suggestion UX Polish

From the 2026-04-04 systematic AI feature testing session.

### T-037: AI suggestion UX improvements
- [x] Hide ThinkingMargin empty state when conversation has content or input has text
      — implemented (shows only when `messages.length === 0 && !inputText.trim() && !extracting`).
- [ ] Fix card description textarea: auto-resize and scrollable
- [ ] Consolidate ThinkingMargin messaging: route the inline "no tasks found" line through
      the new `EmptyState.svelte` primitive (currently bespoke inline markup).
- [ ] Strengthen the "done" signal after Approve All — the redesigned `Toast` now carries a
      tone dot + AI diamond + optional action; wire an Approve-All summary toast and verify
      the celebrate glow is visible.
- [ ] Add save feedback indicator for label description textarea edits
- [~] Surface raw error messages in all catch blocks — commit `dba7805` "enhanced error
      handling in various components" likely covers most of this; **audit remaining catch
      blocks** and close out.

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
> Current state: a plain `variant="ghost"` text button labelled "Tag" in ThinkingMargin
> (and "Auto-tag" on `/extract`). No icon, no tooltip — still low-discoverability.
- [ ] Make the auto-tag action more discoverable (icon + `Tip` tooltip, or relocate to a
      more visible surface)
- [ ] Consider auto-tag onboarding for first-time use

---

## Phase 8: Frontend Review 2026-04-18

From the 2026-04-18 review session. Full findings catalogued during the session.

### T-041: Quick correctness fixes
- [x] **F-2**: Calendar toggle on All Tasks "did nothing" — schedule API now returns 403
      (not 401) so the api wrapper leaves it alone and `CalendarView` renders its error banner.
- [x] **F-3**: Sidebar "(0 tasks)" on `/settings` — `tasksStore.fetchAll()` now runs in the
      layout `onMount` so counts are correct on every route.
- [x] **F-5**: Main FAB aria-label now toggles "Open/Close thinking margin" based on state.
- [x] **F-6**: BubbleCanvas `handleTaskClick` calls `bubbleStore.collapseImmediate()` before
      opening TaskDetail, so inline expansion no longer lingers behind the side panel.

### T-042: Desktop bubble layout (absorbs T-036 desktop work)
> Status update: desktop BubbleCanvas/BubbleCluster is now **flex-wrap** (`flex; flex-wrap;
> gap: 12px`), not the uniform row-grid the review flagged — the worst anti-pattern is gone.
> Mobile uses true CSS-columns masonry. Remaining work is to make desktop genuinely organic.
- [ ] **F-1**: Move desktop from flex-wrap to true masonry (CSS columns, 3+ at wide widths)
      so card heights interlock instead of leaving row gaps.
- [ ] Priority-driven ordering within the canvas (high → top-left), via `smartSort` —
      position/weight only, **no size-scaling** (per Visual Language).

### T-043: Orphan cleanup
- [x] **F-4**: Deleted `frontend/src/routes/extract/` (2026-06-18). The ThinkingMargin
      slide-out panel fully covers paste + chat + proposal review from any route, so the
      standalone page was dead duplication. No nav/link referenced it.

### T-044: Empty-state polish (consolidates T-034 warmer-copy)
> `EmptyState.svelte` primitive now exists but Upcoming/Overdue still render bespoke inline
> empty states through `ViewOrchestrator`/`BubbleCanvas`. Wire them to the primitive.
- [ ] **F-7**: Context-aware warmer copy for Upcoming/Overdue empty states
      ("Nothing coming up this week — nice"), rendered via `EmptyState.svelte`.
- [ ] **F-9**: Hide the `new thought…` placeholder on filtered views (Upcoming/Overdue)
      where a new task wouldn't match the active filter.

### T-045: Smaller UX items
- [~] **F-8**: Sidebar narrow-width projects — now a monogram-in-ring **plus** a `Tip` hover
      tooltip (title + count) at all widths. Re-evaluate whether a hover-expand rail is still
      wanted, or close as resolved.
- [ ] **F-11**: List-view shows an inline dismissible hint bar (`J K` / `X` / `E` / `N` / `?`).
      The `?` key is advertised but no cheat-sheet overlay exists yet — build the `?` overlay.
- [ ] **F-12**: TaskDetail side-panel IA — reorder so notes/subtasks come before the large
      attachment drop zone.

### T-046: OAuth refresh_token loss across logout/login
- [x] `/api/auth/logout` no longer wipes the Google refresh_token (cookie-only now).
- [x] `/api/auth/login` self-heals: auto-appends `prompt=consent` when no refresh_token exists.
- [x] `/api/auth/login?reconnect=true` + "Reconnect Google" button as the manual fallback.
- [x] 6 new tests in `test_auth.py`; 27/27 auth+schedule tests pass.

---

## Phase 9: Design System Overhaul (2026-06-14)

Implemented from the Claude **Cognito Design System** handoff bundle. All `npm run check`
clean + backend tests pass. **Not yet eyeballed in a running app** (OAuth blocks headless
screenshots) — the bundle's `prototypes/*.html` are the visual oracle.

### T-047: Tokens & motion (landed)
- [x] Reconcile DS tokens into `app.css` additively (surfaces, shadows, type, spacing, radius)
- [x] `--priority-high` `#E8772E → #F0A04B` (amber) so tangerine stays action/AI-only
- [x] `lib/transitions.ts` motion module — `DURATION`/`VIEW`, house easings matching `--ease-*`,
      reduced-motion-aware factories (`panelFly`, `backdropFade`, `dialogPop`, `listSlide`, `sheetRise`)

### T-048: Quiet ThoughtBubble (landed)
- [x] "Whisper rail" indicator (3px, 45%→full hover; overdue forces `--urgent`)
- [x] Drop priority size-scaling, colored left border, corner triangle, hover quick-complete square
- [x] One mono data line (pip · date · steps · ai); check slides into the data line on hover
- [x] `PriorityMeter.svelte` (5 colored segments incl. `none`) in expanded bubble + TaskDetailContent

### T-049: Project workspace (landed)
- [x] `ProjectWorkspace.svelte` (StatusBriefing + open bubbles + NotesDoc + CompletedLedger rail)
- [x] Backend: `project_workspace` table; `GET/PUT /api/projects/{id}/notes`;
      `GET/POST /api/projects/{id}/briefing` (LLM-generated, cached)
- [x] `mark_briefing_stale()` flips on task create/update in `tasks.py`

### T-050: Mobile redesign (landed)
- [x] Bottom `TabBar` (thoughts/projects/+/upcoming/search) replaces hamburger + top chips
- [x] Home = cross-project presence **stream** with project pips; `LensTabs` + settings gear in header
- [x] New `/projects` picker route with AI summaries
- [x] New primitives: `ViewSwitcher`, `LensTabs`, `Fab`, `EmptyState`; `Toast` → bottom-left
      with tone dot + AI diamond + optional undo action

### T-051: Design-system follow-ups (open)
- [ ] Eyeball every route in a running app against `prototypes/*.html`; log visual drift
- [ ] Adopt `EmptyState.svelte` everywhere bespoke empty states remain (ties to T-037, T-044)
- [ ] Confirm all `{#if}`-block transitions use the motion-module factories (no raw easing,
      no `transition: all`)

---

## Phase 10: Notifications, PWA & Briefing (landed — uncommitted)

New since the design overhaul; present as uncommitted working-tree changes. Not previously
tracked. Backend tests for briefing exist (`backend/tests/test_briefing.py`).

### T-052: "Today" briefing page (landed)
- [x] `routers/briefing.py` — `GET /api/briefing` (AI line cached per day) + `POST /regenerate`
- [x] `services/nudge_engine.py` `build_briefing()` — due-today / overdue / done-today / calendar / undated
- [x] `routes/briefing/+page.svelte` — in-app landing spot for digest/nudge clicks
- [x] Sidebar "Today" nav item → `/briefing`

### T-053: Web push / PWA (landed)
- [x] `service-worker.ts` — push handler; routes clicks to `/?task=<id>` or `/briefing`
- [x] Notification support + PWA wiring (commit `b05bf51`)
- [ ] **Follow-up:** verify push subscription lifecycle (permission prompt, re-subscribe on
      key rotation, unsubscribe on logout) end-to-end on a device

### T-054: Briefing/notifications follow-ups (open)
- [ ] Wire the morning digest schedule to user schedule preferences (T-038)
- [ ] Surface briefing-regenerate state (loading/stale) in the UI
- [ ] Backend tests: confirm `test_briefing.py` covers force-regen + caching invalidation

---

## Notes

- **Read the referenced spec section before starting each task.**
- **Use the design tokens.** Never hardcode colours or spacing. Priority is expressed by
  position/weight/opacity — **never size** (per `DESIGN_PHILOSOPHY.md`).
- **Motion goes through `lib/transitions.ts`.** Never `transition: all`; never raw Svelte easing.
- **Test each task before moving on** — does it render? Does the API work? Does optimistic rollback work?
- **Vikunja swagger docs** at `http://tasks.epicrunze.com/api/v1/docs`.
- Legend: `[x]` done · `[ ]` open · `[~]` mostly done, audit remainder · `[→]` moved/merged.

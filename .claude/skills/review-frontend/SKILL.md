---
name: review-frontend
description: >
  Agentic frontend review loop. Uses Chrome DevTools MCP (headless) to screenshot
  every route and view, analyzes visuals against DESIGN_PHILOSOPHY.md, reviews code
  structure, proposes improvements and new features, then implements approved changes.
triggers:
  - review frontend
  - frontend review
  - design review
  - visual QA
  - UI review
  - improve frontend
  - self improvement
  - design check
---

# Frontend Review Loop

An agentic review cycle that visually inspects the live Cognito app, analyzes code,
and proposes improvements aligned with the design philosophy.

**Prerequisites:** Chrome DevTools MCP must be configured (`.mcp.json`) with `--headless`.

### Config: Save Screenshots to Disk

By default, screenshots are saved to `/tmp/cognito-review/` so the user can inspect
them. To disable saving (screenshots still visible to Claude inline), set
`SAVE_SCREENSHOTS=false` when invoking the skill.

When saving is enabled:
- Create the output directory: `mkdir -p /tmp/cognito-review`
- Use `filePath` parameter on `take_screenshot`: e.g.,
  `filePath: "/tmp/cognito-review/01-home-bubbles.png"`
- Name files with a numbered prefix matching the capture list below
- After the review, tell the user: "Screenshots saved to `/tmp/cognito-review/`"

---

## Phase 1: Setup & Authentication

1. **Generate a JWT** for the headless browser session:
   ```bash
   docker exec cognito-backend uv run python -c "
   from app.auth.jwt import create_access_token
   from app.models.user import User
   user = User(email='epicrunze@gmail.com', name='Review Bot')
   print(create_access_token(user))
   "
   ```
   **Important:** Generate the JWT inside the Docker container, not locally — the
   container has a different `JWT_SECRET` than the local backend `.env` defaults.
   Save the token output.

2. **Navigate** headless Chrome to `https://cognito.epicrunze.com`:
   - Use MCP tool: `navigate_page` with url `https://cognito.epicrunze.com`

3. **Inject the auth cookie** using MCP `evaluate_script`:
   ```js
   document.cookie = 'cognito_auth=<JWT_TOKEN>; domain=.epicrunze.com; path=/; secure; samesite=lax';
   ```
   Replace `<JWT_TOKEN>` with the token from step 1.

4. **Reload** the page using `navigate_page` to the same URL again.

5. **Verify auth** by taking a screenshot — confirm the page shows logged-in state
   (sidebar with projects visible, not the login page).

---

## Phase 2: Visual Capture

Take screenshots of every major route and view state. Use Chrome DevTools MCP tools:
`navigate_page`, `click`, `press_key`, `take_screenshot`.

### Capture List

**Main views (all require view toggle clicks):**
| # | Route | Action | Description |
|---|-------|--------|-------------|
| 1 | `/` | None | Home — bubbles view (default) |
| 2 | `/` | Click bubbles→kanban toggle | Kanban view |
| 3 | `/` | Click kanban→list toggle | List view |
| 4 | `/` | Click list→gantt toggle | Gantt view |

**Filtered views:**
| # | Route | Description |
|---|-------|-------------|
| 5 | `/upcoming` | Upcoming tasks filter |
| 6 | `/overdue` | Overdue tasks filter |

**Project views:**
| # | Action | Description |
|---|--------|-------------|
| 7 | Click first project in sidebar | Project bubble view |
| 8 | Click kanban toggle | Project kanban view |

**Feature panels:**
| # | Action | Description |
|---|--------|-------------|
| 9 | Press `E` key | ThinkingMargin (AI chat panel) |
| 10 | Click any task card | TaskDetail side panel |

**Other pages:**
| # | Route | Description |
|---|-------|-------------|
| 11 | `/extract` | AI extraction page |
| 12 | `/settings` | Settings page |

**Timing:** After each navigation or interaction, wait for animations to settle
(300-500ms). Use `wait_for` if available, or take screenshot after a brief pause.

---

## Phase 3: Visual Analysis

For **each screenshot**, analyze against `docs/DESIGN_PHILOSOPHY.md`. Read the design
philosophy file first if you haven't already.

### Visual Checklist

Check each of these criteria (see `references/review-checklist.md` for details):

1. **Metaphor alignment** — Does this feel like a "thinking space" or a traditional task manager?
2. **Color restraint** — Is tangerine (#E8772E) used ONLY for actions and AI features? Are bubble surfaces neutral?
3. **Information density** — Default bubbles show only title + subtle indicator row? Or too data-dense?
4. **Visual hierarchy** — Priority communicated through position and weight, not decoration?
5. **Spacing & breathing room** — Clusters separated by whitespace, not borders or dividers?
6. **Typography** — IBM Plex Sans, correct weights per design tokens in `app.css`?
7. **Dark theme serving the metaphor** — Light surfaces floating on dark ground?
8. **Anti-patterns** — Check for: uniform grid, too-dense cards, page transitions instead of card animations, dominating sidebar, decorative animation

### Performance & Accessibility

Run `lighthouse_audit` on the main page for:
- Accessibility score and violations
- Performance score
- Best practices

---

## Phase 4: Code Analysis

Read the frontend source code and analyze:

### Component Health
- **Size** — Flag any component over 500 LOC. Current large files:
  - `TaskDetailContent.svelte` (~1184 LOC)
  - `ThoughtBubble.svelte` (~960 LOC)
  - `ProjectContextMenu.svelte` (~866 LOC)
  - `Sidebar.svelte` (~729 LOC)
- **Decomposition opportunities** — Can large components be split without breaking patterns?

### Pattern Consistency
- Are design tokens from `app.css` used consistently, or are there inline styles / hardcoded values?
- Is Tailwind used alongside CSS custom properties consistently?
- Are optimistic update patterns followed uniformly?

### Accessibility
- Missing ARIA labels on interactive elements
- Keyboard navigation gaps
- Focus management (especially in modals, slide-overs, task detail)
- Color contrast against dark theme

### Design Token Usage
- Read `frontend/src/app.css` for the canonical design tokens
- Check if components use `var(--token)` or hardcoded values
- Check shadow, spacing, transition timing consistency

### Store Architecture
- 19 stores in `lib/stores/` — any unnecessary coupling or state duplication?
- Are $effect patterns consistent and guarded?

### Feature Opportunities
- What's missing that would serve the "thinking space" metaphor?
- What interactions feel incomplete or could be more delightful?
- What would make the app feel more like Google Keep / Are.na / Muse and less like a todo app?

---

## Phase 5: Present Findings & Implement

### Present Proposals

Group findings by category and severity:

```
## [CATEGORY] Finding #N: Title
**Severity:** Critical / Moderate / Minor
**Screenshot:** (reference which screenshot shows this)
**Issue:** What's wrong or missing
**Design Philosophy:** Quote the relevant principle from DESIGN_PHILOSOPHY.md
**Proposed Fix:** Specific, actionable change
**Scope:** Estimated effort (small CSS tweak / component refactor / new feature)
```

**Categories:**
- **Visual QA** — design philosophy violations visible in screenshots
- **Accessibility** — Lighthouse findings + manual analysis
- **Code Quality** — large components, inconsistencies, anti-patterns
- **Feature Ideas** — new capabilities that serve the vision

### Get Approval

Ask: "Which proposals would you like me to implement? (e.g., '1, 3, 5' or 'all critical' or 'all visual QA')"

### Implement

For each approved proposal:
1. Read the relevant file(s) before editing
2. Make the change
3. Run `svelte-autofixer` on any modified `.svelte` files (Svelte MCP tool)
4. After all changes: run `npm run check` from `frontend/` to verify TypeScript
5. Optionally re-screenshot the affected route for before/after comparison

---

## Notes

- The Chrome DevTools MCP `take_screenshot` returns the image directly — Claude can
  analyze it visually as a multimodal model.
- If Chrome DevTools MCP is not available, fall back to code-only analysis (skip
  Phases 1-2, do Phase 3 from code reading only, proceed with Phase 4-5).
- The public URL `https://cognito.epicrunze.com` is reachable from the host machine.
- Auth cookie: `cognito_auth`, domain `.epicrunze.com`, secure, samesite=lax.
- JWT generation uses `backend/app/auth/jwt.py:create_access_token()`.

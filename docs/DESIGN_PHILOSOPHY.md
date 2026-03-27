# Cognito Design Philosophy

Read this before any UI/UX work. This is how you think about design decisions in this app.

## The Metaphor

Cognito is a **thinking space**, not a task manager. The name means "I think" in Latin. The app should feel like looking at a surface of your thoughts — some urgent and prominent, some fading, all spatially organized. Not a spreadsheet. Not a filing cabinet. A mind.

The primary view is thought-bubbles — small cards clustered by project. The most urgent rise to the top-left. You glance at the screen and immediately know what needs attention. Closer to Google Keep than Linear.

You can also think out loud — the chat agent is a natural language interface to this thinking space, letting you search, modify, and create tasks through conversation.

## Core Interactions

**The Bubble.** Default: small. Title + subtle indicator row (overdue dot, subtask progress, attachment count) — always visible but muted. Hover: the bubble wakes up with a lift and metadata fade-in. Click: expands in-place, pushing neighbours aside organically. Click away: contracts back. The expansion should feel physical — like a thought unfolding.

**The Cluster.** Bubbles grouped by project with a subtle label and generous whitespace. Position is automatic: urgent floats top-left, low priority drifts down-right. Completed items fade or collect at the bottom.

**The Transformation.** Switching bubble → kanban within a project, the same cards animate into columns. This is the signature moment — thoughts organizing themselves, not a page transition. Snappy (300-400ms with stagger). Speed > spectacle.

**The List.** Secondary "focus mode" for methodical work. A tool, not the identity.

**On Mobile.** The thinking space adapts to a smaller canvas — same metaphor, different interaction vocabulary. Bottom sheets replace slide-overs (thoughts rise up to meet your thumb). Masonry columns replace flex-wrap (organic flow, not rigid grid). Kanban becomes collapsible accordion sections. Swipe-to-complete is the most natural gesture for "done with this thought." Filter chips replace sidebar nav for horizontal, thumb-friendly context switching. The FAB preserves "capture a thought instantly."

## Visual Language

**Cards, not rows.** Every thought is a card with subtle elevation, rounded corners (8-10px), variable width within masonry layout, no internal borders.

**Priority as presence.** Position (high = top-left), visual weight (opacity, title brightness, shadow depth). Priority is felt at a glance, not read. Explicit indicators appear only on expand.

**Colour restraint.** Tangerine (#E8772E) is for actions and AI only. Bubbles are neutral surfaces. Overdue gets a subtle warm hint — enough for peripheral vision, not alarming.

**Fading as communication.** Low-priority and old tasks genuinely fade — less present through muted text, near-invisible shadow, reduced opacity. Creates a natural attention gradient.

**Completion as acknowledgment.** Finishing a thought gets brief feedback — green glow + check, never blocking. The animation is feedback, not decoration.

**The dark theme serves the metaphor.** Dark background = surface of thought. Lighter bubbles float on it. Light objects on dark ground creates "things emerging from a background" — the cognitive metaphor made visual.

## The AI Extraction Experience

You paste unstructured text. Proposals appear as new bubbles with tangerine glow, streaming in as thoughts crystallize. Approve them and they join the main view. The extraction page is an incubator — a staging area where raw input becomes structured thought.

## Process: Propose Before Building

When making UI/UX changes:
1. **Describe your approach first.** What feels wrong, what you plan to change, the intended effect.
2. **Propose 2 directions when the choice isn't obvious.** Tradeoffs, let me pick.
3. **Start with the riskiest interaction.** Get feedback before polishing.
4. **Show, don't describe.** A real component is worth more than a paragraph.

## Anti-Patterns

- **Uniform grid** — bubbles are organic. Same-size perfect grid = Google Keep done wrong.
- **Info-dense default bubbles** — title + subtle indicators only. Details on hover/expand.
- **Page transitions between views** — same cards moving, not DOM rebuild.
- **Sidebar dominating** — sidebar is navigation, bubbles are the app.
- **Decorative animation** — every animation communicates state change. Nothing moves just to move.
- **Treating this like a todo app** — this is a thinking space that tracks tasks.

## Reference Energy

Google Keep (spatial, cards as objects), Are.na (ideas as first-class objects, calm density), Muse App (spatial canvas), Things 3 (satisfaction of completion), iA Writer (confidence in reduction), Obsidian graph (thoughts spatially — the feeling, not the feature).

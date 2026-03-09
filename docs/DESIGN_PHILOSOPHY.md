# Cognito Design Philosophy

Read this before any UI/UX work. This is how you think about design decisions in this app.

## The Metaphor

Cognito is not a task manager. It's a **thinking space**.

The name means "I think" in Latin. The app should feel like looking at a surface of your thoughts — some urgent and prominent, some fading into the background, all spatially organized in a way your brain naturally understands. Not a spreadsheet. Not a filing cabinet. A mind.

The primary view is **thought-bubbles** — small cards clustered by project, with priority determining visual prominence and position. The most urgent thoughts rise to the top-left. The least important ones fade down and to the right. You glance at the screen and immediately know what needs your attention.

This is closer to **Google Keep** than to Linear. Each thought has its own presence as an object in space, not a row in a table.

## Core Interactions

### The Bubble

Default state: small. Title only, 2-3 lines max. A quiet presence — you can see many at once without overwhelm. Priority is communicated through position and a subtle visual signal (border weight, colour intensity), not through explicit indicators like dots or numbers.

Hover: the bubble wakes up slightly — maybe a subtle lift (shadow increase), a hint of additional info fading in (project name, due date). An invitation.

Click: the bubble **expands in-place**. It grows, pushing its neighbours aside organically. Now you see everything: description, labels, due date, attachments, edit controls. The expansion should feel physical — like the thought is unfolding. The surrounding bubbles yield gently, not snapping to new positions but flowing.

Click away or press Escape: the bubble contracts back. Its neighbours return.

### The Cluster

Bubbles are grouped by project. Each cluster has a subtle label (project name, small, muted) and its own spatial region. Clusters are separated by generous whitespace — not borders, not dividers. Just breathing room.

Within a cluster, position is automatic based on priority and recency. Urgent + overdue items float to the top-left. Low priority drifts down-right. Completed items either fade to minimal presence or collect at the bottom edge of the cluster.

The "All Tasks" view shows all clusters together. Clicking a project in the sidebar shows only that project's cluster, expanded to fill the space.

### The Transformation

This is the signature moment of the app.

When you switch from bubble view to kanban view within a project, the same cards **animate into columns**. Each bubble flies to its kanban column based on its bucket assignment. The columns form as the cards arrive. It should feel like thoughts organizing themselves — not a page transition, but a spatial reorganization of the same objects.

The reverse should also work: switching back from kanban to bubbles, the cards release from their columns and settle back into the organic cluster layout.

This animation should be snappy (300-400ms total, with stagger) — impressive but never slow. If it feels sluggish, cut the duration. Speed > spectacle.

### The List

The list view still exists as a secondary mode. Think of it as "focus mode" — when you need to methodically work through tasks, sort, filter, bulk-edit. It's a tool, not the identity. Accessible via a view toggle, but it's not the landing page.

## Visual Language

### Cards, not rows

Every thought is a card. Cards have:
- A subtle surface elevation (very slight shadow or border, not heavy)
- Rounded corners (8-10px — softer than typical UI, reflecting the organic metaphor)
- Variable width within the masonry layout, but consistent within a cluster
- No internal borders or dividers — content flows naturally within the card

### Priority as presence, not decoration

Priority is communicated through:
- **Position** — high priority = top-left of cluster
- **Visual weight** — urgent items might have a slightly more visible border, or the title text is the full primary colour instead of slightly muted
- **Size hint** — urgent items could be fractionally larger, giving them more spatial gravity

When the bubble expands, THEN show the explicit priority indicator (dots). But at glance-level, priority is felt, not read.

### Colour restraint

The tangerine accent (#E8772E) is for actions and AI features only. The bubbles themselves are neutral surfaces. Project identity comes from the cluster label, not from colouring every card.

The exception: overdue tasks get a subtle warmth — maybe a very faint red-shifted border or a tiny red dot. Enough to catch peripheral vision without making the whole view look alarming.

### Fading as communication

Low-priority and old tasks should genuinely fade. Not just "lower opacity" — they should feel less present. Maybe they're slightly smaller, their text is the tertiary colour, their shadow is nearly invisible. When you scroll down or look toward the edges, the thoughts get quieter. This creates a natural attention gradient.

### The dark theme serves the metaphor

Dark background = the surface of thought. The bubbles are lighter surfaces floating on it. This inversion (light objects on dark ground) naturally creates the sense of "things emerging from a background" which is exactly the cognitive metaphor. The dark isn't just an aesthetic choice — it's functional.

## The AI Extraction Experience

Extraction is where raw text becomes structured thought. The flow:

1. You paste or type unstructured text into the extraction panel
2. The AI processes it — show this as a subtle thinking state, not a loading spinner
3. Proposals appear as **new bubbles** — they stream in with the tangerine glow, each one emerging as a new thought. Not a list of results. Actual bubble-cards that look like they'll eventually join the main view.
4. You approve them, and they **fly to their project cluster** in the main view. Or if you're already in a project, they settle into position among the other bubbles.

The extraction page should feel like an incubator for thoughts — a staging area where raw input crystallizes into structured ideas before they join the rest.

## Process: Propose Before Building

**When making UI/UX changes, DO NOT just implement.**

1. **Describe your approach first.** What feels wrong now, what you plan to change, what the intended effect is. Use analogies — "like how Google Keep handles X" or "imagine the cards behaving like Y."

2. **Propose 2 directions when the choice isn't obvious.** Describe both, explain tradeoffs, let me pick.

3. **Start with the riskiest interaction.** The bubble expand/contract animation. The cluster layout algorithm. The kanban transformation. Get feedback on these before polishing padding and typography.

4. **Show, don't describe.** Build one component to demonstrate the direction. A real bubble I can click is worth more than a paragraph.

## Anti-Patterns

- **Uniform grid.** The whole point of bubbles is organic layout. If every card is the same size in a perfect grid, we've just built Google Keep wrong.
- **Too much info on the default bubble.** Title only. Maybe a tiny priority signal. That's it. Resist the urge to show labels, dates, descriptions at default size.
- **Page transitions between views.** Bubble → kanban should be the SAME cards moving, not a route change that rebuilds the DOM.
- **The sidebar dominating.** The sidebar is navigation. The bubbles are the app. The sidebar should feel minimal — thin, quiet, almost invisible until you need it.
- **Decorative animation.** Every animation communicates a state change. Bubbles expand because you asked to see more. Cards fly to columns because they're reorganizing. Nothing moves just to move.
- **Treating this like a todo app.** This is a thinking space that happens to track tasks. The language, the interactions, the visual weight should all reflect "thoughts" not "items."

## Reference Energy

- **Google Keep** — spatial layout, cards as objects, variable sizing, quick capture
- **Are.na** — how it treats ideas as first-class objects in space, the calm density
- **Muse App** — spatial canvas for thinking, organic arrangement
- **Things 3** — the satisfaction of completion, the feeling of calm control
- **iA Writer** — confidence in reduction, typography as design
- **Obsidian graph view** — thoughts as nodes with relationships (we're not building a graph, but the FEELING of seeing your thoughts spatially)

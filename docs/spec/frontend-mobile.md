# Frontend Mobile UX

## Responsive Breakpoints

Defined in `lib/stores/responsive.svelte.ts` using `matchMedia`:

| Breakpoint | Range | `responsiveStore` flag |
|-----------|-------|----------------------|
| Mobile | `< 768px` | `isMobile` |
| Tablet | `768px - 1023px` | `isTablet` |
| Desktop | `>= 1024px` | `isDesktop` |

CSS overrides in `app.css`:
- Mobile (`max-width: 767px`): `--sidebar-width: 0px`, scrollbars hidden
- Tablet (`768px - 1023px`): `--sidebar-width: 64px`
- Desktop: default `--sidebar-width: 64px`

The store auto-initializes on first import and listens for `change` events on media queries. When resizing to desktop, the mobile sidebar overlay auto-closes.

## BottomSheet

`components/ui/BottomSheet.svelte` -- mobile replacement for `SlideOver`:

- **Snap points**: Configurable array of viewport fractions (default: `[0.5, 1]`)
- **Initial snap**: Index into snap points array (default: `0`)
- **Drag gestures**: Touch/mouse drag on handle; snaps to nearest point on release
- **visualViewport handling**: Tracks `window.visualViewport.height` to handle mobile browser address bar show/hide
- **Dismiss**: Drag below lowest snap point to close; calls `onclose` callback
- **Overlay**: Fade backdrop behind sheet

Used by `TaskDetail` on mobile (replaces `SlideOver`).

## Accordion Kanban

On mobile, `KanbanBoard` renders columns as collapsible accordions instead of horizontal scrolling columns. Each bucket becomes a tappable header that expands to show its tasks.

## Masonry Layout

`BubbleCanvas` on mobile uses CSS `column-count: 2` for a masonry-style grid layout instead of the physics-based bubble simulation used on desktop.

## Swipe-to-Complete

`ThoughtBubble` in compact (list) mode supports horizontal swipe gestures on mobile:
- Swipe right to complete a task
- Visual feedback during swipe with progress indicator
- Triggers `toggleDone` on threshold

## FAB Quick-Add

`MobileQuickAdd.svelte` -- floating action button (bottom-right corner):
- Tapping opens a quick-add input sheet
- Minimal input: title + optional project selection
- Submits via `tasksStore.create()`

## Mobile Sidebar

On mobile (`isMobile`), the sidebar is hidden by default (`--sidebar-width: 0px`). Toggling via hamburger menu opens a 280px slide-over overlay:
- `responsiveStore.toggleSidebar()` controls open/close state
- Backdrop overlay dismisses on tap
- Auto-closes when breakpoint changes to desktop

## Filter Chips

On mobile, `FilterBar` renders as horizontal scrolling filter chips in the top bar instead of the desktop dropdown/popover pattern. Chips show active filter counts (e.g., overdue count, upcoming count derived in `+layout.svelte`).

## Mobile Task Detail

Task detail renders in a `BottomSheet` (mobile) instead of `SlideOver` (desktop). The `mobileTaskFullscreen` state in `+layout.svelte` tracks whether the sheet is expanded to full height.

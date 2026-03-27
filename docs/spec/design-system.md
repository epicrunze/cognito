# Design System

Dark theme with tangerine accent on warm dark neutrals. Defined as CSS custom properties in `frontend/src/app.css`.

## Colors

### Backgrounds
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-base` | `#111110` | Page background |
| `--bg-surface` | `#1A1A19` | Card/panel backgrounds |
| `--bg-surface-hover` | `#222221` | Surface hover state |
| `--bg-sidebar` | `#161615` | Sidebar background |
| `--bg-overlay` | `rgba(0,0,0,0.6)` | Modal/overlay backdrop |
| `--bg-elevated` | `#212120` | Elevated surface (dropdowns, popovers) |

### Borders
| Token | Value |
|-------|-------|
| `--border-default` | `#2A2A28` |
| `--border-strong` | `#3A3A37` |
| `--border-subtle` | `#1F1F1E` |

### Text
| Token | Value | Usage |
|-------|-------|-------|
| `--text-primary` | `#EDEDEC` | Body text |
| `--text-secondary` | `#A1A09A` | Secondary/muted text |
| `--text-tertiary` | `#6B6A65` | Placeholders, disabled |
| `--text-on-accent` | `#111110` | Text on accent backgrounds |

### Accent
| Token | Value |
|-------|-------|
| `--accent` | `#E8772E` (tangerine) |
| `--accent-hover` | `#D4691F` |
| `--accent-subtle` | `rgba(232,119,46,0.1)` |
| `--accent-glow` | `rgba(232,119,46,0.25)` |

### Semantic
| Token | Value | Usage |
|-------|-------|-------|
| `--priority-urgent` | `#EF5744` | Priority 5 |
| `--priority-high` | `#E8772E` | Priority 4 |
| `--priority-medium` | `#E2C541` | Priority 3 |
| `--priority-low` | `#5BBC6E` | Priority 2 |
| `--priority-none` | `#4A4A46` | Priority 1 |
| `--done` | `#5BBC6E` | Completed tasks |
| `--overdue` | `#EF5744` | Overdue indicator |

## Typography

- **Sans**: `IBM Plex Sans` (400, 500, 600) -- `--font-sans`
- **Mono**: `IBM Plex Mono` (400, 500) -- `--font-mono`

| Token | Size |
|-------|------|
| `--text-xs` | 0.75rem |
| `--text-sm` | 0.8125rem |
| `--text-base` | 0.9375rem |
| `--text-md` | 1rem |
| `--text-lg` | 1.125rem |
| `--text-xl` | 1.25rem |

Line heights: `--leading-tight` (1.25), `--leading-normal` (1.5), `--leading-relaxed` (1.625).

## Shadows

| Token | Value |
|-------|-------|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.3)` |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.4)` |
| `--shadow-lift` | `0 6px 20px rgba(0,0,0,0.4)` |
| `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.5)` |
| `--shadow-slide-over` | `-8px 0 32px rgba(0,0,0,0.5)` |

## Transitions

| Token | Duration | Usage |
|-------|----------|-------|
| `--transition-fast` | 150ms | Hover states |
| `--transition-normal` | 200ms | Panel toggles |
| `--transition-slow` | 300ms | Slide-overs, major transitions |

## Key Animations

| Name | Usage |
|------|-------|
| `pulse` | Skeleton loading |
| `spin` | Loading spinners |
| `slideUp` | Element entrance |
| `fadeIn` | Opacity entrance |
| `breathe` | Subtle ambient pulse |
| `diamond-drift` | Sidebar diamond rotation |
| `projectBirth` | New project appearance |
| `pulse-glow` | Accent glow pulse (AI-tagged tasks) |
| `aiGlowFade` | AI tag glow fade-out after viewing |
| `thinkingBounce` | AI thinking indicator dots |
| `celebrate-*` | Task completion celebration (check, glow, fill, pulse-card) |

## Layout

- `--sidebar-width`: 64px (desktop/tablet), 0px (mobile)

import { fade, fly, slide } from 'svelte/transition';
import type { TransitionConfig } from 'svelte/transition';

/**
 * The motion module — single source of truth for app motion.
 *
 * Durations and easing curves mirror the CSS tokens in `app.css` (`--t-*`,
 * `--ease-out`, `--ease-in-out`) so JS-driven Svelte transitions feel identical
 * to the CSS-driven ones sitting right next to them. See DESIGN_PHILOSOPHY.md
 * ("Motion") for when to use each.
 */

export const DURATION = {
  fast: 150,
  normal: 200,
  slow: 300,
} as const;

/**
 * View-switch (Bubbles↔Kanban↔List↔Gantt) timing. The signature card-flight
 * lives in `viewTransitionAnimator.ts`; these are the single source of truth so
 * the JS flight, the `--t-view` token, and `::view-transition-group` agree.
 *
 * `groupCrossfade` drives the default cross-fade for elements that DON'T fly
 * (e.g. root). Flighted cards suppress that cross-fade and use `flightEnter`/
 * `flightLeave` instead — so a longer flight than the crossfade is intentional,
 * not a conflict.
 */
export const VIEW = {
  groupCrossfade: 250,
  flightEnter: 300,
  flightLeave: 240,
  enterStagger: 25,
  leaveStagger: 15,
} as const;

/* ── Easing ──────────────────────────────────────────────────────────────
 * JS easing functions that EXACTLY match the CSS cubic-beziers, so a Svelte
 * `fly`/`slide`/`fade` carries the same curve as a sibling CSS transition.
 */

/** Build an easing fn from a CSS cubic-bezier control polygon. */
export function cubicBezier(x1: number, y1: number, x2: number, y2: number): (t: number) => number {
  const cx = 3 * x1;
  const bx = 3 * (x2 - x1) - cx;
  const ax = 1 - cx - bx;
  const cy = 3 * y1;
  const by = 3 * (y2 - y1) - cy;
  const ay = 1 - cy - by;

  const sampleX = (t: number) => ((ax * t + bx) * t + cx) * t;
  const sampleY = (t: number) => ((ay * t + by) * t + cy) * t;
  const sampleDerivX = (t: number) => (3 * ax * t + 2 * bx) * t + cx;

  const solveX = (x: number) => {
    // Newton-Raphson, with a bisection fallback for flat regions.
    let t = x;
    for (let i = 0; i < 8; i++) {
      const err = sampleX(t) - x;
      if (Math.abs(err) < 1e-5) return t;
      const d = sampleDerivX(t);
      if (Math.abs(d) < 1e-6) break;
      t -= err / d;
    }
    let lo = 0;
    let hi = 1;
    t = x;
    for (let i = 0; i < 20; i++) {
      const err = sampleX(t) - x;
      if (Math.abs(err) < 1e-5) break;
      if (err > 0) hi = t;
      else lo = t;
      t = (lo + hi) / 2;
    }
    return t;
  };

  return (t: number) => {
    if (t <= 0) return 0;
    if (t >= 1) return 1;
    return sampleY(solveX(t));
  };
}

/** House snappy-out curve — `--ease-out` in app.css. Use for entrances. */
export const easeOut = cubicBezier(0.22, 1, 0.36, 1);
/** Symmetric curve — `--ease-in-out` in app.css. Use for moves/reorders. */
export const easeInOut = cubicBezier(0.65, 0, 0.35, 1);
/** Faster ease-in for exits — `--ease-exit` in app.css. */
export const easeExit = cubicBezier(0.55, 0, 1, 0.45);

/** Same curves as CSS strings, for the Web Animations API (WAAPI `easing`). */
export const EASING_CSS = {
  out: 'cubic-bezier(0.22, 1, 0.36, 1)',
  inOut: 'cubic-bezier(0.65, 0, 0.35, 1)',
  exit: 'cubic-bezier(0.55, 0, 1, 0.45)',
} as const;

/* ── Reduced motion ────────────────────────────────────────────────────── */

/** True when the user asked for reduced motion. SSR-safe (returns false). */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** Collapse a duration to ~instant when reduced motion is requested. */
function motion(ms: number): number {
  return prefersReducedMotion() ? 0 : ms;
}

/* ── Preconfigured transition factories ───────────────────────────────────
 * Use these on `transition:`/`in:`/`out:` so every directive carries the house
 * easing and reduced-motion behaviour without hand-rolling params. Each is a
 * Svelte transition `(node, params) => config`; pass overrides as the param.
 */

/** Side panel / slide-over: slides in from the right edge. */
export function panelFly(node: Element, params: { x?: number; duration?: number } = {}): TransitionConfig {
  return fly(node, {
    x: params.x ?? 200,
    duration: motion(params.duration ?? DURATION.slow),
    easing: easeOut,
  });
}

/** Overlay / scrim backdrop fade. Pair with a panel/sheet/dialog. */
export function backdropFade(node: Element, params: { duration?: number } = {}): TransitionConfig {
  return fade(node, { duration: motion(params.duration ?? DURATION.normal) });
}

/** Modal/dialog content: small rise + fade. */
export function dialogPop(node: Element, params: { y?: number; duration?: number } = {}): TransitionConfig {
  return fly(node, {
    y: params.y ?? 8,
    duration: motion(params.duration ?? DURATION.normal),
    easing: easeOut,
  });
}

/** List row insert/remove. Local so a sibling's removal doesn't reflow the parent. */
export function listSlide(node: Element, params: { duration?: number } = {}): TransitionConfig {
  return slide(node, { duration: motion(params.duration ?? DURATION.normal), easing: easeOut });
}

/** Mobile bottom sheet: rises from the bottom edge. */
export function sheetRise(node: Element, params: { y?: number; duration?: number } = {}): TransitionConfig {
  return fly(node, {
    y: params.y ?? window.innerHeight,
    duration: motion(params.duration ?? DURATION.slow),
    easing: cubicBezier(0.32, 0.72, 0, 1),
  });
}

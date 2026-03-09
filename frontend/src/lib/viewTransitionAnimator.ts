// View transition flight animations — cards fly from/to sidebar icons

interface CardSnapshot {
  id: string;
  rect: DOMRect;
  priority: number;
  viewTransitionName: string;
}

interface Point { x: number; y: number }

interface FlightConfig {
  enterFrom: Point;
  leaveTo: Point;
}

const MAX_ANIMATED = 15;
const ENTER_DURATION = 300;
const LEAVE_DURATION = 240;
const ENTER_STAGGER = 25;
const LEAVE_STAGGER = 15;
const ENTER_EASING = 'cubic-bezier(0.16, 1, 0.3, 1)';
const LEAVE_EASING = 'cubic-bezier(0.7, 0, 1, 0.5)';
const SCALE_AT_SIDEBAR = 0.15;

export function snapshotCards(): CardSnapshot[] {
  const els = document.querySelectorAll<HTMLElement>('[data-transition-id]');
  const cards: CardSnapshot[] = [];
  for (const el of els) {
    const id = el.dataset.transitionId!;
    const priority = parseInt(el.dataset.taskPriority ?? '3', 10);
    const vtn = el.style.viewTransitionName || '';
    if (!vtn) continue;
    cards.push({
      id,
      rect: el.getBoundingClientRect(),
      priority,
      viewTransitionName: vtn,
    });
  }
  return cards;
}

export function diffSnapshots(
  oldSnap: CardSnapshot[],
  newSnap: CardSnapshot[],
): { entering: CardSnapshot[]; leaving: CardSnapshot[] } {
  const oldIds = new Set(oldSnap.map(c => c.id));
  const newIds = new Set(newSnap.map(c => c.id));

  return {
    entering: newSnap.filter(c => !oldIds.has(c.id)),
    leaving: oldSnap.filter(c => !newIds.has(c.id)),
  };
}

export function animateFlights(
  transition: ViewTransition,
  entering: CardSnapshot[],
  leaving: CardSnapshot[],
  config: FlightConfig,
) {
  const allNames = [
    ...entering.map(c => c.viewTransitionName),
    ...leaving.map(c => c.viewTransitionName),
  ];

  if (allNames.length === 0) return;

  // Inject style to suppress default cross-fade on unmatched cards
  const style = document.createElement('style');
  style.textContent = allNames
    .map(
      name =>
        `::view-transition-old(${name}),::view-transition-new(${name}){animation:none!important;}`
    )
    .join('\n');
  document.head.appendChild(style);

  // Animate on transition.ready
  transition.ready.then(() => {
    // Sort entering: priority DESC (urgent first)
    const sortedEntering = [...entering].sort((a, b) => b.priority - a.priority);
    // Sort leaving: priority ASC (least important first)
    const sortedLeaving = [...leaving].sort((a, b) => a.priority - b.priority);

    // Animate entering cards
    sortedEntering.forEach((card, i) => {
      const cardCenter = {
        x: card.rect.left + card.rect.width / 2,
        y: card.rect.top + card.rect.height / 2,
      };
      const dx = config.enterFrom.x - cardCenter.x;
      const dy = config.enterFrom.y - cardCenter.y;

      if (i < MAX_ANIMATED) {
        try {
          document.documentElement.animate(
            [
              { transform: `translate(${dx}px, ${dy}px) scale(${SCALE_AT_SIDEBAR})`, opacity: 0 },
              { transform: 'translate(0, 0) scale(1)', opacity: 1 },
            ],
            {
              duration: ENTER_DURATION,
              easing: ENTER_EASING,
              delay: i * ENTER_STAGGER,
              fill: 'both',
              pseudoElement: `::view-transition-new(${card.viewTransitionName})`,
            }
          );
        } catch {
          // Browser doesn't support pseudoElement option — fallback is fine
        }
      } else {
        // Overflow cards: instant appear
        try {
          document.documentElement.animate(
            [{ opacity: 0 }, { opacity: 1 }],
            {
              duration: 50,
              fill: 'both',
              pseudoElement: `::view-transition-new(${card.viewTransitionName})`,
            }
          );
        } catch { /* ignore */ }
      }
    });

    // Animate leaving cards
    sortedLeaving.forEach((card, i) => {
      const cardCenter = {
        x: card.rect.left + card.rect.width / 2,
        y: card.rect.top + card.rect.height / 2,
      };
      const dx = config.leaveTo.x - cardCenter.x;
      const dy = config.leaveTo.y - cardCenter.y;

      if (i < MAX_ANIMATED) {
        try {
          document.documentElement.animate(
            [
              { transform: 'translate(0, 0) scale(1)', opacity: 1 },
              { transform: `translate(${dx}px, ${dy}px) scale(${SCALE_AT_SIDEBAR})`, opacity: 0 },
            ],
            {
              duration: LEAVE_DURATION,
              easing: LEAVE_EASING,
              delay: i * LEAVE_STAGGER,
              fill: 'both',
              pseudoElement: `::view-transition-old(${card.viewTransitionName})`,
            }
          );
        } catch { /* ignore */ }
      } else {
        try {
          document.documentElement.animate(
            [{ opacity: 1 }, { opacity: 0 }],
            {
              duration: 50,
              fill: 'both',
              pseudoElement: `::view-transition-old(${card.viewTransitionName})`,
            }
          );
        } catch { /* ignore */ }
      }
    });
  });

  // Cleanup dynamic style when transition finishes
  const cleanup = () => style.remove();
  transition.finished.then(cleanup).catch(cleanup);
}

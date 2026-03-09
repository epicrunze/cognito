import { tick } from 'svelte';

let _expandedTaskId = $state<number | string | null>(null);

function withViewTransition(update: () => void) {
  if (typeof document !== 'undefined' && document.startViewTransition) {
    document.startViewTransition(async () => {
      update();
      await tick();
    });
  } else {
    update();
  }
}

export const bubbleStore = {
  get expandedTaskId() { return _expandedTaskId; },
  expand(id: number | string) {
    withViewTransition(() => { _expandedTaskId = id; });
  },
  collapse() {
    if (_expandedTaskId === null) return;
    withViewTransition(() => { _expandedTaskId = null; });
  },
  toggle(id: number | string) {
    withViewTransition(() => {
      _expandedTaskId = _expandedTaskId === id ? null : id;
    });
  },
  /** Collapse without View Transition — for callers that manage their own VT */
  collapseImmediate() { _expandedTaskId = null; },
};

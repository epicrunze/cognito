// Maps sidebar nav/project paths → element center points for fly-from/to animations

interface Point { x: number; y: number }

let _rects = $state<Map<string, Point>>(new Map());

function getCenter(el: Element): Point {
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
}

export const sidebarRectsStore = {
  register(path: string, el: Element) {
    _rects.set(path, getCenter(el));
  },

  unregister(path: string) {
    _rects.delete(path);
  },

  refresh(path: string, el: Element) {
    _rects.set(path, getCenter(el));
  },

  getOrigin(path: string): Point | null {
    return _rects.get(path) ?? null;
  },
};

/** Svelte action: registers an element's center point for a given path */
export function registerRect(node: Element, path: string) {
  sidebarRectsStore.register(path, node);

  const onResize = () => sidebarRectsStore.refresh(path, node);
  window.addEventListener('resize', onResize);

  return {
    update(newPath: string) {
      sidebarRectsStore.unregister(path);
      path = newPath;
      sidebarRectsStore.register(path, node);
    },
    destroy() {
      window.removeEventListener('resize', onResize);
      sidebarRectsStore.unregister(path);
    },
  };
}

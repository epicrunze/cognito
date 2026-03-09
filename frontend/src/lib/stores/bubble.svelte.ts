let _expandedTaskId = $state<number | string | null>(null);

export const bubbleStore = {
  get expandedTaskId() { return _expandedTaskId; },
  expand(id: number | string) { _expandedTaskId = id; },
  collapse() { _expandedTaskId = null; },
  toggle(id: number | string) { _expandedTaskId = _expandedTaskId === id ? null : id; },
};

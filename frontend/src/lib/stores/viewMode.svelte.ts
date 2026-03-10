let _viewMode = $state<'bubbles' | 'kanban' | 'list'>('bubbles');

export const viewModeStore = {
  get current() { return _viewMode; },
  set(mode: 'bubbles' | 'kanban' | 'list') { _viewMode = mode; },
  get isKanban() { return _viewMode === 'kanban'; },
};

let _viewMode = $state<'bubbles' | 'kanban' | 'list' | 'gantt' | 'calendar'>('bubbles');
let _isFocus = $state(typeof localStorage !== 'undefined' && localStorage.getItem('cognito:focus-mode') === 'true');

export const viewModeStore = {
  get current() { return _viewMode; },
  set(mode: 'bubbles' | 'kanban' | 'list' | 'gantt' | 'calendar') { _viewMode = mode; },
  get isKanban() { return _viewMode === 'kanban'; },
  get isFocus() { return _isFocus; },
  toggleFocus() {
    _isFocus = !_isFocus;
    localStorage.setItem('cognito:focus-mode', String(_isFocus));
  },
};

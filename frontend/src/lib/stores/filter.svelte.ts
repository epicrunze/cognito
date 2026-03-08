export type SortMode = 'smart' | 'priority' | 'due_date' | 'created' | 'title';

let _status = $state<'all' | 'active' | 'completed'>('all');
let _priorities = $state<number[]>([]);
let _labelIds = $state<number[]>([]);
let _sortMode = $state<SortMode>('smart');
let _viewedTaskIds = $state<Set<number>>(new Set());

export const filterStore = {
  get status() { return _status; },
  get priorities() { return _priorities; },
  get labelIds() { return _labelIds; },
  get sortMode() { return _sortMode; },
  get viewedTaskIds() { return _viewedTaskIds; },

  setStatus(s: 'all' | 'active' | 'completed') { _status = s; },
  setSortMode(m: SortMode) { _sortMode = m; },

  togglePriority(p: number) {
    if (_priorities.includes(p)) {
      _priorities = _priorities.filter(v => v !== p);
    } else {
      _priorities = [..._priorities, p];
    }
  },

  toggleLabel(id: number) {
    if (_labelIds.includes(id)) {
      _labelIds = _labelIds.filter(v => v !== id);
    } else {
      _labelIds = [..._labelIds, id];
    }
  },

  markViewed(taskId: number) {
    _viewedTaskIds = new Set([..._viewedTaskIds, taskId]);
  },

  get activeFilterCount(): number {
    let count = 0;
    if (_status !== 'all') count++;
    if (_priorities.length > 0) count++;
    if (_labelIds.length > 0) count++;
    return count;
  },

  clearAll() {
    _status = 'all';
    _priorities = [];
    _labelIds = [];
  },
};

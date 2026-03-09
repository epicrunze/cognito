export type SortMode = 'smart' | 'priority' | 'due_date' | 'created' | 'title';

function loadSet(key: string): Set<number> {
  if (typeof localStorage === 'undefined') return new Set();
  try {
    const raw = localStorage.getItem(key);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function saveSet(key: string, set: Set<number>) {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(key, JSON.stringify([...set]));
}

let _status = $state<'all' | 'active' | 'completed'>('all');
let _priorities = $state<number[]>([]);
let _labelIds = $state<number[]>([]);
let _sortMode = $state<SortMode>('smart');
let _viewedTaskIds = $state<Set<number>>(loadSet('cognito:viewed-task-ids'));
let _aiTaggedIds = $state<Set<number>>(loadSet('cognito:ai-tagged-ids'));

export const filterStore = {
  get status() { return _status; },
  get priorities() { return _priorities; },
  get labelIds() { return _labelIds; },
  get sortMode() { return _sortMode; },
  get viewedTaskIds() { return _viewedTaskIds; },
  get aiTaggedIds() { return _aiTaggedIds; },

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
    saveSet('cognito:viewed-task-ids', _viewedTaskIds);
  },

  addAiTagged(taskId: number) {
    _aiTaggedIds = new Set([..._aiTaggedIds, taskId]);
    saveSet('cognito:ai-tagged-ids', _aiTaggedIds);
  },

  addAiTaggedBatch(taskIds: number[]) {
    _aiTaggedIds = new Set([..._aiTaggedIds, ...taskIds]);
    saveSet('cognito:ai-tagged-ids', _aiTaggedIds);
  },

  get vikunjaSort(): { sort_by: string; order_by: string } | null {
    switch (_sortMode) {
      case 'smart': return null;
      case 'priority': return { sort_by: 'priority', order_by: 'desc' };
      case 'due_date': return { sort_by: 'due_date', order_by: 'asc' };
      case 'created': return { sort_by: 'created', order_by: 'desc' };
      case 'title': return { sort_by: 'title', order_by: 'asc' };
      default: return null;
    }
  },

  get vikunjaFilter(): string {
    const parts: string[] = [];
    if (_status === 'active') parts.push('done = false');
    else if (_status === 'completed') parts.push('done = true');
    if (_priorities.length > 0) {
      parts.push(`priority in [${_priorities.join(', ')}]`);
    }
    return parts.join(' && ');
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

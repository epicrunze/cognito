import { dateBoundaryUTC, localToday } from '$lib/dateUtils';

export type SortMode = 'smart' | 'priority' | 'due_date' | 'created' | 'title';
export type DueDatePreset = 'any' | 'overdue' | 'today' | 'this_week' | 'this_month' | 'no_date';

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
let _dueDateFilter = $state<DueDatePreset>('any');
let _hasSubtasks = $state<boolean | null>(null);
let _viewedTaskIds = $state<Set<number>>(loadSet('cognito:viewed-task-ids'));
let _aiTaggedIds = $state<Set<number>>(loadSet('cognito:ai-tagged-ids'));

export const filterStore = {
  get status() { return _status; },
  get priorities() { return _priorities; },
  get labelIds() { return _labelIds; },
  get sortMode() { return _sortMode; },
  get dueDateFilter() { return _dueDateFilter; },
  get hasSubtasks() { return _hasSubtasks; },
  get viewedTaskIds() { return _viewedTaskIds; },
  get aiTaggedIds() { return _aiTaggedIds; },

  setStatus(s: 'all' | 'active' | 'completed') { _status = s; },
  setSortMode(m: SortMode) { _sortMode = m; },
  setDueDateFilter(f: DueDatePreset) { _dueDateFilter = f; },
  setHasSubtasks(v: boolean | null) { _hasSubtasks = v; },

  setPriorities(ps: number[]) { _priorities = ps; },

  setLabelIds(ids: number[]) { _labelIds = ids; },

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
    // Due date server-side filters (no_date handled client-side)
    if (_dueDateFilter !== 'any' && _dueDateFilter !== 'no_date') {
      const today = localToday();
      const todayStart = dateBoundaryUTC(today);
      const tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
      const tomorrowStart = dateBoundaryUTC(tomorrow);

      switch (_dueDateFilter) {
        case 'overdue':
          parts.push(`due_date < "${todayStart}" && due_date != "0001-01-01T00:00:00Z"`);
          break;
        case 'today':
          parts.push(`due_date >= "${todayStart}" && due_date < "${tomorrowStart}"`);
          break;
        case 'this_week': {
          const weekEnd = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 7);
          parts.push(`due_date >= "${todayStart}" && due_date < "${dateBoundaryUTC(weekEnd)}"`);
          break;
        }
        case 'this_month': {
          const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 1);
          parts.push(`due_date >= "${todayStart}" && due_date < "${dateBoundaryUTC(monthEnd)}"`);
          break;
        }
      }
    }
    return parts.join(' && ');
  },

  get activeFilterCount(): number {
    let count = 0;
    if (_status !== 'all') count++;
    if (_priorities.length > 0) count++;
    if (_labelIds.length > 0) count++;
    if (_dueDateFilter !== 'any') count++;
    if (_hasSubtasks !== null) count++;
    return count;
  },

  clearAll() {
    _status = 'all';
    _priorities = [];
    _labelIds = [];
    _dueDateFilter = 'any';
    _hasSubtasks = null;
  },
};

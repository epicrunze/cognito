import type { Task } from '$lib/types';
import { filterStore } from '$lib/stores/filter.svelte';
import { searchStore } from '$lib/stores/search.svelte';

/**
 * Apply client-side filters (priority, labels, due date, subtasks, search).
 * Used by BubbleCanvas, TaskList, and KanbanBoard to avoid duplicated logic.
 */
export function applyClientFilters(tasks: Task[], query?: string): Task[] {
  let t = tasks;

  // Search
  const q = (query ?? searchStore.query ?? '').toLowerCase();
  if (q) {
    t = t.filter(task => task.title.toLowerCase().includes(q) || task.description?.toLowerCase().includes(q));
  }

  // Priority
  if (filterStore.priorities.length > 0) {
    t = t.filter(task => filterStore.priorities.includes(task.priority));
  }

  // Labels
  if (filterStore.labelIds.length > 0) {
    t = t.filter(task => task.labels.some(l => filterStore.labelIds.includes(l.id)));
  }

  // Due date: "no_date" preset (client-side only since Vikunja null date filtering is unreliable)
  if (filterStore.dueDateFilter === 'no_date') {
    t = t.filter(task => !task.due_date || task.due_date.startsWith('0001-01-01'));
  }

  // Has subtasks
  if (filterStore.hasSubtasks === true) {
    t = t.filter(task => (task.subtask_total ?? 0) > 0);
  } else if (filterStore.hasSubtasks === false) {
    t = t.filter(task => (task.subtask_total ?? 0) === 0);
  }

  return t;
}

import { tasksStore } from '$lib/stores/tasks.svelte';
import { kanbanStore } from '$lib/stores/kanban.svelte';

function createTaskDetailStore() {
  let selectedTaskId = $state<number | null>(null);

  const isOpen = $derived(selectedTaskId !== null);

  return {
    get selectedTaskId() {
      return selectedTaskId;
    },
    get isOpen() {
      return isOpen;
    },

    open(taskId: number) {
      selectedTaskId = taskId;
    },

    close() {
      selectedTaskId = null;
    },

    /** Navigate to next task in the visible task list */
    navigateNext() {
      if (selectedTaskId == null) return;
      const tasks = this._getVisibleTasks();
      const idx = tasks.findIndex(t => t.id === selectedTaskId);
      if (idx >= 0 && idx < tasks.length - 1) {
        selectedTaskId = tasks[idx + 1].id;
      }
    },

    /** Navigate to previous task in the visible task list */
    navigatePrev() {
      if (selectedTaskId == null) return;
      const tasks = this._getVisibleTasks();
      const idx = tasks.findIndex(t => t.id === selectedTaskId);
      if (idx > 0) {
        selectedTaskId = tasks[idx - 1].id;
      }
    },

    /** Get the current visible task list (from tasks store or kanban) */
    _getVisibleTasks() {
      // If kanban has tasks loaded, flatten them in bucket order
      if (kanbanStore.buckets.length > 0 && kanbanStore.tasksByBucket.size > 0) {
        const tasks = [];
        for (const bucket of kanbanStore.buckets) {
          const bucketTasks = kanbanStore.tasksByBucket.get(bucket.id) ?? [];
          tasks.push(...bucketTasks);
        }
        if (tasks.length > 0) return tasks;
      }
      // Fallback to tasks store
      return tasksStore.tasks;
    },
  };
}

export const taskDetailStore = createTaskDetailStore();

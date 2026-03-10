import { tasksApi } from '$lib/api';
import { tasksStore } from '$lib/stores/tasks.svelte';
import { kanbanStore } from '$lib/stores/kanban.svelte';
import { optimisticUpdate } from '$lib/optimistic';
import type { Task } from '$lib/types';

/** Find a task's full object in whichever store has it */
function findTask(id: number): Task | undefined {
  const fromList = tasksStore.tasks.find(t => t.id === id);
  if (fromList) return fromList;
  for (const tasks of kanbanStore.tasksByBucket.values()) {
    const found = tasks.find(t => t.id === id);
    if (found) return found;
  }
  return undefined;
}

export async function updateTask(id: number, data: Partial<Task>) {
  const original = findTask(id);
  if (!original) return;
  const kanbanSnapshot = new Map(kanbanStore.tasksByBucket);

  const result = await optimisticUpdate({
    apply: () => {
      tasksStore.patchTask(id, data);
      kanbanStore.patchTask(id, data);
    },
    apiCall: () => tasksApi.update(id, data),
    rollback: () => {
      tasksStore.patchTask(id, original);
      kanbanStore.restoreTasksByBucket(kanbanSnapshot);
    },
    errorMessage: 'Failed to update task',
  });
  // Merge server timestamp so UI reflects the real updated time
  if (result?.updated) {
    tasksStore.patchTask(id, { updated: result.updated });
    kanbanStore.patchTask(id, { updated: result.updated });
  }
}

export async function toggleDone(id: number) {
  const task = findTask(id);
  if (!task) return;
  await updateTask(id, { done: !task.done });
}

export async function deleteTask(id: number) {
  const tasksSnapshot = [...tasksStore.tasks];
  const kanbanSnapshot = new Map(kanbanStore.tasksByBucket);

  await optimisticUpdate({
    apply: () => {
      tasksStore.removeTask(id);
      kanbanStore.removeTask(id);
    },
    apiCall: () => tasksApi.delete(id),
    rollback: () => {
      tasksStore.restoreTasks(tasksSnapshot);
      kanbanStore.restoreTasksByBucket(kanbanSnapshot);
    },
    errorMessage: 'Failed to delete task',
  });
}

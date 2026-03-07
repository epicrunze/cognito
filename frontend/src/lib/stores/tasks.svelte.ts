import { tasksApi } from '$lib/api';
import { optimisticUpdate } from '$lib/optimistic';
import type { Task } from '$lib/types';

function createTasksStore() {
  let tasks = $state<Task[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  return {
    get tasks() {
      return tasks;
    },
    get loading() {
      return loading;
    },
    get error() {
      return error;
    },

    async fetchAll() {
      loading = true;
      error = null;
      try {
        const res = await tasksApi.list({});
        tasks = res.tasks;
      } catch (e) {
        error = e instanceof Error ? e.message : 'Failed to load tasks';
      } finally {
        loading = false;
      }
    },

    async fetchByProject(projectId: number) {
      loading = true;
      error = null;
      try {
        const res = await tasksApi.list({ project_id: projectId });
        tasks = res.tasks;
      } catch (e) {
        error = e instanceof Error ? e.message : 'Failed to load tasks';
      } finally {
        loading = false;
      }
    },

    async create(data: { project_id: number; title: string; priority?: number; due_date?: string; description?: string }) {
      const tempId = -Date.now();
      const temp: Task = {
        id: tempId,
        title: data.title,
        done: false,
        priority: (data.priority ?? 3) as Task['priority'],
        due_date: data.due_date ?? null,
        project_id: data.project_id,
        labels: [],
        description: data.description ?? '',
        done_at: null,
        start_date: null,
        end_date: null,
        percent_done: 0,
        hex_color: '',
        repeat_after: 0,
        repeat_mode: 0,
        index: 0,
        identifier: '',
        is_favorite: false,
        position: 0,
        bucket_id: 0,
        created_by: null,
        created: new Date().toISOString(),
        updated: new Date().toISOString(),
      };

      await optimisticUpdate({
        apply: () => {
          tasks = [temp, ...tasks];
        },
        apiCall: async () => {
          const created = await tasksApi.create(data);
          console.log('[tasks] created:', created);
          tasks = tasks.map((t) => (t.id === tempId ? created : t));
        },
        rollback: () => {
          tasks = tasks.filter((t) => t.id !== tempId);
        },
        errorMessage: 'Failed to create task',
      });
    },

    async toggleDone(id: number) {
      const task = tasks.find((t) => t.id === id);
      if (!task) return;
      const newDone = !task.done;

      await optimisticUpdate({
        apply: () => {
          tasks = tasks.map((t) => (t.id === id ? { ...t, done: newDone } : t));
        },
        apiCall: () => tasksApi.update(id, { done: newDone }),
        rollback: () => {
          tasks = tasks.map((t) => (t.id === id ? { ...t, done: !newDone } : t));
        },
        errorMessage: 'Failed to update task',
      });
    },

    async update(id: number, data: Partial<Task>) {
      const original = tasks.find((t) => t.id === id);
      if (!original) return;

      await optimisticUpdate({
        apply: () => {
          tasks = tasks.map((t) => (t.id === id ? { ...t, ...data } : t));
        },
        apiCall: () => tasksApi.update(id, data),
        rollback: () => {
          tasks = tasks.map((t) => (t.id === id ? original : t));
        },
        errorMessage: 'Failed to update task',
      });
    },

    async delete(id: number) {
      const snapshot = [...tasks];

      await optimisticUpdate({
        apply: () => {
          tasks = tasks.filter((t) => t.id !== id);
        },
        apiCall: () => tasksApi.delete(id),
        rollback: () => {
          tasks = snapshot;
        },
        errorMessage: 'Failed to delete task',
      });
    },
  };
}

export const tasksStore = createTasksStore();

import { tasksApi } from '$lib/api';
import { optimisticUpdate } from '$lib/optimistic';
import type { Task } from '$lib/types';

export interface FetchParams {
  sort_by?: string;
  order_by?: string;
  filter?: string;
}

function normalizeTask(t: Task): Task {
  return { ...t, labels: t.labels ?? [] };
}

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

    async fetchAll(params?: FetchParams) {
      loading = true;
      error = null;
      try {
        const res = await tasksApi.list({ ...params });
        tasks = res.tasks.map(normalizeTask);
      } catch (e) {
        error = e instanceof Error ? e.message : 'Failed to load tasks';
      } finally {
        loading = false;
      }
    },

    async fetchByProject(projectId: number, params?: FetchParams) {
      loading = true;
      error = null;
      try {
        const res = await tasksApi.list({ project_id: projectId, ...params });
        tasks = res.tasks.map(normalizeTask);
      } catch (e) {
        error = e instanceof Error ? e.message : 'Failed to load tasks';
      } finally {
        loading = false;
      }
    },

    async create(data: { project_id: number; title: string; priority?: number; due_date?: string; description?: string }): Promise<Task | undefined> {
      const tempId = -Date.now();
      const temp: Task = {
        id: tempId,
        title: data.title,
        done: false,
        priority: (data.priority ?? 3) as Task['priority'],
        due_date: data.due_date ?? null,
        project_id: data.project_id,
        labels: [],
        attachments: [],
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

      const result = await optimisticUpdate({
        apply: () => {
          tasks = [temp, ...tasks];
        },
        apiCall: async () => {
          const created = await tasksApi.create(data);
          tasks = tasks.map((t) => (t.id === tempId ? normalizeTask(created) : t));
          return normalizeTask(created);
        },
        rollback: () => {
          tasks = tasks.filter((t) => t.id !== tempId);
        },
        errorMessage: 'Failed to create task',
      });
      return result;
    },

    patchTask(id: number, data: Partial<Task>) {
      tasks = tasks.map(t => t.id === id ? { ...t, ...data } : t);
    },

    removeTask(id: number) {
      tasks = tasks.filter(t => t.id !== id);
    },

    restoreTasks(snapshot: Task[]) {
      tasks = snapshot;
    },
  };
}

export const tasksStore = createTasksStore();

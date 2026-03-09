import { kanbanApi, tasksApi } from '$lib/api';
import { optimisticUpdate } from '$lib/optimistic';
import type { Bucket, ProjectView, Task } from '$lib/types';

function normalizeTask(t: Task): Task {
  return { ...t, labels: t.labels ?? [] };
}

function createKanbanStore() {
  let projectId = $state<number>(0);
  let view = $state<ProjectView | null>(null);
  let buckets = $state<Bucket[]>([]);
  let tasksByBucket = $state<Map<number, Task[]>>(new Map());
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Lightweight task→bucket name lookup for list view badges
  let taskBucketNames = $state<Map<number, string>>(new Map());
  let bucketMapFetchedFor = new Set<number>();

  return {
    get projectId() { return projectId; },
    get view() { return view; },
    get buckets() { return buckets; },
    get tasksByBucket() { return tasksByBucket; },
    get loading() { return loading; },
    get error() { return error; },
    get taskBucketNames() { return taskBucketNames; },

    async fetchBoard(pid: number) {
      projectId = pid;
      loading = true;
      error = null;
      try {
        // 1. Get views, find kanban view
        const viewsRes = await kanbanApi.listViews(pid);
        let kanbanView = viewsRes.views.find(
          (v) => v.view_kind === 'kanban'
        );

        // Auto-create kanban view if none exists
        if (!kanbanView) {
          kanbanView = await kanbanApi.createView(pid, 'Kanban', 'kanban');
        }
        view = kanbanView;

        // 2. Get buckets with nested tasks via view tasks endpoint
        const data = await kanbanApi.listViewTasks(pid, kanbanView.id);
        // Kanban view tasks endpoint returns an array of buckets with nested tasks
        if (Array.isArray(data) && data.length > 0 && data[0]?.id != null) {
          buckets = data.map((b: Bucket) => ({ ...b, tasks: undefined })) as Bucket[];
          const newMap = new Map<number, Task[]>();
          for (const b of data) {
            newMap.set(b.id, (b.tasks ?? []).map(t => ({ ...normalizeTask(t), bucket_id: b.id })));
          }
          tasksByBucket = newMap;

          // Also populate bucket name lookup
          const nameMap = new Map(taskBucketNames);
          for (const b of data) {
            for (const t of b.tasks ?? []) {
              nameMap.set(t.id, b.title);
            }
          }
          taskBucketNames = nameMap;
          bucketMapFetchedFor.add(pid);
        } else {
          // Fallback: fetch buckets separately
          const bucketsRes = await kanbanApi.listBuckets(pid, kanbanView.id);
          buckets = bucketsRes.buckets;
          const newMap = new Map<number, Task[]>();
          for (const b of buckets) {
            newMap.set(b.id, []);
          }
          tasksByBucket = newMap;
        }
      } catch (e) {
        error = e instanceof Error ? e.message : 'Failed to load kanban board';
      } finally {
        loading = false;
      }
    },

    async fetchBucketMap(pid: number) {
      // Skip if already fetched for this project (or if fetchBoard already populated it)
      if (bucketMapFetchedFor.has(pid)) return;
      try {
        const viewsRes = await kanbanApi.listViews(pid);
        const kanbanView = viewsRes.views.find(v => v.view_kind === 'kanban');
        if (!kanbanView) return;

        const data = await kanbanApi.listViewTasks(pid, kanbanView.id);
        if (Array.isArray(data) && data.length > 0 && data[0]?.id != null) {
          const nameMap = new Map(taskBucketNames);
          for (const b of data) {
            for (const t of b.tasks ?? []) {
              nameMap.set(t.id, b.title);
            }
          }
          taskBucketNames = nameMap;
          bucketMapFetchedFor.add(pid);
        }
      } catch {
        // Non-critical — silently skip
      }
    },

    getBucketName(taskId: number): string | null {
      return taskBucketNames.get(taskId) ?? null;
    },

    async moveTask(taskId: number, fromBucketId: number, toBucketId: number, newIndex: number) {
      if (!view) return;
      const viewId = view.id;
      const pid = projectId;

      // Calculate position based on neighbours
      const targetTasks = [...(tasksByBucket.get(toBucketId) ?? [])];
      // Remove task from source if same bucket reorder
      const taskIdx = targetTasks.findIndex(t => t.id === taskId);
      let task: Task | undefined;

      if (fromBucketId === toBucketId && taskIdx >= 0) {
        [task] = targetTasks.splice(taskIdx, 1);
      } else {
        const sourceTasks = tasksByBucket.get(fromBucketId) ?? [];
        task = sourceTasks.find(t => t.id === taskId);
      }
      if (!task) return;

      // Insert at new position to calculate midpoint
      const before = newIndex > 0 ? targetTasks[newIndex - 1]?.position ?? null : null;
      const after = newIndex < targetTasks.length ? targetTasks[newIndex]?.position ?? null : null;
      const newPosition = midpoint(before, after);

      const snapshot = new Map(tasksByBucket);

      await optimisticUpdate({
        apply: () => {
          const newMap = new Map(tasksByBucket);
          // Remove from source
          const src = [...(newMap.get(fromBucketId) ?? [])].filter(t => t.id !== taskId);
          newMap.set(fromBucketId, src);
          // Add to destination
          const dst = [...(newMap.get(toBucketId) ?? [])].filter(t => t.id !== taskId);
          const updatedTask = { ...task!, position: newPosition, bucket_id: toBucketId };
          dst.splice(newIndex, 0, updatedTask);
          newMap.set(toBucketId, dst);
          tasksByBucket = newMap;
        },
        apiCall: async () => {
          if (fromBucketId !== toBucketId) {
            await kanbanApi.moveTaskToBucket(pid, viewId, toBucketId, taskId);
          }
          await kanbanApi.updateTaskPosition(taskId, newPosition, viewId);
        },
        rollback: () => {
          tasksByBucket = snapshot;
        },
        errorMessage: 'Failed to move task',
      });
    },

    async createBucket(title: string) {
      if (!view) return;
      const pid = projectId;
      const viewId = view.id;

      try {
        const bucket = await kanbanApi.createBucket(pid, viewId, title);
        buckets = [...buckets, bucket];
        const newMap = new Map(tasksByBucket);
        newMap.set(bucket.id, []);
        tasksByBucket = newMap;
      } catch {
        // Error handled by api.ts
      }
    },

    async createTaskInBucket(bucketId: number, title: string) {
      if (!view) return;
      const pid = projectId;

      try {
        const task = await tasksApi.create({ project_id: pid, title });
        const normalized = normalizeTask(task);
        // Move to correct bucket
        await kanbanApi.moveTaskToBucket(pid, view.id, bucketId, task.id);
        const newMap = new Map(tasksByBucket);
        const tasks = [...(newMap.get(bucketId) ?? []), normalized];
        newMap.set(bucketId, tasks);
        tasksByBucket = newMap;
      } catch {
        // Error handled by api.ts
      }
    },

    /** Update local state after DnD events (before API call) */
    updateLocalBucketTasks(bucketId: number, tasks: Task[]) {
      const newMap = new Map(tasksByBucket);
      newMap.set(bucketId, tasks);
      tasksByBucket = newMap;
    },

    patchTask(taskId: number, data: Partial<Task>) {
      const newMap = new Map(tasksByBucket);
      for (const [bucketId, bucketTasks] of newMap) {
        const idx = bucketTasks.findIndex(t => t.id === taskId);
        if (idx >= 0) {
          newMap.set(bucketId, [
            ...bucketTasks.slice(0, idx),
            { ...bucketTasks[idx], ...data },
            ...bucketTasks.slice(idx + 1),
          ]);
          tasksByBucket = newMap;
          return;
        }
      }
    },

    removeTask(taskId: number) {
      const newMap = new Map(tasksByBucket);
      for (const [bucketId, bucketTasks] of newMap) {
        if (bucketTasks.some(t => t.id === taskId)) {
          newMap.set(bucketId, bucketTasks.filter(t => t.id !== taskId));
          tasksByBucket = newMap;
          return;
        }
      }
    },

    restoreTasksByBucket(snapshot: Map<number, Task[]>) {
      tasksByBucket = snapshot;
    },
  };
}

function midpoint(before: number | null, after: number | null): number {
  if (before == null && after == null) return 65536;
  if (before == null) return after! / 2;
  if (after == null) return before + 65536;
  return (before + after) / 2;
}

export const kanbanStore = createKanbanStore();

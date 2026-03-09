<script lang="ts">
  import type { Task } from '$lib/types';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';
  import KanbanColumn from './KanbanColumn.svelte';
  import TaskPanel from './TaskPanel.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';

  let { projectId }: { projectId: number } = $props();

  let editingTaskId = $state<number | null>(null);
  let addingColumn = $state(false);
  let newColumnTitle = $state('');

  function findDraggedTask(oldOrder: number[], newOrder: number[]): { taskId: number; newIndex: number } | null {
    for (let i = 0; i < newOrder.length; i++) {
      const taskId = newOrder[i];
      if (oldOrder[i] === taskId) continue;
      const oldWithout = oldOrder.filter(id => id !== taskId);
      const newWithout = newOrder.filter(id => id !== taskId);
      if (oldWithout.length === newWithout.length && oldWithout.every((id, j) => id === newWithout[j])) {
        return { taskId, newIndex: i };
      }
    }
    return null;
  }

  const editingTask = $derived.by(() => {
    if (editingTaskId == null) return null;
    for (const tasks of kanbanStore.tasksByBucket.values()) {
      const found = tasks.find(t => t.id === editingTaskId);
      if (found) return found;
    }
    return null;
  });

  $effect(() => {
    if (kanbanStore.shouldSkipFetch()) return;
    kanbanStore.fetchBoard(projectId);
  });

  function handleTaskClick(taskId: number) {
    editingTaskId = taskId;
    filterStore.markViewed(taskId);
  }

  function handleTaskFinalized(bucketId: number, tasks: Task[]) {
    // Detect cross-bucket move: a task whose bucket_id doesn't match this bucket
    for (let i = 0; i < tasks.length; i++) {
      const task = tasks[i];
      if (task.bucket_id && task.bucket_id !== bucketId) {
        const fromBucketId = task.bucket_id;
        kanbanStore.updateLocalBucketTasks(bucketId, tasks);
        kanbanStore.moveTask(task.id, fromBucketId, bucketId, i);
        return;
      }
    }

    // Same-bucket reorder: read pre-drag order directly from store (not mutated during drag)
    const oldOrder = (kanbanStore.tasksByBucket.get(bucketId) ?? []).map(t => t.id);
    const newOrder = tasks.map(t => t.id);

    const dragged = findDraggedTask(oldOrder, newOrder);
    if (dragged) {
      kanbanStore.updateLocalBucketTasks(bucketId, tasks);
      kanbanStore.moveTask(dragged.taskId, bucketId, bucketId, dragged.newIndex);
    }
  }

  async function handleCreateColumn() {
    if (!newColumnTitle.trim()) return;
    await kanbanStore.createBucket(newColumnTitle.trim());
    newColumnTitle = '';
    addingColumn = false;
  }

  function handleColumnKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') handleCreateColumn();
    if (e.key === 'Escape') { addingColumn = false; newColumnTitle = ''; }
  }
</script>

{#if kanbanStore.loading}
  <div style="display: flex; gap: 16px; padding: 20px 24px; overflow-x: auto;">
    {#each [1, 2, 3] as _ (_)}
      <div style="width: 280px; flex-shrink: 0;">
        <Skeleton width="100%" height={300} radius={10} />
      </div>
    {/each}
  </div>
{:else if kanbanStore.error}
  <div style="display: flex; align-items: center; justify-content: center; padding: 80px 24px;">
    <span style="font-size: 15px; color: var(--overdue);">{kanbanStore.error}</span>
  </div>
{:else}
  <div style="display: flex; gap: 16px; padding: 20px 24px; overflow-x: auto; flex: 1; align-items: flex-start;">
    {#each kanbanStore.buckets as bucket (bucket.id)}
      <KanbanColumn
        {bucket}
        tasks={kanbanStore.tasksByBucket.get(bucket.id) ?? []}
        onTaskClick={handleTaskClick}
        onTaskFinalized={handleTaskFinalized}
        onCreateTask={(title) => kanbanStore.createTaskInBucket(bucket.id, title)}
      />
    {/each}

    <!-- Add column button -->
    {#if addingColumn}
      <div style="width: 280px; flex-shrink: 0;">
        <!-- svelte-ignore a11y_autofocus -->
        <input
          bind:value={newColumnTitle}
          onkeydown={handleColumnKeydown}
          placeholder="Column title..."
          style="width: 100%; background: var(--bg-surface); border: 1px solid var(--accent); border-radius: 8px; padding: 12px 14px; font-size: 14px; color: var(--text-primary); font-family: var(--font-sans); outline: none;"
          autofocus
        />
      </div>
    {:else}
      <button
        onclick={() => addingColumn = true}
        style="width: 280px; flex-shrink: 0; padding: 14px 16px; background: var(--bg-surface); border: 1px dashed var(--border-default); border-radius: 10px; color: var(--text-tertiary); font-size: 14px; font-weight: 500; cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
      >+ Add Column</button>
    {/if}
  </div>
{/if}

<TaskPanel mode="edit" open={editingTaskId !== null} task={editingTask ?? undefined} onclose={() => editingTaskId = null} />

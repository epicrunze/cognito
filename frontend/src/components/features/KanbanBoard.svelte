<script lang="ts">
  import type { Bucket, Task } from '$lib/types';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';
  import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
  import { applyClientFilters } from '$lib/filterUtils';
  import { dragHandleZone } from 'svelte-dnd-action';
  import KanbanColumn from './KanbanColumn.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';

  let { projectId }: { projectId: number } = $props();

  let addingColumn = $state(false);
  let newColumnTitle = $state('');
  let localBuckets = $state<Bucket[]>([]);
  let isDraggingColumn = $state(false);

  $effect(() => {
    if (!isDraggingColumn) {
      localBuckets = [...kanbanStore.buckets];
    }
  });

  function handleColumnConsider(e: CustomEvent<{ items: Bucket[] }>) {
    isDraggingColumn = true;
    localBuckets = e.detail.items;
  }

  function handleColumnFinalize(e: CustomEvent<{ items: Bucket[] }>) {
    isDraggingColumn = false;
    localBuckets = e.detail.items;
    // Find which bucket moved and to where
    const oldIds = kanbanStore.buckets.map(b => b.id);
    const newIds = e.detail.items.map(b => b.id);
    for (let i = 0; i < newIds.length; i++) {
      if (oldIds[i] !== newIds[i]) {
        const movedId = newIds[i];
        // Verify it actually moved (not just a downstream shift)
        const oldIdx = oldIds.indexOf(movedId);
        if (oldIdx !== i) {
          kanbanStore.reorderBuckets(movedId, i);
          return;
        }
      }
    }
  }

  // Density toggle with localStorage persistence
  let kanbanDensity = $state<'full' | 'compact'>(
    typeof localStorage !== 'undefined'
      ? (localStorage.getItem('cognito:kanban-density') as 'full' | 'compact') ?? 'full'
      : 'full'
  );

  function toggleDensity() {
    kanbanDensity = kanbanDensity === 'full' ? 'compact' : 'full';
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('cognito:kanban-density', kanbanDensity);
    }
  }

  // Filtered tasks per bucket
  const filteredTasksByBucket = $derived.by(() => {
    const result = new Map<number, Task[]>();
    for (const bucket of kanbanStore.buckets) {
      const raw = kanbanStore.tasksByBucket.get(bucket.id) ?? [];
      result.set(bucket.id, applyClientFilters(raw));
    }
    return result;
  });

  // Column color map based on common bucket names
  const columnColors: Record<string, string> = {
    'to do': 'var(--border-default)',
    'todo': 'var(--border-default)',
    'doing': 'var(--accent-blue, #5B8DEF)',
    'in progress': 'var(--accent-blue, #5B8DEF)',
    'done': 'var(--done)',
    'completed': 'var(--done)',
  };
  function getColumnColor(title: string): string {
    return columnColors[title.toLowerCase()] ?? 'var(--border-default)';
  }
  function isDoneBucket(bucketId: number): boolean {
    return bucketId === kanbanStore.doneBucketId;
  }

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

  $effect(() => {
    if (kanbanStore.shouldSkipFetch()) return;
    kanbanStore.fetchBoard(projectId);
  });

  function handleTaskClick(taskId: number) {
    taskDetailStore.open(taskId);
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
  <div style="display: flex; flex-direction: column; flex: 1; overflow: hidden;">
    <!-- Kanban toolbar -->
    <div style="display: flex; align-items: center; justify-content: flex-end; padding: 8px 24px 0; flex-shrink: 0;">
      <button
        onclick={toggleDensity}
        style="height: 28px; padding: 0 10px; font-size: 12px; font-weight: 500; color: var(--text-tertiary); background: var(--bg-elevated); border: 1px solid var(--border-default); border-radius: 6px; cursor: pointer; font-family: var(--font-sans); transition: all var(--transition-fast);"
      >{kanbanDensity === 'full' ? 'Compact' : 'Full'}</button>
    </div>
    <div style="display: flex; gap: 16px; padding: 12px 24px 20px; overflow-x: auto; -webkit-overflow-scrolling: touch; flex: 1; align-items: flex-start;">
    <div
      use:dragHandleZone={{ items: localBuckets, type: 'kanban-column', dropTargetStyle: { outline: '2px dashed var(--accent)', outlineOffset: '-2px' } }}
      onconsider={handleColumnConsider}
      onfinalize={handleColumnFinalize}
      style="display: flex; gap: 16px; align-items: flex-start;"
    >
    {#each localBuckets as bucket (bucket.id)}
      <KanbanColumn
        {bucket}
        tasks={filteredTasksByBucket.get(bucket.id) ?? []}
        allTasks={kanbanStore.tasksByBucket.get(bucket.id) ?? []}
        columnColor={getColumnColor(bucket.title)}
        isDoneBucket={isDoneBucket(bucket.id)}
        density={kanbanDensity}
        onTaskClick={handleTaskClick}
        onTaskFinalized={handleTaskFinalized}
        onCreateTask={(title) => kanbanStore.createTaskInBucket(bucket.id, title)}
      />
    {/each}
    </div>

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
        style="width: 280px; flex-shrink: 0; padding: 14px 16px; background: var(--bg-surface); border: 1px dashed var(--border-default); border-radius: 10px; color: var(--text-tertiary); font-size: 14px; font-weight: 500; cursor: pointer; font-family: var(--font-sans); transition: all var(--transition-fast);"
      >+ Add Column</button>
    {/if}
    </div>
  </div>
{/if}

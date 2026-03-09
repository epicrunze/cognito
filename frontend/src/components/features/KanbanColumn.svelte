<script lang="ts">
  import type { Bucket, Task } from '$lib/types';
  import { dndzone } from 'svelte-dnd-action';
  import KanbanCard from './KanbanCard.svelte';

  let {
    bucket,
    tasks = [],
    onTaskClick,
    onTaskFinalized,
    onCreateTask,
  }: {
    bucket: Bucket;
    tasks: Task[];
    onTaskClick?: (taskId: number) => void;
    onTaskFinalized?: (bucketId: number, tasks: Task[]) => void;
    onCreateTask?: (title: string) => void;
  } = $props();

  let localItems = $state<Task[]>([]);
  let isDragging = $state(false);
  let quickAddValue = $state('');

  $effect(() => {
    if (!isDragging) {
      localItems = [...tasks];
    }
  });

  function handleConsider(e: CustomEvent<{ items: Task[] }>) {
    isDragging = true;
    localItems = e.detail.items;
  }

  function handleFinalize(e: CustomEvent<{ items: Task[] }>) {
    isDragging = false;
    localItems = e.detail.items;
    onTaskFinalized?.(bucket.id, e.detail.items);
  }

  function handleQuickAdd(e: KeyboardEvent) {
    if (e.key !== 'Enter' || !quickAddValue.trim()) return;
    onCreateTask?.(quickAddValue.trim());
    quickAddValue = '';
  }
</script>

<div style="width: 280px; flex-shrink: 0; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 10px; display: flex; flex-direction: column; max-height: 100%;">
  <!-- Header -->
  <div style="padding: 14px 16px 10px; display: flex; align-items: center; justify-content: space-between;">
    <span style="font-size: 14px; font-weight: 600; color: var(--text-primary);">{bucket.title}</span>
    <span style="font-size: 12px; color: var(--text-tertiary); background: var(--bg-elevated); padding: 2px 8px; border-radius: 9999px;">{tasks.length}</span>
  </div>

  <!-- Cards (DnD zone) -->
  <div
    use:dndzone={{ items: localItems, dropTargetStyle: { outline: '2px dashed var(--accent)', outlineOffset: '-2px' }, type: 'kanban-card' }}
    onconsider={handleConsider}
    onfinalize={handleFinalize}
    style="flex: 1; overflow-y: auto; padding: 0 10px 10px; display: flex; flex-direction: column; gap: 8px; min-height: 60px;"
  >
    {#each localItems as task (task.id)}
      <div>
        <KanbanCard {task} onclick={() => onTaskClick?.(task.id)} />
      </div>
    {/each}
  </div>

  <!-- Quick add -->
  <div style="padding: 10px; border-top: 1px solid var(--border-subtle);">
    <input
      bind:value={quickAddValue}
      onkeydown={handleQuickAdd}
      placeholder="+ Add task..."
      style="width: 100%; background: transparent; border: 1px solid var(--border-default); border-radius: 6px; padding: 8px 10px; font-size: 13px; color: var(--text-primary); font-family: var(--font-sans); outline: none; transition: border-color 150ms;"
    />
  </div>
</div>

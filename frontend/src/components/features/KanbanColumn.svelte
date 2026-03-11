<script lang="ts">
  import type { Bucket, Task } from '$lib/types';
  import { dndzone } from 'svelte-dnd-action';
  import { bubbleStore } from '$lib/stores/bubble.svelte';
  import { toggleDone } from '$lib/stores/taskMutations';
  import { registerCelebrationElement, unregisterCelebrationElement } from '$lib/celebrate';
  import ThoughtBubble from './ThoughtBubble.svelte';

  // Track card elements for celebration on drag-to-done
  const cardElements = new Map<number, HTMLDivElement>();

  function trackCard(node: HTMLDivElement, taskId: number) {
    cardElements.set(taskId, node);
    registerCelebrationElement(taskId, node);
    return {
      destroy() {
        cardElements.delete(taskId);
        unregisterCelebrationElement(taskId);
      },
    };
  }

  let {
    bucket,
    tasks = [],
    allTasks,
    columnColor = 'var(--border-default)',
    isDoneBucket = false,
    density = 'full',
    onTaskClick,
    onTaskFinalized,
    onCreateTask,
  }: {
    bucket: Bucket;
    tasks: Task[];
    allTasks?: Task[];
    columnColor?: string;
    isDoneBucket?: boolean;
    density?: 'full' | 'compact';
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
    bubbleStore.collapse();
    localItems = e.detail.items;
  }

  function handleFinalize(e: CustomEvent<{ items: Task[] }>) {
    isDragging = false;
    localItems = e.detail.items;
    onTaskFinalized?.(bucket.id, e.detail.items);
    // Auto-complete tasks dragged to Done bucket
    if (isDoneBucket) {
      for (const task of e.detail.items) {
        if (!task.done) {
          toggleDone(task.id);
        }
      }
    }
  }

  function handleQuickAdd(e: KeyboardEvent) {
    if (e.key !== 'Enter' || !quickAddValue.trim()) return;
    onCreateTask?.(quickAddValue.trim());
    quickAddValue = '';
  }
</script>

<div style="width: 280px; flex-shrink: 0; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 10px; display: flex; flex-direction: column; max-height: 100%;">
  <!-- Header -->
  <div style="padding: 14px 16px 10px; display: flex; align-items: center; justify-content: space-between; border-top: 2px solid {columnColor}; border-radius: 10px 10px 0 0;">
    <span style="font-size: 14px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
      {#if isDoneBucket}
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="var(--done)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.5" /><path d="M5.5 8l2 2 3.5-3.5" /></svg>
      {/if}
      {bucket.title}
    </span>
    <span style="font-size: 12px; color: var(--text-tertiary); background: var(--bg-elevated); padding: 2px 8px; border-radius: 9999px;">{allTasks && allTasks.length !== tasks.length ? `${tasks.length}/${allTasks.length}` : tasks.length}</span>
  </div>

  <!-- Cards (DnD zone) -->
  <div
    use:dndzone={{ items: localItems, dropTargetStyle: { outline: '2px dashed var(--accent)', outlineOffset: '-2px' }, type: 'kanban-card' }}
    onconsider={handleConsider}
    onfinalize={handleFinalize}
    style="flex: 1; overflow-y: auto; padding: 0 10px 10px; display: flex; flex-direction: column; gap: 8px; min-height: 60px;"
  >
    {#each localItems as task (task.id)}
      <div use:trackCard={task.id}>
        <ThoughtBubble {task} kanban={true} kanbanCompact={density === 'compact'} onclick={() => onTaskClick?.(task.id)} />
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

<script lang="ts">
  import { untrack } from 'svelte';
  import { fly } from 'svelte/transition';
  import { tasksStore } from '$lib/stores.svelte';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';
  import { viewModeStore } from '$lib/stores/viewMode.svelte';
  import TaskDetailContent from './TaskDetailContent.svelte';
  import type { Task } from '$lib/types';
  import { onMount } from 'svelte';

  const task = $derived.by((): Task | undefined => {
    const id = taskDetailStore.selectedTaskId;
    if (id == null) return undefined;

    // Check kanban store first (may have fresher data)
    for (const tasks of kanbanStore.tasksByBucket.values()) {
      const found = tasks.find(t => t.id === id);
      if (found) return found;
    }

    // Fallback to tasks store
    return tasksStore.tasks.find(t => t.id === id);
  });

  const isKanban = $derived(viewModeStore.isKanban);

  function handleClose() {
    taskDetailStore.close();
  }

  // Mark task as viewed when opened
  $effect(() => {
    const id = taskDetailStore.selectedTaskId;
    if (id != null) {
      untrack(() => filterStore.markViewed(id));
    }
  });

  // --- Draggable overlay for kanban mode ---
  const STORAGE_KEY = 'cognito:taskdetail-pos';
  const DEFAULT_POS = { top: 80, right: 24 };

  let dragPos = $state<{ top: number; right: number }>(DEFAULT_POS);
  let dragging = $state(false);
  let dragOffset = { x: 0, y: 0 };

  // Load saved position
  onMount(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (typeof parsed.top === 'number' && typeof parsed.right === 'number') {
          dragPos = parsed;
        }
      }
    } catch { /* use default */ }
  });

  function handleDragStart(e: MouseEvent) {
    e.preventDefault();
    dragging = true;
    // Convert right-based to left-based for dragging
    const panelLeft = window.innerWidth - dragPos.right - 440;
    dragOffset = { x: e.clientX - panelLeft, y: e.clientY - dragPos.top };
    window.addEventListener('mousemove', handleDragMove);
    window.addEventListener('mouseup', handleDragEnd);
  }

  function handleDragMove(e: MouseEvent) {
    const newLeft = e.clientX - dragOffset.x;
    const newTop = e.clientY - dragOffset.y;
    const newRight = window.innerWidth - newLeft - 440;
    dragPos = {
      top: Math.max(0, Math.min(newTop, window.innerHeight - 100)),
      right: Math.max(0, Math.min(newRight, window.innerWidth - 200)),
    };
  }

  function handleDragEnd() {
    dragging = false;
    window.removeEventListener('mousemove', handleDragMove);
    window.removeEventListener('mouseup', handleDragEnd);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(dragPos));
    } catch { /* ignore */ }
  }

  // Reset position when panel opens
  $effect(() => {
    if (taskDetailStore.isOpen && isKanban) {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (typeof parsed.top === 'number' && typeof parsed.right === 'number') {
            dragPos = parsed;
          }
        }
      } catch { /* use current */ }
    }
  });
</script>

{#if taskDetailStore.isOpen}
  {#if isKanban}
    <!-- Kanban mode: fixed overlay panel -->
    <div
      transition:fly={{ x: 200, duration: 200 }}
      class="kanban-detail-panel"
      style="top: {dragPos.top}px; right: {dragPos.right}px; {dragging ? 'user-select: none;' : ''}"
    >
      <!-- Drag handle -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="drag-handle"
        onmousedown={handleDragStart}
      >
        <div class="drag-handle-bar"></div>
      </div>
      <div style="flex: 1; overflow-y: auto; min-height: 0;">
        {#if task}
          {#key task.id}
            <TaskDetailContent mode="edit" {task} onclose={handleClose} />
          {/key}
        {:else}
          <div style="padding: 28px; color: var(--text-tertiary); font-size: 14px;">
            Task not found
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <!-- Default: flex sibling panel -->
    <div
      transition:fly={{ x: 200, duration: 200 }}
      style="width: 440px; flex-shrink: 0; border-left: 1px solid var(--border-subtle); overflow-y: auto; height: 100%; background: var(--bg-surface);"
    >
      {#if task}
        {#key task.id}
          <TaskDetailContent mode="edit" {task} onclose={handleClose} />
        {/key}
      {:else}
        <div style="padding: 28px; color: var(--text-tertiary); font-size: 14px;">
          Task not found
        </div>
      {/if}
    </div>
  {/if}
{/if}

<style>
  .kanban-detail-panel {
    position: fixed;
    z-index: 100;
    width: 440px;
    max-height: calc(100vh - 40px);
    display: flex;
    flex-direction: column;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: 12px;
    box-shadow: var(--shadow-lg, 0 8px 32px rgba(0,0,0,0.3));
  }

  .drag-handle {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 20px;
    cursor: grab;
    border-radius: 12px 12px 0 0;
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .drag-handle:active {
    cursor: grabbing;
  }

  .drag-handle-bar {
    width: 32px;
    height: 3px;
    border-radius: 2px;
    background: var(--border-strong);
    opacity: 0.5;
    transition: opacity 150ms;
  }

  .drag-handle:hover .drag-handle-bar {
    opacity: 0.8;
  }
</style>

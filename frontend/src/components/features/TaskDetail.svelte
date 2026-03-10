<script lang="ts">
  import { untrack } from 'svelte';
  import { fly } from 'svelte/transition';
  import { tasksStore } from '$lib/stores.svelte';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';
  import TaskDetailContent from './TaskDetailContent.svelte';
  import type { Task } from '$lib/types';

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
</script>

{#if taskDetailStore.isOpen}
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

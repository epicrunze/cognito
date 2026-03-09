<script lang="ts">
  import type { Project, Task } from '$lib/types';
  import { transitionStore } from '$lib/stores/transition.svelte';
  import ThoughtBubble from './ThoughtBubble.svelte';

  let {
    project,
    tasks,
    ontaskclick,
  }: {
    project: Project;
    tasks: Task[];
    ontaskclick?: (id: number) => void;
  } = $props();

  let showCompleted = $state(false);

  const activeTasks = $derived(
    [...tasks].filter(t => !t.done).sort((a, b) => b.priority - a.priority)
  );
  const completedTasks = $derived(tasks.filter(t => t.done));
</script>

<div style="margin-bottom: 44px;">
  <!-- Header -->
  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px; padding-left: 2px; opacity: {transitionStore.chromeFaded ? 0 : 1}; transition: opacity 200ms;">
    <div style="width: 8px; height: 8px; border-radius: 50%; background: {project.hex_color || 'var(--text-tertiary)'};"></div>
    <span style="font-size: 12px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.07em;">{project.title}</span>
    <span style="font-size: 12px; color: var(--text-tertiary); opacity: 0.5;">{activeTasks.length}</span>
  </div>

  <!-- Bubble area -->
  <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; align-content: flex-start;">
    {#each activeTasks as task (task.id)}
      <ThoughtBubble {task} onclick={() => ontaskclick?.(task.id)} />
    {/each}
  </div>

  <!-- Completed section -->
  {#if completedTasks.length > 0}
    <button
      onclick={() => showCompleted = !showCompleted}
      style="font-size: 12px; color: var(--text-tertiary); background: none; border: none; cursor: pointer; margin-top: 14px; padding: 0; opacity: 0.5; font-family: var(--font-sans);"
    >
      {showCompleted ? '\u25BE' : '\u25B8'} {completedTasks.length} completed
    </button>
    {#if showCompleted}
      <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; opacity: 0.65;">
        {#each completedTasks as task (task.id)}
          <ThoughtBubble {task} onclick={() => ontaskclick?.(task.id)} />
        {/each}
      </div>
    {/if}
  {/if}
</div>

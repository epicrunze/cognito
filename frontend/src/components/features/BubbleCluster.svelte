<script lang="ts">
  import type { Project, Task } from '$lib/types';
  import { slide } from 'svelte/transition';
  import ThoughtBubble from './ThoughtBubble.svelte';
  import SeedBubble from './SeedBubble.svelte';
  import ProjectContextMenu from './ProjectContextMenu.svelte';

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
  let menuOpen = $state(false);
  let menuPos = $state({ x: 0, y: 0 });

  const activeTasks = $derived(
    [...tasks].filter(t => !t.done).sort((a, b) => b.priority - a.priority)
  );
  const completedTasks = $derived(tasks.filter(t => t.done));
</script>

<div style="margin-bottom: 44px;">
  <!-- Header -->
  <div class="cluster-header" style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px; padding-left: 2px;">
    <div style="width: 8px; height: 8px; border-radius: 50%; background: {project.hex_color || 'var(--text-tertiary)'};"></div>
    <span style="font-size: 12px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.07em;">{project.title}</span>
    <span style="font-size: 12px; color: var(--text-tertiary); opacity: 0.5;">{activeTasks.length}</span>
    <button
      class="menu-trigger"
      onclick={(e: MouseEvent) => {
        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
        menuPos = { x: rect.left, y: rect.bottom + 4 };
        menuOpen = true;
      }}
      style="width: 20px; height: 20px; border-radius: 50%; background: none; border: none; display: flex; align-items: center; justify-content: center; opacity: 0; color: var(--text-tertiary); font-size: 14px; cursor: pointer; transition: opacity 150ms; padding: 0; margin-left: auto;"
    >
      &#8942;
    </button>
  </div>

  <!-- Bubble area -->
  <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; align-content: flex-start;">
    {#each activeTasks as task (task.id)}
      <ThoughtBubble {task} onclick={() => ontaskclick?.(task.id)} />
    {/each}
    <SeedBubble projectId={project.id} projectColor={project.hex_color} />
  </div>

  <!-- Completed section -->
  {#if completedTasks.length > 0}
    <button
      class="completed-toggle"
      onclick={() => showCompleted = !showCompleted}
    >
      {showCompleted ? '\u25BE' : '\u25B8'} {completedTasks.length} completed
    </button>
    {#if showCompleted}
      <div transition:slide={{ duration: 200 }} style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; opacity: 0.65;">
        {#each completedTasks as task (task.id)}
          <ThoughtBubble {task} onclick={() => ontaskclick?.(task.id)} />
        {/each}
      </div>
    {/if}
  {/if}

  {#if menuOpen}
    <ProjectContextMenu {project} position={menuPos} onclose={() => menuOpen = false} />
  {/if}
</div>

<style>
  .cluster-header:hover .menu-trigger {
    opacity: 1;
  }

  .completed-toggle {
    font-size: 12px;
    color: var(--text-tertiary);
    background: none;
    border: none;
    cursor: pointer;
    margin-top: 14px;
    padding: 4px 8px;
    border-radius: 6px;
    opacity: 0.5;
    font-family: var(--font-sans);
    transition: opacity 150ms, background 150ms;
  }
  .completed-toggle:hover {
    opacity: 0.8;
    background: var(--bg-surface-hover);
  }
</style>

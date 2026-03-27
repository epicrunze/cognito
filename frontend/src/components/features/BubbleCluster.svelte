<script lang="ts">
  import type { Project, Task } from '$lib/types';
  import { slide } from 'svelte/transition';
  import { DURATION } from '$lib/transitions';
  import { smartSort } from '$lib/smartSort';
  import { dndzone } from 'svelte-dnd-action';
  import ThoughtBubble from './ThoughtBubble.svelte';
  import SeedBubble from './SeedBubble.svelte';
  import ProjectContextMenu from './ProjectContextMenu.svelte';
  import { responsiveStore } from '$lib/stores/responsive.svelte';

  let {
    project,
    tasks,
    ontaskclick,
    onfinalize,
  }: {
    project: Project;
    tasks: Task[];
    ontaskclick?: (id: number) => void;
    onfinalize?: (projectId: number, tasks: Task[]) => void;
  } = $props();

  let localItems = $state<Task[]>([]);
  let isDragging = $state(false);

  let showCompleted = $state(false);
  let menuOpen = $state(false);
  let menuPos = $state({ x: 0, y: 0 });

  const activeTasks = $derived(smartSort(tasks.filter(t => !t.done)));
  const completedTasks = $derived(tasks.filter(t => t.done));

  $effect(() => {
    if (!isDragging) {
      localItems = [...activeTasks];
    }
  });

  function handleConsider(e: CustomEvent<{ items: Task[] }>) {
    isDragging = true;
    localItems = e.detail.items;
  }

  function handleFinalize(e: CustomEvent<{ items: Task[] }>) {
    isDragging = false;
    localItems = e.detail.items;
    onfinalize?.(project.id, e.detail.items);
  }
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
      style="width: 20px; height: 20px; border-radius: 50%; background: none; border: none; display: flex; align-items: center; justify-content: center; opacity: 0; color: var(--text-tertiary); font-size: 14px; cursor: pointer; transition: opacity var(--transition-fast); padding: 0; margin-left: auto;"
    >
      &#8942;
    </button>
  </div>

  <!-- Bubble area -->
  {#if responsiveStore.isMobile}
    <div class="masonry-grid">
      {#each localItems as task (task.id)}
        <div class="masonry-item">
          <ThoughtBubble {task} onclick={() => ontaskclick?.(task.id)} />
        </div>
      {/each}
      <div class="masonry-item">
        <SeedBubble projectId={project.id} projectColor={project.hex_color} />
      </div>
    </div>
  {:else}
    <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start;">
      <div
        use:dndzone={{ items: localItems, type: 'cross-project-bubble', dropTargetStyle: {} }}
        onconsider={handleConsider}
        onfinalize={handleFinalize}
        style="display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; align-content: flex-start; min-height: 60px;"
      >
        {#each localItems as task (task.id)}
          <ThoughtBubble {task} onclick={() => ontaskclick?.(task.id)} />
        {/each}
      </div>
      <SeedBubble projectId={project.id} projectColor={project.hex_color} />
    </div>
  {/if}
  {#if localItems.length === 0}
    <div class="empty-hint">Your first thought goes here...</div>
  {/if}

  <!-- Completed section -->
  {#if completedTasks.length > 0}
    <button
      class="completed-toggle"
      onclick={() => showCompleted = !showCompleted}
    >
      {showCompleted ? '\u25BE' : '\u25B8'} {completedTasks.length} completed
    </button>
    {#if showCompleted}
      {#if responsiveStore.isMobile}
        <div transition:slide={{ duration: DURATION.normal }} class="masonry-grid" style="margin-top: 10px; opacity: 0.65;">
          {#each completedTasks as task (task.id)}
            <div class="masonry-item">
              <ThoughtBubble {task} onclick={() => ontaskclick?.(task.id)} />
            </div>
          {/each}
        </div>
      {:else}
        <div transition:slide={{ duration: DURATION.normal }} style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; opacity: 0.65;">
          {#each completedTasks as task (task.id)}
            <ThoughtBubble {task} onclick={() => ontaskclick?.(task.id)} />
          {/each}
        </div>
      {/if}
    {/if}
  {/if}

  {#if menuOpen}
    <ProjectContextMenu {project} position={menuPos} onclose={() => menuOpen = false} />
  {/if}
</div>

<style>
  .empty-hint {
    font-size: 13px;
    color: var(--text-tertiary);
    font-style: italic;
    opacity: 0.6;
  }

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
    transition: opacity var(--transition-fast), background var(--transition-fast);
  }
  .completed-toggle:hover {
    opacity: 0.8;
    background: var(--bg-surface-hover);
  }

  .masonry-grid {
    column-count: 2;
    column-gap: 10px;
  }

  .masonry-item {
    break-inside: avoid;
    margin-bottom: 10px;
  }
</style>

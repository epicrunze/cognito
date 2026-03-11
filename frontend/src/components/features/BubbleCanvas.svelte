<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { flip } from 'svelte/animate';
  import type { Task, Project } from '$lib/types';
  import { tasksStore, projectsStore } from '$lib/stores.svelte';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';
  import { bubbleStore } from '$lib/stores/bubble.svelte';
  import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
  import { applyClientFilters } from '$lib/filterUtils';
  import type { FetchParams } from '$lib/stores/tasks.svelte';
  import BubbleCluster from './BubbleCluster.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';

  let {
    projectId,
    filter,
  }: {
    projectId?: number;
    filter?: (t: Task) => boolean;
  } = $props();

  // Re-fetch when sort/filter/projectId changes
  $effect(() => {
    const sort = filterStore.vikunjaSort;
    const vikunjaFilter = filterStore.vikunjaFilter;

    const params: FetchParams = {};
    if (sort) {
      params.sort_by = sort.sort_by;
      params.order_by = sort.order_by;
    }
    if (vikunjaFilter) {
      params.filter = vikunjaFilter;
    }

    const fetchParams = Object.keys(params).length ? params : undefined;

    if (tasksStore.shouldSkipFetch()) return;

    if (projectId != null) {
      tasksStore.fetchByProject(projectId, fetchParams);
    } else {
      tasksStore.fetchAll(fetchParams);
    }
  });

  const filteredTasks = $derived.by(() => {
    let t = tasksStore.tasks;
    if (projectId != null) t = t.filter(task => task.project_id === projectId);
    if (filter) t = t.filter(filter);
    return applyClientFilters(t);
  });

  // Group by project (includes project object for animation-friendly rendering)
  const projectGroups = $derived.by(() => {
    const groups = new Map<number, Task[]>();
    for (const task of filteredTasks) {
      const pid = task.project_id;
      if (!groups.has(pid)) groups.set(pid, []);
      groups.get(pid)!.push(task);
    }
    // Sort projects by project list order
    const ordered: { projectId: number; project: Project; tasks: Task[] }[] = [];
    for (const p of projectsStore.projects) {
      const tasks = groups.get(p.id);
      if (tasks && tasks.length > 0) {
        ordered.push({ projectId: p.id, project: p, tasks });
      } else if (projectId != null && p.id === projectId) {
        // Show empty project in single-project view so BubbleCluster renders with empty hint + SeedBubble
        ordered.push({ projectId: p.id, project: p, tasks: [] });
      }
    }
    // Include any tasks from projects not in the list
    for (const [pid, tasks] of groups) {
      if (!ordered.some(o => o.projectId === pid)) {
        const p = projectsStore.projects.find(proj => proj.id === pid);
        if (p) ordered.push({ projectId: pid, project: p, tasks });
      }
    }
    return ordered;
  });

  function handleCanvasClick() {
    bubbleStore.collapse();
  }

  function handleTaskClick(taskId: number) {
    taskDetailStore.open(taskId);
    filterStore.markViewed(taskId);
  }

  onMount(() => {
    function handleKeydown(e: KeyboardEvent) {
      if (e.key === 'Escape' && bubbleStore.expandedTaskId != null) {
        bubbleStore.collapse();
      }
    }
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div onclick={handleCanvasClick} style="padding: 24px; min-height: 100%;">
  {#if tasksStore.loading}
    <!-- Skeleton placeholders -->
    <div style="display: flex; flex-wrap: wrap; gap: 12px;">
      {#each [1, 2, 3, 4, 5, 6] as _ (_)}
        <Skeleton width={200} height={90} radius={10} />
      {/each}
    </div>
  {:else if projectGroups.length === 0}
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 24px; gap: 12px;">
      <span style="font-size: 40px; opacity: 0.3;">&#9744;</span>
      <span style="font-size: 15px; color: var(--text-tertiary);">No tasks</span>
    </div>
  {:else}
    {#each projectGroups as group (group.projectId)}
      <div animate:flip={{ duration: 300 }} transition:fade|local={{ duration: 200 }}>
        <BubbleCluster project={group.project} tasks={group.tasks} ontaskclick={handleTaskClick} />
      </div>
    {/each}
  {/if}
</div>

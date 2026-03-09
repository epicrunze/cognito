<script lang="ts">
  import { onMount } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import type { Task } from '$lib/types';
  import { tasksStore, projectsStore } from '$lib/stores.svelte';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import { updateTask, toggleDone } from '$lib/stores/taskMutations';
  import { addToast } from '$lib/stores/toast.svelte';
  import { searchStore } from '$lib/stores/search.svelte';
  import { filterStore, type SortMode } from '$lib/stores/filter.svelte';
  import type { FetchParams } from '$lib/stores/tasks.svelte';
  import { shortcuts } from '$lib/shortcuts';
  import TaskRow from './TaskRow.svelte';
  import TaskPanel from './TaskPanel.svelte';
  import Dropdown from '$components/ui/Dropdown.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';
  import Kbd from '$components/ui/Kbd.svelte';

  let hintBarDismissed = $state(typeof localStorage !== 'undefined' && localStorage.getItem('cognito:hint-bar-dismissed') === 'true');

  function dismissHintBar() {
    hintBarDismissed = true;
    localStorage.setItem('cognito:hint-bar-dismissed', 'true');
  }

  let {
    projectId,
    filter,
  }: {
    projectId?: number;
    filter?: (t: Task) => boolean;
  } = $props();

  let showCompleted = $state(false);
  let quickAddValue = $state('');
  let quickAddRef = $state<HTMLInputElement>();
  let editingTaskId = $state<number | null>(null);
  let selectedIndex = $state(-1);
  let taskRowEls = new SvelteMap<number, HTMLDivElement>();
  const editingTask = $derived(editingTaskId != null ? tasksStore.tasks.find(t => t.id === editingTaskId) ?? null : null);

  // Sort options
  const sortOptions = [
    { value: 'smart', label: 'Smart' },
    { value: 'priority', label: 'Priority' },
    { value: 'due_date', label: 'Due Date' },
    { value: 'created', label: 'Created' },
    { value: 'title', label: 'Alphabetical' },
  ];

  // Sort: overdue first, then priority desc, then due date asc
  function smartSort(tasks: Task[]): Task[] {
    const now = new Date();
    return [...tasks].sort((a, b) => {
      const aOverdue = a.due_date && new Date(a.due_date) < now ? 1 : 0;
      const bOverdue = b.due_date && new Date(b.due_date) < now ? 1 : 0;
      if (bOverdue !== aOverdue) return bOverdue - aOverdue;
      if (b.priority !== a.priority) return b.priority - a.priority;
      if (a.due_date && b.due_date) return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
      if (a.due_date) return -1;
      if (b.due_date) return 1;
      return 0;
    });
  }

  function sortTasks(tasks: Task[], mode: SortMode): Task[] {
    if (mode === 'smart') return smartSort(tasks);
    return [...tasks].sort((a, b) => {
      switch (mode) {
        case 'priority':
          return b.priority - a.priority;
        case 'due_date': {
          if (!a.due_date && !b.due_date) return 0;
          if (!a.due_date) return 1;
          if (!b.due_date) return -1;
          return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
        }
        case 'created':
          return new Date(b.created).getTime() - new Date(a.created).getTime();
        case 'title':
          return a.title.localeCompare(b.title);
        default:
          return 0;
      }
    });
  }

  // Re-fetch when sort/filter/projectId changes (server-side optimization)
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

    if (projectId != null) {
      tasksStore.fetchByProject(projectId, fetchParams);
      kanbanStore.fetchBucketMap(projectId);
    } else {
      tasksStore.fetchAll(fetchParams);
      // Fetch bucket maps for all projects so badges show in All Tasks view
      for (const p of projectsStore.projects) {
        kanbanStore.fetchBucketMap(p.id);
      }
    }
  });

  const allTasks = $derived.by(() => {
    let t = tasksStore.tasks;
    if (projectId != null) t = t.filter(task => task.project_id === projectId);
    if (filter) t = t.filter(filter);
    if (searchStore.query) {
      const q = searchStore.query.toLowerCase();
      t = t.filter(task => task.title.toLowerCase().includes(q) || task.description?.toLowerCase().includes(q));
    }
    // Client-side filters (labels can't be done server-side cleanly)
    if (filterStore.priorities.length > 0) {
      t = t.filter(task => filterStore.priorities.includes(task.priority));
    }
    if (filterStore.labelIds.length > 0) {
      t = t.filter(task => task.labels.some(l => filterStore.labelIds.includes(l.id)));
    }
    return t;
  });

  const activeTasks = $derived.by(() => {
    const tasks = allTasks.filter(t => !t.done);
    if (filterStore.status === 'completed') return [];
    return sortTasks(tasks, filterStore.sortMode);
  });

  const completedTasks = $derived.by(() => {
    if (filterStore.status === 'active') return [];
    return allTasks.filter(t => t.done);
  });

  const selectedTask = $derived(selectedIndex >= 0 && selectedIndex < activeTasks.length ? activeTasks[selectedIndex] : null);

  // Scroll selected row into view
  $effect(() => {
    if (selectedTask) {
      const el = taskRowEls.get(selectedTask.id);
      el?.scrollIntoView({ block: 'nearest' });
    }
  });

  // Clear selection when task list changes significantly
  $effect(() => {
    // Access activeTasks.length to track changes
    if (activeTasks.length === 0) selectedIndex = -1;
    else if (selectedIndex >= activeTasks.length) selectedIndex = activeTasks.length - 1;
  });

  onMount(() => {
    const handler = () => quickAddRef?.focus();
    window.addEventListener('cognito:focusQuickAdd', handler);
    return () => window.removeEventListener('cognito:focusQuickAdd', handler);
  });

  // Keyboard navigation
  onMount(() => {
    shortcuts.register('j', () => {
      if (activeTasks.length === 0) return;
      selectedIndex = Math.min(selectedIndex + 1, activeTasks.length - 1);
    });
    shortcuts.register('k', () => {
      if (activeTasks.length === 0) return;
      selectedIndex = Math.max(selectedIndex - 1, 0);
    });
    shortcuts.register('x', () => {
      if (selectedTask) toggleDone(selectedTask.id);
    });
    shortcuts.register('e', () => {
      if (selectedTask) openTask(selectedTask.id);
    });
    shortcuts.register('Enter', () => {
      if (selectedTask) openTask(selectedTask.id);
    });

    shortcuts.register('Escape', () => {
      if (selectedIndex >= 0) {
        selectedIndex = -1;
      } else if (document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
      }
    });

    // Priority shortcuts 1-5
    for (let i = 1; i <= 5; i++) {
      shortcuts.register(String(i), () => {
        if (selectedTask) updateTask(selectedTask.id, { priority: i as Task['priority'] });
      });
    }

    return () => {
      shortcuts.unregister('j');
      shortcuts.unregister('k');
      shortcuts.unregister('x');
      shortcuts.unregister('e');
      shortcuts.unregister('Enter');
      for (let i = 1; i <= 5; i++) shortcuts.unregister(String(i));
      // Restore default Escape
      shortcuts.register('Escape', () => {
        if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
      });
    };
  });

  function trackRow(node: HTMLDivElement, taskId: number) {
    taskRowEls.set(taskId, node);
    return {
      destroy() {
        taskRowEls.delete(taskId);
      },
    };
  }

  function openTask(id: number) {
    editingTaskId = id;
    filterStore.markViewed(id);
  }

  function handleSortChange(value: string) {
    filterStore.setSortMode(value as SortMode);
  }

  async function handleQuickAdd(e: KeyboardEvent) {
    if (e.key !== 'Enter' || !quickAddValue.trim()) return;
    const title = quickAddValue.trim();
    quickAddValue = '';
    const pid = projectId ?? projectsStore.projects[0]?.id;
    if (!pid) {
      addToast('No projects loaded — try refreshing', 'error');
      return;
    }
    await tasksStore.create({ project_id: pid, title });
  }
</script>

<!-- Quick add + sort -->
<div style="padding: 11px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 10px; flex-shrink: 0;">
  <span style="color: var(--text-tertiary); opacity: 0.5;">+</span>
  <input
    bind:this={quickAddRef}
    bind:value={quickAddValue}
    onkeydown={handleQuickAdd}
    placeholder="Add task..."
    style="flex: 1; background: transparent; border: none; outline: none; font-size: 15px; color: var(--text-primary); font-family: var(--font-sans);"
  />
  <Dropdown
    options={sortOptions}
    value={filterStore.sortMode}
    onchange={handleSortChange}
    placeholder="Sort..."
    width={140}
  />
</div>

{#if tasksStore.loading}
  <!-- Skeleton -->
  <div style="padding: 0 24px;">
    {#each [1, 2, 3, 4, 5] as _ (_)}
      <div style="display: grid; grid-template-columns: 20px 42px 1fr auto; gap: 14px; padding: 14px 0; border-bottom: 1px solid var(--border-subtle); align-items: center;">
        <Skeleton width={20} height={20} radius={10} />
        <Skeleton width={42} height={8} />
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <Skeleton width="60%" height={14} />
          <Skeleton width="30%" height={10} />
        </div>
        <Skeleton width={60} height={12} />
      </div>
    {/each}
  </div>
{:else if activeTasks.length === 0 && completedTasks.length === 0}
  <!-- Empty state -->
  <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 24px; gap: 12px;">
    <span style="font-size: 40px; opacity: 0.3;">&#9744;</span>
    <span style="font-size: 15px; color: var(--text-tertiary);">No tasks yet</span>
    <span style="font-size: 13px; color: var(--text-tertiary);">Press <kbd style="padding: 2px 6px; background: var(--bg-elevated); border: 1px solid var(--border-default); border-radius: 4px; font-size: 12px;">N</kbd> or use the field above to add one</span>
  </div>
{:else}
  <!-- Active tasks -->
  {#each activeTasks as task, i (task.id)}
    <div use:trackRow={task.id}>
      <TaskRow
        {task}
        selected={selectedIndex === i}
        viewed={filterStore.viewedTaskIds.has(task.id)}
        ontoggle={() => toggleDone(task.id)}
        onclick={() => { selectedIndex = i; openTask(task.id); }}
      />
    </div>
  {/each}

  <!-- Completed divider -->
  {#if completedTasks.length > 0}
    <button
      onclick={() => showCompleted = !showCompleted}
      style="display: flex; align-items: center; gap: 10px; padding: 16px 24px; width: 100%; color: var(--text-tertiary); font-size: 13px; background: none; border: none; cursor: pointer; font-family: var(--font-sans);"
    >
      <span style="flex: 1; height: 1px; background: var(--border-default);"></span>
      <span>Completed ({completedTasks.length})</span>
      <span style="font-size: 10px; transition: transform 150ms; transform: {showCompleted ? 'rotate(180deg)' : 'rotate(0deg)'};">&#9660;</span>
      <span style="flex: 1; height: 1px; background: var(--border-default);"></span>
    </button>
    {#if showCompleted}
      <div style="opacity: 0.65;">
        {#each completedTasks as task (task.id)}
          <TaskRow
            {task}
            ontoggle={() => toggleDone(task.id)}
            onclick={() => openTask(task.id)}
          />
        {/each}
      </div>
    {/if}
  {/if}
{/if}

{#if !hintBarDismissed && !tasksStore.loading && (activeTasks.length > 0 || completedTasks.length > 0)}
  <div style="display: flex; align-items: center; justify-content: center; gap: 16px; padding: 6px 24px; border-top: 1px solid var(--border-subtle); background: var(--bg-surface); font-size: 12px; color: var(--text-tertiary); flex-shrink: 0;">
    <span><Kbd>J</Kbd><Kbd>K</Kbd> Navigate</span>
    <span><Kbd>X</Kbd> Done</span>
    <span><Kbd>E</Kbd> Edit</span>
    <span><Kbd>N</Kbd> New</span>
    <span><Kbd>?</Kbd> Help</span>
    <button
      onclick={dismissHintBar}
      style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 14px; padding: 0 2px; line-height: 1; margin-left: 4px; opacity: 0.6;"
      aria-label="Dismiss hint bar"
    >&times;</button>
  </div>
{/if}

<TaskPanel mode="edit" open={editingTaskId !== null} task={editingTask ?? undefined} onclose={() => editingTaskId = null} />

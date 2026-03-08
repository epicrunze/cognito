<script lang="ts">
  import { onMount } from 'svelte';
  import type { Task } from '$lib/types';
  import { tasksStore, projectsStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import { searchStore } from '$lib/stores/search.svelte';
  import TaskRow from './TaskRow.svelte';
  import TaskPanel from './TaskPanel.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';

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
  const editingTask = $derived(editingTaskId != null ? tasksStore.tasks.find(t => t.id === editingTaskId) ?? null : null);

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

  const allTasks = $derived.by(() => {
    let t = tasksStore.tasks;
    if (projectId != null) t = t.filter(task => task.project_id === projectId);
    if (filter) t = t.filter(filter);
    if (searchStore.query) {
      const q = searchStore.query.toLowerCase();
      t = t.filter(task => task.title.toLowerCase().includes(q) || task.description?.toLowerCase().includes(q));
    }
    return t;
  });

  const activeTasks = $derived(smartSort(allTasks.filter(t => !t.done)));
  const completedTasks = $derived(allTasks.filter(t => t.done));

  onMount(() => {
    const handler = () => quickAddRef?.focus();
    window.addEventListener('cognito:focusQuickAdd', handler);
    return () => window.removeEventListener('cognito:focusQuickAdd', handler);
  });

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

<!-- Quick add -->
<div style="padding: 11px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 10px; flex-shrink: 0;">
  <span style="color: var(--text-tertiary); opacity: 0.5;">+</span>
  <input
    bind:this={quickAddRef}
    bind:value={quickAddValue}
    onkeydown={handleQuickAdd}
    placeholder="Add task..."
    style="flex: 1; background: transparent; border: none; outline: none; font-size: 15px; color: var(--text-primary); font-family: var(--font-sans);"
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
  {#each activeTasks as task (task.id)}
    <TaskRow
      {task}
      ontoggle={() => tasksStore.toggleDone(task.id)}
      onclick={() => editingTaskId = task.id}
    />
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
            ontoggle={() => tasksStore.toggleDone(task.id)}
            onclick={() => editingTaskId = task.id}
          />
        {/each}
      </div>
    {/if}
  {/if}
{/if}

<TaskPanel mode="edit" open={editingTaskId !== null} task={editingTask ?? undefined} onclose={() => editingTaskId = null} />

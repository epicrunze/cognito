<script lang="ts">
  import { page } from '$app/stores';
  import { tick } from 'svelte';
  import type { Task } from '$lib/types';
  import { tasksStore } from '$lib/stores.svelte';
  import { bubbleStore } from '$lib/stores/bubble.svelte';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import BubbleCanvas from './BubbleCanvas.svelte';
  import KanbanBoard from './KanbanBoard.svelte';
  import TaskList from './TaskList.svelte';

  const pathname = $derived($page.url.pathname);
  const projectMatch = $derived(pathname.match(/^\/project\/(\d+)/));
  const projectId = $derived(projectMatch ? Number(projectMatch[1]) : null);
  const filterMode = $derived(
    pathname === '/upcoming' ? 'upcoming' :
    pathname === '/overdue' ? 'overdue' : null
  );

  let viewMode = $state<'bubbles' | 'kanban' | 'list'>('bubbles');
  let prevPathname = $state('');

  // Buffered values — only update inside startViewTransition callback
  // so the browser captures the old DOM before we swap to new content
  let displayProjectId = $state<number | null>(null);
  let displayFilterMode = $state<string | null>(null);

  // Animate view change on route navigation
  $effect(() => {
    if (pathname === prevPathname) return;
    const oldPath = prevPathname;
    prevPathname = pathname;

    const newMode: 'bubbles' | 'kanban' | 'list' = projectId != null ? 'kanban' : 'bubbles';

    if (!oldPath) {
      viewMode = newMode;
      displayProjectId = projectId;
      displayFilterMode = filterMode;
      return;
    }

    void updateView(newMode, projectId, filterMode);
  });

  async function updateView(
    newMode: 'bubbles' | 'kanban' | 'list',
    newProjectId: number | null = projectId,
    newFilterMode: string | null = filterMode,
  ) {
    // Prefetch while old view visible
    try {
      if (newMode === 'kanban' && newProjectId != null) {
        await kanbanStore.prefetch(newProjectId);
        kanbanStore.skipNextFetch();
      } else if (newMode === 'bubbles') {
        await tasksStore.prefetch(newProjectId ?? undefined);
        tasksStore.skipNextFetch();
      }
    } catch { /* proceed anyway */ }

    bubbleStore.collapse();

    if (!document.startViewTransition) {
      viewMode = newMode;
      displayProjectId = newProjectId;
      displayFilterMode = newFilterMode;
      return;
    }

    document.startViewTransition(async () => {
      viewMode = newMode;
      displayProjectId = newProjectId;
      displayFilterMode = newFilterMode;
      await tick();
    });
  }

  // Filter functions for upcoming/overdue
  const sevenDays = 7 * 24 * 60 * 60 * 1000;

  function upcomingFilter(t: Task): boolean {
    if (!t.due_date || t.done) return false;
    const due = new Date(t.due_date).getTime();
    const now = Date.now();
    return due >= now && due <= now + sevenDays;
  }

  function overdueFilter(t: Task): boolean {
    if (!t.due_date || t.done) return false;
    return new Date(t.due_date) < new Date();
  }

  const activeFilter = $derived(
    displayFilterMode === 'upcoming' ? upcomingFilter :
    displayFilterMode === 'overdue' ? overdueFilter : undefined
  );

  // Whether to show the view toggle (only for project pages)
  const showViewToggle = $derived(displayProjectId != null);

  const viewOptions: { value: 'bubbles' | 'kanban' | 'list'; label: string }[] = [
    { value: 'bubbles', label: 'Bubbles' },
    { value: 'kanban', label: 'Kanban' },
    { value: 'list', label: 'List' },
  ];

  async function switchView(newMode: 'bubbles' | 'kanban' | 'list') {
    if (newMode === viewMode) return;
    await updateView(newMode);
  }
</script>

{#if showViewToggle}
  <div style="display: flex; align-items: center; gap: 4px; padding: 10px 24px 0; flex-shrink: 0;">
    {#each viewOptions as opt (opt.value)}
      <button
        onclick={() => switchView(opt.value)}
        style="height: 28px; padding: 0 12px; font-size: 12.5px; font-weight: 500; border-radius: 6px; border: 1px solid {viewMode === opt.value ? 'var(--accent)' : 'var(--border-default)'}; background: {viewMode === opt.value ? 'var(--accent-subtle)' : 'transparent'}; color: {viewMode === opt.value ? 'var(--accent)' : 'var(--text-secondary)'}; cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
      >{opt.label}</button>
    {/each}
  </div>
{/if}

{#if viewMode === 'kanban'}
  <KanbanBoard projectId={displayProjectId!} />
{:else if viewMode === 'list'}
  <TaskList projectId={displayProjectId ?? undefined} filter={activeFilter} />
{:else}
  <BubbleCanvas projectId={displayProjectId ?? undefined} filter={activeFilter} />
{/if}

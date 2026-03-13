<script lang="ts">
  import { page } from '$app/stores';
  import { tick } from 'svelte';
  import type { Task } from '$lib/types';
  import { tasksStore } from '$lib/stores.svelte';
  import { bubbleStore } from '$lib/stores/bubble.svelte';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import { sidebarRectsStore } from '$lib/stores/sidebarRects.svelte';
  import { viewModeStore } from '$lib/stores/viewMode.svelte';
  import { snapshotCards, diffSnapshots, animateFlights } from '$lib/viewTransitionAnimator';
  import BubbleCanvas from './BubbleCanvas.svelte';
  import GanttChart from './GanttChart.svelte';
  import KanbanBoard from './KanbanBoard.svelte';
  import TaskList from './TaskList.svelte';

  const pathname = $derived($page.url.pathname);
  const projectMatch = $derived(pathname.match(/^\/project\/(\d+)/));
  const projectId = $derived(projectMatch ? Number(projectMatch[1]) : null);
  const filterMode = $derived(
    pathname === '/upcoming' ? 'upcoming' :
    pathname === '/overdue' ? 'overdue' : null
  );

  let viewMode = $state<'bubbles' | 'kanban' | 'list' | 'gantt'>('bubbles');
  $effect(() => { viewModeStore.set(viewMode); });
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

    const newMode: 'bubbles' | 'kanban' | 'list' | 'gantt' = projectId != null ? 'kanban' : 'bubbles';

    if (!oldPath) {
      viewMode = newMode;
      displayProjectId = projectId;
      displayFilterMode = filterMode;
      return;
    }

    void updateView(newMode, projectId, filterMode, oldPath);
  });

  /** Get a fallback origin point (brand-mark dot or viewport center) */
  function getFallbackOrigin(): { x: number; y: number } {
    const brandMark = document.querySelector('.brand-mark');
    if (brandMark) {
      const r = brandMark.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    }
    return { x: 32, y: 40 };
  }

  async function prefetchData(newMode: string, newProjectId: number | null) {
    try {
      if (newMode === 'kanban' && newProjectId != null) {
        await kanbanStore.prefetch(newProjectId);
        kanbanStore.skipNextFetch();
      } else if (newMode === 'bubbles' || newMode === 'gantt') {
        await tasksStore.prefetch(newProjectId ?? undefined);
        tasksStore.skipNextFetch();
      }
    } catch { /* proceed anyway */ }
  }

  async function updateView(
    newMode: 'bubbles' | 'kanban' | 'list' | 'gantt',
    newProjectId: number | null = projectId,
    newFilterMode: string | null = filterMode,
    oldPath: string = '',
  ) {
    bubbleStore.collapseImmediate();

    // Determine sidebar origins for flight animations
    const oldOrigin = sidebarRectsStore.getOrigin(oldPath) ?? getFallbackOrigin();
    const newOrigin = sidebarRectsStore.getOrigin(pathname) ?? getFallbackOrigin();

    // Snapshot BEFORE anything changes
    const oldSnapshot = snapshotCards();

    if (!document.startViewTransition) {
      await prefetchData(newMode, newProjectId);
      viewMode = newMode;
      displayProjectId = newProjectId;
      displayFilterMode = newFilterMode;
      return;
    }

    // Start transition — browser captures old DOM here
    const transition = document.startViewTransition(async () => {
      // Prefetch INSIDE callback (old DOM already captured by browser)
      await prefetchData(newMode, newProjectId);
      viewMode = newMode;
      displayProjectId = newProjectId;
      displayFilterMode = newFilterMode;
      await tick();
    });

    // After DOM update, snapshot new cards and animate flights
    transition.updateCallbackDone.then(() => {
      const newSnapshot = snapshotCards();
      const { entering, leaving } = diffSnapshots(oldSnapshot, newSnapshot);

      if (entering.length > 0 || leaving.length > 0) {
        animateFlights(transition, entering, leaving, {
          enterFrom: newOrigin,
          leaveTo: oldOrigin,
        });
      }
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

  // Whether to show the view toggle (project pages always, home page shows gantt option too)
  const showViewToggle = $derived(true);

  type ViewOption = 'bubbles' | 'kanban' | 'list' | 'gantt';
  const viewOptions = $derived.by(() => {
    const opts: { value: ViewOption; label: string }[] = [
      { value: 'bubbles', label: 'Bubbles' },
      { value: 'list', label: 'List' },
      { value: 'gantt', label: 'Gantt' },
    ];
    if (displayProjectId != null) {
      opts.splice(1, 0, { value: 'kanban', label: 'Kanban' });
    }
    return opts;
  });

  async function switchView(newMode: ViewOption) {
    if (newMode === viewMode) return;
    await updateView(newMode);
  }
</script>

<div style="display: flex; align-items: center; gap: 4px; padding: 10px 24px 0; flex-shrink: 0;">
  {#if showViewToggle}
    {#each viewOptions as opt (opt.value)}
      <button
        onclick={() => switchView(opt.value)}
        style="height: 28px; padding: 0 12px; font-size: 12.5px; font-weight: 500; border-radius: 6px; border: 1px solid {viewMode === opt.value ? 'var(--accent)' : 'var(--border-default)'}; background: {viewMode === opt.value ? 'var(--accent-subtle)' : 'transparent'}; color: {viewMode === opt.value ? 'var(--accent)' : 'var(--text-secondary)'}; cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
      >{opt.label}</button>
    {/each}
  {/if}
  <button
    onclick={() => viewModeStore.toggleFocus()}
    style="height: 28px; padding: 0 12px; font-size: 12.5px; font-weight: 500; border-radius: 6px; border: 1px solid {viewModeStore.isFocus ? 'var(--accent)' : 'var(--border-default)'}; background: {viewModeStore.isFocus ? 'var(--accent-subtle)' : 'transparent'}; color: {viewModeStore.isFocus ? 'var(--accent)' : 'var(--text-secondary)'}; cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
  >Focus</button>
</div>

{#if viewMode === 'kanban'}
  <KanbanBoard projectId={displayProjectId!} />
{:else if viewMode === 'list'}
  <TaskList projectId={displayProjectId ?? undefined} filter={activeFilter} />
{:else if viewMode === 'gantt'}
  <GanttChart projectId={displayProjectId ?? undefined} />
{:else}
  <BubbleCanvas projectId={displayProjectId ?? undefined} filter={activeFilter} />
{/if}

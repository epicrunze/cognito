<script lang="ts">
  import { page } from '$app/stores';
  import { tick } from 'svelte';
  import type { Task } from '$lib/types';
  import { tasksStore } from '$lib/stores.svelte';
  import { bubbleStore } from '$lib/stores/bubble.svelte';
  import { flipStore } from '$lib/stores/flip.svelte';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import { transitionStore } from '$lib/stores/transition.svelte';
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
  let isTransitioning = $state(false);

  // Buffered values — only update at controlled moments so the old view
  // stays rendered with old data until FLIP captures positions
  let displayProjectId = $state<number | null>(null);
  let displayFilterMode = $state<string | null>(null);

  // Animate view change on route navigation
  $effect(() => {
    if (pathname === prevPathname) return;
    const oldPath = prevPathname;
    prevPathname = pathname;

    const newMode: 'bubbles' | 'kanban' | 'list' = projectId != null ? 'kanban' : 'bubbles';

    if (!oldPath) {
      // Initial mount — sync immediately, no animation
      viewMode = newMode;
      displayProjectId = projectId;
      displayFilterMode = filterMode;
      return;
    }

    if (newMode === viewMode) {
      // Same view mode — check if context changed (different project or filter)
      const contextChanged = projectId !== displayProjectId || filterMode !== displayFilterMode;
      if (!contextChanged) return;
      void dropTransition();
      return;
    }

    // Different view mode — run FLIP transition
    void animateTransition(newMode);
  });

  async function dropTransition() {
    if (isTransitioning) return;
    isTransitioning = true;
    try {
      // 1. Collapse any expanded bubble
      bubbleStore.collapse();
      await tick();

      // 2. Animate old cards dropping DOWN + fading out
      const oldElements = [...flipStore.getAllElements()];
      const dropOutAnimations = oldElements.map(([, el], i) =>
        el.animate(
          [
            { transform: 'translateY(0)', opacity: 1 },
            { transform: 'translateY(40px)', opacity: 0 },
          ],
          { duration: 250, delay: i * 15, easing: 'cubic-bezier(0.4, 0, 1, 1)', fill: 'forwards' }
        )
      );

      // 3. Fade out chrome in parallel
      transitionStore.fadeOut();

      // Wait for drop-out to finish
      await Promise.all(dropOutAnimations.map(a => a.finished));

      // 4. Prefetch new data
      if (viewMode === 'kanban' && projectId != null) {
        await kanbanStore.prefetch(projectId);
        kanbanStore.skipNextFetch();
      } else if (viewMode === 'bubbles') {
        await tasksStore.prefetch(projectId ?? undefined);
        tasksStore.skipNextFetch();
      }

      // 5. Clear old registrations, swap display values
      flipStore.clearAll();
      displayProjectId = projectId;
      displayFilterMode = filterMode;
      await tick();

      // 6. Wait for new cards to register
      await flipStore.waitForCards(1000);
      await new Promise(r => requestAnimationFrame(r));

      // 7. Animate new cards dropping IN from above
      const newElements = [...flipStore.getAllElements()];
      newElements.map(([, el], i) =>
        el.animate(
          [
            { transform: 'translateY(-40px)', opacity: 0 },
            { transform: 'translateY(0)', opacity: 1 },
          ],
          { duration: 300, delay: i * 15, easing: 'cubic-bezier(0, 0, 0.2, 1)', fill: 'backwards' }
        )
      );

      // 8. Fade in chrome after cards start dropping in
      await new Promise(r => setTimeout(r, 150));
    } finally {
      transitionStore.fadeIn();
      isTransitioning = false;
    }
  }

  async function animateTransition(newMode: 'bubbles' | 'kanban' | 'list') {
    if (isTransitioning) return;
    isTransitioning = true;

    try {
      const isFlippable = newMode !== 'list' && viewMode !== 'list';
      let oldPositions: Map<number | string, DOMRect> | null = null;

      if (isFlippable) {
        // 1. Collapse any expanded bubble
        bubbleStore.collapse();
        await tick();

        // 2. Fade out chrome (sidebar, top bar, headers)
        transitionStore.fadeOut();
        await new Promise(r => setTimeout(r, 200));

        // 3. Capture positions of all currently-visible cards
        oldPositions = flipStore.capturePositions();

        // 4. Pre-fetch target data (old cards stay visible)
        try {
          if (newMode === 'kanban' && projectId != null) {
            await kanbanStore.prefetch(projectId);
            kanbanStore.skipNextFetch();
          } else if (newMode === 'bubbles') {
            await tasksStore.prefetch(projectId ?? undefined);
            tasksStore.skipNextFetch();
          }
        } catch {
          // Prefetch failed — fall back to normal view switch (no FLIP)
          displayProjectId = projectId;
          displayFilterMode = filterMode;
          viewMode = newMode;
          return;
        }

        // 5. Clear old registrations
        flipStore.clearAll();
      }

      // 6. Now safe to update — old positions are captured
      displayProjectId = projectId;
      displayFilterMode = filterMode;
      viewMode = newMode;
      await tick();

      if (isFlippable && oldPositions && oldPositions.size > 0) {
        // 7. Wait for new cards to register
        await flipStore.waitForCards(1000);
        await new Promise(r => requestAnimationFrame(r));

        // 8. Animate cards from old → new positions
        flipStore.play(oldPositions);

        // 9. Fade in new chrome (after cards settle)
        await new Promise(r => setTimeout(r, 300));
      }
    } finally {
      transitionStore.fadeIn();
      isTransitioning = false;
    }
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

  const displayActiveFilter = $derived(
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
    await animateTransition(newMode);
  }
</script>

{#if showViewToggle}
  <div style="display: flex; align-items: center; gap: 4px; padding: 10px 24px 0; flex-shrink: 0; opacity: {transitionStore.chromeFaded ? 0 : 1}; transition: opacity 200ms;">
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
  <TaskList projectId={displayProjectId ?? undefined} filter={displayActiveFilter} />
{:else}
  <BubbleCanvas projectId={displayProjectId ?? undefined} filter={displayActiveFilter} />
{/if}

<script lang="ts">
  import '../app.css';
  import type { Snippet } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import { authStore, tasksStore, projectsStore, labelsStore, bubbleStore, toggleDone } from '$lib/stores.svelte';
  import { shortcuts } from '$lib/shortcuts';
  import { extractIcon } from '$lib/icons';
  import Sidebar from '$components/features/Sidebar.svelte';
  import ThinkingMargin from '$components/features/ThinkingMargin.svelte';
  import ProjectContextMenu from '$components/features/ProjectContextMenu.svelte';
  import FilterBar from '$components/features/FilterBar.svelte';
  import ShortcutsModal from '$components/features/ShortcutsModal.svelte';
  import Input from '$components/ui/Input.svelte';
  import Button from '$components/ui/Button.svelte';
  import ToastContainer from '$components/ui/ToastContainer.svelte';
  import ConfirmDialog from '$components/ui/ConfirmDialog.svelte';
  import { searchStore } from '$lib/stores/search.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';
  import { revisionsStore } from '$lib/stores/revisions.svelte';
  import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
  import { viewModeStore } from '$lib/stores/viewMode.svelte';
  import { responsiveStore } from '$lib/stores/responsive.svelte';
  import ViewOrchestrator from '$components/features/ViewOrchestrator.svelte';
  import TaskDetail from '$components/features/TaskDetail.svelte';
  import BottomSheet from '$components/ui/BottomSheet.svelte';
  import MobileQuickAdd from '$components/features/MobileQuickAdd.svelte';

  let { children }: { children: Snippet } = $props();

  let searchRef = $state<HTMLInputElement | undefined>(undefined);
  let searchValue = $state('');
  let thinkingOpen = $state(false);
  let filterOpen = $state(false);
  let shortcutsOpen = $state(false);
  let mobileTaskFullscreen = $state(false);
  let quickAddOpen = $state(false);

  // Filter counts for mobile chips
  const upcomingCount = $derived(tasksStore.tasks.filter(t => !t.done && t.due_date && new Date(t.due_date) > new Date() && new Date(t.due_date).getTime() <= Date.now() + 7 * 24 * 60 * 60 * 1000).length);
  const overdueCount = $derived(tasksStore.tasks.filter(t => !t.done && t.due_date && new Date(t.due_date) < new Date()).length);

  const isLoginPage = $derived($page.url.pathname === '/login');
  const isTaskViewRoute = $derived.by(() => {
    const path = $page.url.pathname;
    return path === '/' || path === '/upcoming' || path === '/overdue' || path.startsWith('/project/');
  });

  // Page title mapping
  const pageTitles: Record<string, string> = {
    '/': 'All Tasks',
    '/upcoming': 'Upcoming',
    '/overdue': 'Overdue',
    '/settings': 'Settings',
  };
  const pageTitle = $derived.by(() => {
    const path = $page.url.pathname;
    if (path.startsWith('/project/')) {
      const project = projectsStore.projects.find(p => p.id === Number(path.split('/')[2]));
      return project?.title ?? 'Project';
    }
    return pageTitles[path] ?? 'Cognito';
  });

  const currentProject = $derived.by(() => {
    const path = $page.url.pathname;
    if (path.startsWith('/project/')) {
      return projectsStore.projects.find(p => p.id === Number(path.split('/')[2])) ?? null;
    }
    return null;
  });

  let projectMenuOpen = $state(false);
  let projectMenuPos = $state({ x: 0, y: 0 });

  onMount(async () => {
    await authStore.check();
    if (!authStore.authenticated && $page.url.pathname !== '/login') {
      goto('/login');
      return;
    }
    if (authStore.authenticated) {
      // tasksStore.fetchAll() is handled reactively by TaskList's $effect
      projectsStore.fetchAll();
      labelsStore.fetchAll();
      labelsStore.fetchStats();
      revisionsStore.fetchRecent();
    }
  });

  // Mutual exclusion: ThinkingMargin ↔ TaskDetail (imperative, no $effect)
  function openThinking() {
    taskDetailStore.close();
    thinkingOpen = !thinkingOpen;
  }

  // Listen for open-thinking-margin event (from settings resume)
  onMount(() => {
    function handleOpenThinking() {
      taskDetailStore.close();
      thinkingOpen = true;
    }
    window.addEventListener('open-thinking-margin', handleOpenThinking);
    return () => window.removeEventListener('open-thinking-margin', handleOpenThinking);
  });

  // Keyboard shortcuts
  onMount(() => {
    shortcuts.register('/', () => searchRef?.focus());
    shortcuts.register('e', () => openThinking());
    shortcuts.register('f', () => viewModeStore.toggleFocus());
    shortcuts.register('?', () => shortcutsOpen = !shortcutsOpen);
    shortcuts.register('Escape', () => {
      if (taskDetailStore.isOpen) {
        taskDetailStore.close();
        return;
      }
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    });
    shortcuts.register('j', () => {
      if (taskDetailStore.isOpen) taskDetailStore.navigateNext();
    });
    shortcuts.register('k', () => {
      if (taskDetailStore.isOpen) taskDetailStore.navigatePrev();
    });
    function handleUndoRedo(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        handleUndo();
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        handleRedo();
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        handleRedo();
      }
    }
    window.addEventListener('keydown', shortcuts.handleKeydown);
    window.addEventListener('keydown', handleUndoRedo);
    return () => {
      window.removeEventListener('keydown', shortcuts.handleKeydown);
      window.removeEventListener('keydown', handleUndoRedo);
    };
  });

  // Redirect to home if viewing a project that was archived/deleted
  $effect(() => {
    const path = $page.url.pathname;
    if (path.startsWith('/project/') && !projectsStore.loading && projectsStore.projects.length > 0 && !currentProject) {
      goto('/');
    }
  });

  // Collapse expanded bubble on route change (skip task-view routes — orchestrator handles those)
  $effect(() => {
    const path = $page.url.pathname;
    if (!isTaskViewRoute) {
      bubbleStore.collapseImmediate();
      taskDetailStore.close();
      filterOpen = false;
    }
  });

  // Close mobile sidebar on route change
  $effect(() => {
    $page.url.pathname;
    responsiveStore.closeSidebar();
    mobileTaskFullscreen = false;
  });

  function handleSearchInput() {
    searchStore.set(searchValue);
  }

  function handleUndo() {
    revisionsStore.undo(() => tasksStore.fetchAll());
  }

  function handleRedo() {
    revisionsStore.redo(() => tasksStore.fetchAll());
  }
</script>

{#if isLoginPage}
  {@render children()}
{:else if authStore.loading}
  <div style="display: flex; align-items: center; justify-content: center; min-height: 100vh;">
    <span style="color: var(--text-tertiary); font-size: 15px;">Loading...</span>
  </div>
{:else if authStore.authenticated}
  <div style="display: flex; height: 100vh;">
    {#if !responsiveStore.isMobile}
      <div style="flex-shrink: 0;">
        <Sidebar />
      </div>
    {/if}
    <div style="flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0;">
      <!-- Top bar -->
      <div style="display: flex; align-items: center; padding: 10px {responsiveStore.isMobile ? '16px' : '24px'}; border-bottom: 1px solid var(--border-subtle); gap: 10px; flex-shrink: 0;">
        {#if responsiveStore.isMobile}
          <button
            class="hamburger-btn"
            aria-label="Open menu"
            onclick={() => responsiveStore.toggleSidebar()}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M3 12h18"/><path d="M3 6h18"/><path d="M3 18h18"/>
            </svg>
          </button>
        {/if}
        {#if currentProject}
          <div class="project-title-group">
            <div
              style="width: 8px; height: 8px; border-radius: 50%; background: {currentProject.hex_color || 'var(--text-tertiary)'}; flex-shrink: 0;"
            ></div>
            <span
              style="font-size: 20px; font-weight: 600; letter-spacing: -0.02em; flex-shrink: 0;"
              oncontextmenu={(e: MouseEvent) => {
                e.preventDefault();
                projectMenuPos = { x: e.clientX, y: e.clientY };
                projectMenuOpen = true;
              }}
            >{pageTitle}</span>
            <button
              class="project-title-menu"
              onclick={(e: MouseEvent) => {
                const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                projectMenuPos = { x: rect.left, y: rect.bottom + 4 };
                projectMenuOpen = true;
              }}
            >&#8942;</button>
          </div>
        {:else}
          <span style="font-size: 20px; font-weight: 600; letter-spacing: -0.02em; flex-shrink: 0; margin-right: auto;">{pageTitle}</span>
        {/if}
        {#if !responsiveStore.isMobile}
          <button
            onclick={handleUndo}
            disabled={!revisionsStore.canUndo || revisionsStore.loading}
            title="Undo (Ctrl+Z)"
            style="background: transparent; border: none; color: var(--text-secondary); font-size: 18px; cursor: pointer; padding: 4px 8px; border-radius: 6px; flex-shrink: 0; white-space: nowrap; opacity: {revisionsStore.canUndo && !revisionsStore.loading ? 1 : 0.35}; transition: opacity var(--transition-fast), background var(--transition-fast);"
            onmouseenter={(e) => { if (revisionsStore.canUndo) (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)'; }}
            onmouseleave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
          >&#8630;</button>
          <button
            onclick={handleRedo}
            disabled={!revisionsStore.canRedo || revisionsStore.loading}
            title="Redo (Ctrl+Shift+Z)"
            style="background: transparent; border: none; color: var(--text-secondary); font-size: 18px; cursor: pointer; padding: 4px 8px; border-radius: 6px; flex-shrink: 0; white-space: nowrap; opacity: {revisionsStore.canRedo && !revisionsStore.loading ? 1 : 0.35}; transition: opacity var(--transition-fast), background var(--transition-fast);"
            onmouseenter={(e) => { if (revisionsStore.canRedo) (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)'; }}
            onmouseleave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
          >&#8631;</button>
          <Input placeholder="Search..." bind:value={searchValue} bind:ref={searchRef} height={34} oninput={handleSearchInput} style="width: 180px; flex-shrink: 1;" />
        {/if}
        {#if isTaskViewRoute}
          <Button variant={filterOpen || filterStore.activeFilterCount > 0 ? 'accent' : 'outline'} size="sm" onclick={() => filterOpen = !filterOpen}>Filter{filterStore.activeFilterCount > 0 ? ` (${filterStore.activeFilterCount})` : ''}</Button>
        {/if}
        {#if projectMenuOpen && currentProject}
          <ProjectContextMenu
            project={currentProject}
            position={projectMenuPos}
            onclose={() => projectMenuOpen = false}
            ondelete={() => goto('/')}
          />
        {/if}
      </div>

      {#if responsiveStore.isMobile && isTaskViewRoute && !currentProject}
        <div class="mobile-filter-chips">
          <button
            class="filter-chip"
            class:filter-chip-active={$page.url.pathname === '/'}
            onclick={() => goto('/')}
          >All</button>
          <button
            class="filter-chip"
            class:filter-chip-active={$page.url.pathname === '/upcoming'}
            onclick={() => goto('/upcoming')}
          >Upcoming{upcomingCount > 0 ? ` ${upcomingCount}` : ''}</button>
          <button
            class="filter-chip"
            class:filter-chip-active={$page.url.pathname === '/overdue'}
            onclick={() => goto('/overdue')}
          >Overdue{overdueCount > 0 ? ` ${overdueCount}` : ''}</button>
        </div>
      {/if}

      {#if isTaskViewRoute}
        <FilterBar open={filterOpen} />
      {/if}

      <!-- Content + Detail Pane -->
      <div style="flex: 1; display: flex; overflow: hidden;">
        <div style="flex: 1; overflow-y: auto; min-width: 0;">
          {#if isTaskViewRoute}
            <ViewOrchestrator />
          {:else}
            {@render children()}
          {/if}
        </div>
        {#if taskDetailStore.isOpen && !responsiveStore.isMobile}
          <TaskDetail />
        {/if}
      </div>
    </div>
  </div>
  {#if responsiveStore.isMobile && taskDetailStore.isOpen && mobileTaskFullscreen}
    <div class="mobile-overlay">
      <div class="mobile-overlay-header">
        <button class="mobile-back-btn" onclick={() => { mobileTaskFullscreen = false; taskDetailStore.close(); }} aria-label="Back">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/>
          </svg>
          Back
        </button>
      </div>
      <div style="flex: 1; overflow-y: auto;">
        <TaskDetail />
      </div>
    </div>
  {/if}
  {#if responsiveStore.isMobile && taskDetailStore.isOpen && !mobileTaskFullscreen}
    {@const selectedTask = tasksStore.tasks.find(t => t.id === taskDetailStore.selectedTaskId)}
    <BottomSheet open={true} onclose={() => taskDetailStore.close()}>
      {#if selectedTask}
        <div class="sheet-task-preview">
          <h3 class="sheet-task-title">{selectedTask.title}</h3>
          <div class="sheet-task-meta">
            {#if selectedTask.priority && selectedTask.priority > 1}
              <span class="sheet-priority" style="color: var(--priority-{selectedTask.priority === 5 ? 'urgent' : selectedTask.priority === 4 ? 'high' : selectedTask.priority === 3 ? 'medium' : 'low'});">
                {'●'.repeat(selectedTask.priority)}
              </span>
            {/if}
            {#if selectedTask.due_date}
              {@const due = new Date(selectedTask.due_date)}
              {@const isOverdue = due < new Date() && !selectedTask.done}
              <span style="color: {isOverdue ? 'var(--overdue)' : 'var(--text-tertiary)'}; font-size: 13px;">
                {due.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </span>
            {/if}
            {#if selectedTask.project_id}
              {@const project = projectsStore.projects.find(p => p.id === selectedTask.project_id)}
              {#if project}
                <span style="font-size: 13px; color: var(--text-tertiary);">{project.title}</span>
              {/if}
            {/if}
          </div>
          {#if selectedTask.description}
            <p class="sheet-task-desc">{selectedTask.description}</p>
          {/if}
          <div class="sheet-task-actions">
            <button class="sheet-action-btn sheet-done-btn" onclick={() => { toggleDone(selectedTask.id); taskDetailStore.close(); }}>Done</button>
            <button class="sheet-action-btn" onclick={() => { mobileTaskFullscreen = true; }}>Open</button>
          </div>
        </div>
      {/if}
    </BottomSheet>
  {/if}
  {#if responsiveStore.isMobile && responsiveStore.sidebarOpen}
    <div
      class="mobile-sidebar-backdrop"
      role="presentation"
      transition:fade={{ duration: 200 }}
      onclick={() => responsiveStore.closeSidebar()}
    ></div>
    <div class="mobile-sidebar" transition:fly={{ x: -280, duration: 200 }}>
      <div class="mobile-sidebar-header">
        <div class="mobile-sidebar-brand"></div>
        <button class="mobile-sidebar-close" onclick={() => responsiveStore.closeSidebar()} aria-label="Close menu">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 6L6 18"/><path d="M6 6l12 12"/>
          </svg>
        </button>
      </div>
      <Sidebar />
    </div>
  {/if}
  <ShortcutsModal open={shortcutsOpen} onclose={() => shortcutsOpen = false} />
  <ThinkingMargin open={thinkingOpen && !taskDetailStore.isOpen} onclose={() => thinkingOpen = false} ontaskschanged={() => tasksStore.fetchAll()} />
  <ToastContainer />
  <ConfirmDialog />
  {#if responsiveStore.isMobile}
    <button class="fab-extract" aria-label="Quick add" onclick={() => quickAddOpen = true}>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <path d="M12 5v14"/><path d="M5 12h14"/>
      </svg>
    </button>
    <MobileQuickAdd open={quickAddOpen} onclose={() => quickAddOpen = false} />
  {:else}
    <button class="fab-extract" class:fab-active={thinkingOpen} aria-label="AI Extract" onclick={openThinking}>
      <span class="diamond-icon">{@html extractIcon}</span>
    </button>
  {/if}
{/if}

<style>
  .project-title-group {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
    margin-right: auto;
  }

  .project-title-menu {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: none;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    color: var(--text-tertiary);
    font-size: 16px;
    cursor: pointer;
    transition: opacity var(--transition-fast), background var(--transition-fast);
    padding: 0;
  }

  .project-title-group:hover .project-title-menu {
    opacity: 1;
  }

  .project-title-menu:hover {
    background: var(--bg-surface-hover);
  }

  .fab-extract {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 40;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: var(--accent);
    color: var(--bg-base);
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 16px rgba(232, 119, 46, 0.3);
    transition: transform var(--transition-fast) ease-out, background var(--transition-fast) ease-out, box-shadow var(--transition-fast) ease-out;
  }

  .fab-extract:hover {
    transform: scale(1.08);
    box-shadow: 0 6px 20px rgba(232, 119, 46, 0.45);
  }

  .fab-active {
    background: var(--accent-glow);
  }

  .fab-extract :global(.diamond-icon) {
    display: flex;
    align-items: center;
    justify-content: center;
    animation: diamond-drift 12s linear infinite;
  }

  .fab-extract:hover :global(.diamond-icon) {
    animation-duration: 4s;
  }

  .hamburger-btn {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    border-radius: 6px;
    flex-shrink: 0;
    transition: background var(--transition-fast);
    padding: 0;
  }

  .hamburger-btn:hover {
    background: var(--bg-surface-hover);
  }

  .mobile-overlay {
    position: fixed;
    inset: 0;
    z-index: 150;
    background: var(--bg-base);
    display: flex;
    flex-direction: column;
  }

  .mobile-overlay-header {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .mobile-back-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 14px;
    font-family: var(--font-sans);
    padding: 4px 8px;
    border-radius: 6px;
    transition: background var(--transition-fast);
  }

  .mobile-back-btn:hover {
    background: var(--bg-surface-hover);
  }

  .mobile-sidebar-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.32);
    z-index: 200;
  }

  .mobile-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 280px;
    z-index: 201;
    background: var(--bg-base);
    border-right: 1px solid var(--border-default);
    border-radius: 0 16px 16px 0;
    box-shadow: var(--shadow-lg);
    --sidebar-width: 280px;
  }

  .mobile-sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 16px 8px;
    flex-shrink: 0;
  }

  .mobile-sidebar-brand {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
    animation: breathe 4s ease-in-out infinite;
  }

  .mobile-sidebar-close {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    color: var(--text-tertiary);
    cursor: pointer;
    border-radius: 6px;
    transition: color var(--transition-fast), background var(--transition-fast);
    padding: 0;
  }

  .mobile-sidebar-close:hover {
    color: var(--text-secondary);
    background: var(--bg-surface-hover);
  }

  .sheet-task-preview {
    padding: 8px 20px 24px;
  }

  .sheet-task-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 8px;
    line-height: 1.3;
  }

  .sheet-task-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }

  .sheet-task-desc {
    font-size: 14px;
    color: var(--text-secondary);
    margin: 0 0 20px;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .sheet-task-actions {
    display: flex;
    gap: 10px;
  }

  .sheet-action-btn {
    height: 40px;
    padding: 0 20px;
    font-size: 14px;
    font-weight: 500;
    font-family: var(--font-sans);
    border-radius: 8px;
    border: 1px solid var(--border-default);
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .sheet-action-btn:active {
    background: var(--bg-surface-hover);
  }

  .sheet-done-btn {
    border-color: var(--done);
    color: var(--done);
  }

  .mobile-filter-chips {
    display: flex;
    gap: 6px;
    padding: 8px 16px 0;
    flex-shrink: 0;
  }

  .filter-chip {
    height: 32px;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 500;
    font-family: var(--font-sans);
    border-radius: 16px;
    border: 1px solid var(--border-default);
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
    white-space: nowrap;
  }

  .filter-chip-active {
    background: var(--accent-subtle);
    border-color: var(--accent);
    color: var(--accent);
  }
</style>

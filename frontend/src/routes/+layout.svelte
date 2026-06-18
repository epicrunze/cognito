<script lang="ts">
  import '../app.css';
  import type { Snippet } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { onMount, tick } from 'svelte';
  import { fly } from 'svelte/transition';
  import { panelFly, backdropFade, easeOut, DURATION } from '$lib/transitions';
  import { authStore, tasksStore, projectsStore, labelsStore, bubbleStore, toggleDone } from '$lib/stores.svelte';
  import { shortcuts } from '$lib/shortcuts';
  import { isOverdue as checkOverdue, isUpcoming as checkUpcoming, parseDateOnly, formatRelativeDate } from '$lib/dateUtils';
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
  import TabBar from '$components/features/TabBar.svelte';
  import LensTabs from '$components/ui/LensTabs.svelte';

  let { children }: { children: Snippet } = $props();

  let searchRef = $state<HTMLInputElement | undefined>(undefined);
  let searchValue = $state('');
  let thinkingOpen = $state(false);
  let filterOpen = $state(false);
  let shortcutsOpen = $state(false);
  let mobileTaskFullscreen = $state(false);
  let quickAddOpen = $state(false);

  // Filter counts for mobile chips
  const upcomingCount = $derived(tasksStore.tasks.filter(t => !t.done && t.due_date && checkUpcoming(t.due_date)).length);
  const overdueCount = $derived(tasksStore.tasks.filter(t => !t.done && t.due_date && checkOverdue(t.due_date)).length);

  const isLoginPage = $derived($page.url.pathname === '/login');
  const isTaskViewRoute = $derived.by(() => {
    const path = $page.url.pathname;
    return path === '/' || path === '/upcoming' || path === '/overdue' || path.startsWith('/project/');
  });

  // Page title mapping
  const pageTitles: Record<string, string> = {
    '/': 'All Tasks',
    '/briefing': 'Today',
    '/upcoming': 'Upcoming',
    '/overdue': 'Overdue',
    '/projects': 'Projects',
    '/settings': 'Settings',
  };

  // ── Mobile bottom-nav (TabBar) ──
  const mobileTabs = [
    { value: 'thoughts', label: 'Thoughts' },
    { value: 'projects', label: 'Projects' },
    { value: 'upcoming', label: 'Upcoming' },
    { value: 'search', label: 'Search' },
  ];
  const activeTab = $derived.by(() => {
    const p = $page.url.pathname;
    if (p === '/projects' || p.startsWith('/project/')) return 'projects';
    if (p === '/upcoming') return 'upcoming';
    return 'thoughts';
  });
  let mobileSearchOpen = $state(false);

  function handleTabChange(value: string) {
    mobileSearchOpen = false;
    if (value === 'thoughts') goto('/');
    else if (value === 'projects') goto('/projects');
    else if (value === 'upcoming') goto('/upcoming');
    else if (value === 'search') {
      mobileSearchOpen = true;
      tick().then(() => searchRef?.focus());
    }
  }

  // Home lenses (all / upcoming / overdue) — the mobile perspective row.
  const homeLenses = $derived([
    { value: '/', label: 'all' },
    { value: '/upcoming', label: 'upcoming', count: upcomingCount || undefined },
    { value: '/overdue', label: 'overdue', count: overdueCount || undefined },
  ]);
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
      tasksStore.fetchAll();
      projectsStore.fetchAll();
      labelsStore.fetchAll();
      labelsStore.fetchStats();
      revisionsStore.fetchRecent();

      // Cold start from a reminder notification: ?task=123 opens that task,
      // then we strip the param so a refresh doesn't reopen it.
      const taskParam = $page.url.searchParams.get('task');
      if (taskParam) {
        const id = Number(taskParam);
        if (Number.isFinite(id)) taskDetailStore.open(id);
        const url = new URL(window.location.href);
        url.searchParams.delete('task');
        history.replaceState(history.state, '', url.pathname + url.search + url.hash);
      }
    }
  });

  // Warm start: the running app receives the click intent from the service
  // worker and routes client-side (no reload).
  onMount(() => {
    if (!('serviceWorker' in navigator)) return;
    function handleSwMessage(e: MessageEvent) {
      const data = e.data;
      if (!data || data.type !== 'notification-click') return;
      if (data.taskId) {
        goto('/');
        taskDetailStore.open(Number(data.taskId));
      } else {
        goto(typeof data.url === 'string' ? data.url : '/');
      }
    }
    navigator.serviceWorker.addEventListener('message', handleSwMessage);
    return () => navigator.serviceWorker.removeEventListener('message', handleSwMessage);
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
    <main style="flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0;">
      <!-- Top bar -->
      <div style="display: flex; align-items: center; padding: 10px {responsiveStore.isMobile ? '16px' : '24px'}; border-bottom: 1px solid var(--border-subtle); gap: 10px; flex-shrink: 0;">
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
        {:else if responsiveStore.isMobile && isTaskViewRoute}
          <div style="margin-right: auto;">
            <LensTabs lenses={homeLenses} value={$page.url.pathname} onchange={(v) => goto(v)} />
          </div>
          <button class="topbar-gear" aria-label="Settings" onclick={() => goto('/settings')}>
            <svg width="20" height="20" viewBox="0 0 22 22" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" fill="none"><circle cx="11" cy="11" r="2.6" /><path d="M11 2.5v2.4M11 17.1v2.4M2.5 11h2.4M17.1 11h2.4M5 5l1.7 1.7M15.3 15.3L17 17M17 5l-1.7 1.7M6.7 15.3L5 17" /></svg>
          </button>
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

      {#if isTaskViewRoute}
        <FilterBar open={filterOpen} />
      {/if}

      <!-- Content + Detail Pane -->
      <div style="flex: 1; display: flex; overflow: hidden;">
        <div style="flex: 1; overflow-y: auto; min-width: 0; {responsiveStore.isMobile ? 'padding-bottom: 76px;' : ''}">
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
    </main>
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
              <span style="width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; background: var(--priority-{selectedTask.priority === 5 ? 'urgent' : selectedTask.priority === 4 ? 'high' : selectedTask.priority === 3 ? 'medium' : 'low'});"></span>
            {/if}
            {#if selectedTask.due_date}
              {@const isOverdueDate = checkOverdue(selectedTask.due_date) && !selectedTask.done}
              <span style="color: {isOverdueDate ? 'var(--overdue)' : 'var(--text-tertiary)'}; font-size: 13px;">
                {formatRelativeDate(selectedTask.due_date)}
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
      transition:backdropFade
      onclick={() => responsiveStore.closeSidebar()}
    ></div>
    <div class="mobile-sidebar" transition:panelFly={{ x: -280 }}>
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
    {#if mobileSearchOpen}
      <div class="mobile-search-bar" transition:fly={{ y: -40, duration: DURATION.normal, easing: easeOut }}>
        <Input placeholder="Search thoughts..." bind:value={searchValue} bind:ref={searchRef} height={38} oninput={handleSearchInput} style="flex: 1;" />
        <button class="mobile-search-close" onclick={() => { mobileSearchOpen = false; searchValue = ''; handleSearchInput(); }} aria-label="Close search">&times;</button>
      </div>
    {/if}
    <TabBar
      tabs={mobileTabs}
      active={activeTab}
      onchange={handleTabChange}
      oncapture={() => quickAddOpen = true}
    />
    <MobileQuickAdd open={quickAddOpen} onclose={() => quickAddOpen = false} />
  {:else}
    <button class="fab-extract" class:fab-active={thinkingOpen} aria-label={thinkingOpen ? 'Close thinking margin' : 'Open thinking margin'} onclick={openThinking}>
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

  .topbar-gear {
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

  .topbar-gear:hover {
    background: var(--bg-surface-hover);
  }

  .mobile-search-bar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 110;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: var(--bg-base);
    border-bottom: 1px solid var(--border-default);
  }

  .mobile-search-close {
    background: none;
    border: none;
    color: var(--text-tertiary);
    cursor: pointer;
    font-size: 22px;
    line-height: 1;
    padding: 0 4px;
    flex-shrink: 0;
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
    transition-property: background-color, border-color, color, box-shadow, transform, opacity; transition-duration: var(--t-fast); transition-timing-function: var(--ease-out);
  }

  .sheet-action-btn:active {
    background: var(--bg-surface-hover);
  }

  .sheet-done-btn {
    border-color: var(--done);
    color: var(--done);
  }

</style>

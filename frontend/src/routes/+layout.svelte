<script lang="ts">
  import '../app.css';
  import type { Snippet } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { authStore, tasksStore, projectsStore, labelsStore, bubbleStore } from '$lib/stores.svelte';
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
  import ViewOrchestrator from '$components/features/ViewOrchestrator.svelte';
  import TaskDetail from '$components/features/TaskDetail.svelte';

  let { children }: { children: Snippet } = $props();

  let searchRef = $state<HTMLInputElement | undefined>(undefined);
  let searchValue = $state('');
  let thinkingOpen = $state(false);
  let filterOpen = $state(false);
  let shortcutsOpen = $state(false);

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
    <div style="flex-shrink: 0;">
      <Sidebar />
    </div>
    <div style="flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0;">
      <!-- Top bar -->
      <div style="display: flex; align-items: center; padding: 10px 24px; border-bottom: 1px solid var(--border-subtle); gap: 10px; flex-shrink: 0;">
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
        <div style="flex: 1; overflow-y: auto; min-width: 0;">
          {#if isTaskViewRoute}
            <ViewOrchestrator />
          {:else}
            {@render children()}
          {/if}
        </div>
        {#if taskDetailStore.isOpen}
          <TaskDetail />
        {/if}
      </div>
    </div>
  </div>
  <ShortcutsModal open={shortcutsOpen} onclose={() => shortcutsOpen = false} />
  <ThinkingMargin open={thinkingOpen && !taskDetailStore.isOpen} onclose={() => thinkingOpen = false} ontaskschanged={() => tasksStore.fetchAll()} />
  <ToastContainer />
  <ConfirmDialog />
  <button class="fab-extract" class:fab-active={thinkingOpen} aria-label="AI Extract" onclick={openThinking}>
    <span class="diamond-icon">{@html extractIcon}</span>
  </button>
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
</style>

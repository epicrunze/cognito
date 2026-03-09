<script lang="ts">
  import '../app.css';
  import type { Snippet } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { authStore, tasksStore, projectsStore, labelsStore } from '$lib/stores.svelte';
  import { shortcuts } from '$lib/shortcuts';
  import Sidebar from '$components/features/Sidebar.svelte';
  import TaskPanel from '$components/features/TaskPanel.svelte';
  import FilterBar from '$components/features/FilterBar.svelte';
  import ShortcutsModal from '$components/features/ShortcutsModal.svelte';
  import Input from '$components/ui/Input.svelte';
  import Button from '$components/ui/Button.svelte';
  import ToastContainer from '$components/ui/ToastContainer.svelte';
  import { searchStore } from '$lib/stores/search.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';

  let { children }: { children: Snippet } = $props();

  let collapsed = $state(false);
  let searchRef = $state<HTMLInputElement | undefined>(undefined);
  let searchValue = $state('');
  let createOpen = $state(false);
  let filterOpen = $state(false);
  let shortcutsOpen = $state(false);

  const isLoginPage = $derived($page.url.pathname === '/login');

  // Page title mapping
  const pageTitles: Record<string, string> = {
    '/': 'All Tasks',
    '/upcoming': 'Upcoming',
    '/overdue': 'Overdue',
    '/extract': 'Extract Tasks',
    '/settings': 'Settings',
  };
  const pageTitle = $derived.by(() => {
    const path = $page.url.pathname;
    if (path.startsWith('/project/')) {
      const project = projectsStore.projects.find(p => p.id === Number(path.split('/')[2]));
      const suffix = path.endsWith('/kanban') ? ' — Kanban' : '';
      return (project?.title ?? 'Project') + suffix;
    }
    return pageTitles[path] ?? 'Cognito';
  });

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
    }
  });

  // Keyboard shortcuts
  onMount(() => {
    shortcuts.register('/', () => searchRef?.focus());
    shortcuts.register('n', () => createOpen = true);
    shortcuts.register('?', () => shortcutsOpen = !shortcutsOpen);
    shortcuts.register('Escape', () => {
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    });
    window.addEventListener('keydown', shortcuts.handleKeydown);
    return () => window.removeEventListener('keydown', shortcuts.handleKeydown);
  });

  // Derive default project from current route
  const defaultProjectId = $derived.by(() => {
    const path = $page.url.pathname;
    if (path.startsWith('/project/')) {
      const id = Number(path.split('/')[2]);
      return isNaN(id) ? undefined : id;
    }
    return undefined;
  });

  function handleSearchInput() {
    searchStore.set(searchValue);
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
    <Sidebar bind:collapsed />
    <div style="flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0;">
      <!-- Top bar -->
      <div style="display: flex; align-items: center; padding: 10px 24px; border-bottom: 1px solid var(--border-subtle); gap: 10px; flex-shrink: 0;">
        <span style="font-size: 20px; font-weight: 600; letter-spacing: -0.02em; flex-shrink: 0; margin-right: auto;">{pageTitle}</span>
        <Input placeholder="Search..." bind:value={searchValue} bind:ref={searchRef} height={34} oninput={handleSearchInput} style="width: 180px; flex-shrink: 1;" />
        <Button variant={filterOpen || filterStore.activeFilterCount > 0 ? 'accent' : 'outline'} size="sm" onclick={() => filterOpen = !filterOpen}>Filter{filterStore.activeFilterCount > 0 ? ` (${filterStore.activeFilterCount})` : ''}</Button>
        <Button variant="accent" size="sm" onclick={() => goto('/extract')}>&diams; Extract</Button>
        <Button variant="accent" size="sm" onclick={() => createOpen = true}>+ New</Button>
      </div>

      <FilterBar open={filterOpen} />

      <!-- Content -->
      <div style="flex: 1; overflow-y: auto;">
        {@render children()}
      </div>
    </div>
  </div>
  <TaskPanel mode="create" open={createOpen} onclose={() => createOpen = false} {defaultProjectId} />
  <ShortcutsModal open={shortcutsOpen} onclose={() => shortcutsOpen = false} />
  <ToastContainer />
{/if}

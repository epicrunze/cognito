<script lang="ts">
  import { page } from '$app/stores';
  import { projectsStore, tasksStore } from '$lib/stores.svelte';
  import { allTasksIcon, upcomingIcon, overdueIcon, settingsIcon } from '$lib/icons';
  import { registerRect } from '$lib/stores/sidebarRects.svelte';
  import { projectIdentifierStore } from '$lib/stores/projectIdentifiers.svelte';
  import Tip from '$components/ui/Tip.svelte';
  import ProjectContextMenu from './ProjectContextMenu.svelte';
  import ColorPicker from '$components/ui/ColorPicker.svelte';
  import Button from '$components/ui/Button.svelte';
  import { goto } from '$app/navigation';
  import { dndzone } from 'svelte-dnd-action';
  import type { Project } from '$lib/types';
  import { PRESET_COLORS } from '$lib/constants';

  const currentPath = $derived($page.url.pathname);

  // Nav counts
  const allCount = $derived(tasksStore.tasks.filter(t => !t.done).length);
  const upcomingCount = $derived(tasksStore.tasks.filter(t => !t.done && t.due_date && new Date(t.due_date) > new Date()).length);
  const overdueCount = $derived(tasksStore.tasks.filter(t => !t.done && t.due_date && new Date(t.due_date) < new Date()).length);

  const nav = $derived([
    { id: '/', label: 'All Tasks', icon: allTasksIcon, path: '/', count: allCount },
    { id: '/upcoming', label: 'Upcoming', icon: upcomingIcon, path: '/upcoming', count: upcomingCount },
    { id: '/overdue', label: 'Overdue', icon: overdueIcon, path: '/overdue', count: overdueCount, countColor: 'var(--overdue)' },
  ]);

  // Task counts per project
  function projectTaskCount(projectId: number): number {
    return tasksStore.tasks.filter(t => t.project_id === projectId && !t.done).length;
  }

  const isSettingsPage = $derived(currentPath.startsWith('/settings'));

  // Context menu state
  let contextMenu = $state<{ project: typeof projectsStore.projects[0]; x: number; y: number } | null>(null);

  // Project creation pop-out state
  let createOpen = $state(false);
  let createPos = $state({ x: 0, y: 0 });
  let newProjectName = $state('');
  let createInput = $state<HTMLInputElement | null>(null);
  let createPanel = $state<HTMLDivElement | null>(null);
  let selectedColor = $state('');
  let selectedIdentifier = $state('');
  let showCustomColor = $state(false);

  // Drag-and-drop state (svelte-dnd-action)
  let localProjects = $state<Project[]>([]);
  let isDragging = $state(false);

  $effect(() => {
    if (!isDragging) {
      localProjects = [...projectsStore.projects];
    }
  });

  function handleConsider(e: CustomEvent<{ items: Project[] }>) {
    isDragging = true;
    localProjects = e.detail.items;
  }

  function handleFinalize(e: CustomEvent<{ items: Project[] }>) {
    isDragging = false;
    localProjects = e.detail.items;

    // Find the project that moved and its new index
    const oldOrder = projectsStore.projects.map(p => p.id);
    const newOrder = e.detail.items.map(p => p.id);
    for (let i = 0; i < newOrder.length; i++) {
      if (newOrder[i] !== oldOrder[i]) {
        // First difference — find which project moved here
        const movedId = newOrder[i];
        projectsStore.reorder(movedId, i);
        break;
      }
    }
  }

  function handleContextMenu(e: MouseEvent, project: typeof projectsStore.projects[0]) {
    e.preventDefault();
    contextMenu = { project, x: e.clientX, y: e.clientY };
  }

  function startCreating(e: MouseEvent) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    createPos = { x: rect.right + 8, y: rect.top };
    createOpen = true;
    newProjectName = '';
    selectedColor = '';
    selectedIdentifier = '';
    showCustomColor = false;
    requestAnimationFrame(() => createInput?.focus());
  }

  async function submitCreate() {
    const name = newProjectName.trim();
    if (!name) {
      createOpen = false;
      return;
    }
    try {
      const project = await projectsStore.create({ title: name, ...(selectedColor ? { hex_color: selectedColor } : {}) });
      if (selectedIdentifier && project) {
        projectIdentifierStore.set(project.id, selectedIdentifier);
      }
      if (project) {
        // Trigger celebration animation after DOM updates
        requestAnimationFrame(() => {
          const el = document.querySelector(`[data-project-id="${project.id}"]`) as HTMLElement;
          if (el) {
            el.style.animation = 'projectBirth 400ms ease-out';
            const color = selectedColor || 'var(--accent)';
            el.style.boxShadow = `0 0 12px ${color}40`;
            el.addEventListener('animationend', () => {
              el.style.animation = '';
            }, { once: true });
            setTimeout(() => { el.style.boxShadow = ''; }, 1500);
          }
        });
        // Navigate to the new project
        goto(`/project/${project.id}`);
      }
    } catch {
      // store handles error
    }
    createOpen = false;
    newProjectName = '';
    selectedColor = '';
    selectedIdentifier = '';
    showCustomColor = false;
  }

  function handleCreateKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      submitCreate();
    } else if (e.key === 'Escape') {
      createOpen = false;
    }
  }

  // Click-outside to dismiss create panel
  $effect(() => {
    if (!createOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (createPanel && !createPanel.contains(e.target as Node)) {
        createOpen = false;
        newProjectName = '';
        selectedColor = '';
        selectedIdentifier = '';
        showCustomColor = false;
      }
    }
    document.addEventListener('mousedown', handleClickOutside, true);
    return () => document.removeEventListener('mousedown', handleClickOutside, true);
  });

</script>

<nav
  class="sidebar"
  aria-label="Main navigation"
>
  <!-- Brand mark — breathing ambient glow -->
  <div class="brand-mark"></div>

  <!-- Navigation icons -->
  <div class="nav-icons">
    {#each nav as item (item.id)}
      {@const active = currentPath === item.path}
      <Tip text="{item.label}{item.count > 0 ? ` (${item.count})` : ''}" side="right">
        <a
          href={item.path}
          class="nav-icon"
          class:nav-icon-active={active}
          aria-label={item.label}
          aria-current={active ? 'page' : undefined}
          use:registerRect={item.path}
        >
          {#if active}
            <span class="nav-glow"></span>
          {/if}
          {@html item.icon}
          {#if item.count > 0}
            <span class="nav-count" style:color={item.countColor ?? 'var(--text-tertiary)'}>{item.count}</span>
          {/if}
          {#if active}
            <span class="nav-underline"></span>
          {/if}
        </a>
      </Tip>
    {/each}
  </div>

  <!-- Gradient separator -->
  <div class="separator"></div>

  <!-- Projects micro-clusters -->
  <div class="projects-section">
    {#if projectsStore.loading}
      {#each [1, 2, 3] as _ (_)}
        <div class="project-zone" style="opacity: 0.3;"></div>
      {/each}
    {:else}
      <div
        class="dnd-project-list"
        use:dndzone={{ items: localProjects, dropTargetStyle: {}, type: 'sidebar-project', flipDurationMs: 200 }}
        onconsider={handleConsider}
        onfinalize={handleFinalize}
      >
        {#each localProjects as project, idx (project.id)}
          {@const active = currentPath === `/project/${project.id}`}
          {@const count = projectTaskCount(project.id)}
          <div
            class="project-zone"
            class:project-active={active}
            data-project-id={project.id}
            role="link"
            tabindex="0"
            aria-label="{project.title} ({count} tasks)"
            onclick={() => { goto(`/project/${project.id}`); }}
            onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goto(`/project/${project.id}`); } }}
            oncontextmenu={(e: MouseEvent) => handleContextMenu(e, project)}
            style="cursor: pointer;"
            use:registerRect={`/project/${project.id}`}
          >
            <Tip text="{project.title} ({count})" side="right">
              {#if active}
                <span class="project-bar" style:background={project.hex_color || 'var(--text-tertiary)'}></span>
              {/if}
              <span class="project-monogram-ring" style="border-color: {project.hex_color || 'var(--text-tertiary)'}; opacity: {active ? 1 : 0.5};">
                {projectIdentifierStore.get(project.id, project.title)}
              </span>
            </Tip>
          </div>
        {/each}
      </div>
    {/if}

    <!-- Create project button -->
    <Tip text="New project" side="right">
      <button class="create-btn" aria-label="Create project" onclick={startCreating}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 5v14"/>
          <path d="M5 12h14"/>
        </svg>
      </button>
    </Tip>
  </div>

  <div style="flex: 1;"></div>

  <!-- Settings -->
  <div class="settings-zone">
    <Tip text="Settings" side="right">
      <a href="/settings" class="settings-btn" class:settings-active={isSettingsPage} aria-label="Settings">
        {@html settingsIcon}
      </a>
    </Tip>
  </div>

  {#if createOpen}
    <div
      bind:this={createPanel}
      class="create-popout"
      style="left: {createPos.x}px; top: {createPos.y}px;"
    >
      <!-- Live preview -->
      <div class="create-preview">
        <span class="create-preview-ring" style="border-color: {selectedColor || 'var(--text-tertiary)'};">
          {selectedIdentifier || (newProjectName.trim() ? newProjectName.trim().charAt(0).toUpperCase() : '?')}
        </span>
        <span class="create-preview-name">
          {newProjectName.trim() || 'New project'}
        </span>
      </div>

      <input
        bind:this={createInput}
        bind:value={newProjectName}
        onkeydown={handleCreateKeydown}
        class="create-popout-input"
        type="text"
        placeholder="Project name"
        spellcheck="false"
      />

      <!-- Identifier -->
      <div class="create-section-label">Identifier</div>
      <input
        class="create-identifier-input"
        type="text"
        maxlength="3"
        placeholder={newProjectName.trim() ? newProjectName.trim().charAt(0).toUpperCase() : 'A'}
        bind:value={selectedIdentifier}
        oninput={() => { selectedIdentifier = selectedIdentifier.toUpperCase(); }}
        onkeydown={handleCreateKeydown}
      />

      <!-- Color swatches -->
      <div class="create-section-label">Color</div>
      <div class="create-swatches">
        {#each PRESET_COLORS as color (color.hex)}
          <button
            class="create-swatch"
            class:selected={selectedColor === color.hex}
            style="background: {color.hex};"
            title={color.name}
            onclick={() => { selectedColor = selectedColor === color.hex ? '' : color.hex; }}
          ></button>
        {/each}
      </div>
      <button class="create-custom-toggle" onclick={() => showCustomColor = !showCustomColor}>
        {showCustomColor ? 'Hide custom' : 'Custom...'}
      </button>
      {#if showCustomColor}
        <div class="create-custom-color">
          <ColorPicker value={selectedColor || '#E8772E'} onchange={(hex: string) => selectedColor = hex} />
        </div>
      {/if}

      <!-- Create button -->
      <Button variant="accent" size="sm" disabled={!newProjectName.trim()} onclick={submitCreate} style="width: 100%; justify-content: center; margin-top: 4px;">
        Create project
      </Button>
    </div>
  {/if}

  {#if contextMenu}
    <ProjectContextMenu
      project={contextMenu.project}
      position={{ x: contextMenu.x, y: contextMenu.y }}
      onclose={() => contextMenu = null}
      ondelete={() => {
        if (currentPath === `/project/${contextMenu?.project.id}`) {
          goto('/');
        }
      }}
    />
  {/if}
</nav>

<style>
  .sidebar {
    width: var(--sidebar-width, 64px);
    background: var(--bg-base);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0 8px;
    height: 100%;
    flex-shrink: 0;
    position: relative;
  }

  /* Brand mark — breathing ambient life */
  .brand-mark {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
    animation: breathe 4s ease-in-out infinite;
    margin-top: 16px;
    flex-shrink: 0;
  }

  /* Nav icons */
  .nav-icons {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 24px;
    align-items: center;
  }

  .nav-icon {
    position: relative;
    width: 40px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-tertiary);
    text-decoration: none;
    border-radius: 6px;
    transition: color var(--transition-fast) ease-out;
  }

  .nav-icon:hover {
    color: var(--text-secondary);
  }

  .nav-icon-active {
    color: var(--text-primary);
  }

  /* Faint glow behind active nav icon */
  .nav-glow {
    position: absolute;
    inset: 2px;
    border-radius: 6px;
    background: rgba(232, 119, 46, 0.05);
    pointer-events: none;
  }

  .nav-count {
    position: absolute;
    top: 1px;
    right: -1px;
    font-size: 8px;
    font-weight: 500;
    line-height: 1;
    min-width: 0;
  }

  .nav-underline {
    position: absolute;
    bottom: 2px;
    left: 50%;
    width: 16px;
    height: 2px;
    background: var(--accent);
    border-radius: 1px;
    animation: underline-in var(--transition-normal) ease-out forwards;
  }

  /* Gradient separator between nav and projects */
  .separator {
    width: 24px;
    height: 1px;
    margin-top: 20px;
    background: linear-gradient(90deg, transparent, var(--border-default), transparent);
  }

  /* Projects */
  .projects-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 16px;
    align-items: center;
    overflow-y: auto;
    overflow-x: hidden;
    max-height: calc(100vh - 320px);
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  .projects-section::-webkit-scrollbar {
    display: none;
  }

  .project-zone {
    position: relative;
    width: 40px;
    min-height: 32px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    text-decoration: none;
    border-radius: 6px;
    padding: 4px 0;
    transition: background var(--transition-fast) ease-out, box-shadow 1.5s ease-out;
    animation: fadeIn var(--transition-slow) ease-out both;
  }

  .project-zone:hover {
    background: var(--bg-surface-hover);
  }

  .project-bar {
    position: absolute;
    left: -8px;
    top: 50%;
    transform: translateY(-50%);
    width: 2px;
    height: 28px;
    border-radius: 1px;
  }

  .project-monogram-ring {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: 1.5px solid; /* color set via inline style */
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    line-height: 1;
    transition: opacity var(--transition-fast), border-color var(--transition-fast);
  }

  .project-zone:hover .project-monogram-ring {
    opacity: 1 !important;
  }

  .project-active .project-monogram-ring {
    opacity: 1 !important;
  }

  /* Settings — centered with proper hit target */
  .settings-zone {
    margin-bottom: 12px;
    width: 100%;
    display: flex;
    justify-content: center;
  }

  .settings-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-tertiary);
    opacity: 0.35;
    text-decoration: none;
    border-radius: 6px;
    transition: opacity var(--transition-fast) ease-out, background var(--transition-fast) ease-out;
  }

  .settings-btn:hover {
    opacity: 0.7;
    background: var(--bg-surface-hover);
  }

  .settings-active {
    opacity: 0.7;
    background: var(--accent-subtle);
  }

  /* Create project */
  .create-btn {
    width: 40px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-tertiary);
    opacity: 0.4;
    background: none;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: opacity var(--transition-fast) ease-out, background var(--transition-fast) ease-out;
    margin-top: 4px;
  }

  .create-btn:hover {
    opacity: 0.8;
    background: var(--bg-surface-hover);
  }

  .create-popout {
    position: fixed;
    z-index: 300;
    width: 260px;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: 10px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(232, 119, 46, 0.08);
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    animation: popout-enter var(--transition-fast) ease-out;
  }

  .create-popout-input {
    width: 100%;
    padding: 7px 10px;
    font-size: 13px;
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 6px;
    outline: none;
    font-family: var(--font-sans);
    box-sizing: border-box;
  }

  .create-popout-input:focus {
    border-color: var(--accent);
  }

  .create-swatches {
    display: flex;
    gap: 6px;
    padding: 2px 2px;
    flex-wrap: wrap;
  }

  .create-swatch {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 2px solid transparent;
    cursor: pointer;
    transition: border-color var(--transition-fast), transform var(--transition-fast);
    padding: 0;
  }

  .create-swatch:hover {
    transform: scale(1.15);
  }

  .create-swatch.selected {
    border-color: var(--text-primary);
  }

  /* Identifier input */
  .create-identifier-input {
    width: 60px;
    padding: 5px 8px;
    font-size: 13px;
    font-weight: 600;
    text-align: center;
    text-transform: uppercase;
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 6px;
    outline: none;
    font-family: var(--font-sans);
    letter-spacing: 0.05em;
  }

  .create-identifier-input:focus {
    border-color: var(--accent);
  }

  /* Custom color toggle */
  .create-custom-toggle {
    width: 100%;
    padding: 3px 8px;
    font-size: 11px;
    color: var(--text-tertiary);
    background: none;
    border: none;
    cursor: pointer;
    font-family: var(--font-sans);
    text-align: center;
    border-radius: 4px;
    transition: color var(--transition-fast), background var(--transition-fast);
  }

  .create-custom-toggle:hover {
    color: var(--text-secondary);
    background: var(--bg-surface-hover);
  }

  .create-custom-color {
    display: flex;
    justify-content: center;
  }

  /* Live preview */
  .create-preview {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    background: var(--bg-base);
    border-radius: 8px;
    border: 1px solid var(--border-subtle);
  }

  .create-preview-ring {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: 1.5px solid;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    line-height: 1;
    flex-shrink: 0;
    transition: border-color var(--transition-fast);
  }

  .create-preview-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Section micro-labels */
  .create-section-label {
    font-size: 10px;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding-left: 2px;
    margin-bottom: -4px;
  }

  /* Drag and drop (svelte-dnd-action) */
  .dnd-project-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    align-items: center;
    width: 100%;
  }

  /* Drag-drop indicator — style the dnd shadow/placeholder */
  .dnd-project-list :global([data-is-dnd-shadow-item-hint]) {
    height: 2px !important;
    min-height: 2px !important;
    background: var(--accent) !important;
    border-radius: 1px;
    opacity: 0.8;
    margin: 2px 6px;
    visibility: visible !important;
  }
</style>

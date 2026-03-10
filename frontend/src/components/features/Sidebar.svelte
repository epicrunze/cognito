<script lang="ts">
  import { page } from '$app/stores';
  import { projectsStore, tasksStore } from '$lib/stores.svelte';
  import { allTasksIcon, upcomingIcon, overdueIcon, extractIcon, settingsIcon } from '$lib/icons';
  import { registerRect } from '$lib/stores/sidebarRects.svelte';
  import Tip from '$components/ui/Tip.svelte';
  import ProjectContextMenu from './ProjectContextMenu.svelte';
  import { goto } from '$app/navigation';

  let { ontoggleextract, extractOpen = false }: { ontoggleextract?: () => void; extractOpen?: boolean } = $props();

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

  // Micro-cluster: how many dots for a task count
  function dotCount(count: number): number {
    if (count <= 0) return 1;
    if (count <= 3) return 1;
    if (count <= 7) return 2;
    if (count <= 12) return 3;
    if (count <= 20) return 4;
    return 5;
  }

  // Fixed organic dot positions within a 32x20 space
  const dotPositions: [number, number][][] = [
    [[16, 10]],
    [[10, 7], [22, 13]],
    [[8, 6], [20, 10], [12, 16]],
    [[8, 5], [22, 7], [6, 14], [20, 15]],
    [[6, 5], [18, 4], [28, 9], [8, 15], [22, 16]],
  ];

  // Pulse animation state
  let pulsingProject = $state<number | null>(null);

  function handleProjectClick(projectId: number) {
    pulsingProject = projectId;
    setTimeout(() => pulsingProject = null, 300);
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

  const COLORS = [
    { name: 'Tangerine', hex: '#E8772E' },
    { name: 'Coral', hex: '#E85D5D' },
    { name: 'Gold', hex: '#D4A845' },
    { name: 'Emerald', hex: '#4CAF7D' },
    { name: 'Teal', hex: '#45A5A5' },
    { name: 'Blue', hex: '#5B8DEF' },
    { name: 'Violet', hex: '#9B72CF' },
    { name: 'Rose', hex: '#CF72A8' },
  ] as const;

  // Drag-and-drop state
  let dragProjectId = $state<number | null>(null);
  let dragOverIdx = $state<number | null>(null);

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
    requestAnimationFrame(() => createInput?.focus());
  }

  async function submitCreate() {
    const name = newProjectName.trim();
    if (!name) {
      createOpen = false;
      return;
    }
    try {
      await projectsStore.create({ title: name, ...(selectedColor ? { hex_color: selectedColor } : {}) });
    } catch {
      // store handles error
    }
    createOpen = false;
    newProjectName = '';
    selectedColor = '';
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
        submitCreate();
      }
    }
    document.addEventListener('mousedown', handleClickOutside, true);
    return () => document.removeEventListener('mousedown', handleClickOutside, true);
  });

  function handleDragStart(e: DragEvent, projectId: number) {
    dragProjectId = projectId;
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', String(projectId));
    }
  }

  function handleDragOver(e: DragEvent, idx: number) {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
    dragOverIdx = idx;
  }

  function handleDragLeave() {
    dragOverIdx = null;
  }

  async function handleDrop(e: DragEvent, targetIdx: number) {
    e.preventDefault();
    dragOverIdx = null;
    if (dragProjectId === null) return;
    const id = dragProjectId;
    dragProjectId = null;
    await projectsStore.reorder(id, targetIdx);
  }

  function handleDragEnd() {
    dragProjectId = null;
    dragOverIdx = null;
  }
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
      {#each projectsStore.projects as project, idx (project.id)}
        {@const active = currentPath === `/project/${project.id}`}
        {@const count = projectTaskCount(project.id)}
        {@const dots = dotCount(count)}
        {@const pulsing = pulsingProject === project.id}
        <Tip text="{project.title} ({count})" side="right">
          <div
            class="project-zone"
            class:project-active={active}
            class:drag-over={dragOverIdx === idx}
            role="link"
            tabindex="0"
            aria-label="{project.title} ({count} tasks)"
            onclick={() => { handleProjectClick(project.id); goto(`/project/${project.id}`); }}
            onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleProjectClick(project.id); goto(`/project/${project.id}`); } }}
            oncontextmenu={(e: MouseEvent) => handleContextMenu(e, project)}
            draggable="true"
            ondragstart={(e: DragEvent) => handleDragStart(e, project.id)}
            ondragover={(e: DragEvent) => handleDragOver(e, idx)}
            ondragleave={handleDragLeave}
            ondrop={(e: DragEvent) => handleDrop(e, idx)}
            ondragend={handleDragEnd}
            style="animation-delay: {idx * 50}ms; cursor: pointer;"
            use:registerRect={`/project/${project.id}`}
          >
            {#if active}
              <span class="project-bar" style:background={project.hex_color || 'var(--text-tertiary)'}></span>
            {/if}
            <svg width="32" height="20" viewBox="0 0 32 20" class="cluster-dots" class:cluster-pulse={pulsing}>
              {#each dotPositions[dots - 1] as [cx, cy], i (i)}
                <circle
                  {cx}
                  {cy}
                  r="2"
                  fill={project.hex_color || 'var(--text-tertiary)'}
                  opacity={active ? 1 : 0.6}
                  style="animation: dot-appear 300ms ease-out {i * 60 + idx * 50}ms both;"
                />
              {/each}
            </svg>
            <span class="project-label" class:project-label-active={active}>
              {project.title.slice(0, 2).toUpperCase()}
            </span>
          </div>
        </Tip>
      {/each}
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

  <!-- AI Extract -->
  <div class="extract-zone">
    <Tip text="AI Extract" side="right">
      <button class="extract-btn" class:extract-active={extractOpen} aria-label="AI Extract" onclick={() => ontoggleextract?.()}>
        <span class="diamond-icon">
          {@html extractIcon}
        </span>
      </button>
    </Tip>
  </div>

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
      <input
        bind:this={createInput}
        bind:value={newProjectName}
        onkeydown={handleCreateKeydown}
        class="create-popout-input"
        type="text"
        placeholder="Project name"
        spellcheck="false"
      />
      <div class="create-swatches">
        {#each COLORS as color (color.hex)}
          <button
            class="create-swatch"
            class:selected={selectedColor === color.hex}
            style="background: {color.hex};"
            title={color.name}
            onclick={() => selectedColor = selectedColor === color.hex ? '' : color.hex}
          ></button>
        {/each}
      </div>
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
    animation: underline-in 200ms ease-out forwards;
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
    transition: background var(--transition-fast) ease-out;
    animation: fadeIn 300ms ease-out both;
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

  .cluster-dots {
    transition: transform 300ms ease-out;
  }

  .cluster-pulse {
    animation: cluster-pulse 300ms ease-out;
  }

  :global(.cluster-dots circle) {
    transition: opacity var(--transition-fast) ease-out;
  }

  .project-zone:hover :global(.cluster-dots circle) {
    opacity: 0.8 !important;
  }

  .project-active :global(.cluster-dots circle) {
    opacity: 1 !important;
  }

  .project-label {
    font-size: 10px;
    color: var(--text-tertiary);
    letter-spacing: 0.05em;
    line-height: 1;
    transition: color var(--transition-fast) ease-out;
  }

  .project-label-active {
    color: var(--text-primary);
  }

  /* Extract */
  .extract-zone {
    margin-bottom: 48px;
  }

  .extract-btn {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--accent-subtle);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
    text-decoration: none;
    transition: background var(--transition-fast) ease-out, box-shadow var(--transition-fast) ease-out;
  }

  .extract-btn:hover {
    background: var(--accent-glow);
    box-shadow: 0 0 8px rgba(232, 119, 46, 0.1);
  }

  .extract-active {
    background: var(--accent-glow);
    box-shadow: 0 0 8px rgba(232, 119, 46, 0.1);
  }

  .diamond-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    animation: diamond-drift 12s linear infinite;
  }

  .extract-btn:hover .diamond-icon {
    animation-duration: 4s;
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
    width: 200px;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
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
    transition: border-color 150ms, transform 150ms;
    padding: 0;
  }

  .create-swatch:hover {
    transform: scale(1.15);
  }

  .create-swatch.selected {
    border-color: var(--text-primary);
  }

  /* Drag and drop */
  .drag-over {
    position: relative;
  }

  .drag-over::before {
    content: '';
    position: absolute;
    top: -2px;
    left: 4px;
    right: 4px;
    height: 2px;
    background: var(--accent);
    border-radius: 1px;
  }
</style>

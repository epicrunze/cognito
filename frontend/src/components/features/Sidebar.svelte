<script lang="ts">
  import { page } from '$app/stores';
  import { projectsStore, tasksStore } from '$lib/stores.svelte';
  import { allTasksIcon, upcomingIcon, overdueIcon, extractIcon, settingsIcon } from '$lib/icons';
  import { registerRect } from '$lib/stores/sidebarRects.svelte';
  import Tip from '$components/ui/Tip.svelte';

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
  const isExtractPage = $derived(currentPath === '/extract');
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
          <a
            href="/project/{project.id}"
            class="project-zone"
            class:project-active={active}
            aria-label="{project.title} ({count} tasks)"
            onclick={() => handleProjectClick(project.id)}
            style="animation-delay: {idx * 50}ms;"
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
          </a>
        </Tip>
      {/each}
    {/if}
  </div>

  <div style="flex: 1;"></div>

  <!-- AI Extract -->
  <div class="extract-zone">
    <Tip text="AI Extract" side="right">
      <a href="/extract" class="extract-btn" class:extract-active={isExtractPage} aria-label="AI Extract">
        <span class="diamond-icon">
          {@html extractIcon}
        </span>
      </a>
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
</style>

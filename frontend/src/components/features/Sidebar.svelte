<script lang="ts">
  import { page } from '$app/stores';
  import { projectsStore, tasksStore, authStore } from '$lib/stores.svelte';
  import Tip from '$components/ui/Tip.svelte';

  let { collapsed = $bindable(false) }: { collapsed?: boolean } = $props();

  const nav = $derived([
    { id: '/', label: 'All Tasks', icon: '\u2630', path: '/', count: tasksStore.tasks.filter(t => !t.done).length },
    { id: '/upcoming', label: 'Upcoming', icon: '\u25F7', path: '/upcoming', count: tasksStore.tasks.filter(t => !t.done && t.due_date && new Date(t.due_date) > new Date()).length },
    { id: '/overdue', label: 'Overdue', icon: '!', path: '/overdue', count: tasksStore.tasks.filter(t => !t.done && t.due_date && new Date(t.due_date) < new Date()).length, countColor: 'var(--overdue)' },
  ]);

  const currentPath = $derived($page.url.pathname);
</script>

<div
  style="width: {collapsed ? 56 : 240}px; background: var(--bg-sidebar); border-right: 1px solid var(--border-subtle); display: flex; flex-direction: column; padding: {collapsed ? '16px 0 12px' : '20px 0'}; flex-shrink: 0; height: 100%; transition: width 200ms ease-out; overflow: {collapsed ? 'visible' : 'hidden'}; position: relative; z-index: 50;"
>
  <!-- Header -->
  <div style="padding: {collapsed ? '0' : '0 20px'}; margin-bottom: {collapsed ? 16 : 28}px; display: flex; align-items: center; justify-content: {collapsed ? 'center' : 'space-between'};">
    {#if !collapsed}
      <span style="font-size: 18px; font-weight: 600; letter-spacing: -0.03em; color: var(--text-primary);">cognito</span>
    {/if}
    <Tip text={collapsed ? 'Expand' : 'Collapse'} side={collapsed ? 'right' : 'top'}>
      <button
        onclick={() => collapsed = !collapsed}
        style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-tertiary); cursor: pointer; border-radius: 6px; font-size: 14px;"
      >
        {collapsed ? '\u00BB' : '\u00AB'}
      </button>
    </Tip>
  </div>

  <!-- Nav -->
  <div style="display: flex; flex-direction: column; gap: 2px; padding: 0 8px;">
    {#each nav as item (item.id)}
      {@const active = currentPath === item.path}
      {#if collapsed}
        <Tip text="{item.label} ({item.count})" side="right">
          <a href={item.path} class="snav-btn" class:snav-active={active} style="justify-content: center;">
            <span style="font-size: 15px; color: {active ? 'var(--accent)' : 'var(--text-secondary)'};">{item.icon}</span>
          </a>
        </Tip>
      {:else}
        <a href={item.path} class="snav-btn" class:snav-active={active}>
          <span style="font-size: 14px; font-weight: {active ? 500 : 400}; color: {active ? 'var(--accent)' : 'var(--text-secondary)'};">{item.label}</span>
          <span style="font-size: 12px; font-weight: 500; color: {item.countColor ?? 'var(--text-tertiary)'}; margin-left: auto;">{item.count}</span>
        </a>
      {/if}
    {/each}
  </div>

  <!-- Projects -->
  {#if !collapsed}
    <div style="padding: 0 20px; margin-top: 28px; margin-bottom: 10px;">
      <span style="font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.08em;">Projects</span>
    </div>
  {/if}
  <div style="display: flex; flex-direction: column; gap: 2px; padding: 0 8px; margin-top: {collapsed ? 16 : 0}px;">
    {#if projectsStore.loading}
      {#each [1, 2, 3] as _ (_)}
        <div class="snav-btn" style="height: 36px; opacity: 0.3;"></div>
      {/each}
    {:else}
      {#each projectsStore.projects as project (project.id)}
        {@const projectActive = currentPath === `/project/${project.id}`}
        {#if collapsed}
          <Tip text={project.title} side="right">
            <a href="/project/{project.id}" class="snav-btn" class:snav-active={projectActive} style="justify-content: center;" aria-label={project.title}>
              <div style="width: 10px; height: 10px; border-radius: 50%; background: {project.hex_color || 'var(--text-tertiary)'};"></div>
            </a>
          </Tip>
        {:else}
          <a href="/project/{project.id}" class="snav-btn" class:snav-active={projectActive}>
            <div style="width: 8px; height: 8px; border-radius: 50%; background: {project.hex_color || 'var(--text-tertiary)'}; flex-shrink: 0;"></div>
            <span style="font-size: 14px; color: var(--text-secondary); flex: 1; text-align: left;">{project.title}</span>
          </a>
        {/if}
      {/each}
    {/if}
  </div>

  <div style="flex: 1;"></div>

  <!-- AI Extract -->
  <div style="padding: 0 8px; margin-bottom: 4px;">
    {#if collapsed}
      <Tip text="AI Extract" side="right">
        <a href="/extract" class="snav-btn" style="justify-content: center; border: 1px solid rgba(232,119,46,0.19); background: var(--accent-subtle);">
          <span style="color: var(--accent); font-size: 16px; font-weight: 700;">&diams;</span>
        </a>
      </Tip>
    {:else}
      <a href="/extract" class="snav-btn" style="border: 1px solid rgba(232,119,46,0.19); background: var(--accent-subtle);">
        <span style="color: var(--accent); font-size: 14px; font-weight: 600;">&diams; AI Extract</span>
      </a>
    {/if}
  </div>

  <!-- Settings -->
  {#if collapsed}
    <div style="padding: 0 8px;">
      <Tip text="Settings" side="right">
        <a href="/settings" class="snav-btn" style="justify-content: center;">
          <span style="font-size: 15px; color: var(--text-tertiary);">&gear;</span>
        </a>
      </Tip>
    </div>
  {:else}
    <div style="padding: 0 8px;">
      <a href="/settings" class="snav-btn">
        <span style="font-size: 13px; color: var(--text-tertiary);">Settings</span>
      </a>
    </div>
    <div style="padding: 12px 20px; margin-top: 8px; border-top: 1px solid var(--border-subtle);">
      <span style="font-size: 13px; color: var(--text-tertiary);">{authStore.user?.email ?? ''}</span>
    </div>
  {/if}
</div>

<style>
  .snav-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-radius: 7px;
    border: none;
    background: transparent;
    cursor: pointer;
    transition: all 100ms ease-out;
    width: 100%;
    text-decoration: none;
  }
  .snav-btn:hover {
    background: var(--bg-surface-hover);
  }
  .snav-active {
    background: var(--accent-subtle);
  }
</style>

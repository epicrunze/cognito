<script lang="ts">
  import type { Snippet } from 'svelte';

  let {
    children,
    color = '',
    stats,
  }: {
    children: Snippet;
    color?: string;
    stats?: { total: number; done: number };
  } = $props();

  let hovering = $state(false);
  const bg = $derived(color ? `${color}20` : 'var(--bg-elevated)');
  const fg = $derived(color || 'var(--text-secondary)');
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<span
  class="relative inline-flex"
  role="group"
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
>
  <span
    style="display: inline-flex; align-items: center; height: 24px; padding: 0 9px; font-size: 12.5px; font-weight: 500; color: {fg}; background: {bg}; border-radius: 9999px; line-height: 1; white-space: nowrap; cursor: {stats ? 'default' : 'inherit'};"
  >
    {@render children()}
  </span>
  {#if stats && hovering}
    <div
      style="position: absolute; bottom: calc(100% + 6px); left: 50%; transform: translateX(-50%); background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: 8px; padding: 10px 14px; box-shadow: var(--shadow-md); z-index: 200; min-width: 170px; animation: fadeIn 100ms ease-out;"
    >
      <div style="font-size: 13px; font-weight: 600; color: {fg}; margin-bottom: 8px;">
        {@render children()}
      </div>
      {#each [['Total', stats.total], ['Done', stats.done], ['Open', stats.total - stats.done]] as [label, value] (label)}
        <div style="display: flex; justify-content: space-between; font-size: 12.5px; margin-bottom: 3px;">
          <span style="color: var(--text-tertiary);">{label}</span>
          <span style="color: var(--text-secondary); font-weight: 500;">{value}</span>
        </div>
      {/each}
      <div style="height: 1px; background: var(--border-default); margin: 5px 0;"></div>
      <div style="display: flex; justify-content: space-between; font-size: 12.5px;">
        <span style="color: var(--text-tertiary);">Completion</span>
        <span style="color: var(--done); font-weight: 500;">{Math.round((stats.done / stats.total) * 100)}%</span>
      </div>
      <div style="position: absolute; bottom: -4px; left: 50%; transform: translateX(-50%) rotate(45deg); width: 7px; height: 7px; background: var(--bg-elevated); border-right: 1px solid var(--border-strong); border-bottom: 1px solid var(--border-strong);"></div>
    </div>
  {/if}
</span>

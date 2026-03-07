<script lang="ts">
  import type { Snippet } from 'svelte';

  let {
    text,
    children,
    side = 'top',
  }: {
    text: string;
    children: Snippet;
    side?: 'top' | 'right';
  } = $props();

  let hovering = $state(false);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<span
  class="relative inline-flex"
  role="tooltip"
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
>
  {@render children()}
  {#if hovering}
    <span
      style="position: absolute; {side === 'right' ? 'left: calc(100% + 8px); top: 50%; transform: translateY(-50%);' : 'bottom: calc(100% + 6px); left: 50%; transform: translateX(-50%);'} background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: 6px; padding: 5px 10px; font-size: 12px; color: var(--text-secondary); white-space: nowrap; z-index: 300; box-shadow: var(--shadow-md); animation: fadeIn 100ms ease-out;"
    >
      {text}
      <span
        style="position: absolute; width: 7px; height: 7px; background: var(--bg-elevated); {side === 'right' ? 'left: -4px; top: 50%; transform: translateY(-50%) rotate(45deg); border-left: 1px solid var(--border-strong); border-bottom: 1px solid var(--border-strong); border-right: none; border-top: none;' : 'bottom: -4px; left: 50%; transform: translateX(-50%) rotate(45deg); border-right: 1px solid var(--border-strong); border-bottom: 1px solid var(--border-strong); border-left: none; border-top: none;'}"
      ></span>
    </span>
  {/if}
</span>

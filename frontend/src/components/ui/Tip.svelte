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
  let ref: HTMLSpanElement | undefined = $state();
  let tipLeft = $state(0);
  let tipTop = $state(0);

  $effect(() => {
    if (hovering && ref) {
      const rect = ref.getBoundingClientRect();
      if (side === 'right') {
        tipLeft = rect.right + 8;
        tipTop = rect.top + rect.height / 2;
      } else {
        tipLeft = rect.left + rect.width / 2;
        tipTop = rect.top - 6;
      }
    }
  });

  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
      destroy() {
        node.remove();
      }
    };
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<span
  bind:this={ref}
  class="relative inline-flex"
  role="tooltip"
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
>
  {@render children()}
  {#if hovering}
    <span
      use:portal
      style="position: fixed; left: {tipLeft}px; top: {tipTop}px; {side === 'right' ? 'transform: translateY(-50%);' : 'transform: translate(-50%, -100%);'} background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: 6px; padding: 5px 10px; font-size: 12px; color: var(--text-secondary); white-space: nowrap; z-index: 9999; box-shadow: var(--shadow-md); animation: fadeIn 100ms ease-out; pointer-events: none;"
    >
      {text}
      <span
        style="position: absolute; width: 7px; height: 7px; background: var(--bg-elevated); {side === 'right' ? 'left: -4px; top: 50%; transform: translateY(-50%) rotate(45deg); border-left: 1px solid var(--border-strong); border-bottom: 1px solid var(--border-strong); border-right: none; border-top: none;' : 'bottom: -4px; left: 50%; transform: translateX(-50%) rotate(45deg); border-right: 1px solid var(--border-strong); border-bottom: 1px solid var(--border-strong); border-left: none; border-top: none;'}"
      ></span>
    </span>
  {/if}
</span>

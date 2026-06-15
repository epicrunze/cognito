<script lang="ts">
  import type { Snippet } from 'svelte';
  import { panelFly, backdropFade, DURATION } from '$lib/transitions';

  let {
    open = false,
    onclose,
    width = 480,
    children,
  }: {
    open: boolean;
    onclose?: () => void;
    width?: number;
    children: Snippet;
  } = $props();

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      const el = document.activeElement;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
        (el as HTMLElement).blur();
        return;
      }
      onclose?.();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <!-- Backdrop -->
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    role="presentation"
    transition:backdropFade={{ duration: DURATION.slow }}
    onclick={onclose}
    style="position: fixed; inset: 0; background: var(--bg-overlay); z-index: 100;"
  ></div>

  <!-- Panel — shares the backdrop's duration so they finish together. -->
  <div
    class="slide-panel"
    transition:panelFly={{ x: width }}
    style="width: {width}px;"
  >
    {@render children()}
  </div>
{/if}

<style>
  .slide-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    max-width: 100vw;
    background: var(--bg-surface);
    border-left: 1px solid var(--border-default);
    box-shadow: var(--shadow-slide-over);
    z-index: 101;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  @media (max-width: 767px) {
    .slide-panel {
      width: 100vw !important;
    }
  }
</style>

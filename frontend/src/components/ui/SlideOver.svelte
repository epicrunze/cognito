<script lang="ts">
  import type { Snippet } from 'svelte';
  import { fly, fade } from 'svelte/transition';

  let {
    open = false,
    onclose,
    children,
  }: {
    open: boolean;
    onclose?: () => void;
    children: Snippet;
  } = $props();

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onclose?.();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <!-- Backdrop -->
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    role="presentation"
    transition:fade={{ duration: 200 }}
    onclick={onclose}
    style="position: fixed; inset: 0; background: var(--bg-overlay); z-index: 100;"
  ></div>

  <!-- Panel -->
  <div
    transition:fly={{ x: 480, duration: 300 }}
    style="position: fixed; top: 0; right: 0; bottom: 0; width: 480px; max-width: 100vw; background: var(--bg-surface); border-left: 1px solid var(--border-default); box-shadow: var(--shadow-slide-over); z-index: 101; overflow-y: auto;"
  >
    {@render children()}
  </div>
{/if}

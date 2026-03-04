<script lang="ts">
  import type { Snippet } from 'svelte';
  import { fly, fade } from 'svelte/transition';

  let {
    open = false,
    onclose,
    children,
  }: {
    open?: boolean;
    onclose?: () => void;
    children: Snippet;
  } = $props();

  $effect(() => {
    if (!open) return;

    document.body.style.overflow = 'hidden';

    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onclose?.();
    };
    window.addEventListener('keydown', handleKeydown);

    return () => {
      window.removeEventListener('keydown', handleKeydown);
      document.body.style.overflow = '';
    };
  });
</script>

{#if open}
  <button
    type="button"
    class="fixed inset-0 bg-overlay z-40 cursor-default p-0 border-0 w-full"
    transition:fade={{ duration: 200 }}
    onclick={onclose}
    aria-label="Close panel"
    tabindex="-1"
  ></button>
  <div
    class="fixed right-0 top-0 w-detail-panel h-full bg-surface shadow-slide-over z-50 overflow-y-auto"
    transition:fly={{ x: 480, duration: 200 }}
    role="dialog"
    aria-modal="true"
  >
    {@render children()}
  </div>
{/if}

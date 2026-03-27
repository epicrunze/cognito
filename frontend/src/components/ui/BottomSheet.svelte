<script lang="ts">
  import type { Snippet } from 'svelte';
  import { fade } from 'svelte/transition';
  import { DURATION } from '$lib/transitions';

  let {
    open = false,
    onclose,
    snapPoints = [0.5, 1] as number[],
    initialSnap = 0,
    children,
  }: {
    open: boolean;
    onclose?: () => void;
    snapPoints?: number[];
    initialSnap?: number;
    children: Snippet;
  } = $props();

  let sheetEl = $state<HTMLDivElement | null>(null);
  let dragging = $state(false);
  let currentY = $state(0);
  let startY = 0;
  let startSheetY = 0;
  let activeSnapIndex = $state(0);
  let viewportHeight = $state(typeof window !== 'undefined' ? window.innerHeight : 812);

  // The sheet position from bottom (0 = closed, viewportHeight = full screen)
  const sheetHeight = $derived(snapPoints[activeSnapIndex] * viewportHeight);
  const translateY = $derived(dragging ? currentY : viewportHeight - sheetHeight);

  $effect(() => {
    if (open) {
      activeSnapIndex = initialSnap;
      currentY = viewportHeight - snapPoints[initialSnap] * viewportHeight;
    }
  });

  function handleTouchStart(e: TouchEvent) {
    const touch = e.touches[0];
    startY = touch.clientY;
    startSheetY = translateY;
    dragging = true;
  }

  function handleTouchMove(e: TouchEvent) {
    if (!dragging) return;
    e.preventDefault();
    const touch = e.touches[0];
    const delta = touch.clientY - startY;
    // Clamp: don't go above full height, allow going below to dismiss
    const newY = Math.max(0, startSheetY + delta);
    currentY = newY;
  }

  function handleTouchEnd() {
    if (!dragging) return;
    dragging = false;

    const currentFraction = 1 - (currentY / viewportHeight);

    // If dragged below 15% of viewport, dismiss
    if (currentFraction < 0.15) {
      onclose?.();
      return;
    }

    // Snap to nearest snap point
    let closestIndex = 0;
    let closestDist = Infinity;
    for (let i = 0; i < snapPoints.length; i++) {
      const dist = Math.abs(currentFraction - snapPoints[i]);
      if (dist < closestDist) {
        closestDist = dist;
        closestIndex = i;
      }
    }
    activeSnapIndex = closestIndex;
    currentY = viewportHeight - snapPoints[closestIndex] * viewportHeight;
  }

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

  function handleResize() {
    viewportHeight = window.innerHeight;
  }
</script>

<svelte:window onkeydown={handleKeydown} onresize={handleResize} />

{#if open}
  <!-- Backdrop -->
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="sheet-backdrop"
    role="presentation"
    transition:fade={{ duration: DURATION.normal }}
    onclick={onclose}
  ></div>

  <!-- Sheet -->
  <div
    class="sheet"
    class:sheet-dragging={dragging}
    bind:this={sheetEl}
    style="transform: translateY({translateY}px);"
  >
    <!-- Drag handle -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="sheet-handle"
      ontouchstart={handleTouchStart}
      ontouchmove={handleTouchMove}
      ontouchend={handleTouchEnd}
    >
      <div class="sheet-handle-bar"></div>
    </div>

    <!-- Content -->
    <div class="sheet-content">
      {@render children()}
    </div>
  </div>
{/if}

<style>
  .sheet-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.32);
    z-index: 150;
  }

  .sheet {
    position: fixed;
    left: 0;
    right: 0;
    top: 0;
    height: 100vh;
    z-index: 151;
    background: var(--bg-surface);
    border-radius: 16px 16px 0 0;
    box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.4);
    display: flex;
    flex-direction: column;
    transition: transform 300ms cubic-bezier(0.32, 0.72, 0, 1);
    will-change: transform;
  }

  .sheet-dragging {
    transition: none;
  }

  .sheet-handle {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 12px 0 8px;
    cursor: grab;
    flex-shrink: 0;
    touch-action: none;
  }

  .sheet-handle:active {
    cursor: grabbing;
  }

  .sheet-handle-bar {
    width: 36px;
    height: 4px;
    border-radius: 2px;
    background: var(--border-strong);
    opacity: 0.5;
  }

  .sheet-content {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    min-height: 0;
    -webkit-overflow-scrolling: touch;
  }
</style>

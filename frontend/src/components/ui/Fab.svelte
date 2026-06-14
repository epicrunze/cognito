<script lang="ts">
  // Instant thought capture. variant 'plus' = solid tangerine disc with a dark +
  // (reads "add"); variant 'brand' = the constellation mark on a dark disc with a
  // small tangerine + badge (capture framed as adding a star to your constellation).
  let {
    onclick,
    variant = 'plus',
    label = 'New thought',
    size,
  }: {
    onclick?: () => void;
    variant?: 'plus' | 'brand';
    label?: string;
    size?: number;
  } = $props();

  const d = $derived(size ?? (variant === 'brand' ? 60 : 52));
</script>

{#if variant === 'brand'}
  <button class="fab brand" aria-label={label} {onclick} style="width: {d}px; height: {d}px;">
    <svg width={d * 0.56} height={d * 0.56} viewBox="0 0 40 40" fill="none" style="display: block;">
      <circle cx="13" cy="11" r="4.5" fill="var(--tangerine)" />
      <circle cx="27" cy="9" r="3" fill="var(--tangerine)" />
      <circle cx="11" cy="27" r="3" fill="var(--tangerine)" />
      <circle cx="29" cy="25" r="4.5" fill="var(--tangerine)" />
    </svg>
    <span class="badge" style="width: {d * 0.37}px; height: {d * 0.37}px;">
      <svg width={d * 0.2} height={d * 0.2} viewBox="0 0 11 11" fill="none"><path d="M5.5 1.5v8M1.5 5.5h8" stroke="var(--text-on-accent)" stroke-width="1.8" stroke-linecap="round" /></svg>
    </span>
  </button>
{:else}
  <button class="fab plus" aria-label={label} {onclick} style="width: {d}px; height: {d}px;">
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none"><path d="M11 4.5V17.5M4.5 11H17.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
  </button>
{/if}

<style>
  .fab {
    border-radius: 50%;
    cursor: pointer;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--shadow-hover);
    transition: all var(--t-fast) var(--ease-out);
  }
  .fab:hover {
    box-shadow: var(--shadow-lift);
  }
  .fab.plus {
    border: none;
    background: var(--action-bg);
    color: var(--text-on-accent);
  }
  .fab.plus:hover {
    background: var(--action-bg-hover);
  }
  .fab.brand {
    position: relative;
    background: var(--surface-card);
    border: 1.5px solid var(--border-strong);
  }
  .fab.brand:hover {
    background: var(--surface-card-hover);
  }
  .badge {
    position: absolute;
    right: -2px;
    bottom: -2px;
    border-radius: 50%;
    background: var(--tangerine);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--shadow-rest);
  }
</style>

<script lang="ts">
  // Quick PERSPECTIVE switches over a single dataset (All / Today / Overdue;
  // Open / Notes / History). The third navigation species — underline tabs,
  // lightest weight, for top-of-screen lenses. Exactly one active; optional count.
  type Lens = { value: string; label: string; count?: number };
  let {
    lenses,
    value,
    onchange,
    gap = 16,
  }: {
    lenses: Lens[];
    value: string;
    onchange?: (value: string) => void;
    gap?: number;
  } = $props();
</script>

<div class="lens-tabs" role="tablist" style="gap: {gap}px;">
  {#each lenses as l (l.value)}
    <button
      role="tab"
      aria-selected={l.value === value}
      class:active={l.value === value}
      onclick={() => onchange?.(l.value)}
    >
      {l.label}
      {#if l.count != null}<span class="count">{l.count}</span>{/if}
    </button>
  {/each}
</div>

<style>
  .lens-tabs {
    display: flex;
    align-items: center;
  }
  .lens-tabs button {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0 0 3px;
    font: var(--type-data);
    font-size: var(--text-xs);
    letter-spacing: var(--tracking-mono);
    color: var(--text-tertiary);
    border-bottom: 1.5px solid transparent;
    transition: color var(--t-fast) var(--ease-out), border-color var(--t-fast) var(--ease-out);
    min-height: 28px;
  }
  .lens-tabs button.active {
    color: var(--text-primary);
    border-bottom-color: var(--tangerine);
  }
  .count {
    font-size: var(--text-2xs);
    color: var(--text-tertiary);
    opacity: 0.7;
  }
</style>

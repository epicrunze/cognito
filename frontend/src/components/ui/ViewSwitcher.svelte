<script lang="ts">
  // EXCLUSIVE view selection (Bubbles / Kanban / List / …). A connected
  // segmented control on a sunken track; the active segment is tangerine-subtle.
  // Visually distinct from FilterChip (modifiers) and LensTabs (perspectives).
  type View = { value: string; label: string };
  let {
    views,
    value,
    onchange,
  }: {
    views: View[];
    value: string;
    onchange?: (value: string) => void;
  } = $props();
</script>

<div class="view-switcher" role="tablist">
  {#each views as v (v.value)}
    <button
      role="tab"
      aria-selected={v.value === value}
      class:active={v.value === value}
      onclick={() => onchange?.(v.value)}
    >{v.label}</button>
  {/each}
</div>

<style>
  .view-switcher {
    display: inline-flex;
    gap: 2px;
    padding: 3px;
    background: var(--bg-base);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-inner);
  }
  .view-switcher button {
    height: 26px;
    padding: 0 12px;
    font: var(--type-ui);
    font-size: var(--text-xs);
    border-radius: 4px;
    border: none;
    cursor: pointer;
    background: transparent;
    color: var(--text-secondary);
    font-weight: var(--font-normal);
    transition-property: background-color, border-color, color, box-shadow, transform, opacity; transition-duration: var(--t-fast); transition-timing-function: var(--ease-out);
  }
  .view-switcher button.active {
    background: var(--selected-tint);
    color: var(--tangerine);
    font-weight: var(--font-medium);
  }
</style>

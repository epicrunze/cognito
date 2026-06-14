<script module lang="ts">
  // Five segments — none → low → medium → high → urgent. Numeric values bridge
  // to the app's priority ints (Vikunja: 1=low … 5=urgent; 0=none). low maps to
  // 1 so the meter stays a single continuous vocabulary.
  const LEVELS = [
    { value: 0, color: 'var(--priority-none)', label: 'none' },
    { value: 1, color: 'var(--low)', label: 'low' },
    { value: 3, color: 'var(--medium)', label: 'medium' },
    { value: 4, color: 'var(--high)', label: 'high' },
    { value: 5, color: 'var(--urgent)', label: 'urgent' },
  ];

  // Map an arbitrary priority int to a segment index (1 and 2 both read "low").
  function indexForValue(v: number): number {
    if (v <= 0) return 0;
    if (v <= 2) return 1;
    if (v === 3) return 2;
    if (v === 4) return 3;
    return 4;
  }
</script>

<script lang="ts">
  let {
    value = 0,
    onchange,
    showLabel = true,
    segWidth = 22,
  }: {
    value?: number;
    onchange?: (value: number) => void;
    showLabel?: boolean;
    segWidth?: number;
  } = $props();

  const idx = $derived(indexForValue(value));

  // Hover previews the level the cursor is over; reverts on leave.
  let hovered = $state<number | null>(null);
  const effIdx = $derived(hovered ?? idx);
  const effColor = $derived(LEVELS[effIdx].color);
  const effLabel = $derived(LEVELS[effIdx].label);
</script>

<div class="priority-meter" role="radiogroup" aria-label="Priority" tabindex="-1" onmouseleave={() => (hovered = null)}>
  <div class="segments">
    {#each LEVELS as lvl, i (lvl.label)}
      {@const isNone = i === 0}
      {@const filled = effIdx >= 1 && i <= effIdx}
      {@const noneEmptyActive = isNone && effIdx === 0}
      <button
        type="button"
        role="radio"
        aria-checked={idx === i}
        aria-label={lvl.label}
        title={lvl.label}
        class:previewing={hovered != null}
        onmouseenter={() => (hovered = i)}
        onclick={(e) => { e.stopPropagation(); onchange?.(lvl.value); }}
        style="
          width: {segWidth}px;
          background: {filled ? effColor : 'transparent'};
          border: {filled
            ? 'none'
            : isNone
              ? `1.5px ${noneEmptyActive ? 'solid var(--text-tertiary)' : 'dashed var(--border-strong)'}`
              : '1.5px solid var(--surface-3)'};
        "
      ></button>
    {/each}
  </div>
  {#if showLabel}
    <span class="meter-label" style="color: {effIdx === 0 ? 'var(--text-tertiary)' : effColor};">{effLabel}</span>
  {/if}
</div>

<style>
  .priority-meter {
    display: inline-flex;
    align-items: center;
    gap: 10px;
  }
  .segments {
    display: inline-flex;
    gap: 4px;
  }
  .segments button {
    height: 10px;
    border-radius: 3px;
    padding: 0;
    cursor: pointer;
    box-sizing: border-box;
    transition: background var(--t-fast) var(--ease-out), border-color var(--t-fast) var(--ease-out), transform var(--t-fast) var(--ease-out);
  }
  /* Lift the segment under the cursor while previewing. */
  .segments button.previewing:hover {
    transform: translateY(-1px);
  }
  .meter-label {
    font: var(--type-data);
    text-transform: uppercase;
    letter-spacing: var(--tracking-mono);
    min-width: 52px;
  }
</style>

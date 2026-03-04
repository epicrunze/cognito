<script lang="ts">
  const PRIORITY_LABELS = ['None', 'Low', 'Low', 'Medium', 'High', 'Urgent'];
  const PRIORITY_COLORS: Record<number, string> = {
    0: 'var(--priority-none)',
    1: 'var(--priority-low)',
    2: 'var(--priority-low)',
    3: 'var(--priority-medium)',
    4: 'var(--priority-high)',
    5: 'var(--priority-urgent)',
  };

  let {
    priority = 0,
    interactive = false,
    onchange,
    ...restProps
  }: {
    priority?: number;
    interactive?: boolean;
    onchange?: (p: number) => void;
    [key: string]: unknown;
  } = $props();
</script>

<span
  class="inline-flex items-center gap-0.5"
  title={interactive ? undefined : PRIORITY_LABELS[priority] ?? 'None'}
  {...restProps}
>
  {#each [1, 2, 3, 4, 5] as n}
    {#if interactive}
      <button
        type="button"
        class="w-1.5 h-1.5 rounded-full cursor-pointer p-0 border-0"
        style="background-color: {n <= priority ? PRIORITY_COLORS[priority] : 'var(--border-default)'}"
        onclick={() => onchange?.(n)}
        title={PRIORITY_LABELS[n]}
        aria-label="Set priority to {PRIORITY_LABELS[n]}"
      ></button>
    {:else}
      <span
        class="w-1.5 h-1.5 rounded-full"
        style="background-color: {n <= priority ? PRIORITY_COLORS[priority] : 'var(--border-default)'}"
      ></span>
    {/if}
  {/each}
</span>

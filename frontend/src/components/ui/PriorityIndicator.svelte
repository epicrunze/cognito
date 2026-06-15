<script lang="ts">
  let { level = 3, size = 'md' }: { level?: number; size?: 'sm' | 'md' } = $props();
  const dotSize = $derived(size === 'sm' ? 7 : 8);
  const colors = ['var(--priority-none)', 'var(--priority-low)', 'var(--priority-low)', 'var(--priority-medium)', 'var(--priority-high)', 'var(--priority-urgent)'];
  const activeColor = $derived(colors[level] ?? colors[0]);
</script>

<div class="flex items-center" style="gap: 3px;">
  {#each [1, 2, 3, 4, 5] as i (i)}
    <div
      style="width: {dotSize}px; height: {dotSize}px; border-radius: 50%; background: {i <= level ? activeColor : 'var(--border-default)'}; transition-property: background-color, border-color, color, box-shadow, transform, opacity; transition-duration: var(--t-fast); transition-timing-function: var(--ease-out);"
    ></div>
  {/each}
</div>

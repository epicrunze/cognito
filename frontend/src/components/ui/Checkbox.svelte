<script lang="ts">
  let { checked = false, onchange, size = 20 }: { checked?: boolean; onchange?: (v: boolean) => void; size?: number } = $props();
  let hovering = $state(false);
</script>

<button
  type="button"
  onclick={() => onchange?.(!checked)}
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
  style="width: {size}px; height: {size}px; border-radius: 3px; border: {checked ? 'none' : `1.5px solid ${hovering ? 'var(--text-tertiary)' : 'var(--border-strong)'}`}; background: {checked ? 'var(--done)' : hovering ? 'var(--bg-surface-hover)' : 'transparent'}; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all var(--transition-normal) ease-out; padding: 0; flex-shrink: 0;"
>
  {#if checked}
    <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
      <path d="M2.5 6L4.5 8L8.5 3.5" stroke="var(--bg-base)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  {/if}
</button>

<script lang="ts">
  import type { Snippet } from 'svelte';
  let { children }: { children: Snippet } = $props();
</script>

<kbd class="inline-flex items-center justify-center font-mono" style="min-width: 22px; height: 22px; padding: 0 6px; font-size: 11.5px; font-weight: 500; color: var(--text-tertiary); background: var(--bg-elevated); border: 1px solid var(--border-default); border-radius: 5px; line-height: 1;">
  {@render children()}
</kbd>

<script lang="ts">
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();
</script>

<kbd class="font-mono text-xs px-1.5 py-0.5 rounded-input border border-default bg-surface-hover text-tertiary inline">
  {@render children()}
</kbd>

<script lang="ts">
  import { formatRelativeDate } from '$lib/dateUtils';
  let { date, overdue = false }: { date: string | null; overdue?: boolean } = $props();
</script>

{#if date}
  <span style="font-size: 13.5px; font-weight: 400; white-space: nowrap; color: {overdue ? 'var(--overdue)' : 'var(--text-tertiary)'};">
    {formatRelativeDate(date)}
  </span>
{/if}

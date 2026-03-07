<script lang="ts">
  let { date, overdue = false }: { date: string | null; overdue?: boolean } = $props();

  function formatRelative(dateStr: string | null): string {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const target = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const diffDays = Math.round((target.getTime() - today.getTime()) / 86400000);
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays === -1) return 'Yesterday';
    if (diffDays > 1 && diffDays <= 7) return `In ${diffDays} days`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
</script>

{#if date}
  <span style="font-size: 13.5px; font-weight: 400; white-space: nowrap; color: {overdue ? 'var(--overdue)' : 'var(--text-tertiary)'};">
    {formatRelative(date)}
  </span>
{/if}

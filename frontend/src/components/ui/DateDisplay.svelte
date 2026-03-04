<script lang="ts">
  let {
    date,
    ...restProps
  }: {
    date: string;
    [key: string]: unknown;
  } = $props();

  function formatDate(dateStr: string): { display: string; overdue: boolean } {
    if (!dateStr) return { display: '', overdue: false };

    const parsed = new Date(dateStr);
    const now = new Date();

    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const target = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());

    const diffMs = target.getTime() - today.getTime();
    const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

    const overdue = diffDays < 0;

    let display: string;
    if (diffDays === 0) {
      display = 'Today';
    } else if (diffDays === 1) {
      display = 'Tomorrow';
    } else if (diffDays === -1) {
      display = 'Yesterday';
    } else if (diffDays >= 2 && diffDays <= 6) {
      display = target.toLocaleDateString('en-US', { weekday: 'long' });
    } else if (target.getFullYear() === today.getFullYear()) {
      display = target.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else {
      display = target.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    return { display, overdue };
  }

  const formatted = $derived(formatDate(date));
</script>

<time
  datetime={date}
  title={date}
  class="text-sm"
  style={formatted.overdue ? 'color: var(--overdue)' : ''}
  {...restProps}
>
  {formatted.display}
</time>

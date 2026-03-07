<script lang="ts">
  let {
    message,
    variant = 'success',
    onclose,
  }: {
    message: string;
    variant?: 'success' | 'error' | 'info';
    onclose?: () => void;
  } = $props();

  const icons: Record<string, string> = { success: '\u2713', error: '\u2715', info: '\u2192' };
  const colors: Record<string, string> = { success: 'var(--done)', error: 'var(--overdue)', info: 'var(--accent)' };
</script>

<div style="display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; box-shadow: var(--shadow-md); font-size: 14px; color: var(--text-primary); min-width: 280px; animation: slideUp 200ms ease-out;">
  <span style="width: 22px; height: 22px; border-radius: 50%; background: {colors[variant]}18; color: {colors[variant]}; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0;">
    {icons[variant]}
  </span>
  <span style="flex: 1;">{message}</span>
  <button onclick={onclose} style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 16px; padding: 0; line-height: 1;">
    &times;
  </button>
</div>

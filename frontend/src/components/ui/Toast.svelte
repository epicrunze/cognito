<script lang="ts">
  import type { ToastAction } from '$lib/stores/toast.svelte';

  let {
    message,
    variant = 'success',
    ai = false,
    action,
    onclose,
  }: {
    message: string;
    variant?: 'success' | 'error' | 'info';
    ai?: boolean;
    action?: ToastAction;
    onclose?: () => void;
  } = $props();

  const toneColors: Record<string, string> = {
    success: 'var(--done)',
    error: 'var(--danger)',
    info: 'var(--info)',
  };
</script>

<div class="toast" role="status">
  {#if ai}
    <svg class="diamond" width="10" height="10" viewBox="0 0 10 10"><rect x="2.2" y="2.2" width="5.6" height="5.6" fill="none" stroke="var(--ai)" stroke-width="1.2" transform="rotate(45 5 5)"></rect></svg>
  {:else}
    <span class="dot" style="background: {toneColors[variant]};"></span>
  {/if}
  <span class="msg">{message}</span>
  {#if action}
    <button class="action" onclick={() => { action.onClick(); onclose?.(); }}>{action.label}</button>
  {/if}
</div>

<style>
  .toast {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 11px 16px;
    background: var(--surface-popover);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-inner);
    box-shadow: var(--shadow-popover);
    font: var(--type-ui);
    color: var(--text-primary);
    animation: slideUp var(--t-slow) var(--ease-out);
    min-width: 240px;
  }
  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .diamond {
    flex-shrink: 0;
  }
  .msg {
    flex: 1;
  }
  .action {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--tangerine);
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    letter-spacing: var(--tracking-mono);
    padding: 0 2px;
    flex-shrink: 0;
  }
</style>

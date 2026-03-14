<script lang="ts">
  import type { Snippet } from 'svelte';

  let {
    children,
    variant = 'accent',
    size = 'md',
    loading = false,
    disabled = false,
    onclick,
    style = '',
    type = 'button',
  }: {
    children: Snippet;
    variant?: 'accent' | 'outline' | 'ghost' | 'danger' | 'toggle';
    size?: 'sm' | 'md';
    loading?: boolean;
    disabled?: boolean;
    onclick?: (e: MouseEvent) => void;
    style?: string;
    type?: 'button' | 'submit';
  } = $props();

  let hovering = $state(false);

  const s = $derived(size === 'sm' ? { h: 34, p: '0 14px', fs: 13.5 } : { h: 40, p: '0 18px', fs: 14 });

  type VariantStyle = { bg: string; bgH: string; c: string; cH: string; b: string; bH: string };
  const variants: Record<string, VariantStyle> = {
    accent: { bg: 'var(--accent)', bgH: 'var(--accent-hover)', c: 'var(--text-on-accent)', cH: 'var(--text-on-accent)', b: 'none', bH: 'none' },
    outline: { bg: 'transparent', bgH: 'var(--bg-surface-hover)', c: 'var(--text-secondary)', cH: 'var(--text-primary)', b: '1px solid var(--border-default)', bH: '1px solid var(--border-strong)' },
    ghost: { bg: 'transparent', bgH: 'var(--bg-surface-hover)', c: 'var(--text-secondary)', cH: 'var(--text-primary)', b: '1px solid transparent', bH: '1px solid transparent' },
    danger: { bg: 'transparent', bgH: '#DC2626', c: 'var(--overdue)', cH: '#fff', b: '1px solid var(--border-strong)', bH: '1px solid #DC2626' },
    toggle: { bg: 'var(--bg-elevated)', bgH: 'var(--bg-surface-hover)', c: 'var(--text-secondary)', cH: 'var(--text-secondary)', b: '1px solid var(--border-default)', bH: '1px solid var(--border-default)' },
  };

  const v = $derived(variants[variant]);
  const bg = $derived(hovering && !disabled ? v.bgH : v.bg);
  const color = $derived(hovering && !disabled ? v.cH : v.c);
  const border = $derived(hovering && !disabled ? v.bH : v.b);
</script>

<button
  {type}
  {onclick}
  disabled={disabled || loading}
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
  style="height: {s.h}px; padding: {s.p}; font-size: {s.fs}px; font-weight: 500; font-family: var(--font-sans); background: {bg}; color: {color}; border: {border}; border-radius: 8px; cursor: {disabled ? 'not-allowed' : 'pointer'}; opacity: {disabled ? 0.4 : 1}; display: inline-flex; align-items: center; gap: 7px; flex-shrink: 0; transition: all var(--transition-fast) ease-out; line-height: 1; letter-spacing: -0.01em; white-space: nowrap; {style}"
>
  {#if loading}
    <span style="display: inline-flex; animation: spin 0.8s linear infinite;">
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
        <circle cx="7.5" cy="7.5" r="6" stroke="currentColor" stroke-width="1.5" opacity="0.25" />
        <path d="M13.5 7.5a6 6 0 0 0-6-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
      </svg>
    </span>
  {/if}
  {@render children()}
</button>

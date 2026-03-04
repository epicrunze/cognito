<script lang="ts">
  import type { Snippet } from 'svelte';

  type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info';
  type Size = 'sm' | 'md';

  let {
    variant = 'default' as Variant,
    size = 'md' as Size,
    color,
    children,
  }: {
    variant?: Variant;
    size?: Size;
    color?: string;
    children: Snippet;
  } = $props();

  const variantStyles: Record<Variant, string> = {
    default: `background-color: var(--bg-surface-hover); color: var(--text-secondary);`,
    success: `background-color: rgba(34,197,94,0.1); color: var(--done);`,
    warning: `background-color: rgba(234,179,8,0.1); color: var(--priority-medium);`,
    danger: `background-color: rgba(239,68,68,0.1); color: var(--priority-urgent);`,
    info: `background-color: rgba(99,102,241,0.1); color: var(--accent);`,
  };

  const sizeClasses: Record<Size, string> = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
  };

  const inlineStyle = $derived(
    color
      ? `background-color: ${color}20; color: ${color};`
      : variantStyles[variant]
  );
</script>

<span
  class="rounded-pill font-medium inline-flex items-center {sizeClasses[size]}"
  style={inlineStyle}
>
  {@render children()}
</span>

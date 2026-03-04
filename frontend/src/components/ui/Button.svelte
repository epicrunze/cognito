<script lang="ts">
  import type { Snippet } from 'svelte';

  type Variant = 'accent' | 'outline' | 'ghost';
  type Size = 'sm' | 'md';
  type ButtonType = 'button' | 'submit' | 'reset';

  let {
    variant = 'accent' as Variant,
    size = 'md' as Size,
    loading = false,
    disabled = false,
    type = 'button' as ButtonType,
    onclick,
    children,
    ...restProps
  }: {
    variant?: Variant;
    size?: Size;
    loading?: boolean;
    disabled?: boolean;
    type?: ButtonType;
    onclick?: (e: MouseEvent) => void;
    children: Snippet;
    [key: string]: unknown;
  } = $props();

  const variantClasses: Record<Variant, string> = {
    accent: 'bg-accent text-on-accent hover:bg-accent-hover',
    outline: 'bg-transparent border border-default text-primary hover:bg-surface-hover',
    ghost: 'bg-transparent text-secondary hover:bg-surface-hover hover:text-primary',
  };

  const sizeClasses: Record<Size, string> = {
    sm: 'h-7 px-2 py-1 text-sm',
    md: 'h-9 px-4 py-2 text-base',
  };
</script>

<button
  {type}
  disabled={disabled || loading}
  {onclick}
  class="rounded-input font-medium duration-fast inline-flex items-center justify-center gap-1.5
    {variantClasses[variant]}
    {sizeClasses[size]}
    {disabled || loading ? 'opacity-50 cursor-not-allowed' : ''}"
  {...restProps}
>
  {#if loading}
    <svg
      class="animate-spin w-4 h-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  {/if}
  {@render children()}
</button>

<script lang="ts">
  type Variant = 'success' | 'error' | 'info';

  let {
    variant = 'info' as Variant,
    message,
    ondismiss,
  }: {
    variant?: Variant;
    message: string;
    ondismiss?: () => void;
  } = $props();

  const dotColor: Record<Variant, string> = {
    success: 'bg-done',
    error: 'bg-overdue',
    info: 'bg-accent',
  };
</script>

<div class="flex items-center gap-3 px-4 py-3 rounded-container shadow-md bg-surface border border-default min-w-64 max-w-sm">
  <span class="w-2 h-2 rounded-full flex-shrink-0 {dotColor[variant]}"></span>
  <span class="text-sm text-primary flex-1">{message}</span>
  {#if ondismiss}
    <button
      type="button"
      class="text-tertiary hover:text-primary duration-fast ml-1 leading-none text-base"
      onclick={ondismiss}
      aria-label="Dismiss"
    >
      ×
    </button>
  {/if}
</div>

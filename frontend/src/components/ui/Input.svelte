<script lang="ts">
  let {
    error,
    value = $bindable(''),
    ...restProps
  }: {
    error?: string;
    value?: string;
    [key: string]: unknown;
  } = $props();

  const baseClasses =
    'w-full h-9 px-3 text-base bg-surface border rounded-input text-primary placeholder:text-tertiary duration-fast outline-none';

  const normalClasses = 'border-default focus:border-accent focus:ring-1 focus:ring-accent';
  const errorClasses = 'focus:ring-1';
  const errorStyle = 'border-color: var(--priority-urgent);';
  const errorFocusStyle =
    'border-color: var(--priority-urgent); --tw-ring-color: var(--priority-urgent);';
</script>

<div class="w-full">
  <input
    bind:value
    class="{baseClasses} {error ? errorClasses : normalClasses}"
    style={error ? errorStyle : ''}
    onfocus={error
      ? (e) => ((e.currentTarget as HTMLInputElement).style.cssText = errorFocusStyle)
      : undefined}
    onblur={error
      ? (e) => ((e.currentTarget as HTMLInputElement).style.cssText = errorStyle)
      : undefined}
    {...restProps}
  />
  {#if error}
    <p class="mt-1 text-xs" style="color: var(--priority-urgent);">{error}</p>
  {/if}
</div>

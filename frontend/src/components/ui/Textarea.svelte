<script lang="ts">
  let {
    error,
    autogrow = false,
    value = $bindable(''),
    ...restProps
  }: {
    error?: string;
    autogrow?: boolean;
    value?: string;
    [key: string]: unknown;
  } = $props();

  let textareaEl: HTMLTextAreaElement;

  $effect(() => {
    if (autogrow && textareaEl) {
      value; // track value changes
      textareaEl.style.height = 'auto';
      textareaEl.style.height = textareaEl.scrollHeight + 'px';
    }
  });

  const baseClasses =
    'w-full px-3 py-2 text-base bg-surface border rounded-input text-primary placeholder:text-tertiary duration-fast outline-none';
  const sizeClasses = 'min-h-[72px]';
  const resizeClass = $derived(autogrow ? 'resize-none overflow-hidden' : 'resize-y');
  const normalClasses = 'border-default focus:border-accent focus:ring-1 focus:ring-accent';
  const errorStyle = 'border-color: var(--priority-urgent);';
</script>

<div class="w-full">
  <textarea
    bind:this={textareaEl}
    bind:value
    class="{baseClasses} {sizeClasses} {resizeClass} {error ? '' : normalClasses}"
    style={error ? errorStyle : ''}
    {...restProps}
  ></textarea>
  {#if error}
    <p class="mt-1 text-xs" style="color: var(--priority-urgent);">{error}</p>
  {/if}
</div>

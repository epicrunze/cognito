<script lang="ts">
  import { fly } from 'svelte/transition';

  type Option = { value: string; label: string };

  let {
    options,
    value = $bindable(''),
    placeholder,
    onchange,
    disabled = false,
    error,
  }: {
    options: Option[];
    value?: string;
    placeholder?: string;
    onchange?: (value: string) => void;
    disabled?: boolean;
    error?: string;
  } = $props();

  let open = $state(false);
  let triggerEl: HTMLButtonElement;

  const displayLabel = $derived(options.find((o) => o.value === value)?.label ?? '');

  function selectOption(opt: Option) {
    value = opt.value;
    open = false;
    onchange?.(value);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') open = false;
  }

  $effect(() => {
    if (!open) return;

    function handleClickOutside(e: MouseEvent) {
      if (triggerEl && !triggerEl.closest('[data-select-root]')?.contains(e.target as Node)) {
        open = false;
      }
    }

    window.addEventListener('click', handleClickOutside);
    return () => window.removeEventListener('click', handleClickOutside);
  });

  const triggerBase =
    'w-full h-9 px-3 text-base bg-surface border rounded-input duration-fast outline-none inline-flex items-center justify-between gap-2';
  const normalTrigger = 'border-default focus:border-accent focus:ring-1 focus:ring-accent';
  const errorTriggerStyle = 'border-color: var(--priority-urgent);';
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="relative w-full" data-select-root onkeydown={handleKeydown}>
  <button
    bind:this={triggerEl}
    type="button"
    {disabled}
    class="{triggerBase} {error ? '' : normalTrigger} {disabled ? 'opacity-50 cursor-not-allowed' : ''}"
    style={error ? errorTriggerStyle : ''}
    aria-expanded={open}
    aria-haspopup="listbox"
    onclick={() => { if (!disabled) open = !open; }}
  >
    <span class={displayLabel ? 'text-primary' : 'text-tertiary'}>
      {displayLabel || placeholder || ''}
    </span>
    <svg
      class="w-4 h-4 text-tertiary flex-shrink-0 duration-fast {open ? 'rotate-180' : ''}"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  </button>

  {#if open}
    <div
      class="absolute z-50 mt-1 w-full bg-surface border border-default rounded-container shadow-md"
      role="listbox"
      transition:fly={{ y: -4, duration: 150 }}
    >
      {#each options as opt (opt.value)}
        <button
          type="button"
          role="option"
          aria-selected={opt.value === value}
          class="w-full text-left px-3 py-2 text-base duration-fast
            {opt.value === value
              ? 'bg-accent-subtle text-accent'
              : 'text-primary hover:bg-surface-hover'}"
          onclick={() => selectOption(opt)}
        >
          {opt.label}
        </button>
      {/each}
    </div>
  {/if}

  {#if error}
    <p class="mt-1 text-xs" style="color: var(--priority-urgent);">{error}</p>
  {/if}
</div>

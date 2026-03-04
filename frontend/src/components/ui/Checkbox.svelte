<script lang="ts">
  import type { Snippet } from 'svelte';
  import { scale } from 'svelte/transition';

  let {
    checked = $bindable(false),
    disabled = false,
    onchange,
    children,
  }: {
    checked?: boolean;
    disabled?: boolean;
    onchange?: (checked: boolean) => void;
    children?: Snippet;
  } = $props();

  function handleChange(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    checked = input.checked;
    onchange?.(checked);
  }
</script>

<label class="inline-flex items-center gap-2 {disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}">
  <input
    type="checkbox"
    class="sr-only"
    {checked}
    {disabled}
    onchange={handleChange}
  />
  <span
    class="w-5 h-5 rounded-full border-2 duration-normal flex items-center justify-center flex-shrink-0"
    style={checked
      ? 'background-color: var(--done); border-color: var(--done);'
      : 'border-color: var(--border-strong);'}
  >
    {#if checked}
      <span transition:scale={{ duration: 200, start: 0.5 }}>
        <svg
          class="w-3 h-3"
          viewBox="0 0 12 12"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M2 6l3 3 5-5"
            stroke="white"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
    {/if}
  </span>
  {#if children}
    {@render children()}
  {/if}
</label>

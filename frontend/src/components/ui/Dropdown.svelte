<script lang="ts">
  import { onMount } from 'svelte';

  type Option = { value: string; label: string; description?: string };

  let {
    options,
    value = '',
    onchange,
    placeholder = 'Select...',
    width = 200,
  }: {
    options: Option[];
    value?: string;
    onchange?: (value: string) => void;
    placeholder?: string;
    width?: number;
  } = $props();

  let open = $state(false);
  let hoveredValue = $state<string | null>(null);
  let ref: HTMLDivElement;

  const selected = $derived(options.find(o => o.value === value));

  onMount(() => {
    const handler = (e: MouseEvent) => {
      if (ref && !ref.contains(e.target as Node)) open = false;
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  });
</script>

<div bind:this={ref} style="position: relative; display: inline-flex; width: {width}px;">
  <button
    type="button"
    onclick={() => open = !open}
    style="width: 100%; height: 34px; padding: 0 12px; font-size: 13.5px; font-weight: 400; color: {selected ? 'var(--text-primary)' : 'var(--text-tertiary)'}; background: var(--bg-elevated); border: 1px solid {open ? 'var(--accent)' : 'var(--border-default)'}; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; transition: all 150ms ease-out; outline: none; box-shadow: {open ? '0 0 0 2px rgba(232,119,46,0.15)' : 'none'}; font-family: var(--font-sans);"
  >
    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
      {selected ? selected.label : placeholder}
    </span>
    <span style="font-size: 10px; color: var(--text-tertiary); margin-left: 8px; transform: {open ? 'rotate(180deg)' : 'rotate(0deg)'}; transition: transform 150ms;">&#9660;</span>
  </button>
  {#if open}
    <div
      style="position: absolute; top: calc(100% + 4px); left: 0; width: 100%; z-index: 300; background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: 8px; box-shadow: var(--shadow-lg); overflow: hidden; animation: fadeIn 100ms ease-out; padding: 4px;"
    >
      {#each options as opt (opt.value)}
        <button
          type="button"
          onmouseenter={() => hoveredValue = opt.value}
          onmouseleave={() => hoveredValue = null}
          onclick={() => { onchange?.(opt.value); open = false; }}
          style="width: 100%; padding: 8px 10px; font-size: 13.5px; font-weight: {opt.value === value ? 500 : 400}; color: {opt.value === value ? 'var(--accent)' : hoveredValue === opt.value ? 'var(--text-primary)' : 'var(--text-secondary)'}; background: {opt.value === value ? 'var(--accent-subtle)' : hoveredValue === opt.value ? 'var(--bg-surface-hover)' : 'transparent'}; border: none; border-radius: 6px; cursor: pointer; display: flex; flex-direction: column; gap: 2px; text-align: left; transition: all 100ms ease-out; font-family: var(--font-sans);"
        >
          <span>{opt.label}</span>
          {#if opt.description}
            <span style="font-size: 12px; color: var(--text-tertiary); font-weight: 400;">{opt.description}</span>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</div>

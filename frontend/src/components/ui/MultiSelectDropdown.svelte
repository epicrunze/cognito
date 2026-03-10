<script lang="ts">
  import { onMount } from 'svelte';

  type Option = { value: string | number; label: string; color?: string };

  let {
    options,
    selected = [],
    onchange,
    placeholder = 'Select...',
    width = 200,
    searchable,
  }: {
    options: Option[];
    selected?: (string | number)[];
    onchange?: (selected: (string | number)[]) => void;
    placeholder?: string;
    width?: number;
    searchable?: boolean;
  } = $props();

  let open = $state(false);
  let search = $state('');
  let hoveredValue = $state<string | number | null>(null);
  let ref = $state<HTMLDivElement>();
  let searchInput = $state<HTMLInputElement>();

  const showSearch = $derived(searchable !== undefined ? searchable : options.length > 6);
  const filtered = $derived(
    search
      ? options.filter(o => o.label.toLowerCase().includes(search.toLowerCase()))
      : options
  );
  const hasSelection = $derived(selected.length > 0);
  const buttonLabel = $derived(
    hasSelection ? `${placeholder} (${selected.length})` : placeholder
  );

  function isSelected(value: string | number): boolean {
    return selected.includes(value);
  }

  function toggle(value: string | number) {
    const next = isSelected(value)
      ? selected.filter(v => v !== value)
      : [...selected, value];
    onchange?.(next);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && open) {
      open = false;
      search = '';
    }
  }

  onMount(() => {
    const handler = (e: MouseEvent) => {
      if (ref && !ref.contains(e.target as Node)) {
        open = false;
        search = '';
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  });

  $effect(() => {
    if (open && showSearch && searchInput) {
      searchInput.focus();
    }
  });
</script>

<svelte:window onkeydown={handleKeydown} />

<div bind:this={ref} style="position: relative; display: inline-flex; width: {width}px;">
  <button
    type="button"
    onclick={() => { open = !open; if (!open) search = ''; }}
    style="width: 100%; height: 34px; padding: 0 12px; font-size: 13.5px; font-weight: 400; color: {hasSelection ? 'var(--text-primary)' : 'var(--text-tertiary)'}; background: var(--bg-elevated); border: 1px solid {open || hasSelection ? 'var(--accent)' : 'var(--border-default)'}; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; transition: all 150ms ease-out; outline: none; box-shadow: {open ? '0 0 0 2px rgba(232,119,46,0.15)' : 'none'}; font-family: var(--font-sans);"
  >
    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
      {buttonLabel}
    </span>
    <span style="font-size: 10px; color: var(--text-tertiary); margin-left: 8px; transform: {open ? 'rotate(180deg)' : 'rotate(0deg)'}; transition: transform 150ms;">&#9660;</span>
  </button>
  {#if open}
    <div
      style="position: absolute; top: calc(100% + 4px); left: 0; width: 100%; z-index: 300; background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: 8px; box-shadow: var(--shadow-lg); overflow: hidden; animation: fadeIn 100ms ease-out; padding: 4px;"
    >
      {#if showSearch}
        <div style="padding: 4px 4px 2px;">
          <input
            bind:this={searchInput}
            bind:value={search}
            type="text"
            placeholder="Search..."
            style="width: 100%; height: 30px; padding: 0 8px; font-size: 13px; color: var(--text-primary); background: var(--bg-surface-hover); border: 1px solid var(--border-default); border-radius: 6px; outline: none; font-family: var(--font-sans); box-sizing: border-box;"
          />
        </div>
      {/if}
      <div style="max-height: 240px; overflow-y: auto;">
        {#each filtered as opt (opt.value)}
          <button
            type="button"
            onmouseenter={() => hoveredValue = opt.value}
            onmouseleave={() => hoveredValue = null}
            onclick={() => toggle(opt.value)}
            style="width: 100%; height: 34px; padding: 0 10px; font-size: 13.5px; font-weight: {isSelected(opt.value) ? 500 : 400}; color: {isSelected(opt.value) ? 'var(--text-primary)' : hoveredValue === opt.value ? 'var(--text-primary)' : 'var(--text-secondary)'}; background: {isSelected(opt.value) ? 'var(--accent-subtle)' : hoveredValue === opt.value ? 'var(--bg-surface-hover)' : 'transparent'}; border: none; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; text-align: left; transition: all 100ms ease-out; font-family: var(--font-sans);"
          >
            <span style="width: 16px; height: 16px; border-radius: 4px; border: 1.5px solid {isSelected(opt.value) ? 'var(--accent)' : 'var(--border-strong)'}; background: {isSelected(opt.value) ? 'var(--accent)' : 'transparent'}; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all 100ms ease-out;">
              {#if isSelected(opt.value)}
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none" style="display: block;">
                  <path d="M2 5.5L4 7.5L8 3" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              {/if}
            </span>
            {#if opt.color}
              <span style="width: 8px; height: 8px; border-radius: 50%; background: {opt.color}; flex-shrink: 0;"></span>
            {/if}
            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{opt.label}</span>
          </button>
        {/each}
        {#if filtered.length === 0}
          <div style="padding: 8px 10px; font-size: 13px; color: var(--text-tertiary); font-family: var(--font-sans);">
            No matches
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

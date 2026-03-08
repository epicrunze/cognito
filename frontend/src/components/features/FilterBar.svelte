<script lang="ts">
  import { slide } from 'svelte/transition';
  import { labelsStore } from '$lib/stores.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';

  let { open = false }: { open?: boolean } = $props();

  const statusOptions = [
    { value: 'all' as const, label: 'All' },
    { value: 'active' as const, label: 'Active' },
    { value: 'completed' as const, label: 'Completed' },
  ];

  const priorityLevels = [1, 2, 3, 4, 5];
  const priorityColors = [
    'var(--priority-low)',
    'var(--priority-low)',
    'var(--priority-medium)',
    'var(--priority-high)',
    'var(--priority-urgent)',
  ];
</script>

{#if open}
  <div
    transition:slide={{ duration: 200 }}
    style="padding: 10px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 16px; flex-shrink: 0; overflow-x: auto; background: var(--bg-surface);"
  >
    <!-- Status -->
    <div style="display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
      <span style="font-size: 12px; color: var(--text-tertiary); margin-right: 4px;">Status</span>
      {#each statusOptions as opt (opt.value)}
        <button
          type="button"
          onclick={() => filterStore.setStatus(opt.value)}
          style="height: 26px; padding: 0 10px; font-size: 12.5px; font-weight: 500; border-radius: 9999px; border: 1px solid {filterStore.status === opt.value ? 'var(--accent)' : 'var(--border-default)'}; background: {filterStore.status === opt.value ? 'var(--accent-subtle)' : 'transparent'}; color: {filterStore.status === opt.value ? 'var(--accent)' : 'var(--text-secondary)'}; cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
        >{opt.label}</button>
      {/each}
    </div>

    <!-- Priority -->
    <div style="display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
      <span style="font-size: 12px; color: var(--text-tertiary); margin-right: 4px;">Priority</span>
      {#each priorityLevels as level (level)}
        {@const active = filterStore.priorities.includes(level)}
        <button
          type="button"
          onclick={() => filterStore.togglePriority(level)}
          style="width: 24px; height: 24px; font-size: 12px; font-weight: 600; border-radius: 50%; border: 2px solid {active ? priorityColors[level - 1] : 'var(--border-default)'}; background: {active ? priorityColors[level - 1] + '30' : 'transparent'}; color: {active ? priorityColors[level - 1] : 'var(--text-tertiary)'}; cursor: pointer; font-family: var(--font-sans); transition: all 150ms; display: flex; align-items: center; justify-content: center;"
        >{level}</button>
      {/each}
    </div>

    <!-- Labels -->
    {#if labelsStore.labels.length > 0}
      <div style="display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
        <span style="font-size: 12px; color: var(--text-tertiary); margin-right: 4px;">Labels</span>
        {#each labelsStore.labels as label (label.id)}
          {@const active = filterStore.labelIds.includes(label.id)}
          <button
            type="button"
            onclick={() => filterStore.toggleLabel(label.id)}
            style="height: 24px; padding: 0 9px; font-size: 12.5px; font-weight: 500; border-radius: 9999px; border: 1px solid {active ? (label.hex_color || 'var(--accent)') : 'var(--border-default)'}; background: {active ? (label.hex_color ? label.hex_color + '25' : 'var(--accent-subtle)') : 'transparent'}; color: {label.hex_color || 'var(--text-secondary)'}; cursor: pointer; font-family: var(--font-sans); transition: all 150ms; white-space: nowrap;"
          >{label.title}</button>
        {/each}
      </div>
    {/if}

    <!-- Clear -->
    {#if filterStore.activeFilterCount > 0}
      <button
        type="button"
        onclick={() => filterStore.clearAll()}
        style="height: 26px; padding: 0 10px; font-size: 12px; color: var(--text-tertiary); background: none; border: none; cursor: pointer; font-family: var(--font-sans); white-space: nowrap; flex-shrink: 0;"
      >Clear all</button>
    {/if}
  </div>
{/if}

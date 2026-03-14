<script lang="ts">
  import { slide } from 'svelte/transition';
  import { DURATION } from '$lib/transitions';
  import { labelsStore } from '$lib/stores.svelte';
  import { filterStore, type DueDatePreset } from '$lib/stores/filter.svelte';
  import Dropdown from '$components/ui/Dropdown.svelte';
  import MultiSelectDropdown from '$components/ui/MultiSelectDropdown.svelte';

  let { open = false }: { open?: boolean } = $props();

  const statusOptions = [
    { value: 'all', label: 'All' },
    { value: 'active', label: 'Active' },
    { value: 'completed', label: 'Completed' },
  ];

  const dueDateOptions: { value: string; label: string }[] = [
    { value: 'any', label: 'Any' },
    { value: 'overdue', label: 'Overdue' },
    { value: 'today', label: 'Today' },
    { value: 'this_week', label: 'This Week' },
    { value: 'this_month', label: 'This Month' },
    { value: 'no_date', label: 'No Date' },
  ];

  const subtaskOptions = [
    { value: 'any', label: 'Any' },
    { value: 'yes', label: 'Has Subtasks' },
    { value: 'no', label: 'No Subtasks' },
  ];

  const priorityOptions = [
    { value: 1, label: 'P1 — Lowest', color: 'var(--priority-low)' },
    { value: 2, label: 'P2 — Low', color: 'var(--priority-low)' },
    { value: 3, label: 'P3 — Medium', color: 'var(--priority-medium)' },
    { value: 4, label: 'P4 — High', color: 'var(--priority-high)' },
    { value: 5, label: 'P5 — Urgent', color: 'var(--priority-urgent)' },
  ];

  const labelOptions = $derived(
    labelsStore.labels.map(l => ({ value: l.id, label: l.title, color: l.hex_color || undefined }))
  );

  const subtaskValue = $derived(
    filterStore.hasSubtasks === true ? 'yes' : filterStore.hasSubtasks === false ? 'no' : 'any'
  );

  function handleSubtaskChange(v: string) {
    filterStore.setHasSubtasks(v === 'yes' ? true : v === 'no' ? false : null);
  }
</script>

{#if open}
  <div
    transition:slide={{ duration: DURATION.normal }}
    style="padding: 10px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 10px; flex-shrink: 0; overflow-x: auto; background: var(--bg-surface);"
  >
    <Dropdown
      options={statusOptions}
      value={filterStore.status}
      onchange={(v) => filterStore.setStatus(v as 'all' | 'active' | 'completed')}
      placeholder="Status"
      width={120}
    />

    <MultiSelectDropdown
      options={priorityOptions}
      selected={filterStore.priorities}
      onchange={(ids) => filterStore.setPriorities(ids as number[])}
      placeholder="Priority"
      width={140}
      searchable={false}
    />

    {#if labelOptions.length > 0}
      <MultiSelectDropdown
        options={labelOptions}
        selected={filterStore.labelIds}
        onchange={(ids) => filterStore.setLabelIds(ids as number[])}
        placeholder="Labels"
        width={160}
      />
    {/if}

    <Dropdown
      options={dueDateOptions}
      value={filterStore.dueDateFilter}
      onchange={(v) => filterStore.setDueDateFilter(v as DueDatePreset)}
      placeholder="Due Date"
      width={150}
    />

    <Dropdown
      options={subtaskOptions}
      value={subtaskValue}
      onchange={handleSubtaskChange}
      placeholder="Subtasks"
      width={140}
    />

    {#if filterStore.activeFilterCount > 0}
      <button
        type="button"
        onclick={() => filterStore.clearAll()}
        style="height: 34px; padding: 0 12px; font-size: 12.5px; color: var(--text-tertiary); background: none; border: 1px solid var(--border-default); border-radius: 8px; cursor: pointer; font-family: var(--font-sans); white-space: nowrap; flex-shrink: 0; transition: all var(--transition-fast);"
      >Clear all</button>
    {/if}
  </div>
{/if}

<script lang="ts">
  import Checkbox from '$components/ui/Checkbox.svelte';
  import PriorityIndicator from '$components/ui/PriorityIndicator.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import DateDisplay from '$components/ui/DateDisplay.svelte';
  import { proposalsApi } from '$lib/api';
  import { addToast } from '$lib/stores/toast.svelte';
  import type { TaskProposal } from '$lib/types';

  interface Props {
    proposal: TaskProposal;
    selected: boolean;
    hovered: boolean;
    onselect: () => void;
    onedit: () => void;
    onmouseenter: () => void;
    onmouseleave: () => void;
    onupdate?: (updated: TaskProposal) => void;
  }

  let { proposal, selected, hovered, onselect, onedit, onmouseenter, onmouseleave, onupdate }: Props = $props();

  let editing = $state(false);
  let editTitle = $state('');
  let editPriority = $state(3);
  let editDueDate = $state('');
  let editMinutes = $state('');

  function startEditing() {
    if (proposal.status !== 'pending') return;
    editing = true;
    editTitle = proposal.title;
    editPriority = proposal.priority;
    editDueDate = proposal.due_date ?? '';
    editMinutes = proposal.estimated_minutes?.toString() ?? '';
  }

  async function saveEdits() {
    if (!editTitle.trim()) return;
    editing = false;
    const data: Record<string, unknown> = {};
    if (editTitle !== proposal.title) data.title = editTitle;
    if (editPriority !== proposal.priority) data.priority = editPriority;
    const newDue = editDueDate || null;
    if (newDue !== proposal.due_date) data.due_date = newDue;
    const newMins = editMinutes ? parseInt(editMinutes) : null;
    if (newMins !== proposal.estimated_minutes) data.estimated_minutes = newMins;

    if (Object.keys(data).length === 0) return;

    try {
      const updated = await proposalsApi.update(proposal.id, data);
      onupdate?.(updated);
    } catch {
      addToast('Failed to update proposal', 'error');
    }
  }

  function handleEditKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveEdits();
    } else if (e.key === 'Escape') {
      editing = false;
    }
  }
</script>

<div
  role="group"
  {onmouseenter}
  {onmouseleave}
  style="position: relative; display: flex; gap: 14px; padding: 16px 18px; background: var(--bg-surface); border: 1px solid {proposal.status === 'approved' ? 'var(--done)' : hovered ? 'var(--border-strong)' : 'var(--border-default)'}; border-radius: 10px; border-left: 2px solid var(--accent); box-shadow: {hovered ? 'var(--shadow-sm), inset 3px 0 8px -4px var(--accent-glow)' : 'inset 3px 0 8px -4px var(--accent-glow)'}; transition: all 150ms ease-out; align-items: flex-start; opacity: {proposal.status === 'approved' ? 0.5 : 1};"
>
  <Checkbox
    checked={selected}
    onchange={onselect}
  />
  {#if editing}
    <!-- Inline editing mode -->
    <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px;">
      <input
        type="text"
        bind:value={editTitle}
        onkeydown={handleEditKeydown}
        onblur={saveEdits}
        style="width: 100%; padding: 6px 10px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; color: var(--text-primary); font-size: 15px; font-weight: 500; font-family: var(--font-sans); outline: none;"
      />
      <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
        <div style="display: flex; gap: 4px; align-items: center;">
          {#each [1, 2, 3, 4, 5] as p (p)}
            <button
              aria-label="Priority {p}"
              onclick={() => editPriority = p}
              style="width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid {p <= editPriority ? 'var(--accent)' : 'var(--border-default)'}; background: {p <= editPriority ? 'var(--accent)' : 'transparent'}; cursor: pointer; padding: 0;"
            ></button>
          {/each}
        </div>
        <input
          type="date"
          bind:value={editDueDate}
          style="padding: 4px 8px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; color: var(--text-secondary); font-size: 13px; font-family: var(--font-sans); outline: none;"
        />
        <div style="display: flex; align-items: center; gap: 4px;">
          <input
            type="number"
            bind:value={editMinutes}
            placeholder="min"
            style="width: 60px; padding: 4px 8px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; color: var(--text-secondary); font-size: 13px; font-family: var(--font-sans); outline: none;"
          />
          <span style="font-size: 12px; color: var(--text-tertiary);">min</span>
        </div>
        <button
          onclick={() => editing = false}
          style="padding: 3px 10px; background: none; border: 1px solid var(--border-default); border-radius: 6px; font-size: 12px; color: var(--text-tertiary); cursor: pointer; font-family: var(--font-sans);"
        >Cancel</button>
      </div>
    </div>
  {:else}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div style="flex: 1; min-width: 0; cursor: pointer;" onclick={onedit} ondblclick={startEditing}>
      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 7px;">
        <PriorityIndicator level={proposal.priority} size="sm" />
        <span style="font-size: 15px; font-weight: 500; color: var(--text-primary); line-height: 1.3;">
          {proposal.title}
        </span>
        {#if proposal.status === 'approved'}
          <span style="font-size: 12px; color: var(--done); font-weight: 500;">Approved</span>
        {/if}
      </div>
      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
        {#if proposal.project_name && !proposal.project_id}
          <Badge color="var(--accent)">{proposal.project_name}</Badge>
          <span style="font-size: 11px; color: var(--accent); font-weight: 500;">New project</span>
          <span style="font-size: 13px; color: var(--border-strong);">&middot;</span>
        {:else if proposal.project_name}
          <span style="font-size: 13px; color: var(--text-tertiary);">{proposal.project_name}</span>
          <span style="font-size: 13px; color: var(--border-strong);">&middot;</span>
        {:else if !proposal.project_id}
          <span style="font-size: 12px; color: var(--danger, #ef4444); font-weight: 500;">No project</span>
          <span style="font-size: 13px; color: var(--border-strong);">&middot;</span>
        {/if}
        <DateDisplay date={proposal.due_date} />
        {#if proposal.estimated_minutes}
          <span style="font-size: 13px; color: var(--border-strong);">&middot;</span>
          <span style="font-size: 13px; color: var(--text-tertiary);">{proposal.estimated_minutes}min</span>
        {/if}
        {#each proposal.labels as label (label)}
          <Badge>{label}</Badge>
        {/each}
      </div>
    </div>
    {#if proposal.status === 'pending'}
      <button
        onclick={startEditing}
        style="position: absolute; top: 12px; right: 14px; background: none; border: 1px solid var(--border-default); border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 500; color: var(--text-tertiary); cursor: pointer; opacity: {hovered ? 1 : 0}; transition: opacity 150ms ease-out; font-family: var(--font-sans);"
      >Edit</button>
    {/if}
  {/if}
</div>

<script lang="ts">
  import Checkbox from '$components/ui/Checkbox.svelte';
  import PriorityIndicator from '$components/ui/PriorityIndicator.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import DateDisplay from '$components/ui/DateDisplay.svelte';
  import type { TaskProposal } from '$lib/types';

  interface Props {
    proposal: TaskProposal;
    selected: boolean;
    hovered: boolean;
    onselect: () => void;
    onedit: () => void;
    onmouseenter: () => void;
    onmouseleave: () => void;
  }

  let { proposal, selected, hovered, onselect, onedit, onmouseenter, onmouseleave }: Props = $props();
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
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div style="flex: 1; min-width: 0; cursor: pointer;" onclick={onedit}>
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
      onclick={onedit}
      style="position: absolute; top: 12px; right: 14px; background: none; border: 1px solid var(--border-default); border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 500; color: var(--text-tertiary); cursor: pointer; opacity: {hovered ? 1 : 0}; transition: opacity 150ms ease-out; font-family: var(--font-sans);"
    >Edit</button>
  {/if}
</div>

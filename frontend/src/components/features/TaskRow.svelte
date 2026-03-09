<script lang="ts">
  import type { Task } from '$lib/types';
  import { projectsStore } from '$lib/stores.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';
  import { kanbanStore } from '$lib/stores/kanban.svelte';
  import Checkbox from '$components/ui/Checkbox.svelte';
  import PriorityIndicator from '$components/ui/PriorityIndicator.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import DateDisplay from '$components/ui/DateDisplay.svelte';
  import Tip from '$components/ui/Tip.svelte';

  let {
    task,
    selected = false,
    viewed = false,
    ontoggle,
    onclick,
  }: {
    task: Task;
    selected?: boolean;
    viewed?: boolean;
    ontoggle?: () => void;
    onclick?: () => void;
  } = $props();

  let hovering = $state(false);

  const project = $derived(projectsStore.projects.find(p => p.id === task.project_id));
  const isOverdue = $derived(Boolean(!task.done && task.due_date && new Date(task.due_date) < new Date()));
  const isAiTagged = $derived(filterStore.aiTaggedIds.has(task.id));
  const showGlow = $derived(isAiTagged && !viewed);
  const bucketName = $derived(kanbanStore.getBucketName(task.id));

  function getBorderLeft(): string {
    if (selected) return '2px solid var(--accent)';
    if (showGlow) return '2px solid var(--accent)';
    return '2px solid transparent';
  }

  function getBoxShadow(): string {
    if (showGlow) return 'inset 3px 0 8px -4px var(--accent-glow)';
    return 'none';
  }
</script>

<div
  role="button"
  tabindex="0"
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
  onclick={onclick}
  onkeydown={(e) => { if (e.key === 'Enter') onclick?.(); }}
  style="display: grid; grid-template-columns: 20px 42px 1fr auto; align-items: start; gap: 14px; padding: 14px 20px; background: {selected ? 'var(--accent-subtle)' : hovering ? 'var(--bg-surface-hover)' : 'transparent'}; border-bottom: 1px solid var(--border-subtle); border-left: {getBorderLeft()}; box-shadow: {getBoxShadow()}; cursor: pointer; transition: all 150ms ease-out; min-height: 56px;"
>
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div style="padding-top: 2px;" onclick={(e) => e.stopPropagation()}>
    <Checkbox checked={task.done} onchange={() => ontoggle?.()} />
  </div>
  <div style="padding-top: 3px;">
    <PriorityIndicator level={task.priority} size="sm" />
  </div>
  <div style="min-width: 0;">
    <div style="font-size: 15px; font-weight: 500; color: {task.done ? 'var(--text-tertiary)' : 'var(--text-primary)'}; text-decoration: {task.done ? 'line-through' : 'none'}; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
      {task.title}
    </div>
    {#if task.description && !task.done}
      <div style="font-size: 13px; color: var(--text-tertiary); margin-top: 3px; line-height: 1.4; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 90%;">
        {task.description}
      </div>
    {/if}
    <div style="display: flex; gap: 7px; margin-top: 5px; align-items: center; flex-wrap: wrap;">
      {#if project}
        <span style="font-size: 13px; color: var(--text-tertiary);">{project.title}</span>
      {/if}
      {#each task.labels as label (label.id)}
        <Badge color={label.hex_color}>{label.title}</Badge>
      {/each}
      {#if bucketName}
        <span style="display: inline-flex; align-items: center; height: 22px; padding: 0 8px; font-size: 11.5px; font-weight: 500; color: var(--text-tertiary); background: transparent; border: 1px solid var(--border-default); border-radius: 9999px; line-height: 1; white-space: nowrap;">{bucketName}</span>
      {/if}
      {#if task.attachments && task.attachments.length > 0}
        <Tip text={`${task.attachments.length} attachment${task.attachments.length > 1 ? 's' : ''}`}>
          <span style="display: inline-flex; align-items: center; gap: 3px; font-size: 12px; color: var(--text-tertiary);">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M13.5 7.5l-5.4 5.4a3.2 3.2 0 01-4.5-4.5l5.4-5.4a2 2 0 012.8 2.8L6.4 11.2a.8.8 0 01-1.1-1.1l4.5-4.5" stroke-linecap="round" />
            </svg>
            {task.attachments.length}
          </span>
        </Tip>
      {/if}
      {#if task.subtask_total && task.subtask_total > 0}
        <Tip text={`${task.subtask_done ?? 0}/${task.subtask_total} subtasks done`}>
          <span style="display: inline-flex; align-items: center; gap: 3px; font-size: 12px; color: {task.subtask_done === task.subtask_total ? 'var(--done)' : 'var(--text-tertiary)'};">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <path d="M2 4h8M2 8h10M2 12h6M13 6l-2 2 4-4" />
            </svg>
            {task.subtask_done ?? 0}/{task.subtask_total}
          </span>
        </Tip>
      {/if}
    </div>
  </div>
  <div style="display: flex; align-items: center; gap: 12px; padding-top: 2px;">
    <DateDisplay date={task.due_date} overdue={isOverdue} />
    <span style="opacity: {hovering ? 0.4 : 0}; transition: opacity 150ms; color: var(--text-tertiary); font-size: 16px;">&rsaquo;</span>
  </div>
</div>

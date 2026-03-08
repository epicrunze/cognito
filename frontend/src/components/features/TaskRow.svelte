<script lang="ts">
  import type { Task } from '$lib/types';
  import { projectsStore } from '$lib/stores.svelte';
  import Checkbox from '$components/ui/Checkbox.svelte';
  import PriorityIndicator from '$components/ui/PriorityIndicator.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import DateDisplay from '$components/ui/DateDisplay.svelte';

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
</script>

<div
  role="button"
  tabindex="0"
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
  onclick={onclick}
  onkeydown={(e) => { if (e.key === 'Enter') onclick?.(); }}
  style="display: grid; grid-template-columns: 20px 42px 1fr auto; align-items: start; gap: 14px; padding: 14px 20px; background: {selected ? 'var(--accent-subtle)' : hovering ? 'var(--bg-surface-hover)' : 'transparent'}; border-bottom: 1px solid var(--border-subtle); border-left: {selected ? '2px solid var(--accent)' : '2px solid transparent'}; cursor: pointer; transition: all 150ms ease-out; min-height: 56px;"
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
    </div>
  </div>
  <div style="display: flex; align-items: center; gap: 12px; padding-top: 2px;">
    <DateDisplay date={task.due_date} overdue={isOverdue} />
    <span style="opacity: {hovering ? 0.4 : 0}; transition: opacity 150ms; color: var(--text-tertiary); font-size: 16px;">&rsaquo;</span>
  </div>
</div>

<script lang="ts">
  import type { Task } from '$lib/types';
  import PriorityIndicator from '$components/ui/PriorityIndicator.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import DateDisplay from '$components/ui/DateDisplay.svelte';

  let {
    task,
    onclick,
  }: {
    task: Task;
    onclick?: () => void;
  } = $props();

  let hovering = $state(false);

  const isOverdue = $derived(Boolean(!task.done && task.due_date && new Date(task.due_date) < new Date()));
</script>

<div
  role="button"
  tabindex="0"
  onmouseenter={() => hovering = true}
  onmouseleave={() => hovering = false}
  onclick={onclick}
  onkeydown={(e) => { if (e.key === 'Enter') onclick?.(); }}
  style="background: var(--bg-surface); border: 1px solid {hovering ? 'var(--border-strong)' : 'var(--border-default)'}; border-radius: 8px; padding: 12px; cursor: pointer; transition: all 150ms ease-out; box-shadow: {hovering ? 'var(--shadow-sm)' : 'none'};"
>
  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
    <PriorityIndicator level={task.priority} size="sm" />
    <span style="font-size: 14px; font-weight: 500; color: {task.done ? 'var(--text-tertiary)' : 'var(--text-primary)'}; text-decoration: {task.done ? 'line-through' : 'none'}; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; flex: 1;">
      {task.title}
    </span>
  </div>
  <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
    {#if task.due_date}
      <DateDisplay date={task.due_date} overdue={isOverdue} />
    {/if}
    {#if task.labels.length > 0}
      <Badge color={task.labels[0].hex_color}>{task.labels[0].title}</Badge>
    {/if}
  </div>
</div>

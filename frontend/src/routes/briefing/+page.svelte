<script lang="ts">
  import { onMount } from 'svelte';
  import { briefingApi, type BriefingResponse, type BriefingCalendarEvent } from '$lib/api';
  import type { Task } from '$lib/types';
  import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
  import { formatRelativeDate, isOverdue, isZeroEpoch } from '$lib/dateUtils';
  import StatusBriefing from '$components/features/project/StatusBriefing.svelte';

  let data = $state<BriefingResponse | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let regenerating = $state(false);

  async function load() {
    loading = true;
    error = null;
    try {
      data = await briefingApi.get();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load briefing';
    } finally {
      loading = false;
    }
  }

  async function regenerate() {
    regenerating = true;
    try {
      data = await briefingApi.regenerate();
    } catch {
      // keep showing the previous briefing on failure
    } finally {
      regenerating = false;
    }
  }

  onMount(load);

  function priorityColor(p: number): string {
    if (p === 5) return 'var(--priority-urgent)';
    if (p === 4) return 'var(--priority-high)';
    if (p === 3) return 'var(--priority-medium)';
    return 'var(--priority-low)';
  }

  function fmtTime(iso: string): string {
    if (!iso) return '';
    // Google all-day events come through as a bare date (YYYY-MM-DD).
    if (iso.length === 10) return 'All day';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }

  function fmtGenerated(iso: string | null): string {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return 'updated ' + d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }

  const briefingText = $derived(data?.briefing_text?.trim() || 'No briefing for today yet.');
</script>

<div class="today">
  {#if loading}
    <div class="state">Loading your day…</div>
  {:else if error}
    <div class="state">
      {error}
      <button class="retry" onclick={load}>Retry</button>
    </div>
  {:else if data}
    <StatusBriefing
      text={briefingText}
      generatedLabel={fmtGenerated(data.generated_at)}
      generating={regenerating}
      onRegenerate={regenerate}
    />

    <div class="grid">
      <!-- Due today -->
      <section class="card">
        <header class="card-head">
          <span class="card-label">Due today</span>
          <span class="card-count">{data.due_today.length}</span>
        </header>
        {#if data.due_today.length}
          {#each data.due_today as task (task.id)}
            {@render taskRow(task)}
          {/each}
        {:else}
          <p class="empty">Nothing due today.</p>
        {/if}
      </section>

      <!-- Overdue -->
      <section class="card">
        <header class="card-head">
          <span class="card-label">Overdue</span>
          <span class="card-count" class:danger={data.overdue.length > 0}>{data.overdue.length}</span>
        </header>
        {#if data.overdue.length}
          {#each data.overdue as task (task.id)}
            {@render taskRow(task)}
          {/each}
        {:else}
          <p class="empty">Nothing overdue. 🎉</p>
        {/if}
      </section>

      <!-- Calendar -->
      <section class="card">
        <header class="card-head">
          <span class="card-label">Calendar</span>
          <span class="card-count">{data.calendar.length}</span>
        </header>
        {#if data.calendar.length}
          {#each data.calendar as event, i (i)}
            {@render calendarRow(event)}
          {/each}
        {:else}
          <p class="empty">No calendar events today.</p>
        {/if}
      </section>

      <!-- Done today -->
      <section class="card">
        <header class="card-head">
          <span class="card-label">Done today</span>
          <span class="card-count">{data.done_today.length}</span>
        </header>
        {#if data.done_today.length}
          {#each data.done_today as task (task.id)}
            {@render taskRow(task, true)}
          {/each}
        {:else}
          <p class="empty">Nothing completed yet.</p>
        {/if}
      </section>
    </div>

    <!-- Undated open tasks — important work without a deadline still surfaces -->
    <section class="card">
      <header class="card-head">
        <span class="card-label">No due date</span>
        <span class="card-count">{data.undated.length}</span>
      </header>
      {#if data.undated.length}
        {#each data.undated as task (task.id)}
          {@render taskRow(task)}
        {/each}
      {:else}
        <p class="empty">Everything has a date.</p>
      {/if}
    </section>
  {/if}
</div>

{#snippet taskRow(task: Task, done = false)}
  <button class="row" onclick={() => taskDetailStore.open(task.id)}>
    {#if done}
      <span class="check">✓</span>
    {:else}
      <span class="dot" style="background: {priorityColor(task.priority)};"></span>
    {/if}
    <span class="row-title" class:row-done={done}>{task.title}</span>
    {#if !done && !isZeroEpoch(task.due_date)}
      <span class="row-meta" class:overdue={isOverdue(task.due_date)}>{formatRelativeDate(task.due_date)}</span>
    {/if}
  </button>
{/snippet}

{#snippet calendarRow(event: BriefingCalendarEvent)}
  <div class="row cal-row">
    <span class="dot" style="background: {event.color || 'var(--text-tertiary)'};"></span>
    <span class="row-title">{event.summary}</span>
    <span class="row-meta">{fmtTime(event.start)}</span>
  </div>
{/snippet}

<style>
  .today {
    max-width: 920px;
    margin: 0 auto;
    padding: 24px 24px 48px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .state {
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--text-tertiary);
    font-size: 15px;
    padding: 48px 0;
    justify-content: center;
  }

  .retry {
    background: var(--action-tint);
    color: var(--tangerine);
    border: none;
    border-radius: var(--radius-inner);
    padding: 4px 10px;
    font-size: 13px;
    font-family: var(--font-sans);
    cursor: pointer;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  @media (max-width: 700px) {
    .grid {
      grid-template-columns: 1fr;
    }
    .today {
      padding: 16px 16px 40px;
    }
  }

  .card {
    background: var(--surface-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-card);
    box-shadow: var(--shadow-rest);
    padding: 14px 16px 10px;
    display: flex;
    flex-direction: column;
  }

  .card-head {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 8px;
  }

  .card-label {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .card-count {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-tertiary);
    opacity: 0.8;
  }

  .card-count.danger {
    color: var(--overdue);
    opacity: 1;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 9px;
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    padding: 7px 6px;
    margin: 0 -6px;
    border-radius: var(--radius-inner);
    cursor: pointer;
    font-family: var(--font-sans);
    transition: background var(--t-fast) var(--ease-out);
  }

  .cal-row {
    cursor: default;
  }

  button.row:hover {
    background: var(--bg-surface-hover);
  }

  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .check {
    width: 12px;
    flex-shrink: 0;
    color: var(--done);
    font-size: 12px;
    line-height: 1;
    text-align: center;
  }

  .row-title {
    flex: 1;
    font-size: 14px;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .row-title.row-done {
    color: var(--text-tertiary);
    text-decoration: line-through;
  }

  .row-meta {
    font-size: 12px;
    color: var(--text-tertiary);
    flex-shrink: 0;
  }

  .row-meta.overdue {
    color: var(--overdue);
  }

  .empty {
    font-size: 13px;
    color: var(--text-tertiary);
    padding: 4px 0 10px;
    margin: 0;
  }
</style>

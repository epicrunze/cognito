<script lang="ts">
  import { onMount } from 'svelte';
  import { calendarStore } from '$lib/stores/calendar.svelte';
  import { tasksStore } from '$lib/stores.svelte';
  import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
  import type { ScheduleSuggestion, Task } from '$lib/types';

  let { projectId }: { projectId?: number } = $props();

  const HOUR_HEIGHT = 60;
  const START_HOUR = 6;
  const END_HOUR = 22;
  const TOTAL_HOURS = END_HOUR - START_HOUR;
  const LABEL_WIDTH = 60;

  const hours = Array.from({ length: TOTAL_HOURS + 1 }, (_, i) => START_HOUR + i);

  let now = $state(new Date());
  let nowTimer: ReturnType<typeof setInterval>;

  onMount(() => {
    nowTimer = setInterval(() => { now = new Date(); }, 60_000);
    return () => clearInterval(nowTimer);
  });

  // Fetch events on mount and whenever the selected date changes
  $effect(() => {
    // Track dateKey as the reactive dependency
    void calendarStore.dateKey;
    calendarStore.fetchEvents();
  });

  // Format date label like "Thu Mar 27"
  const dateLabel = $derived(
    calendarStore.selectedDate.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    })
  );

  // Check if selected date is today
  const isToday = $derived(
    calendarStore.dateKey === toDateKey(now)
  );

  function toDateKey(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  // Current time indicator position
  const nowTopPx = $derived.by(() => {
    const h = now.getHours();
    const m = now.getMinutes();
    if (h < START_HOUR || h >= END_HOUR) return -1;
    return (h - START_HOUR) * HOUR_HEIGHT + (m / 60) * HOUR_HEIGHT;
  });

  // Filter tasks scheduled for the selected date
  const scheduledTasks = $derived.by(() => {
    const dateKey = calendarStore.dateKey;
    return tasksStore.tasks.filter((t: Task) => {
      if (t.done || !t.start_date) return false;
      if (projectId != null && t.project_id !== projectId) return false;
      const taskDate = t.start_date.slice(0, 10);
      return taskDate === dateKey;
    });
  });

  // Helpers: time to pixel position
  function timeToTop(isoStr: string): number {
    const d = new Date(isoStr);
    const h = d.getHours();
    const m = d.getMinutes();
    return Math.max(0, (h - START_HOUR) * HOUR_HEIGHT + (m / 60) * HOUR_HEIGHT);
  }

  function blockHeight(startIso: string, endIso: string): number {
    const startMs = new Date(startIso).getTime();
    const endMs = new Date(endIso).getTime();
    const durationMin = (endMs - startMs) / 60_000;
    return Math.max(24, (durationMin / 60) * HOUR_HEIGHT);
  }

  function formatTime(isoStr: string): string {
    const d = new Date(isoStr);
    return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  }

  function formatHour(hour: number): string {
    if (hour === 0 || hour === 24) return '12 AM';
    if (hour === 12) return '12 PM';
    if (hour < 12) return `${hour} AM`;
    return `${hour - 12} PM`;
  }

  // Accept a suggestion: create event then remove from list
  async function acceptSuggestion(s: ScheduleSuggestion) {
    await calendarStore.createEvent({
      summary: s.task_title,
      start: s.suggested_start,
      end: s.suggested_end,
      task_id: s.task_id,
    });
    calendarStore.removeSuggestion(s.task_id);
  }
</script>

<!-- Top bar -->
<div style="
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
  font-family: var(--font-sans);
">
  <button
    onclick={() => calendarStore.navigateDay(-1)}
    style="
      display: flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border-radius: 6px;
      border: 1px solid var(--border-default); background: transparent;
      color: var(--text-secondary); cursor: pointer;
      font-size: var(--text-sm); transition: all var(--transition-fast);
    "
    aria-label="Previous day"
  >&lsaquo;</button>

  <span style="
    font-size: var(--text-base); font-weight: 500;
    color: var(--text-primary); min-width: 120px; text-align: center;
  ">{dateLabel}</span>

  <button
    onclick={() => calendarStore.navigateDay(1)}
    style="
      display: flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border-radius: 6px;
      border: 1px solid var(--border-default); background: transparent;
      color: var(--text-secondary); cursor: pointer;
      font-size: var(--text-sm); transition: all var(--transition-fast);
    "
    aria-label="Next day"
  >&rsaquo;</button>

  <button
    onclick={() => calendarStore.goToday()}
    style="
      height: 28px; padding: 0 10px; font-size: var(--text-xs); font-weight: 500;
      border-radius: 6px; border: 1px solid {isToday ? 'var(--accent)' : 'var(--border-default)'};
      background: {isToday ? 'var(--accent-subtle)' : 'transparent'};
      color: {isToday ? 'var(--accent)' : 'var(--text-secondary)'};
      cursor: pointer; font-family: var(--font-sans);
      transition: all var(--transition-fast);
    "
  >Today</button>

  <div style="flex: 1;"></div>

  <button
    onclick={() => calendarStore.suggestSchedule()}
    disabled={calendarStore.suggestLoading}
    style="
      height: 28px; padding: 0 12px; font-size: var(--text-xs); font-weight: 500;
      border-radius: 6px; border: 1px solid var(--accent);
      background: var(--accent-subtle); color: var(--accent);
      cursor: {calendarStore.suggestLoading ? 'wait' : 'pointer'};
      font-family: var(--font-sans); transition: all var(--transition-fast);
      display: flex; align-items: center; gap: 6px;
      opacity: {calendarStore.suggestLoading ? 0.7 : 1};
    "
  >
    {#if calendarStore.suggestLoading}
      <span style="
        display: inline-block; width: 12px; height: 12px;
        border: 2px solid var(--accent); border-top-color: transparent;
        border-radius: 50%; animation: calendar-spin 0.6s linear infinite;
      "></span>
    {/if}
    Suggest
  </button>
</div>

<!-- Main content area -->
<div style="flex: 1; overflow-y: auto; position: relative;">
  {#if calendarStore.loading}
    <!-- Loading skeleton -->
    <div style="padding: 16px {LABEL_WIDTH + 16}px 16px 16px;">
      {#each [1, 2, 3, 4, 5] as i (i)}
        <div style="
          height: 48px; margin-bottom: 12px; border-radius: 8px;
          background: var(--bg-elevated);
          animation: calendar-pulse 1.5s ease-in-out infinite;
          animation-delay: {i * 150}ms;
          opacity: 0.5;
        "></div>
      {/each}
    </div>
  {:else}
    <!-- Error banner (non-blocking — grid still renders below) -->
    {#if calendarStore.error}
      <div style="
        display: flex; align-items: center; gap: 8px;
        padding: 8px 16px; margin: 8px 16px 0;
        background: rgba(239, 87, 68, 0.08);
        border: 1px solid rgba(239, 87, 68, 0.2);
        border-radius: 6px;
      ">
        <span style="font-size: var(--text-xs); color: var(--overdue); flex: 1;">
          {calendarStore.error}
        </span>
        <button
          onclick={() => calendarStore.fetchEvents()}
          style="
            height: 24px; padding: 0 10px; font-size: 10px; font-weight: 500;
            border-radius: 4px; border: 1px solid var(--border-default);
            background: var(--bg-surface); color: var(--text-secondary);
            cursor: pointer; font-family: var(--font-sans);
            transition: all var(--transition-fast); flex-shrink: 0;
          "
        >Retry</button>
      </div>
    {/if}

    <!-- Time grid -->
    <div style="position: relative; min-height: {TOTAL_HOURS * HOUR_HEIGHT}px;">
      <!-- Hour rows and labels -->
      {#each hours as hour (hour)}
        <div style="
          position: absolute;
          top: {(hour - START_HOUR) * HOUR_HEIGHT}px;
          left: 0; right: 0;
          height: {HOUR_HEIGHT}px;
          display: flex; align-items: flex-start;
        ">
          <!-- Time label -->
          <div style="
            width: {LABEL_WIDTH}px; flex-shrink: 0;
            padding: 4px 8px 0 0; text-align: right;
            font-size: var(--text-xs); color: var(--text-tertiary);
            font-family: var(--font-mono); line-height: 1;
          ">{formatHour(hour)}</div>

          <!-- Grid line -->
          <div style="
            flex: 1; border-top: 1px solid var(--border-default);
            height: 100%;
          "></div>
        </div>
      {/each}

      <!-- Content area for event blocks -->
      <div style="
        position: absolute;
        top: 0; left: {LABEL_WIDTH}px; right: 8px;
        height: {TOTAL_HOURS * HOUR_HEIGHT}px;
      ">
        <!-- Current time indicator -->
        {#if isToday && nowTopPx >= 0}
          <div style="
            position: absolute; top: {nowTopPx}px;
            left: -8px; right: 0;
            display: flex; align-items: center;
            z-index: 10; pointer-events: none;
          ">
            <div style="
              width: 8px; height: 8px; border-radius: 50%;
              background: var(--accent); flex-shrink: 0;
            "></div>
            <div style="
              flex: 1; height: 2px;
              background: var(--accent);
            "></div>
          </div>
        {/if}

        <!-- Google Calendar events -->
        {#each calendarStore.events as event (event.id)}
          {@const top = timeToTop(event.start)}
          {@const height = blockHeight(event.start, event.end)}
          {#if event.task_id}
            <div
              style="
                position: absolute; top: {top}px; left: 4px; right: 4px;
                height: {height}px;
                background: var(--bg-elevated);
                border-left: 3px solid var(--accent);
                border-radius: 6px; padding: 6px 10px;
                overflow: hidden; cursor: pointer;
                transition: background var(--transition-fast);
                z-index: 2;
              "
              onclick={() => taskDetailStore.open(event.task_id!)}
              onkeydown={(e) => {
                if (e.key === 'Enter') taskDetailStore.open(event.task_id!);
              }}
              role="button"
              tabindex={0}
            >
              <div style="
                font-size: var(--text-xs); font-weight: 500;
                color: var(--text-primary); white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis;
              ">{event.summary}</div>
              {#if height >= 36}
                <div style="
                  font-size: 10px; color: var(--text-tertiary);
                  margin-top: 2px;
                ">{formatTime(event.start)} - {formatTime(event.end)}</div>
              {/if}
            </div>
          {:else}
            <div
              style="
                position: absolute; top: {top}px; left: 4px; right: 4px;
                height: {height}px;
                background: var(--bg-elevated);
                border-left: 3px solid var(--accent);
                border-radius: 6px; padding: 6px 10px;
                overflow: hidden;
                transition: background var(--transition-fast);
                z-index: 2;
              "
            >
              <div style="
                font-size: var(--text-xs); font-weight: 500;
                color: var(--text-primary); white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis;
              ">{event.summary}</div>
              {#if height >= 36}
                <div style="
                  font-size: 10px; color: var(--text-tertiary);
                  margin-top: 2px;
                ">{formatTime(event.start)} - {formatTime(event.end)}</div>
              {/if}
            </div>
          {/if}
        {/each}

        <!-- Scheduled tasks (from Vikunja) -->
        {#each scheduledTasks as task (task.id)}
          {@const top = timeToTop(task.start_date!)}
          {@const height = task.end_date ? blockHeight(task.start_date!, task.end_date) : 24}
          <div
            style="
              position: absolute; top: {top}px; left: 4px; right: 4px;
              height: {height}px;
              background: var(--accent-subtle);
              border-left: 3px solid var(--accent);
              border-radius: 6px; padding: 6px 10px;
              overflow: hidden; cursor: pointer;
              transition: background var(--transition-fast);
              z-index: 2;
            "
            onclick={() => taskDetailStore.open(task.id)}
            onkeydown={(e) => {
              if (e.key === 'Enter') taskDetailStore.open(task.id);
            }}
            role="button"
            tabindex={0}
          >
            <div style="
              font-size: var(--text-xs); font-weight: 500;
              color: var(--accent); white-space: nowrap;
              overflow: hidden; text-overflow: ellipsis;
            ">{task.title}</div>
            {#if height >= 36}
              <div style="
                font-size: 10px; color: var(--text-tertiary);
                margin-top: 2px;
              ">{formatTime(task.start_date!)}{task.end_date ? ` - ${formatTime(task.end_date)}` : ''}</div>
            {/if}
          </div>
        {/each}

        <!-- LLM suggestions (ghost blocks) -->
        {#each calendarStore.suggestions as suggestion (suggestion.task_id)}
          {@const top = timeToTop(suggestion.suggested_start)}
          {@const height = blockHeight(suggestion.suggested_start, suggestion.suggested_end)}
          <div style="
            position: absolute; top: {top}px; left: 4px; right: 4px;
            height: {Math.max(height, 48)}px;
            background: transparent;
            border: 1px dashed var(--accent);
            border-radius: 6px; padding: 6px 10px;
            overflow: hidden; z-index: 3;
            display: flex; flex-direction: column; justify-content: space-between;
          ">
            <div>
              <div style="
                font-size: var(--text-xs); font-weight: 500;
                color: var(--accent); white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis;
                opacity: 0.8;
              ">{suggestion.task_title}</div>
              {#if height >= 36}
                <div style="
                  font-size: 10px; color: var(--text-tertiary);
                  margin-top: 2px;
                ">{formatTime(suggestion.suggested_start)} - {formatTime(suggestion.suggested_end)}</div>
              {/if}
            </div>
            <div style="display: flex; gap: 4px; justify-content: flex-end;">
              <button
                onclick={() => acceptSuggestion(suggestion)}
                style="
                  height: 20px; padding: 0 8px; font-size: 10px; font-weight: 500;
                  border-radius: 4px; border: 1px solid var(--accent);
                  background: var(--accent-subtle); color: var(--accent);
                  cursor: pointer; font-family: var(--font-sans);
                  transition: all var(--transition-fast);
                "
              >Accept</button>
              <button
                onclick={() => calendarStore.removeSuggestion(suggestion.task_id)}
                style="
                  height: 20px; padding: 0 8px; font-size: 10px; font-weight: 500;
                  border-radius: 4px; border: 1px solid var(--border-default);
                  background: transparent; color: var(--text-tertiary);
                  cursor: pointer; font-family: var(--font-sans);
                  transition: all var(--transition-fast);
                "
              >Dismiss</button>
            </div>
          </div>
        {/each}

        <!-- Empty state (no events, no tasks, no suggestions) -->
        {#if calendarStore.events.length === 0 && scheduledTasks.length === 0 && calendarStore.suggestions.length === 0}
          <div style="
            position: absolute; top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
          ">
            <div style="
              font-size: var(--text-sm); color: var(--text-tertiary);
              font-style: italic;
            ">No events scheduled</div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  @keyframes calendar-spin {
    to { transform: rotate(360deg); }
  }
  @keyframes calendar-pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 0.6; }
  }
</style>

<script lang="ts">
  import { onMount } from 'svelte';

  let {
    value = '',
    onchange,
  }: {
    value?: string;
    onchange: (date: string | null) => void;
  } = $props();

  let open = $state(false);
  let ref: HTMLDivElement;

  // Current view month/year
  let viewYear = $state(new Date().getFullYear());
  let viewMonth = $state(new Date().getMonth());

  // Sync view to selected value when it changes
  $effect(() => {
    if (value) {
      const d = new Date(value + 'T00:00:00');
      if (!isNaN(d.getTime())) {
        viewYear = d.getFullYear();
        viewMonth = d.getMonth();
      }
    }
  });

  const DAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  const displayText = $derived.by(() => {
    if (!value) return '';
    const d = new Date(value + 'T00:00:00');
    if (isNaN(d.getTime())) return value;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  });

  const todayStr = $derived.by(() => {
    const t = new Date();
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`;
  });

  interface CalDay {
    date: number;
    month: number;
    year: number;
    key: string;
    isCurrentMonth: boolean;
  }

  const calendarDays = $derived.by((): CalDay[] => {
    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const daysInPrevMonth = new Date(viewYear, viewMonth, 0).getDate();

    const days: CalDay[] = [];

    // Previous month padding
    for (let i = firstDay - 1; i >= 0; i--) {
      const d = daysInPrevMonth - i;
      const m = viewMonth === 0 ? 11 : viewMonth - 1;
      const y = viewMonth === 0 ? viewYear - 1 : viewYear;
      days.push({ date: d, month: m, year: y, key: `${y}-${m}-${d}`, isCurrentMonth: false });
    }

    // Current month
    for (let d = 1; d <= daysInMonth; d++) {
      days.push({ date: d, month: viewMonth, year: viewYear, key: `${viewYear}-${viewMonth}-${d}`, isCurrentMonth: true });
    }

    // Next month padding (fill to 42 = 6 rows)
    const remaining = 42 - days.length;
    for (let d = 1; d <= remaining; d++) {
      const m = viewMonth === 11 ? 0 : viewMonth + 1;
      const y = viewMonth === 11 ? viewYear + 1 : viewYear;
      days.push({ date: d, month: m, year: y, key: `${y}-${m}-${d}`, isCurrentMonth: false });
    }

    return days;
  });

  function toDateStr(day: CalDay): string {
    return `${day.year}-${String(day.month + 1).padStart(2, '0')}-${String(day.date).padStart(2, '0')}`;
  }

  function selectDay(day: CalDay) {
    onchange(toDateStr(day));
    open = false;
  }

  function prevMonth() {
    if (viewMonth === 0) { viewMonth = 11; viewYear--; }
    else { viewMonth--; }
  }

  function nextMonth() {
    if (viewMonth === 11) { viewMonth = 0; viewYear++; }
    else { viewMonth++; }
  }

  function selectToday() {
    const t = new Date();
    viewYear = t.getFullYear();
    viewMonth = t.getMonth();
    onchange(todayStr);
    open = false;
  }

  function clear() {
    onchange(null);
    open = false;
  }

  onMount(() => {
    const handler = (e: MouseEvent) => {
      if (ref && !ref.contains(e.target as Node)) open = false;
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  });
</script>

<div bind:this={ref} style="position: relative; display: inline-flex;">
  <button
    type="button"
    onclick={() => open = !open}
    style="height: 40px; padding: 0 12px; font-size: 13.5px; font-weight: 400; color: {value ? 'var(--text-primary)' : 'var(--text-tertiary)'}; background: var(--bg-elevated); border: 1px solid {open ? 'var(--accent)' : 'var(--border-default)'}; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 150ms ease-out; outline: none; box-shadow: {open ? '0 0 0 2px rgba(232,119,46,0.15)' : 'none'}; font-family: var(--font-sans); min-width: 160px;"
  >
    <span style="opacity: 0.5; font-size: 14px;">&#128197;</span>
    <span>{displayText || 'Pick a date...'}</span>
  </button>

  {#if open}
    <div style="position: absolute; top: calc(100% + 4px); left: 0; z-index: 300; background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: 10px; box-shadow: var(--shadow-lg); padding: 12px; width: 280px; animation: fadeIn 100ms ease-out;">
      <!-- Month/Year header -->
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <button
          type="button"
          onclick={prevMonth}
          style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-secondary); cursor: pointer; border-radius: 6px; font-size: 14px; font-family: var(--font-sans);"
        >&lsaquo;</button>
        <span style="font-size: 14px; font-weight: 600; color: var(--text-primary);">
          {MONTHS[viewMonth]} {viewYear}
        </span>
        <button
          type="button"
          onclick={nextMonth}
          style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-secondary); cursor: pointer; border-radius: 6px; font-size: 14px; font-family: var(--font-sans);"
        >&rsaquo;</button>
      </div>

      <!-- Weekday headers -->
      <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; margin-bottom: 4px;">
        {#each DAYS as day (day)}
          <span style="text-align: center; font-size: 11px; font-weight: 500; color: var(--text-tertiary); padding: 4px 0;">{day}</span>
        {/each}
      </div>

      <!-- Day grid -->
      <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px;">
        {#each calendarDays as day (day.key)}
          {@const dateStr = toDateStr(day)}
          {@const isSelected = dateStr === value}
          {@const isToday = dateStr === todayStr}
          <button
            type="button"
            onclick={() => selectDay(day)}
            style="width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: {isSelected ? 600 : 400}; color: {isSelected ? 'white' : 'var(--text-primary)'}; background: {isSelected ? 'var(--accent)' : 'transparent'}; border: {isToday && !isSelected ? '1px solid rgba(232,119,46,0.4)' : '1px solid transparent'}; border-radius: 8px; cursor: pointer; opacity: {day.isCurrentMonth ? 1 : 0.3}; transition: all 100ms ease-out; font-family: var(--font-sans); margin: auto;"
          >
            {day.date}
          </button>
        {/each}
      </div>

      <!-- Footer -->
      <div style="display: flex; justify-content: space-between; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-subtle);">
        <button
          type="button"
          onclick={clear}
          style="background: none; border: none; color: var(--text-tertiary); font-size: 12.5px; cursor: pointer; font-family: var(--font-sans); padding: 4px 0;"
        >Clear</button>
        <button
          type="button"
          onclick={selectToday}
          style="background: none; border: none; color: var(--accent); font-size: 12.5px; cursor: pointer; font-weight: 500; font-family: var(--font-sans); padding: 4px 0;"
        >Today</button>
      </div>
    </div>
  {/if}
</div>

<script lang="ts">
  import { onMount } from 'svelte';

  let {
    value = '',
    onchange,
    initialOpen = false,
  }: {
    value?: string;
    onchange: (date: string | null) => void;
    initialOpen?: boolean;
  } = $props();

  let open = $state(false);

  // Set initial open state once on mount
  onMount(() => { if (initialOpen) open = true; });
  let ref: HTMLDivElement;

  // Current view month/year
  let viewYear = $state(new Date().getFullYear());
  let viewMonth = $state(new Date().getMonth());

  // Picker mode: calendar, month selector, year selector
  let pickerMode = $state<'calendar' | 'month' | 'year'>('calendar');

  // Text input state
  let inputValue = $state('');

  // Sync inputValue from value prop
  $effect(() => {
    inputValue = value || '';
  });

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
  const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  const todayStr = $derived.by(() => {
    const t = new Date();
    return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`;
  });

  // Year grid: 12 years centered on viewYear
  const yearGridStart = $derived(viewYear - (viewYear % 12));
  const yearGridYears = $derived(Array.from({ length: 12 }, (_, i) => yearGridStart + i));

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

  function isValidDateStr(s: string): boolean {
    return /^\d{4}-\d{2}-\d{2}$/.test(s) && !isNaN(new Date(s + 'T00:00:00').getTime());
  }

  function selectDay(day: CalDay) {
    onchange(toDateStr(day));
    open = false;
    pickerMode = 'calendar';
  }

  function selectMonth(month: number) {
    viewMonth = month;
    pickerMode = 'calendar';
  }

  function selectYear(year: number) {
    viewYear = year;
    pickerMode = 'month';
  }

  function prevNav() {
    if (pickerMode === 'calendar') {
      if (viewMonth === 0) { viewMonth = 11; viewYear--; }
      else { viewMonth--; }
    } else if (pickerMode === 'month') {
      viewYear--;
    } else {
      viewYear = yearGridStart - 12;
    }
  }

  function nextNav() {
    if (pickerMode === 'calendar') {
      if (viewMonth === 11) { viewMonth = 0; viewYear++; }
      else { viewMonth++; }
    } else if (pickerMode === 'month') {
      viewYear++;
    } else {
      viewYear = yearGridStart + 12;
    }
  }

  function selectToday() {
    const t = new Date();
    viewYear = t.getFullYear();
    viewMonth = t.getMonth();
    onchange(todayStr);
    open = false;
    pickerMode = 'calendar';
  }

  function clear() {
    onchange(null);
    open = false;
    pickerMode = 'calendar';
  }

  function handleInputBlur() {
    commitInput();
  }

  function handleInputKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      commitInput();
    }
  }

  function commitInput() {
    const trimmed = inputValue.trim();
    if (!trimmed) {
      onchange(null);
      return;
    }
    if (isValidDateStr(trimmed)) {
      onchange(trimmed);
    } else {
      // Revert to current value
      inputValue = value || '';
    }
  }

  function toggleCalendar() {
    open = !open;
    if (!open) pickerMode = 'calendar';
  }

  onMount(() => {
    const handler = (e: MouseEvent) => {
      if (ref && !ref.contains(e.target as Node)) {
        open = false;
        pickerMode = 'calendar';
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  });
</script>

<div bind:this={ref} style="position: relative; display: inline-flex;">
  <!-- Text input + calendar icon -->
  <div style="display: flex; align-items: center; gap: 0; height: 40px; background: var(--bg-elevated); border: 1px solid {open ? 'var(--accent)' : 'var(--border-default)'}; border-radius: 8px; transition: all 150ms ease-out; box-shadow: {open ? '0 0 0 2px rgba(232,119,46,0.15)' : 'none'};">
    <input
      type="text"
      bind:value={inputValue}
      onblur={handleInputBlur}
      onkeydown={handleInputKeydown}
      placeholder="YYYY-MM-DD"
      style="height: 100%; padding: 0 12px; font-size: 13.5px; font-weight: 400; color: var(--text-primary); background: transparent; border: none; outline: none; font-family: var(--font-sans); width: 120px;"
    />
    <button
      type="button"
      onclick={toggleCalendar}
      aria-label="Toggle calendar"
      style="height: 100%; padding: 0 10px; background: none; border: none; border-left: 1px solid var(--border-subtle); color: var(--text-tertiary); cursor: pointer; display: flex; align-items: center; font-size: 16px; border-radius: 0 8px 8px 0; transition: color 150ms;"
    >&#128197;</button>
  </div>

  {#if open}
    <div style="position: absolute; top: calc(100% + 4px); left: 0; z-index: 300; background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: 10px; box-shadow: var(--shadow-lg); padding: 12px; width: 280px; animation: fadeIn 100ms ease-out;">
      <!-- Header with nav arrows -->
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <button
          type="button"
          onclick={prevNav}
          style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-secondary); cursor: pointer; border-radius: 6px; font-size: 14px; font-family: var(--font-sans);"
        >&lsaquo;</button>

        {#if pickerMode === 'calendar'}
          <button
            type="button"
            onclick={() => pickerMode = 'month'}
            style="background: none; border: none; font-size: 14px; font-weight: 600; color: var(--text-primary); cursor: pointer; padding: 4px 8px; border-radius: 6px; font-family: var(--font-sans); transition: background 150ms;"
          >
            {MONTHS[viewMonth]} {viewYear}
          </button>
        {:else if pickerMode === 'month'}
          <button
            type="button"
            onclick={() => pickerMode = 'year'}
            style="background: none; border: none; font-size: 14px; font-weight: 600; color: var(--text-primary); cursor: pointer; padding: 4px 8px; border-radius: 6px; font-family: var(--font-sans); transition: background 150ms;"
          >
            {viewYear}
          </button>
        {:else}
          <span style="font-size: 14px; font-weight: 600; color: var(--text-primary);">
            {yearGridStart}&ndash;{yearGridStart + 11}
          </span>
        {/if}

        <button
          type="button"
          onclick={nextNav}
          style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-secondary); cursor: pointer; border-radius: 6px; font-size: 14px; font-family: var(--font-sans);"
        >&rsaquo;</button>
      </div>

      {#if pickerMode === 'calendar'}
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

      {:else if pickerMode === 'month'}
        <!-- Month grid (4x3) -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px;">
          {#each MONTHS_SHORT as month, i (month)}
            {@const isCurrentMonth = i === viewMonth && viewYear === new Date().getFullYear()}
            {@const isSelected = i === viewMonth}
            <button
              type="button"
              onclick={() => selectMonth(i)}
              style="height: 40px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: {isSelected ? 600 : 400}; color: {isSelected ? 'white' : 'var(--text-primary)'}; background: {isSelected ? 'var(--accent)' : 'transparent'}; border: {isCurrentMonth && !isSelected ? '1px solid rgba(232,119,46,0.4)' : '1px solid transparent'}; border-radius: 8px; cursor: pointer; transition: all 100ms ease-out; font-family: var(--font-sans);"
            >
              {month}
            </button>
          {/each}
        </div>

      {:else}
        <!-- Year grid (4x3) -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px;">
          {#each yearGridYears as year (year)}
            {@const isCurrentYear = year === new Date().getFullYear()}
            {@const isSelected = year === viewYear}
            <button
              type="button"
              onclick={() => selectYear(year)}
              style="height: 40px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: {isSelected ? 600 : 400}; color: {isSelected ? 'white' : 'var(--text-primary)'}; background: {isSelected ? 'var(--accent)' : 'transparent'}; border: {isCurrentYear && !isSelected ? '1px solid rgba(232,119,46,0.4)' : '1px solid transparent'}; border-radius: 8px; cursor: pointer; transition: all 100ms ease-out; font-family: var(--font-sans);"
            >
              {year}
            </button>
          {/each}
        </div>
      {/if}

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

<script lang="ts">
  import { onMount } from 'svelte';
  import { scheduleApi } from '$lib/api';
  import { addToast } from '$lib/stores/toast.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';
  import type { GoogleCalendar } from '$lib/types';

  let calendars = $state<GoogleCalendar[]>([]);
  let loading = $state(true);
  let error = $state(false);
  let saving = $state(false);

  async function fetchCalendars() {
    loading = true;
    error = false;
    try {
      const res = await scheduleApi.listCalendars();
      calendars = res.calendars;
    } catch {
      error = true;
    } finally {
      loading = false;
    }
  }

  async function saveCalendars() {
    saving = true;
    try {
      const enabledIds = calendars.filter(c => c.enabled).map(c => c.id);
      await scheduleApi.updateCalendars(enabledIds);
      addToast('Calendars updated', 'success');
    } catch {
      addToast('Failed to update calendars', 'error');
    } finally {
      saving = false;
    }
  }

  function toggleCalendar(id: string) {
    calendars = calendars.map(c => c.id === id ? { ...c, enabled: !c.enabled } : c);
    saveCalendars();
  }

  onMount(() => {
    fetchCalendars();
  });
</script>

<!-- Calendars -->
<div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px;">
  <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 12px; display: block;">Google Calendars</span>

  {#if loading}
    <div style="display: flex; flex-direction: column; gap: 8px;">
      {#each [1, 2, 3] as _ (_)}
        <div style="display: flex; align-items: center; gap: 10px; padding: 8px 10px;">
          <Skeleton width={8} height={8} radius={4} />
          <Skeleton width="60%" height={13} />
          <div style="margin-left: auto;">
            <Skeleton width={16} height={16} radius={3} />
          </div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 16px 0;">
      <span style="font-size: 13px; color: var(--text-tertiary);">Failed to load calendars.</span>
      <button
        onclick={fetchCalendars}
        style="font-size: 13px; color: var(--accent); background: none; border: 1px solid var(--accent); border-radius: 6px; padding: 4px 12px; cursor: pointer;"
      >
        Retry
      </button>
    </div>
  {:else if calendars.length === 0}
    <span style="font-size: 13px; color: var(--text-tertiary);">No calendars found.</span>
  {:else}
    <div style="display: flex; flex-direction: column; gap: 6px;">
      {#each calendars as calendar (calendar.id)}
        <label style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; font-size: 13px; cursor: pointer;">
          <div style="width: 8px; height: 8px; border-radius: 50%; background: {calendar.background_color}; flex-shrink: 0;"></div>
          <span style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary);">
            {calendar.summary}
            {#if calendar.primary}
              <span style="font-size: 11px; color: var(--text-tertiary); font-weight: 500; margin-left: 4px;">(Primary)</span>
            {/if}
          </span>
          <input
            type="checkbox"
            checked={calendar.enabled}
            onchange={() => toggleCalendar(calendar.id)}
            disabled={saving}
            style="accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer; flex-shrink: 0;"
          />
        </label>
      {/each}
    </div>
  {/if}
</div>

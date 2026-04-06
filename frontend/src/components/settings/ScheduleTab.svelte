<script lang="ts">
  import { onMount } from 'svelte';
  import { configApi } from '$lib/api';
  import { addToast } from '$lib/stores/toast.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';

  let weekdayStart = $state(8);
  let weekdayEnd = $state(18);
  let weekendStart = $state(10);
  let weekendEnd = $state(16);
  let weekendEnabled = $state(true);
  let loading = $state(true);
  let saved = $state(false);
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let savedTimer: ReturnType<typeof setTimeout> | undefined;

  function formatHour(h: number): string {
    if (h === 0) return '12:00 AM';
    if (h < 12) return `${h}:00 AM`;
    if (h === 12) return '12:00 PM';
    return `${h - 12}:00 PM`;
  }

  const hours = Array.from({ length: 24 }, (_, i) => i);

  onMount(async () => {
    try {
      const config = await configApi.get();
      weekdayStart = config.schedule_weekday_start;
      weekdayEnd = config.schedule_weekday_end;
      weekendStart = config.schedule_weekend_start;
      weekendEnd = config.schedule_weekend_end;
      weekendEnabled = config.schedule_weekend_enabled;
    } catch {
      addToast('Failed to load schedule preferences', 'error');
    } finally {
      loading = false;
    }
  });

  function debouncedSave() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        await configApi.update({
          schedule_weekday_start: weekdayStart,
          schedule_weekday_end: weekdayEnd,
          schedule_weekend_start: weekendStart,
          schedule_weekend_end: weekendEnd,
          schedule_weekend_enabled: weekendEnabled,
        });
        saved = true;
        clearTimeout(savedTimer);
        savedTimer = setTimeout(() => { saved = false; }, 2000);
      } catch {
        addToast('Failed to save schedule preferences', 'error');
      }
    }, 500);
  }
</script>

<div style="display: flex; flex-direction: column; gap: 16px;">
  <!-- Description -->
  <div style="padding: 0 2px;">
    <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0;">
      Configure when schedule suggestions should be made. These preferences are used by the AI when suggesting time blocks for your tasks.
    </p>
  </div>

  {#if loading}
    <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 20px;">
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <Skeleton width="30%" height={14} />
        <div style="display: flex; gap: 12px;">
          <Skeleton width="48%" height={36} radius={6} />
          <Skeleton width="48%" height={36} radius={6} />
        </div>
        <Skeleton width="30%" height={14} />
        <div style="display: flex; gap: 12px;">
          <Skeleton width="48%" height={36} radius={6} />
          <Skeleton width="48%" height={36} radius={6} />
        </div>
      </div>
    </div>
  {:else}
    <!-- Weekday Hours -->
    <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 20px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
        <span style="font-size: 13px; font-weight: 500; color: var(--text-primary);">Weekday hours</span>
        {#if saved}
          <span style="font-size: 12px; color: var(--accent); transition: opacity var(--transition-fast);">Saved</span>
        {/if}
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <div style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
          <label for="weekday-start" style="font-size: 11px; color: var(--text-tertiary);">Start</label>
          <select
            id="weekday-start"
            bind:value={weekdayStart}
            onchange={debouncedSave}
            style="width: 100%; padding: 8px 10px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto;"
          >
            {#each hours as h (h)}
              <option value={h}>{formatHour(h)}</option>
            {/each}
          </select>
        </div>
        <span style="color: var(--text-tertiary); margin-top: 18px; font-size: 13px;">to</span>
        <div style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
          <label for="weekday-end" style="font-size: 11px; color: var(--text-tertiary);">End</label>
          <select
            id="weekday-end"
            bind:value={weekdayEnd}
            onchange={debouncedSave}
            style="width: 100%; padding: 8px 10px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto;"
          >
            {#each hours as h (h)}
              <option value={h}>{formatHour(h)}</option>
            {/each}
          </select>
        </div>
      </div>
    </div>

    <!-- Weekend Hours -->
    <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 20px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
        <span style="font-size: 13px; font-weight: 500; color: var(--text-primary);">Weekend hours</span>
      </div>

      <!-- Weekend toggle -->
      <label style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px; cursor: pointer;">
        <input
          type="checkbox"
          bind:checked={weekendEnabled}
          onchange={debouncedSave}
          style="accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer;"
        />
        <span style="font-size: 13px; color: var(--text-secondary);">Enable suggestions on weekends</span>
      </label>

      <!-- Weekend hour selects -->
      <div style="display: flex; gap: 12px; align-items: center; opacity: {weekendEnabled ? 1 : 0.4}; pointer-events: {weekendEnabled ? 'auto' : 'none'}; transition: opacity var(--transition-fast);">
        <div style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
          <label for="weekend-start" style="font-size: 11px; color: var(--text-tertiary);">Start</label>
          <select
            id="weekend-start"
            bind:value={weekendStart}
            onchange={debouncedSave}
            disabled={!weekendEnabled}
            style="width: 100%; padding: 8px 10px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto;"
          >
            {#each hours as h (h)}
              <option value={h}>{formatHour(h)}</option>
            {/each}
          </select>
        </div>
        <span style="color: var(--text-tertiary); margin-top: 18px; font-size: 13px;">to</span>
        <div style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
          <label for="weekend-end" style="font-size: 11px; color: var(--text-tertiary);">End</label>
          <select
            id="weekend-end"
            bind:value={weekendEnd}
            onchange={debouncedSave}
            disabled={!weekendEnabled}
            style="width: 100%; padding: 8px 10px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto;"
          >
            {#each hours as h (h)}
              <option value={h}>{formatHour(h)}</option>
            {/each}
          </select>
        </div>
      </div>
    </div>
  {/if}
</div>

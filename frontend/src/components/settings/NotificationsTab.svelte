<script lang="ts">
  import { onMount } from 'svelte';
  import { configApi, notificationsApi } from '$lib/api';
  import {
    disablePush,
    enablePush,
    getExistingSubscription,
    getPermission,
    getPushSupport,
    type PushSupport,
  } from '$lib/push';
  import { addToast } from '$lib/stores/toast.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';

  // Push state
  let support = $state<PushSupport>('supported');
  let subscribed = $state(false);
  let busy = $state(false);

  // Config state
  let digestEnabled = $state(true);
  let remindersEnabled = $state(true);
  let nudgesEnabled = $state(true);
  let reviewEnabled = $state(true);
  let digestHour = $state(8);
  let reviewHour = $state(21);
  let maxPerDay = $state(5);
  let maxNudgesPerDay = $state(2);
  let reminderLeadHours = $state(2);
  let quietStart = $state(22);
  let quietEnd = $state(7);
  let nudgeRunsPerDay = $state(3);
  let timezone = $state('UTC');

  let loading = $state(true);
  let saved = $state(false);
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let savedTimer: ReturnType<typeof setTimeout> | undefined;

  const hours = Array.from({ length: 24 }, (_, i) => i);

  function formatHour(h: number): string {
    if (h === 0) return '12:00 AM';
    if (h < 12) return `${h}:00 AM`;
    if (h === 12) return '12:00 PM';
    return `${h - 12}:00 PM`;
  }

  onMount(async () => {
    support = getPushSupport();
    if (support === 'supported') {
      try {
        subscribed = (await getExistingSubscription()) !== null && getPermission() === 'granted';
      } catch {
        subscribed = false;
      }
    }
    try {
      const config = await configApi.get();
      digestEnabled = config.notif_digest_enabled;
      remindersEnabled = config.notif_reminders_enabled;
      nudgesEnabled = config.notif_nudges_enabled;
      reviewEnabled = config.notif_review_enabled;
      digestHour = parseInt(config.notif_digest_time.split(':')[0], 10);
      reviewHour = parseInt(config.notif_review_time.split(':')[0], 10);
      maxPerDay = config.notif_max_per_day;
      maxNudgesPerDay = config.notif_max_nudges_per_day;
      reminderLeadHours = config.notif_reminder_lead_hours;
      quietStart = config.notif_quiet_start;
      quietEnd = config.notif_quiet_end;
      nudgeRunsPerDay = config.notif_nudge_runs_per_day;
      timezone = config.notif_timezone;
      // First visit: adopt the browser's timezone automatically
      const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (timezone === 'UTC' && browserTz && browserTz !== 'UTC') {
        timezone = browserTz;
        await configApi.update({ notif_timezone: browserTz });
      }
    } catch {
      addToast('Failed to load notification settings', 'error');
    } finally {
      loading = false;
    }
  });

  function debouncedSave() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        await configApi.update({
          notif_digest_enabled: digestEnabled,
          notif_reminders_enabled: remindersEnabled,
          notif_nudges_enabled: nudgesEnabled,
          notif_review_enabled: reviewEnabled,
          notif_digest_time: `${String(digestHour).padStart(2, '0')}:00`,
          notif_review_time: `${String(reviewHour).padStart(2, '0')}:00`,
          notif_max_per_day: maxPerDay,
          notif_max_nudges_per_day: maxNudgesPerDay,
          notif_reminder_lead_hours: reminderLeadHours,
          notif_quiet_start: quietStart,
          notif_quiet_end: quietEnd,
          notif_nudge_runs_per_day: nudgeRunsPerDay,
          notif_timezone: timezone,
        });
        saved = true;
        clearTimeout(savedTimer);
        savedTimer = setTimeout(() => { saved = false; }, 2000);
      } catch {
        addToast('Failed to save notification settings', 'error');
      }
    }, 500);
  }

  async function togglePush() {
    busy = true;
    try {
      if (subscribed) {
        await disablePush();
        subscribed = false;
        addToast('Notifications disabled on this device', 'success');
      } else {
        await enablePush();
        subscribed = true;
        addToast('Notifications enabled on this device', 'success');
      }
    } catch (e) {
      addToast(e instanceof Error ? e.message : 'Failed to update push subscription', 'error');
    } finally {
      busy = false;
    }
  }

  async function sendTest() {
    busy = true;
    try {
      const { success } = await notificationsApi.sendTest();
      if (success) {
        addToast('Test notification sent', 'success');
      } else {
        addToast('No subscribed devices found', 'error');
      }
    } catch {
      addToast('Failed to send test notification', 'error');
    } finally {
      busy = false;
    }
  }
</script>

<div style="display: flex; flex-direction: column; gap: 16px;">
  <!-- Description -->
  <div style="padding: 0 2px;">
    <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0;">
      Get push notifications on your phone: a morning digest, due-date reminders, AI nudges, and an evening review. On iPhone, add Cognito to your home screen first (Share &rarr; Add to Home Screen).
    </p>
  </div>

  {#if loading}
    <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 20px;">
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <Skeleton width="30%" height={14} />
        <Skeleton width="60%" height={36} radius={6} />
        <Skeleton width="30%" height={14} />
        <Skeleton width="80%" height={36} radius={6} />
        <Skeleton width="80%" height={36} radius={6} />
      </div>
    </div>
  {:else}
    <!-- This device -->
    <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 20px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
        <span style="font-size: 13px; font-weight: 500; color: var(--text-primary);">This browser</span>
      </div>
      <p style="font-size: 12px; color: var(--text-tertiary); line-height: 1.5; margin: 0 0 12px 0;">
        Each browser and installed home-screen app subscribes separately — enable notifications in every place you want to receive them.
      </p>
      {#if support === 'needs-install'}
        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0;">
          To receive notifications on iPhone, add Cognito to your home screen: tap the Share button in Safari, then "Add to Home Screen", and open the app from there.
        </p>
      {:else if support === 'unsupported'}
        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0;">
          This browser doesn't support push notifications.
        </p>
      {:else}
        <div style="display: flex; gap: 10px; align-items: center;">
          <button
            onclick={togglePush}
            disabled={busy}
            style="padding: 8px 14px; background: {subscribed ? 'var(--bg-base)' : 'var(--accent)'}; border: 1px solid {subscribed ? 'var(--border-subtle)' : 'var(--accent)'}; border-radius: 6px; color: {subscribed ? 'var(--text-primary)' : 'var(--bg-base)'}; font-family: var(--font-sans); font-size: 13px; font-weight: 500; cursor: {busy ? 'wait' : 'pointer'}; opacity: {busy ? 0.6 : 1}; transition: opacity var(--transition-fast);"
          >
            {subscribed ? 'Disable notifications' : 'Enable notifications'}
          </button>
          {#if subscribed}
            <button
              onclick={sendTest}
              disabled={busy}
              style="padding: 8px 14px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-secondary); font-family: var(--font-sans); font-size: 13px; font-weight: 500; cursor: {busy ? 'wait' : 'pointer'}; opacity: {busy ? 0.6 : 1}; transition: opacity var(--transition-fast);"
            >
              Send test
            </button>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Notification types -->
    <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 20px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
        <span style="font-size: 13px; font-weight: 500; color: var(--text-primary);">Notification types</span>
        {#if saved}
          <span style="font-size: 12px; color: var(--accent); transition: opacity var(--transition-fast);">Saved</span>
        {/if}
      </div>
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <!-- Morning digest -->
        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; flex-wrap: wrap;">
          <input
            type="checkbox"
            bind:checked={digestEnabled}
            onchange={debouncedSave}
            style="accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer;"
          />
          <span style="font-size: 13px; color: var(--text-secondary);">Morning digest at</span>
          <select
            bind:value={digestHour}
            onchange={debouncedSave}
            disabled={!digestEnabled}
            aria-label="Morning digest time"
            style="padding: 6px 8px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto; opacity: {digestEnabled ? 1 : 0.4};"
          >
            {#each hours as h (h)}
              <option value={h}>{formatHour(h)}</option>
            {/each}
          </select>
        </label>

        <!-- Due-date reminders -->
        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; flex-wrap: wrap;">
          <input
            type="checkbox"
            bind:checked={remindersEnabled}
            onchange={debouncedSave}
            style="accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer;"
          />
          <span style="font-size: 13px; color: var(--text-secondary);">Due-date reminders,</span>
          <select
            bind:value={reminderLeadHours}
            onchange={debouncedSave}
            disabled={!remindersEnabled}
            aria-label="Reminder lead time in hours"
            style="padding: 6px 8px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto; opacity: {remindersEnabled ? 1 : 0.4};"
          >
            {#each ([1, 2, 4, 8] as const) as h (h)}
              <option value={h}>{h}</option>
            {/each}
          </select>
          <span style="font-size: 13px; color: var(--text-secondary);">h before due</span>
        </label>

        <!-- AI nudges -->
        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; flex-wrap: wrap;">
          <input
            type="checkbox"
            bind:checked={nudgesEnabled}
            onchange={debouncedSave}
            style="accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer;"
          />
          <span style="font-size: 13px; color: var(--text-secondary);">AI nudges,</span>
          <select
            bind:value={nudgeRunsPerDay}
            onchange={debouncedSave}
            disabled={!nudgesEnabled}
            aria-label="AI nudge evaluations per day"
            style="padding: 6px 8px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto; opacity: {nudgesEnabled ? 1 : 0.4};"
          >
            {#each ([1, 2, 3, 4] as const) as n (n)}
              <option value={n}>{n}</option>
            {/each}
          </select>
          <span style="font-size: 13px; color: var(--text-secondary);">&times; per day</span>
        </label>

        <!-- Evening review -->
        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; flex-wrap: wrap;">
          <input
            type="checkbox"
            bind:checked={reviewEnabled}
            onchange={debouncedSave}
            style="accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer;"
          />
          <span style="font-size: 13px; color: var(--text-secondary);">Evening review at</span>
          <select
            bind:value={reviewHour}
            onchange={debouncedSave}
            disabled={!reviewEnabled}
            aria-label="Evening review time"
            style="padding: 6px 8px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto; opacity: {reviewEnabled ? 1 : 0.4};"
          >
            {#each hours as h (h)}
              <option value={h}>{formatHour(h)}</option>
            {/each}
          </select>
        </label>
      </div>
    </div>

    <!-- Guardrails -->
    <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; padding: 20px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
        <span style="font-size: 13px; font-weight: 500; color: var(--text-primary);">Guardrails</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
          <label for="notif-max-per-day" style="font-size: 13px; color: var(--text-secondary);">Max notifications per day</label>
          <select
            id="notif-max-per-day"
            bind:value={maxPerDay}
            onchange={debouncedSave}
            style="padding: 6px 8px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto;"
          >
            {#each ([3, 5, 8, 12] as const) as n (n)}
              <option value={n}>{n}</option>
            {/each}
          </select>
        </div>

        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
          <label for="notif-max-nudges" style="font-size: 13px; color: var(--text-secondary);">Max AI nudges per day</label>
          <select
            id="notif-max-nudges"
            bind:value={maxNudgesPerDay}
            onchange={debouncedSave}
            style="padding: 6px 8px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto;"
          >
            {#each ([1, 2, 3, 4] as const) as n (n)}
              <option value={n}>{n}</option>
            {/each}
          </select>
        </div>

        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
          <label for="notif-quiet-start" style="font-size: 13px; color: var(--text-secondary);">Quiet hours</label>
          <div style="display: flex; align-items: center; gap: 8px;">
            <select
              id="notif-quiet-start"
              bind:value={quietStart}
              onchange={debouncedSave}
              style="padding: 6px 8px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto;"
            >
              {#each hours as h (h)}
                <option value={h}>{formatHour(h)}</option>
              {/each}
            </select>
            <span style="font-size: 13px; color: var(--text-tertiary);">to</span>
            <select
              id="notif-quiet-end"
              bind:value={quietEnd}
              onchange={debouncedSave}
              aria-label="Quiet hours end"
              style="padding: 6px 8px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; outline: none; cursor: pointer; appearance: auto;"
            >
              {#each hours as h (h)}
                <option value={h}>{formatHour(h)}</option>
              {/each}
            </select>
          </div>
        </div>

        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
          <span style="font-size: 13px; color: var(--text-secondary);">Timezone</span>
          <span style="font-size: 13px; color: var(--text-secondary); font-family: var(--font-mono);">{timezone}</span>
        </div>
      </div>
    </div>
  {/if}
</div>

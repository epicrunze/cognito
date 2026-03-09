<script lang="ts">
  import { authStore } from '$lib/stores.svelte';
  import { configApi } from '$lib/api';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import Button from '$components/ui/Button.svelte';

  let systemPrompt = $state('');
  let saved = $state(false);
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let savedTimer: ReturnType<typeof setTimeout> | undefined;

  onMount(async () => {
    try {
      const config = await configApi.get();
      systemPrompt = config.system_prompt_override ?? '';
    } catch {
      // ignore fetch errors on mount
    }
  });

  function handleInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        await configApi.update({ system_prompt_override: systemPrompt || null });
        saved = true;
        clearTimeout(savedTimer);
        savedTimer = setTimeout(() => { saved = false; }, 2000);
      } catch {
        // save failed silently
      }
    }, 500);
  }
</script>

<div style="max-width: 600px; padding: 40px 24px;">
  <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 24px;">Settings</h2>

  <!-- Account -->
  <div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; margin-bottom: 16px;">
    <div style="margin-bottom: 16px;">
      <span style="font-size: 13px; color: var(--text-tertiary);">Signed in as</span>
      <div style="font-size: 15px; color: var(--text-primary); margin-top: 4px;">{authStore.user?.email ?? ''}</div>
    </div>
    <Button variant="outline" size="sm" onclick={async () => { await authStore.logout(); goto('/login'); }}>
      Sign out
    </Button>
  </div>

  <!-- Navigation -->
  <div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; margin-bottom: 16px;">
    <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 12px; display: block;">Manage</span>
    <a href="/settings/labels" style="display: flex; align-items: center; gap: 8px; padding: 8px 0; color: var(--text-primary); text-decoration: none; font-size: 14px; transition: color 150ms;">
      Labels
      <span style="color: var(--text-tertiary); font-size: 12px;">→</span>
    </a>
  </div>

  <!-- AI Behavior -->
  <div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
      <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">AI Behavior</span>
      {#if saved}
        <span style="font-size: 12px; color: var(--accent); transition: opacity 150ms;">Saved</span>
      {/if}
    </div>
    <textarea
      bind:value={systemPrompt}
      oninput={handleInput}
      placeholder="Custom instructions for task extraction, e.g.:&#10;&#8226; Always categorize tasks into specific projects&#10;&#8226; Prefer high priority for deadline-sensitive items"
      style="width: 100%; min-height: 100px; padding: 10px 12px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; color: var(--text-primary); font-size: 14px; font-family: inherit; line-height: 1.5; resize: vertical; outline: none; transition: border-color 150ms;"
    ></textarea>
    <span style="font-size: 12px; color: var(--text-tertiary); margin-top: 8px; display: block;">
      These instructions guide how the AI extracts and categorizes tasks from your input.
    </span>
  </div>
</div>

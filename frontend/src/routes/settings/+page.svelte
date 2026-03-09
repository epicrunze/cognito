<script lang="ts">
  import { authStore } from '$lib/stores.svelte';
  import { goto } from '$app/navigation';
  import Button from '$components/ui/Button.svelte';
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
  <div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px;">
    <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 12px; display: block;">Manage</span>
    <a href="/settings/labels" style="display: flex; align-items: center; gap: 8px; padding: 8px 0; color: var(--text-primary); text-decoration: none; font-size: 14px; transition: color 150ms;">
      Labels
      <span style="color: var(--text-tertiary); font-size: 12px;">→</span>
    </a>
  </div>
</div>

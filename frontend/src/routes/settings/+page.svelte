<script lang="ts">
  import { authStore } from '$lib/stores.svelte';
  import { goto } from '$app/navigation';
  import Button from '$components/ui/Button.svelte';
</script>

<div style="max-width: 600px; padding: 40px 24px;">
  <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 24px;">Settings</h2>

  <div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px;">
    <div style="margin-bottom: 16px;">
      <span style="font-size: 13px; color: var(--text-tertiary);">Signed in as</span>
      <div style="font-size: 15px; color: var(--text-primary); margin-top: 4px;">{authStore.user?.email ?? ''}</div>
    </div>
    <Button variant="outline" size="sm" onclick={async () => { await authStore.logout(); goto('/login'); }}>
      Sign out
    </Button>
  </div>
</div>

<script lang="ts">
  import { authApi } from '$lib/api';
  import Button from '$components/ui/Button.svelte';
</script>

<div style="display: flex; align-items: center; justify-content: center; min-height: 100vh; background: var(--bg-base);">
  <div style="display: flex; flex-direction: column; align-items: center; gap: 32px; padding: 48px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; box-shadow: var(--shadow-lg); max-width: 400px; width: 100%;">
    <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
      <span style="font-size: 28px; font-weight: 600; letter-spacing: -0.03em; color: var(--accent);">cognito</span>
      <span style="font-size: 14px; color: var(--text-tertiary);">AI-powered task extraction</span>
    </div>

    <a href={authApi.loginUrl()} style="text-decoration: none; width: 100%;">
      <Button variant="accent" style="width: 100%; justify-content: center;">
        Sign in with Google
      </Button>
    </a>

    <span style="font-size: 12px; color: var(--text-tertiary);">
      Only authorized accounts can access this app.
    </span>
  </div>
</div>

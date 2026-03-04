<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { getMe, loginUrl } from '$lib/api';
  import { appState } from '$lib/stores.svelte';

  let { children } = $props();

  onMount(async () => {
    try {
      const me = await getMe();
      appState.user = me;
    } catch {
      appState.user = null;
    } finally {
      appState.authChecked = true;
    }
  });
</script>

<div class="min-h-screen flex flex-col">
  <!-- Top navigation bar -->
  <header class="border-b border-surface-800 bg-surface-900/80 backdrop-blur-sm sticky top-0 z-50">
    <div class="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
          <span class="text-white font-bold text-sm">C</span>
        </div>
        <h1 class="text-surface-100 font-semibold text-lg tracking-tight">Cognito</h1>
        <span class="text-surface-600 text-sm hidden sm:block">Task Agent</span>
      </div>

      <nav class="flex items-center gap-2">
        <a
          href="http://localhost:3456"
          target="_blank"
          rel="noopener noreferrer"
          class="btn-ghost text-sm"
          title="Open Vikunja">
          Vikunja ↗
        </a>

        {#if appState.authChecked}
          {#if appState.user}
            <div class="flex items-center gap-2">
              {#if appState.user.picture}
                <img
                  src={appState.user.picture}
                  alt={appState.user.name}
                  class="w-7 h-7 rounded-full ring-1 ring-surface-700"
                />
              {/if}
              <span class="text-surface-400 text-sm hidden sm:block">{appState.user.name}</span>
            </div>
          {:else}
            <a href={loginUrl()} class="btn-primary text-sm py-1.5">Sign in</a>
          {/if}
        {/if}
      </nav>
    </div>
  </header>

  <!-- Main content -->
  <main class="flex-1 max-w-4xl mx-auto w-full px-4 py-6">
    {#if !appState.authChecked}
      <div class="flex items-center justify-center h-64">
        <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    {:else if !appState.user}
      <div class="flex flex-col items-center justify-center h-64 gap-4">
        <div class="text-6xl">🔐</div>
        <p class="text-surface-400 text-center max-w-sm">
          Sign in with your Google account to start extracting tasks.
        </p>
        <a href={loginUrl()} class="btn-primary">Sign in with Google</a>
      </div>
    {:else}
      {@render children()}
    {/if}
  </main>
</div>

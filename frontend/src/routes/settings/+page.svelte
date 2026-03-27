<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import AccountTab from '$components/settings/AccountTab.svelte';
  import AIBehaviorTab from '$components/settings/AIBehaviorTab.svelte';
  import LabelsTab from '$components/settings/LabelsTab.svelte';
  import HistoryTab from '$components/settings/HistoryTab.svelte';

  const tabs = [
    { id: 'account', label: 'Account', icon: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2|M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8' },
    { id: 'ai', label: 'AI & Agent', icon: 'm12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z' },
    { id: 'labels', label: 'Labels', icon: 'M12 2H2v10l9.29 9.29a1.58 1.58 0 0 0 2.24 0l6.18-6.18a1.58 1.58 0 0 0 0-2.24L12 2Z|M7 7h.01' },
    { id: 'history', label: 'History', icon: 'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8|M3 3v5h5|M12 7v5l4 2' },
  ] as const;

  const activeTab = $derived($page.url.searchParams.get('tab') ?? 'account');

  function setTab(id: string) {
    goto(`/settings?tab=${id}`, { replaceState: true });
  }
</script>

<div class="settings-layout">
  <!-- Left nav -->
  <nav class="settings-nav">
    <h2 class="settings-title">Settings</h2>
    {#each tabs as tab (tab.id)}
      <button
        class="nav-item"
        class:active={activeTab === tab.id}
        onclick={() => setTab(tab.id)}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          {#each tab.icon.split('|') as d, i (i)}
            <path d={d}/>
          {/each}
        </svg>
        {tab.label}
      </button>
    {/each}
  </nav>

  <!-- Right content -->
  <div class="settings-content">
    {#if activeTab === 'account'}
      <AccountTab />
    {:else if activeTab === 'ai'}
      <AIBehaviorTab />
    {:else if activeTab === 'labels'}
      <LabelsTab />
    {:else if activeTab === 'history'}
      <HistoryTab />
    {/if}
  </div>
</div>

<style>
  .settings-layout {
    display: flex;
    height: 100%;
    max-width: 900px;
  }

  .settings-nav {
    width: 200px;
    flex-shrink: 0;
    padding: 32px 16px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .settings-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 20px 8px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 9px 12px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-tertiary);
    background: none;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    text-align: left;
    font-family: var(--font-sans);
    transition: color var(--transition-fast), background var(--transition-fast);
  }

  .nav-item:hover {
    color: var(--text-secondary);
    background: var(--bg-surface-hover);
  }

  .nav-item.active {
    color: var(--text-primary);
    background: var(--bg-surface);
  }

  .settings-content {
    flex: 1;
    min-width: 0;
    padding: 32px 24px;
    overflow-y: auto;
    max-width: 640px;
  }

  @media (max-width: 767px) {
    .settings-layout {
      flex-direction: column;
    }

    .settings-nav {
      width: 100%;
      flex-direction: row;
      overflow-x: auto;
      padding: 16px 16px 0;
      gap: 0;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: none;
    }

    .settings-nav::-webkit-scrollbar {
      display: none;
    }

    .settings-title {
      display: none;
    }

    .nav-item {
      flex-shrink: 0;
      padding: 8px 12px;
      white-space: nowrap;
    }

    .settings-content {
      padding: 20px 16px;
    }
  }
</style>

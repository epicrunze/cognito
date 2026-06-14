<script lang="ts">
  // Mobile bottom navigation — up to four exclusive destinations with an
  // optional raised tangerine capture button in the center (Cognito's one
  // persistent action). Built-in geometric glyphs; mono micro-labels.
  type Tab = { value: string; label: string };
  let {
    tabs,
    active,
    onchange,
    oncapture,
    captureVariant = 'brand',
    safeArea = 18,
  }: {
    tabs: Tab[];
    active: string;
    onchange?: (value: string) => void;
    oncapture?: () => void;
    captureVariant?: 'brand' | 'plus';
    safeArea?: number;
  } = $props();

  const left = $derived(oncapture ? tabs.slice(0, Math.ceil(tabs.length / 2)) : tabs);
  const right = $derived(oncapture ? tabs.slice(Math.ceil(tabs.length / 2)) : []);
</script>

{#snippet glyph(kind: string, on: boolean)}
  {@const c = on ? 'var(--text-primary)' : 'var(--text-tertiary)'}
  {#if kind === 'projects'}
    <svg width="22" height="22" viewBox="0 0 22 22"><circle cx="11" cy="11" r="7.5" stroke={c} stroke-width="1.4" fill="none" /></svg>
  {:else if kind === 'upcoming'}
    <svg width="22" height="22" viewBox="0 0 22 22" stroke={c} stroke-width="1.4" stroke-linecap="round" fill="none"><rect x="3.5" y="5" width="15" height="13" rx="2.5" /><path d="M3.5 9.5h15M7.5 3.5v3M14.5 3.5v3" /></svg>
  {:else if kind === 'search'}
    <svg width="22" height="22" viewBox="0 0 22 22" stroke={c} stroke-width="1.4" stroke-linecap="round" fill="none"><circle cx="9.5" cy="9.5" r="5.5" /><path d="M13.7 13.7L18 18" /></svg>
  {:else}
    <svg width="22" height="22" viewBox="0 0 22 22" stroke={c} stroke-width="1.4" stroke-linecap="round" fill="none"><circle cx="7" cy="8" r="3.2" /><circle cx="15.5" cy="12.5" r="2.4" /><circle cx="8.5" cy="16" r="1.6" /></svg>
  {/if}
{/snippet}

{#snippet tabButton(tab: Tab)}
  {@const on = active === tab.value}
  <button class="tab" class:on aria-current={on ? 'page' : undefined} onclick={() => onchange?.(tab.value)}>
    {@render glyph(tab.value, on)}
    {#if tab.label}<span class="tab-label">{tab.label}</span>{/if}
  </button>
{/snippet}

<nav class="tabbar" style="padding-bottom: {safeArea}px;">
  <div class="tabbar-row">
    {#each left as t (t.value)}
      {@render tabButton(t)}
    {/each}
    {#if oncapture}
      <div class="capture-slot">
        {#if captureVariant === 'brand'}
          <button class="capture brand" aria-label="New thought" onclick={oncapture}>
            <svg width="29" height="29" viewBox="0 0 40 40" fill="none" style="display: block;">
              <circle cx="13" cy="11" r="4.5" fill="var(--tangerine)" />
              <circle cx="27" cy="9" r="3" fill="var(--tangerine)" />
              <circle cx="11" cy="27" r="3" fill="var(--tangerine)" />
              <circle cx="29" cy="25" r="4.5" fill="var(--tangerine)" />
            </svg>
            <span class="capture-badge">
              <svg width="10" height="10" viewBox="0 0 11 11" fill="none"><path d="M5.5 1.5v8M1.5 5.5h8" stroke="var(--text-on-accent)" stroke-width="1.8" stroke-linecap="round" /></svg>
            </span>
          </button>
        {:else}
          <button class="capture plus" aria-label="New thought" onclick={oncapture}>
            <svg width="20" height="20" viewBox="0 0 20 20"><path d="M10 4v12M4 10h12" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
          </button>
        {/if}
      </div>
    {/if}
    {#each right as t (t.value)}
      {@render tabButton(t)}
    {/each}
  </div>
</nav>

<style>
  .tabbar {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 100;
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-base);
  }
  .tabbar-row {
    display: flex;
    align-items: flex-start;
    padding: 0 8px;
  }
  .tab {
    flex: 1;
    min-width: 0;
    background: none;
    border: none;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding-top: 10px;
    min-height: 48px;
  }
  .tab-label {
    font: var(--type-data);
    font-size: var(--text-2xs);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-tertiary);
    opacity: 0.7;
  }
  .tab.on .tab-label {
    color: var(--text-secondary);
    opacity: 1;
  }
  .capture-slot {
    flex: 1;
    display: flex;
    justify-content: center;
  }
  .capture {
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: -16px;
    box-shadow: var(--shadow-lift);
    border-radius: 50%;
  }
  .capture.brand {
    position: relative;
    width: 52px;
    height: 52px;
    background: var(--surface-card);
    border: 1.5px solid var(--border-strong);
  }
  .capture.plus {
    width: 50px;
    height: 50px;
    border: none;
    background: var(--action-bg);
    color: var(--text-on-accent);
  }
  .capture-badge {
    position: absolute;
    right: -2px;
    bottom: -2px;
    width: 19px;
    height: 19px;
    border-radius: 50%;
    background: var(--tangerine);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--shadow-rest);
  }
</style>

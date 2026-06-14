<script lang="ts">
  // The LLM-maintained "where this project is at" block. AI-touched tone:
  // tangerine edge + diamond say who wrote it. Stale fades the text and
  // promotes Regenerate to a tinted action.
  let {
    text = '',
    generatedLabel = '',
    stale = false,
    generating = false,
    onRegenerate,
  }: {
    text?: string;
    generatedLabel?: string;
    stale?: boolean;
    generating?: boolean;
    onRegenerate?: () => void;
  } = $props();
</script>

<div class="briefing">
  <span class="edge"></span>
  <div class="head">
    <svg width="9" height="9" viewBox="0 0 10 10" style="flex-shrink: 0;">
      <rect x="2.2" y="2.2" width="5.6" height="5.6" fill="none" stroke="var(--ai)" stroke-width="1.2" transform="rotate(45 5 5)"></rect>
    </svg>
    <span class="label">status</span>
    <span class="meta">{generating ? 'thinking…' : stale ? 'stale · tasks changed' : generatedLabel}</span>
    <span style="flex: 1;"></span>
    {#if stale && !generating}
      <button class="regen-btn" onclick={onRegenerate}>
        <svg width="11" height="11" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><path d="M12 7a5 5 0 1 1-1.5-3.6"></path><path d="M12 1.5V4h-2.5"></path></svg>
        Regenerate
      </button>
    {:else}
      <button class="regen-icon" title="Regenerate" disabled={generating} onclick={onRegenerate} aria-label="Regenerate briefing">
        <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><path d="M12 7a5 5 0 1 1-1.5-3.6"></path><path d="M12 1.5V4h-2.5"></path></svg>
      </button>
    {/if}
  </div>
  <div class="body" class:dim={stale || generating}>{text}</div>
</div>

<style>
  .briefing {
    position: relative;
    background: var(--surface-card);
    border-radius: var(--radius-card);
    border: 1px solid var(--border-subtle);
    box-shadow: var(--shadow-rest);
    padding: 16px 18px 15px 21px;
    box-sizing: border-box;
  }
  .edge {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 2px;
    background: var(--ai);
    opacity: 0.8;
    border-top-left-radius: var(--radius-card);
    border-bottom-left-radius: var(--radius-card);
  }
  .head {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 9px;
  }
  .label {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ai);
  }
  .meta {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-tertiary);
    opacity: 0.8;
    letter-spacing: 0.04em;
  }
  .regen-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: none;
    border-radius: var(--radius-inner);
    cursor: pointer;
    background: var(--action-tint);
    color: var(--tangerine);
    font-family: var(--font-sans);
    font-size: 12px;
    font-weight: var(--font-medium);
    padding: 4px 9px;
  }
  .regen-icon {
    width: 26px;
    height: 26px;
    border-radius: var(--radius-inner);
    border: none;
    cursor: pointer;
    padding: 0;
    background: transparent;
    color: var(--text-tertiary);
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .regen-icon:disabled {
    cursor: default;
  }
  .body {
    font-family: var(--font-sans);
    font-size: 15px;
    line-height: var(--leading-normal);
    color: var(--text-primary);
    text-wrap: pretty;
    max-width: 680px;
    transition: color var(--t-normal) var(--ease-out);
  }
  .body.dim {
    color: var(--text-tertiary);
  }
</style>

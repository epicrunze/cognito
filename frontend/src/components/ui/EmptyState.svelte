<script lang="ts">
  import type { Snippet } from 'svelte';
  // A quiet, intentional state — not a void. A faint breathing constellation
  // glyph, a calm line, an optional action. Centered.
  let {
    title,
    hint = '',
    action,
  }: {
    title: string;
    hint?: string;
    action?: Snippet;
  } = $props();
</script>

<div class="empty-state">
  <span class="glyph">
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
      <circle cx="13" cy="11" r="4" fill="currentColor" />
      <circle cx="27" cy="9" r="2.5" fill="currentColor" />
      <circle cx="11" cy="27" r="2.5" fill="currentColor" />
      <circle cx="29" cy="25" r="4" fill="currentColor" />
    </svg>
  </span>
  <span class="title">{title}</span>
  {#if hint}<span class="hint">{hint}</span>{/if}
  {#if action}<div class="action">{@render action()}</div>{/if}
</div>

<style>
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: var(--space-3);
    padding: var(--space-12) var(--space-6);
  }
  .glyph {
    color: var(--border-strong);
    animation: breathe 4s var(--ease-in-out) infinite;
  }
  .title {
    font: var(--type-section);
    font-size: var(--text-lg);
    color: var(--text-secondary);
  }
  .hint {
    font: var(--type-body);
    font-size: var(--text-sm);
    color: var(--text-tertiary);
    max-width: 320px;
  }
  .action {
    margin-top: var(--space-2);
  }
</style>

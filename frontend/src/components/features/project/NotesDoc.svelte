<script lang="ts">
  // Read-only preview card for the ONE markdown doc per project. Lives in the
  // project page rail; clicking opens the NotesEditor. Never editable in place.
  let {
    text = '',
    editedLabel = '',
    lines = 4,
    onOpen,
  }: {
    text?: string;
    editedLabel?: string;
    lines?: number;
    onOpen?: () => void;
  } = $props();

  // First non-heading paragraph of the doc.
  const firstPara = $derived(
    (text || '').split('\n').find((l) => l.trim() && !l.startsWith('#')) || ''
  );
</script>

<button class="notes-doc" onclick={onOpen} aria-label="Open notes">
  <div class="head">
    <span class="label">notes</span>
    {#if editedLabel}<span class="edited">{editedLabel}</span>{/if}
    <span style="flex: 1;"></span>
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="var(--text-tertiary)" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 1.5l2 2L4 10l-2.6.6L2 8z"></path></svg>
  </div>
  {#if firstPara}
    <div class="preview" style="-webkit-line-clamp: {lines};">{firstPara}</div>
  {:else}
    <div class="preview empty">Capture decisions, links, scratch — anything this project needs.</div>
  {/if}
  <span class="open-link">open notes →</span>
</button>

<style>
  .notes-doc {
    display: block;
    width: 100%;
    text-align: left;
    background: var(--surface-card);
    border: none;
    border-radius: var(--radius-card);
    box-shadow: var(--shadow-rest);
    padding: 14px 16px;
    cursor: pointer;
    box-sizing: border-box;
    transition: background var(--t-fast) var(--ease-out), box-shadow var(--t-fast) var(--ease-out);
  }
  .notes-doc:hover {
    background: var(--surface-card-hover);
    box-shadow: var(--shadow-lift);
  }
  .head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .label {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }
  .edited {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-tertiary);
    opacity: 0.8;
  }
  .preview {
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: var(--leading-relaxed);
    color: var(--text-secondary);
    text-wrap: pretty;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .preview.empty {
    color: var(--text-tertiary);
    font-style: italic;
  }
  .open-link {
    display: inline-block;
    margin-top: 10px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-tertiary);
  }
</style>

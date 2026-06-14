<script module lang="ts">
  // Minimal markdown parse for read mode: ## headings, - list rows with optional
  // [label](url) links, plain paragraphs. Deliberately small — project notes are
  // a thinking doc, not a wiki.
  type Block =
    | { kind: 'heading'; text: string }
    | { kind: 'link'; label: string; url: string }
    | { kind: 'item'; text: string }
    | { kind: 'para'; text: string };

  export function renderNotesMd(src: string): Block[] {
    const out: Block[] = [];
    (src || '').split('\n').forEach((line) => {
      if (!line.trim()) return;
      if (line.startsWith('## ')) {
        out.push({ kind: 'heading', text: line.slice(3) });
      } else if (line.startsWith('- ')) {
        const m = line.match(/^- \[(.+?)\]\((.+?)\)/);
        if (m) out.push({ kind: 'link', label: m[1], url: m[2] });
        else out.push({ kind: 'item', text: line.slice(2) });
      } else {
        out.push({ kind: 'para', text: line });
      }
    });
    return out;
  }
</script>

<script lang="ts">
  import { onMount } from 'svelte';

  let {
    value = '',
    onChange,
    mode = 'write',
    onModeChange,
    saveState = 'saved',
    savedLabel = 'saved · just now',
    onClose,
  }: {
    value?: string;
    onChange?: (v: string) => void;
    mode?: 'write' | 'read';
    onModeChange?: (m: 'write' | 'read') => void;
    saveState?: 'saved' | 'saving';
    savedLabel?: string;
    onClose?: () => void;
  } = $props();

  const blocks = $derived(renderNotesMd(value));

  onMount(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose?.();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });
</script>

<div class="notes-editor">
  <div class="head">
    <span class="label">notes</span>
    <span class="save" class:saving={saveState === 'saving'}>{saveState === 'saving' ? 'saving…' : savedLabel}</span>
    <span style="flex: 1;"></span>
    <button class="seg" class:active={mode === 'write'} onclick={() => onModeChange?.('write')}>write</button>
    <button class="seg" class:active={mode === 'read'} onclick={() => onModeChange?.('read')}>read</button>
    <button class="close" onclick={onClose} aria-label="Close notes">&times;</button>
  </div>

  {#if mode === 'write'}
    <textarea
      class="doc-text"
      value={value}
      oninput={(e) => onChange?.((e.currentTarget as HTMLTextAreaElement).value)}
      placeholder="Decisions, links, scratch…"
    ></textarea>
  {:else}
    <div class="doc-read">
      {#each blocks as b, i (i)}
        {#if b.kind === 'heading'}
          <div class="md-head"><span class="label">{b.text}</span></div>
        {:else if b.kind === 'link'}
          <div class="md-row"><span class="bullet">·</span><a href={b.url} target="_blank" rel="noreferrer">{b.label} ↗</a></div>
        {:else if b.kind === 'item'}
          <div class="md-row"><span class="bullet">·</span><span>{b.text}</span></div>
        {:else}
          <div class="md-para">{b.text}</div>
        {/if}
      {/each}
    </div>
  {/if}

  <div class="foot">
    <span>autosaves as you type · esc closes</span>
  </div>
</div>

<style>
  .notes-editor {
    width: var(--detail-panel-width);
    max-width: 100%;
    height: 100%;
    box-sizing: border-box;
    background: var(--surface-1);
    border-left: 1px solid var(--border-default);
    box-shadow: var(--shadow-slide-over);
    padding: 20px 24px 14px;
    display: flex;
    flex-direction: column;
  }
  .head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
  }
  .label {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }
  .save {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-tertiary);
    opacity: 0.9;
  }
  .save.saving {
    color: var(--text-secondary);
  }
  .seg {
    border: none;
    cursor: pointer;
    border-radius: var(--radius-inner);
    padding: 3px 9px;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.04em;
    background: transparent;
    color: var(--text-tertiary);
  }
  .seg.active {
    background: var(--selected-tint);
    color: var(--tangerine);
  }
  .close {
    border: none;
    background: none;
    cursor: pointer;
    color: var(--text-tertiary);
    font-size: 16px;
    line-height: 1;
    padding: 2px 4px;
  }
  .doc-text {
    flex: 1;
    width: 100%;
    box-sizing: border-box;
    resize: none;
    outline: none;
    background: transparent;
    border: none;
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: var(--leading-relaxed);
    color: var(--text-secondary);
    caret-color: var(--tangerine);
  }
  .doc-read {
    flex: 1;
    overflow-y: auto;
  }
  .md-head {
    margin: 14px 0 6px;
  }
  .md-head:first-child {
    margin-top: 0;
  }
  .md-row {
    display: flex;
    gap: 8px;
    padding: 2px 0;
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: var(--leading-relaxed);
    color: var(--text-secondary);
  }
  .md-row .bullet {
    color: var(--text-tertiary);
  }
  .md-row a {
    color: var(--text-link);
    text-decoration: none;
  }
  .md-para {
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: var(--leading-relaxed);
    color: var(--text-secondary);
    text-wrap: pretty;
    padding: 1px 0;
  }
  .foot {
    border-top: 1px solid var(--border-subtle);
    padding-top: 9px;
    margin-top: 10px;
  }
  .foot span {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-tertiary);
    opacity: 0.75;
    letter-spacing: 0.04em;
  }
</style>

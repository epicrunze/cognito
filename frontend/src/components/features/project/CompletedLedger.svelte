<script lang="ts">
  // Done-task history as dense mono rows. The day column only speaks when the
  // day changes; everything else stays tertiary. History is data, not celebration.
  type Entry = { day: string; title: string; time?: string };
  let {
    entries = [],
    limit = Infinity,
    totalCount,
    onShowAll,
  }: {
    entries?: Entry[];
    limit?: number;
    totalCount?: number;
    onShowAll?: () => void;
  } = $props();

  const shown = $derived(entries.slice(0, limit));
  const total = $derived(totalCount ?? entries.length);

  // Precompute whether each shown row should print its day column.
  const rows = $derived.by(() => {
    let last: string | null = null;
    return shown.map((r) => {
      const showDay = r.day !== last;
      last = r.day;
      return { ...r, showDay };
    });
  });
</script>

<div class="ledger">
  {#each rows as r, i (i)}
    <div class="row" class:bordered={i > 0}>
      <span class="day" style="opacity: {r.showDay ? 1 : 0.35};">{r.showDay ? r.day : '·'}</span>
      <span class="check">
        <span class="check-box">
          <svg width="7" height="7" viewBox="0 0 11 11" fill="none"><path d="M2.5 6L4.5 8L8.5 3.5" stroke="var(--bg-base)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
        </span>
      </span>
      <span class="title">{r.title}</span>
      {#if r.time}<span class="time">{r.time}</span>{/if}
    </div>
  {/each}
  {#if total > shown.length}
    <button class="show-all" onclick={onShowAll}>all {total} completed <span style="font-size: 12px;">→</span></button>
  {/if}
</div>

<style>
  .ledger {
    display: block;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 27px;
  }
  .row.bordered {
    border-top: 1px solid var(--border-subtle);
  }
  .day {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-tertiary);
    width: 48px;
    flex-shrink: 0;
  }
  .check {
    opacity: 0.6;
    display: inline-flex;
  }
  .check-box {
    width: 11px;
    height: 11px;
    border-radius: 3px;
    flex-shrink: 0;
    background: var(--done);
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .title {
    font-family: var(--font-sans);
    font-size: 13px;
    color: var(--text-tertiary);
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .time {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-tertiary);
    opacity: 0.6;
    flex-shrink: 0;
  }
  .show-all {
    margin-top: 8px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-tertiary);
    display: inline-flex;
    align-items: center;
    gap: 6px;
    letter-spacing: 0.02em;
  }
</style>

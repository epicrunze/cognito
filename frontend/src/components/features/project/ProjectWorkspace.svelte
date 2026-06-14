<script lang="ts">
  import type { Task } from '$lib/types';
  import { tasksStore } from '$lib/stores.svelte';
  import { responsiveStore } from '$lib/stores/responsive.svelte';
  import { projectWorkspaceStore } from '$lib/stores/projectWorkspace.svelte';
  import { formatRelativeDate } from '$lib/dateUtils';
  import BubbleCanvas from '../BubbleCanvas.svelte';
  import StatusBriefing from './StatusBriefing.svelte';
  import NotesDoc from './NotesDoc.svelte';
  import CompletedLedger from './CompletedLedger.svelte';
  import NotesEditor from './NotesEditor.svelte';

  let { projectId }: { projectId: number } = $props();

  let notesOpen = $state(false);
  let notesMode = $state<'write' | 'read'>('write');

  // Load notes + briefing for this project.
  $effect(() => {
    projectWorkspaceStore.load(projectId);
  });

  const ws = projectWorkspaceStore;

  // Only OPEN thoughts float in the grid; completed go to the ledger.
  const openOnly = (t: Task) => !t.done;

  // Completed history rows for this project, newest first.
  const ledgerEntries = $derived.by(() => {
    const done = tasksStore.tasks
      .filter((t) => t.project_id === projectId && t.done)
      .sort((a, b) => (b.done_at ?? b.updated ?? '').localeCompare(a.done_at ?? a.updated ?? ''));
    return done.map((t) => {
      const stamp = t.done_at ?? t.updated;
      return {
        day: stamp ? formatRelativeDate(stamp) : '',
        title: t.title,
        time: '',
      };
    });
  });

  function openNotes() {
    notesMode = 'write';
    notesOpen = true;
  }
  function closeNotes() {
    ws.flush();
    notesOpen = false;
  }
</script>

<div class="workspace" class:mobile={responsiveStore.isMobile}>
  <div class="main">
    <div class="briefing-wrap">
      <StatusBriefing
        text={ws.briefing || 'No briefing yet — regenerate to summarize this project.'}
        generatedLabel={ws.briefingLabel}
        stale={ws.briefingStale}
        generating={ws.briefingGenerating}
        onRegenerate={() => ws.regenerateBriefing()}
      />
    </div>
    <BubbleCanvas {projectId} filter={openOnly} />
  </div>

  <aside class="rail">
    <NotesDoc text={ws.notes} editedLabel={ws.notes ? ws.savedLabel : ''} onOpen={openNotes} />
    {#if ledgerEntries.length > 0}
      <div class="ledger-card">
        <span class="rail-label">completed</span>
        <CompletedLedger entries={ledgerEntries} limit={8} totalCount={ledgerEntries.length} />
      </div>
    {/if}
  </aside>
</div>

{#if notesOpen}
  <div class="notes-scrim" role="presentation" onclick={closeNotes}></div>
  <div class="notes-panel">
    <NotesEditor
      value={ws.notes}
      onChange={(v) => ws.setNotes(v)}
      mode={notesMode}
      onModeChange={(m) => (notesMode = m)}
      saveState={ws.saveState}
      savedLabel={ws.savedLabel}
      onClose={closeNotes}
    />
  </div>
{/if}

<style>
  .workspace {
    display: flex;
    gap: 24px;
    align-items: flex-start;
    padding: 8px 24px 24px;
  }
  .workspace.mobile {
    flex-direction: column;
    padding: 4px 12px 24px;
    gap: 16px;
  }
  .main {
    flex: 1;
    min-width: 0;
  }
  .briefing-wrap {
    padding: 16px 24px 0;
  }
  .workspace.mobile .briefing-wrap {
    padding: 12px 12px 0;
  }
  .rail {
    width: 320px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-top: 16px;
  }
  .workspace.mobile .rail {
    width: 100%;
    padding-top: 0;
  }
  .ledger-card {
    background: var(--surface-card);
    border-radius: var(--radius-card);
    box-shadow: var(--shadow-rest);
    padding: 14px 16px;
  }
  .rail-label {
    display: block;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 10px;
  }
  .notes-scrim {
    position: fixed;
    inset: 0;
    background: var(--bg-overlay);
    z-index: 120;
    animation: fadeIn var(--t-normal) var(--ease-out);
  }
  .notes-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 121;
    animation: notes-slide-in var(--t-normal) var(--ease-out);
  }
  @keyframes notes-slide-in {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
</style>

<script lang="ts">
  import { extractTasks, modelsApi, type ModelOption } from '$lib/api';
  import { proposalsStore, tasksStore, projectsStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import type { TaskProposal } from '$lib/types';
  import Textarea from '$components/ui/Textarea.svelte';
  import Button from '$components/ui/Button.svelte';
  import Dropdown from '$components/ui/Dropdown.svelte';
  import Kbd from '$components/ui/Kbd.svelte';
  import TaskPanel from '$components/features/TaskPanel.svelte';
  import ProposalCard from '$components/features/ProposalCard.svelte';
  import { fly } from 'svelte/transition';
  import { onMount } from 'svelte';

  let modelOptions = $state<{ value: string; label: string; description: string }[]>([
    { value: 'gemini-flash', label: 'Gemini 3.1 Flash Lite', description: 'Fast, good for most tasks' },
  ]);

  onMount(async () => {
    try {
      const models = await modelsApi.list();
      modelOptions = models.map((m) => ({ value: m.value, label: m.label, description: m.description }));
    } catch {
      // Keep fallback defaults
    }
  });

  let inputText = $state('');
  let selectedModel = $state('gemini-flash');
  let extracting = $state(false);
  let proposals = $state<TaskProposal[]>([]);
  let selectedIds = $state<Set<string>>(new Set());
  let rawResponse = $state('');
  let showRaw = $state(false);
  let editingProposal = $state<TaskProposal | null>(null);
  let hoveringCardId = $state<string | null>(null);

  const isLocal = $derived(selectedModel.startsWith('ollama'));

  function toggleSelected(id: string) {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    selectedIds = next;
  }

  function selectAll() {
    selectedIds = new Set(proposals.filter(p => p.status === 'pending').map(p => p.id));
  }

  async function handleExtract() {
    if (!inputText.trim() || extracting) return;
    extracting = true;
    proposals = [];
    selectedIds = new Set();
    rawResponse = '';

    try {
      for await (const event of extractTasks(inputText, { model: selectedModel })) {
        if (event.type === 'proposal' && event.proposal) {
          proposals = [...proposals, event.proposal];
          selectedIds = new Set([...selectedIds, event.proposal.id]);
          proposalsStore.add(event.proposal);
        } else if (event.type === 'done') {
          addToast(`Extracted ${event.count} tasks`, 'success');
        } else if (event.type === 'error') {
          addToast(event.detail ?? 'Extraction failed', 'error');
        }
      }
    } catch (e) {
      addToast(e instanceof Error ? e.message : 'Extraction failed', 'error');
    } finally {
      extracting = false;
      if (proposals.length === 0) {
        addToast('No tasks extracted — check the backend logs', 'error');
      }
    }
  }

  async function handleApproveAll() {
    const pending = proposals.filter(p => selectedIds.has(p.id) && p.status === 'pending');
    if (pending.length === 0) return;

    // Check if any proposals will create new projects
    const newProjectProposals = pending.filter(p => !p.project_id && p.project_name);
    if (newProjectProposals.length > 0) {
      const names = [...new Set(newProjectProposals.map(p => p.project_name))];
      if (!confirm(`This will create ${names.length} new project${names.length > 1 ? 's' : ''}: ${names.join(', ')}. Continue?`)) {
        return;
      }
    }

    const ids = Array.from(selectedIds);
    const res = await proposalsStore.approveAll(ids);

    if (res.approved > 0) {
      addToast(`${res.approved} task${res.approved === 1 ? '' : 's'} created`, 'success');
      proposals = proposals.map(p => selectedIds.has(p.id) && p.status !== 'pending' ? p : selectedIds.has(p.id) ? { ...p, status: 'approved' as const } : p);
      await tasksStore.fetchAll();
      if (res.new_projects && res.new_projects.length > 0) {
        await projectsStore.fetchAll();
      }
    }

    if (res.errors.length > 0) {
      const details = res.errors.map(e => e.title ? `"${e.title}": ${e.error}` : e.error).join('; ');
      addToast(`${res.errors.length} task${res.errors.length === 1 ? '' : 's'} failed: ${details}`, 'error');
    }
  }

  async function handleRejectSelected() {
    const toReject = proposals.filter(p => selectedIds.has(p.id) && p.status === 'pending');
    for (const p of toReject) {
      await proposalsStore.reject(p.id);
    }
    proposals = proposals.filter(p => !selectedIds.has(p.id));
    selectedIds = new Set();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleExtract();
    }
  }
</script>

<div style="max-width: 720px; margin: 0 auto; padding: 32px 24px;">
  <!-- Header -->
  <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
    <span style="font-size: 20px; font-weight: 600; color: var(--accent);">&#9670; Extract Tasks</span>
  </div>

  <!-- Controls -->
  <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap;">
    <Dropdown options={modelOptions} value={selectedModel} onchange={(v) => selectedModel = v} width={220} />
    <Button
      variant="toggle"
      size="sm"
      onclick={() => {
        selectedModel = isLocal ? 'gemini-flash' : 'ollama-qwen';
      }}
    >
      {isLocal ? '\uD83D\uDD12 Local' : '\u2601 Cloud'}
    </Button>
  </div>

  {#if isLocal}
    <div style="padding: 10px 14px; margin-bottom: 16px; background: var(--accent-subtle); border: 1px solid rgba(232,119,46,0.2); border-radius: 8px; font-size: 13px; color: var(--accent);">
      Processing locally — your text stays on your machine
    </div>
  {/if}

  <!-- Input -->
  <div style="margin-bottom: 16px;">
    <Textarea
      bind:value={inputText}
      placeholder="Paste meeting notes, emails, or ideas here..."
      rows={6}
      onkeydown={handleKeydown}
    />
  </div>

  <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 32px;">
    <Button variant="accent" loading={extracting} onclick={handleExtract} disabled={!inputText.trim()}>
      {extracting ? 'Extracting...' : 'Extract Tasks'}
    </Button>
    <Kbd>Ctrl+&crarr;</Kbd>
  </div>

  <!-- Raw Response -->
  {#if rawResponse}
    <div style="margin-bottom: 24px;">
      <button
        onclick={() => showRaw = !showRaw}
        style="display: flex; align-items: center; gap: 6px; background: none; border: none; color: var(--text-tertiary); font-size: 13px; cursor: pointer; padding: 0; font-family: var(--font-sans);"
      >
        <span style="transform: {showRaw ? 'rotate(90deg)' : 'rotate(0deg)'}; transition: transform 150ms; font-size: 10px;">&#9654;</span>
        Raw AI Response
      </button>
      {#if showRaw}
        <pre style="margin-top: 10px; padding: 16px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 8px; font-size: 12.5px; font-family: var(--font-mono); color: var(--text-secondary); line-height: 1.6; overflow: auto; max-height: 300px; white-space: pre-wrap;">{rawResponse}</pre>
      {/if}
    </div>
  {/if}

  <!-- Proposals -->
  {#if proposals.length > 0}
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
      <Button variant="accent" size="sm" onclick={handleApproveAll} disabled={selectedIds.size === 0}>
        Approve All ({selectedIds.size})
      </Button>
      <Button variant="outline" size="sm" onclick={selectAll}>Select All</Button>
      {#if selectedIds.size > 0}
        <Button variant="danger" size="sm" onclick={handleRejectSelected}>
          Reject Selected
        </Button>
      {/if}
    </div>

    <div style="display: flex; flex-direction: column; gap: 10px;">
      {#each proposals as proposal, i (proposal.id)}
        <div in:fly={{ y: 20, duration: 200, delay: i * 50 }}>
          <ProposalCard
            {proposal}
            selected={selectedIds.has(proposal.id)}
            hovered={hoveringCardId === proposal.id}
            onselect={() => toggleSelected(proposal.id)}
            onedit={() => { if (proposal.status === 'pending') editingProposal = proposal; }}
            onmouseenter={() => hoveringCardId = proposal.id}
            onmouseleave={() => { if (hoveringCardId === proposal.id) hoveringCardId = null; }}
          />
        </div>
      {/each}
    </div>
  {/if}
</div>

<TaskPanel
  mode="proposal"
  open={editingProposal !== null}
  proposal={editingProposal ?? undefined}
  onclose={() => editingProposal = null}
  onupdate={(updated) => {
    proposals = proposals.map(p => p.id === updated.id ? updated : p);
    editingProposal = null;
  }}
/>

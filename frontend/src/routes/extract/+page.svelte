<script lang="ts">
  import { extractTasks } from '$lib/api';
  import { proposalsStore, tasksStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import type { TaskProposal } from '$lib/types';
  import Textarea from '$components/ui/Textarea.svelte';
  import Button from '$components/ui/Button.svelte';
  import Dropdown from '$components/ui/Dropdown.svelte';
  import Kbd from '$components/ui/Kbd.svelte';
  import Checkbox from '$components/ui/Checkbox.svelte';
  import PriorityIndicator from '$components/ui/PriorityIndicator.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import DateDisplay from '$components/ui/DateDisplay.svelte';
  import { fly } from 'svelte/transition';

  const modelOptions = [
    { value: 'gemini-flash', label: 'Gemini 2.0 Flash', description: 'Fast, good for most tasks' },
    { value: 'gemini-pro', label: 'Gemini 2.0 Pro', description: 'Higher quality, slower' },
    { value: 'ollama-qwen', label: 'Qwen 3.x (Local)', description: 'Private, runs on your machine' },
    { value: 'ollama-llama', label: 'Llama 3.3 (Local)', description: 'Private, larger model' },
  ];

  let inputText = $state('');
  let selectedModel = $state('gemini-flash');
  let extracting = $state(false);
  let proposals = $state<TaskProposal[]>([]);
  let selectedIds = $state<Set<string>>(new Set());
  let rawResponse = $state('');
  let showRaw = $state(false);

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

    await proposalsStore.approveAll();
    addToast(`${pending.length} tasks created`, 'success');
    proposals = proposals.map(p => selectedIds.has(p.id) ? { ...p, status: 'approved' as const } : p);
    await tasksStore.fetchAll();
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
    <span style="font-size: 20px; font-weight: 600; color: var(--accent);">&diams; Extract Tasks</span>
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
        <div
          in:fly={{ y: 20, duration: 200, delay: i * 50 }}
          style="display: flex; gap: 14px; padding: 16px 18px; background: var(--bg-surface); border: 1px solid {proposal.status === 'approved' ? 'var(--done)' : 'var(--border-default)'}; border-radius: 10px; border-left: 2px solid var(--accent); box-shadow: inset 3px 0 8px -4px var(--accent-glow); transition: all 150ms ease-out; align-items: flex-start; opacity: {proposal.status === 'approved' ? 0.5 : 1};"
        >
          <Checkbox
            checked={selectedIds.has(proposal.id)}
            onchange={() => toggleSelected(proposal.id)}
          />
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 7px;">
              <PriorityIndicator level={proposal.priority} size="sm" />
              <span style="font-size: 15px; font-weight: 500; color: var(--text-primary); line-height: 1.3;">
                {proposal.title}
              </span>
              {#if proposal.status === 'approved'}
                <span style="font-size: 12px; color: var(--done); font-weight: 500;">Approved</span>
              {/if}
            </div>
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
              {#if proposal.project_name}
                <span style="font-size: 13px; color: var(--text-tertiary);">{proposal.project_name}</span>
                <span style="font-size: 13px; color: var(--border-strong);">&middot;</span>
              {/if}
              <DateDisplay date={proposal.due_date} />
              {#if proposal.estimated_minutes}
                <span style="font-size: 13px; color: var(--border-strong);">&middot;</span>
                <span style="font-size: 13px; color: var(--text-tertiary);">{proposal.estimated_minutes}min</span>
              {/if}
              {#each proposal.labels as label (label)}
                <Badge>{label}</Badge>
              {/each}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

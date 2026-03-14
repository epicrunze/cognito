<script lang="ts">
  import { extractTasks, modelsApi, tasksApi, type ModelOption } from '$lib/api';
  import { proposalsStore, tasksStore, projectsStore } from '$lib/stores.svelte';
  import { chatStore } from '$lib/stores/chat.svelte';
  import { filterStore } from '$lib/stores/filter.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import type { TaskProposal } from '$lib/types';
  import Textarea from '$components/ui/Textarea.svelte';
  import Button from '$components/ui/Button.svelte';
  import Dropdown from '$components/ui/Dropdown.svelte';
  import Kbd from '$components/ui/Kbd.svelte';
  import TaskPanel from '$components/features/TaskPanel.svelte';
  import ThoughtBubble from '$components/features/ThoughtBubble.svelte';
  import { fly, slide, fade } from 'svelte/transition';
  import { DURATION } from '$lib/transitions';
  import { onMount, tick } from 'svelte';

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

  let tab = $state<'paste' | 'chat'>('paste');
  let inputText = $state('');
  let selectedModel = $state('gemini-flash');
  let extracting = $state(false);
  let proposals = $state<TaskProposal[]>([]);
  let selectedIds = $state<Set<string>>(new Set());
  let rawResponse = $state('');
  let showRaw = $state(false);
  let editingProposal = $state<TaskProposal | null>(null);
  let extractError = $state<string | null>(null);

  // Chat state
  let chatInput = $state('');
  let chatContainerRef = $state<HTMLDivElement | undefined>(undefined);

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
    extractError = null;

    try {
      for await (const event of extractTasks(inputText, { model: selectedModel })) {
        if (event.type === 'proposal' && event.proposal) {
          proposals = [...proposals, event.proposal];
          selectedIds = new Set([...selectedIds, event.proposal.id]);
          proposalsStore.add(event.proposal);
        } else if (event.type === 'done') {
          addToast(`Extracted ${event.count} tasks`, 'success');
        } else if (event.type === 'error') {
          extractError = event.detail ?? 'Extraction failed';
          addToast(extractError, 'error');
        }
      }
    } catch (e) {
      extractError = e instanceof Error ? e.message : 'Extraction failed';
      addToast(extractError, 'error');
    } finally {
      extracting = false;
      if (proposals.length === 0 && !extractError) {
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

  async function handleAutoTag() {
    try {
      addToast('Auto-tagging tasks...', 'info');
      const res = await tasksApi.autoTag(undefined, selectedModel);
      if (res.tagged > 0) {
        const taggedIds = res.results.map(r => r.task_id);
        filterStore.addAiTaggedBatch(taggedIds);
        addToast(`Auto-tagged ${res.tagged} task${res.tagged === 1 ? '' : 's'}`, 'success');
        await tasksStore.fetchAll();
      } else {
        addToast('No tasks to auto-tag', 'info');
      }
    } catch (e) {
      addToast(e instanceof Error ? e.message : 'Auto-tag failed', 'error');
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleExtract();
    }
  }

  async function handleChatSend() {
    if (!chatInput.trim() || chatStore.loading) return;
    const msg = chatInput;
    chatInput = '';
    await chatStore.sendMessage(msg, selectedModel);
    await tick();
    if (chatContainerRef) {
      chatContainerRef.scrollTop = chatContainerRef.scrollHeight;
    }
  }

  function handleChatKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSend();
    }
  }
</script>

<div style="max-width: 720px; margin: 0 auto; padding: 32px 24px;">
  <!-- Header -->
  <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
    <span style="font-size: 20px; font-weight: 600; color: var(--accent);">&#9670; Extract Tasks</span>
  </div>

  <!-- Tab toggle -->
  <div style="display: flex; gap: 0; margin-bottom: 20px; border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden; width: fit-content;">
    <button
      onclick={() => tab = 'paste'}
      style="padding: 7px 18px; font-size: 13px; font-weight: 500; font-family: var(--font-sans); border: none; cursor: pointer; background: {tab === 'paste' ? 'var(--accent)' : 'transparent'}; color: {tab === 'paste' ? 'white' : 'var(--text-secondary)'}; transition: all var(--transition-fast);"
    >Paste</button>
    <button
      onclick={() => tab = 'chat'}
      style="padding: 7px 18px; font-size: 13px; font-weight: 500; font-family: var(--font-sans); border: none; border-left: 1px solid var(--border-default); cursor: pointer; background: {tab === 'chat' ? 'var(--accent)' : 'transparent'}; color: {tab === 'chat' ? 'white' : 'var(--text-secondary)'}; transition: all var(--transition-fast);"
    >Chat</button>
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
    <Button variant="ghost" size="sm" onclick={handleAutoTag}>Auto-tag</Button>
  </div>

  {#if isLocal}
    <div style="padding: 10px 14px; margin-bottom: 16px; background: var(--accent-subtle); border: 1px solid rgba(232,119,46,0.2); border-radius: 8px; font-size: 13px; color: var(--accent);">
      Processing locally — your text stays on your machine
    </div>
  {/if}

  <!-- PASTE TAB -->
  {#if tab === 'paste'}
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
      <Button variant="accent" loading={extracting} onclick={handleExtract} disabled={!inputText.trim()} style={extracting ? 'animation: pulse-glow 1.5s ease-in-out infinite;' : ''}>
        {extracting ? 'Extracting...' : 'Extract Tasks'}
      </Button>
      <Kbd>Ctrl+&crarr;</Kbd>
    </div>

    <!-- Error + Retry -->
    {#if extractError && !extracting}
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding: 12px 16px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px;">
        <span style="font-size: 13px; color: var(--danger, #ef4444); flex: 1;">{extractError}</span>
        <Button variant="outline" size="sm" onclick={handleExtract}>Retry</Button>
      </div>
    {/if}

    <!-- Raw Response -->
    {#if rawResponse}
      <div style="margin-bottom: 24px;">
        <button
          onclick={() => showRaw = !showRaw}
          style="display: flex; align-items: center; gap: 6px; background: none; border: none; color: var(--text-tertiary); font-size: 13px; cursor: pointer; padding: 0; font-family: var(--font-sans);"
        >
          <span style="transform: {showRaw ? 'rotate(90deg)' : 'rotate(0deg)'}; transition: transform var(--transition-fast); font-size: 10px;">&#9654;</span>
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

      <div style="display: flex; flex-wrap: wrap; gap: 12px;">
        {#each proposals as proposal, i (proposal.id)}
          {#if proposal.status !== 'approved'}
            <div in:fly={{ y: 20, duration: DURATION.normal, delay: i * 50 }} out:slide|local={{ duration: DURATION.normal }}>
              <ThoughtBubble
                {proposal}
                proposalMode
                selected={selectedIds.has(proposal.id)}
                onselect={() => toggleSelected(proposal.id)}
                onapprove={async () => {
                  const res = await proposalsStore.approveAll([proposal.id]);
                  if (res.approved > 0) {
                    proposals = proposals.map(p => p.id === proposal.id ? { ...p, status: 'approved' as const } : p);
                    addToast('Task created', 'success');
                    await tasksStore.fetchAll();
                  }
                }}
                onreject={async () => {
                  await proposalsStore.reject(proposal.id);
                  proposals = proposals.filter(p => p.id !== proposal.id);
                }}
                onproposalupdate={(updated) => { proposals = proposals.map(p => p.id === updated.id ? updated : p); }}
              />
            </div>
          {:else}
            <div out:slide|local={{ duration: DURATION.normal }} style="opacity: 0.5;">
              <ThoughtBubble
                {proposal}
                proposalMode
                selected={selectedIds.has(proposal.id)}
                onselect={() => toggleSelected(proposal.id)}
              />
            </div>
          {/if}
        {/each}
      </div>
    {/if}

  <!-- CHAT TAB -->
  {:else}
    <div style="display: flex; flex-direction: column; height: calc(100vh - 340px); min-height: 300px;">
      <!-- Messages -->
      <div bind:this={chatContainerRef} style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding: 8px 0; margin-bottom: 16px;">
        {#if chatStore.messages.length === 0}
          <div style="flex: 1; display: flex; align-items: center; justify-content: center;">
            <span style="color: var(--text-tertiary); font-size: 14px;">Start a conversation to extract tasks naturally.</span>
          </div>
        {/if}
        {#each chatStore.messages as msg, i (i)}
          <div style="display: flex; justify-content: {msg.role === 'user' ? 'flex-end' : 'flex-start'};">
            <div style="max-width: 85%; padding: 10px 14px; border-radius: 12px; background: {msg.role === 'user' ? 'var(--accent)' : 'var(--bg-surface)'}; color: {msg.role === 'user' ? 'white' : 'var(--text-primary)'}; font-size: 14px; line-height: 1.5; border: {msg.role === 'assistant' ? '1px solid var(--border-default)' : 'none'};">
              {msg.content}
              {#if msg.proposals && msg.proposals.length > 0}
                <div style="margin-top: 10px; display: flex; flex-direction: column; gap: 8px;">
                  {#each msg.proposals as proposal (proposal.id)}
                    <div style="padding: 8px 12px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 8px; border-left: 2px solid var(--accent); font-size: 13px;">
                      <span style="font-weight: 500;">{proposal.title}</span>
                      {#if proposal.project_name}
                        <span style="color: var(--text-tertiary); margin-left: 8px;">{proposal.project_name}</span>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        {/each}
        {#if chatStore.loading}
          <div style="display: flex; justify-content: flex-start;">
            <div style="padding: 10px 14px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; color: var(--text-tertiary); font-size: 14px;">
              <span class="typing-indicator">Thinking</span>
            </div>
          </div>
        {/if}
      </div>

      <!-- Chat input -->
      <div style="display: flex; gap: 10px; align-items: flex-end;">
        <div style="flex: 1;">
          <Textarea
            bind:value={chatInput}
            placeholder="Type a message..."
            rows={2}
            onkeydown={handleChatKeydown}
          />
        </div>
        <Button variant="accent" onclick={handleChatSend} disabled={!chatInput.trim() || chatStore.loading}>
          Send
        </Button>
      </div>

      {#if chatStore.conversationId}
        <div style="margin-top: 8px;">
          <Button variant="ghost" size="sm" onclick={() => chatStore.startNewConversation()}>New conversation</Button>
        </div>
      {/if}
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

<style>
  .typing-indicator::after {
    content: '';
    animation: dots 1.5s steps(4, end) infinite;
  }
</style>

<script lang="ts">
  import SlideOver from '$components/ui/SlideOver.svelte';
  import Dropdown from '$components/ui/Dropdown.svelte';
  import Button from '$components/ui/Button.svelte';
  import Textarea from '$components/ui/Textarea.svelte';
  import ThoughtBubble from '$components/features/ThoughtBubble.svelte';
  import { chatStore } from '$lib/stores/chat.svelte';
  import { chatApi, extractTasks, modelsApi, proposalsApi, tasksApi } from '$lib/api';
  import { projectsStore, proposalsStore, tasksStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import { onMount, tick } from 'svelte';
  import { SvelteSet } from 'svelte/reactivity';
  import { slide } from 'svelte/transition';
  import type { ChatAction, TaskProposal } from '$lib/types';
  import type { ModelOption } from '$lib/api';

  let {
    open = false,
    onclose,
    ontaskschanged,
  }: {
    open: boolean;
    onclose?: () => void;
    ontaskschanged?: () => void;
  } = $props();

  let inputText = $state('');
  let messagesEl: HTMLDivElement | undefined = $state();
  let allModels = $state<ModelOption[]>([]);
  let modelOptions = $state<{ value: string; label: string; description?: string }[]>([]);
  let selectedModel = $state('');
  let pastedBulk = $state(false);
  let extracting = $state(false);
  let selectedProposals = new SvelteSet<string>();

  // Cloud/Local toggle state
  let isLocal = $derived(allModels.find((m) => m.value === selectedModel)?.provider === 'ollama');
  const firstGemini = $derived(allModels.find((m) => m.provider === 'gemini'));
  const firstOllama = $derived(allModels.find((m) => m.provider === 'ollama'));

  onMount(async () => {
    try {
      const models: ModelOption[] = await modelsApi.list();
      allModels = models;
      modelOptions = models.map((m) => ({
        value: m.value,
        label: m.label,
        description: m.description,
      }));
      if (modelOptions.length > 0 && !selectedModel) {
        selectedModel = modelOptions[0].value;
      }
    } catch {
      // Models endpoint may not be available
    }
  });

  async function scrollToBottom() {
    await tick();
    if (messagesEl) {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  }

  $effect(() => {
    if (chatStore.messages.length) {
      scrollToBottom();
    }
  });

  function evaluatePasteMode(text: string) {
    const lines = text.split('\n').filter((l) => l.trim());
    pastedBulk = lines.length > 1 || text.length > 150;
  }

  function handlePaste() {
    // Use setTimeout so value is updated after paste
    setTimeout(() => {
      evaluatePasteMode(inputText);
    }, 0);
  }

  function handleInput() {
    evaluatePasteMode(inputText);
  }

  async function handleSend() {
    const text = inputText.trim();
    if (!text) return;

    if (pastedBulk) {
      await handleExtract(text);
    } else {
      inputText = '';
      pastedBulk = false;
      await chatStore.sendMessage(text, selectedModel || undefined);
      scrollToBottom();
    }
  }

  async function handleExtract(text: string) {
    inputText = '';
    pastedBulk = false;
    extracting = true;

    // Add user message
    chatStore.addMessage({ role: 'user', content: text, created_at: new Date().toISOString() });
    scrollToBottom();

    const streamedProposals: TaskProposal[] = [];

    try {
      for await (const event of extractTasks(text, { model: selectedModel || undefined })) {
        if (event.type === 'proposal' && event.proposal) {
          streamedProposals.push(event.proposal);
          // Add/update assistant message with proposals so far
          chatStore.setExtractingProposals(streamedProposals);
          scrollToBottom();
        } else if (event.type === 'error') {
          addToast(event.detail ?? 'Extraction error', 'error');
        }
      }

      if (streamedProposals.length > 0) {
        addToast(`Extracted ${streamedProposals.length} task${streamedProposals.length > 1 ? 's' : ''}`, 'success');
      } else {
        chatStore.addMessage({
          role: 'assistant',
          content: 'No tasks found in the text.',
          created_at: new Date().toISOString(),
        });
      }
    } catch (e) {
      addToast(e instanceof Error ? e.message : 'Extraction failed', 'error');
    } finally {
      extracting = false;
      chatStore.finishExtracting();
      scrollToBottom();
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleNewConversation() {
    chatStore.startNewConversation();
    selectedProposals.clear();
  }

  function toggleCloudLocal() {
    if (isLocal && firstGemini) {
      selectedModel = firstGemini.value;
    } else if (!isLocal && firstOllama) {
      selectedModel = firstOllama.value;
    }
  }

  async function handleAutoTag() {
    try {
      const result = await tasksApi.autoTag(undefined, selectedModel || undefined);
      await tasksStore.fetchAll();
      ontaskschanged?.();
      addToast(`Auto-tagged ${result.tagged} task${result.tagged !== 1 ? 's' : ''}`, 'success');
    } catch {
      addToast('Auto-tag failed', 'error');
    }
  }

  async function handleApprove(proposalId: string) {
    try {
      const result = await proposalsApi.approve(proposalId);
      chatStore.removeProposal(proposalId);
      selectedProposals.delete(proposalId);
      await tasksStore.fetchAll();
      ontaskschanged?.();
      if (result.new_project_created) {
        const proposal = chatStore.pendingProposals.find((p) => p.id === proposalId)
          ?? chatStore.messages.flatMap((m) => m.proposals ?? []).find((p) => p.id === proposalId);
        const projectName = proposal?.project_name ?? 'Unknown';
        addToast(`New project "${projectName}" created`, 'success');
        chatStore.addSystemMessage(`New project "${projectName}" was created. You can configure its color in project settings.`);
        await projectsStore.fetchAll();
      } else {
        addToast('Task created', 'success');
      }
    } catch {
      addToast('Failed to approve proposal', 'error');
    }
  }

  async function handleReject(proposalId: string) {
    try {
      await proposalsStore.reject(proposalId);
      chatStore.removeProposal(proposalId);
      selectedProposals.delete(proposalId);
    } catch {
      addToast('Failed to reject proposal', 'error');
    }
  }

  async function handleApproveAll() {
    const pendingIds = chatStore.pendingProposals.map((p) => p.id);
    if (pendingIds.length === 0) return;
    try {
      await proposalsStore.approveAll(pendingIds);
      for (const id of pendingIds) chatStore.removeProposal(id);
      selectedProposals.clear();
      await tasksStore.fetchAll();
      ontaskschanged?.();
      addToast(`Approved ${pendingIds.length} task${pendingIds.length !== 1 ? 's' : ''}`, 'success');
    } catch {
      addToast('Failed to approve all', 'error');
    }
  }

  async function handleRejectAll() {
    const pendingIds = chatStore.pendingProposals.map((p) => p.id);
    if (pendingIds.length === 0) return;
    try {
      for (const id of pendingIds) {
        await proposalsStore.reject(id);
        chatStore.removeProposal(id);
      }
      selectedProposals.clear();
    } catch {
      addToast('Failed to reject all', 'error');
    }
  }

  async function handleActionConfirm(action: ChatAction) {
    try {
      await chatApi.executeAction(action);
      chatStore.removePendingAction(action.task_id);
      await tasksStore.fetchAll();
      ontaskschanged?.();
      const name = action.task_title ?? action.title ?? 'task';
      switch (action.type) {
        case 'update': addToast(`Updated "${name}"`, 'success'); break;
        case 'complete': addToast(`Marked "${name}" as done`, 'success'); break;
        case 'move': addToast(`Moved "${name}"`, 'success'); break;
        case 'delete': addToast(`Deleted "${name}"`, 'success'); break;
      }
    } catch {
      addToast(`Failed to ${action.type} task`, 'error');
    }
  }

  function handleActionCancel(action: ChatAction) {
    chatStore.removePendingAction(action.task_id);
  }

  function actionIcon(type: string): string {
    switch (type) {
      case 'complete':
        return '\u2713';
      case 'update':
        return '\u270E';
      case 'move':
        return '\u2192';
      case 'delete':
        return '\u2717';
      default:
        return '\u2022';
    }
  }

  function actionLabel(action: ChatAction): string {
    const name = action.task_title ?? action.title ?? `task #${action.task_id}`;
    switch (action.type) {
      case 'complete':
        return `Marked \u201C${name}\u201D as done`;
      case 'update':
        return `Updated \u201C${name}\u201D`;
      case 'move':
        return `Moved \u201C${name}\u201D`;
      case 'delete':
        return `Deleted \u201C${name}\u201D`;
      default:
        return name;
    }
  }

  function isPendingAction(action: ChatAction): boolean {
    return chatStore.pendingActions.some(
      (a) => a.task_id === action.task_id && a.type === action.type
    );
  }

  function actionButtonLabel(type: string): string {
    switch (type) {
      case 'update': return 'Apply Changes';
      case 'complete': return 'Mark Done';
      case 'move': return 'Move Task';
      case 'delete': return 'Delete Task';
      default: return 'Confirm';
    }
  }

  function actionButtonVariant(type: string): 'accent' | 'danger' {
    return type === 'delete' ? 'danger' : 'accent';
  }

  function pendingActionLabel(action: ChatAction): string {
    const name = action.task_title ?? action.title ?? `task #${action.task_id}`;
    switch (action.type) {
      case 'update': {
        const fields = action.changes ? Object.keys(action.changes).join(', ') : 'fields';
        return `Update "${name}" (${fields})`;
      }
      case 'complete': return `Mark "${name}" as done`;
      case 'move': return `Move "${name}" to another project`;
      case 'delete': return `Delete "${name}"`;
      default: return name;
    }
  }

  function formatChangeValue(key: string, value: unknown): string {
    if (key === 'due_date' && typeof value === 'string') return value.split('T')[0];
    if (key === 'done') return value ? 'Yes' : 'No';
    return String(value ?? 'none');
  }
</script>

<SlideOver {open} {onclose} width={400}>
  <!-- Header -->
  <div
    style="display: flex; align-items: center; gap: 8px; padding: 16px 20px; border-bottom: 1px solid var(--border-default); flex-shrink: 0; flex-wrap: nowrap;"
  >
    <span
      style="color: var(--accent); font-size: 16px; line-height: 1; flex-shrink: 0;"
    >&#9670;</span>
    <span
      style="font-size: 15px; font-weight: 600; color: var(--text-primary); font-family: var(--font-sans); flex: 1; white-space: nowrap;"
    >Thinking Margin</span>

    {#if modelOptions.length > 0}
      <Dropdown
        options={modelOptions}
        value={selectedModel}
        onchange={(v) => (selectedModel = v)}
        width={130}
        placeholder="Model"
      />

      {#if firstGemini && firstOllama}
        <button
          class="cloud-local-toggle"
          onclick={toggleCloudLocal}
          title={isLocal ? 'Local (private) — click for cloud' : 'Cloud — click for local'}
        >
          {#if isLocal}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          {:else}
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
            </svg>
          {/if}
        </button>
      {/if}
    {/if}

    <Button variant="ghost" size="sm" onclick={handleAutoTag} style="padding: 0 8px; font-size: 12px;">
      Tag
    </Button>

    <Button variant="ghost" size="sm" onclick={handleNewConversation} style="padding: 0 10px;">
      New
    </Button>
  </div>

  <!-- Bulk action bar -->
  {#if chatStore.pendingProposals.length > 1}
    <div
      transition:slide={{ duration: 200 }}
      style="display: flex; align-items: center; gap: 8px; padding: 8px 20px; border-bottom: 1px solid var(--border-default); background: var(--bg-elevated); flex-shrink: 0;"
    >
      <span style="font-size: 13px; color: var(--text-secondary); font-family: var(--font-sans); flex: 1;">
        {chatStore.pendingProposals.length} proposals
      </span>
      <Button variant="accent" size="sm" onclick={handleApproveAll} style="padding: 0 10px; height: 28px; font-size: 12px;">
        Approve All ({chatStore.pendingProposals.length})
      </Button>
      <Button variant="ghost" size="sm" onclick={handleRejectAll} style="padding: 0 10px; height: 28px; font-size: 12px;">
        Reject All
      </Button>
    </div>
  {/if}

  <!-- Messages -->
  <div
    bind:this={messagesEl}
    style="flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; min-height: 0;"
  >
    {#if chatStore.messages.length === 0}
      <div
        style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 8px; color: var(--text-tertiary); font-size: 14px; font-family: var(--font-sans); text-align: center; padding: 40px 20px;"
      >
        <span style="font-size: 28px; opacity: 0.4;">&#9670;</span>
        <span>Describe tasks, changes, or paste notes.</span>
        <span style="font-size: 12px; opacity: 0.7;">Paste multi-line text to extract tasks. Short messages start a chat.</span>
      </div>
    {/if}

    {#each chatStore.messages as msg, i (i)}
      {#if msg.role === 'user'}
        <!-- User message -->
        <div style="display: flex; justify-content: flex-end;">
          <div
            style="max-width: 85%; padding: 10px 14px; border-radius: 14px 14px 4px 14px; background: var(--accent); color: var(--text-on-accent); font-size: 14px; line-height: 1.5; font-family: var(--font-sans); word-break: break-word; white-space: pre-wrap;"
          >{msg.content}</div>
        </div>
      {:else}
        <!-- Assistant message -->
        <div style="display: flex; justify-content: flex-start;">
          <div style="max-width: 100%; width: 100%; display: flex; flex-direction: column; gap: 8px;">
            {#if msg.content}
              <div
                style="padding: 10px 14px; border-radius: 14px 14px 14px 4px; background: var(--bg-elevated); color: var(--text-primary); font-size: 14px; line-height: 1.5; font-family: var(--font-sans); word-break: break-word; white-space: pre-wrap;"
              >{msg.content}</div>
            {/if}

            <!-- Proposals as ThoughtBubble -->
            {#if msg.proposals && msg.proposals.length > 0}
              {#each msg.proposals as proposal (proposal.id)}
                {@const isPending = chatStore.pendingProposals.some((p) => p.id === proposal.id)}
                {#if isPending}
                  <div transition:slide={{ duration: 200 }} style="max-width: 100%;">
                    <ThoughtBubble
                      {proposal}
                      proposalMode
                      selected={selectedProposals.has(proposal.id)}
                      onselect={() => {
                        if (selectedProposals.has(proposal.id)) {
                          selectedProposals.delete(proposal.id);
                        } else {
                          selectedProposals.add(proposal.id);
                        }
                      }}
                      onapprove={() => handleApprove(proposal.id)}
                      onreject={() => handleReject(proposal.id)}
                      onproposalupdate={(updated) => chatStore.updateProposal(proposal.id, updated)}
                    />
                  </div>
                {:else}
                  <div
                    style="font-size: 11px; color: var(--text-tertiary); font-style: italic; font-family: var(--font-sans); padding: 2px 0;"
                  >{proposal.title} — {proposal.status === 'approved' ? 'Approved' : proposal.status === 'rejected' ? 'Rejected' : proposal.status}</div>
                {/if}
              {/each}
            {/if}

            <!-- Actions -->
            {#if msg.actions && msg.actions.length > 0}
              {#each msg.actions as action (action.task_id)}
                {#if isPendingAction(action)}
                  <!-- Pending action confirmation -->
                  <div
                    style="border: 1px solid var(--border-strong); background: var(--bg-elevated); border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; gap: 6px;"
                  >
                    <div
                      style="font-size: 13px; color: var(--text-primary); font-family: var(--font-sans); font-weight: 500;"
                    >{pendingActionLabel(action)}</div>
                    {#if action.type === 'update' && action.changes}
                      <div style="font-size: 12px; color: var(--text-secondary); font-family: var(--font-sans); display: flex; flex-direction: column; gap: 2px; padding-left: 4px;">
                        {#each Object.entries(action.changes) as [key, value] (key)}
                          <span>{key}: {formatChangeValue(key, value)}</span>
                        {/each}
                      </div>
                    {/if}
                    <div style="display: flex; gap: 6px;">
                      <Button variant={actionButtonVariant(action.type)} size="sm" onclick={() => handleActionConfirm(action)} style="padding: 0 10px; height: 28px; font-size: 12px;">
                        {actionButtonLabel(action.type)}
                      </Button>
                      <Button variant="ghost" size="sm" onclick={() => handleActionCancel(action)} style="padding: 0 10px; height: 28px; font-size: 12px;">
                        Cancel
                      </Button>
                    </div>
                  </div>
                {:else}
                  <!-- Completed action summary -->
                  <div
                    style="font-size: 13px; color: var(--text-secondary); font-family: var(--font-sans); padding: 4px 0; display: flex; align-items: center; gap: 6px;"
                  >
                    <span style="color: var(--accent); font-size: 14px;">{actionIcon(action.type)}</span>
                    <span>{actionLabel(action)}</span>
                  </div>
                {/if}
              {/each}
            {/if}
          </div>
        </div>
      {/if}
    {/each}

    <!-- Loading indicator -->
    {#if chatStore.loading || extracting}
      <div style="display: flex; justify-content: flex-start;">
        <div
          style="padding: 10px 14px; border-radius: 14px 14px 14px 4px; background: var(--bg-elevated); display: flex; gap: 4px; align-items: center;"
        >
          <span class="thinking-dot" style="animation-delay: 0ms;"></span>
          <span class="thinking-dot" style="animation-delay: 150ms;"></span>
          <span class="thinking-dot" style="animation-delay: 300ms;"></span>
        </div>
      </div>
    {/if}
  </div>

  <!-- Input area -->
  <div
    style="padding: 12px 20px 16px; border-top: 1px solid var(--border-default); flex-shrink: 0;"
  >
    <Textarea
      bind:value={inputText}
      placeholder={pastedBulk ? 'Pasted text — click Extract to process...' : 'Describe tasks or changes...'}
      rows={pastedBulk ? 4 : 2}
      onkeydown={handleKeydown}
      oninput={handleInput}
      onpaste={handlePaste}
    />
    <div style="display: flex; justify-content: flex-end; margin-top: 8px;">
      <Button
        variant="accent"
        size="sm"
        onclick={handleSend}
        loading={chatStore.loading || extracting}
        disabled={!inputText.trim() || chatStore.loading || extracting}
      >
        {pastedBulk ? 'Extract' : 'Send'}
      </Button>
    </div>
  </div>
</SlideOver>

<style>
  .thinking-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text-tertiary);
    animation: thinkingBounce 1s ease-in-out infinite;
  }

  @keyframes thinkingBounce {
    0%,
    60%,
    100% {
      opacity: 0.3;
      transform: translateY(0);
    }
    30% {
      opacity: 1;
      transform: translateY(-4px);
    }
  }

  .cloud-local-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    border: 1px solid var(--border-default);
    background: var(--bg-elevated);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 150ms ease-out;
    flex-shrink: 0;
  }

  .cloud-local-toggle:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
</style>

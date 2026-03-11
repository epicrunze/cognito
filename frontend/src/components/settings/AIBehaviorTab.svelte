<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { configApi, chatApi } from '$lib/api';
  import { addToast } from '$lib/stores/toast.svelte';
  import { showConfirmDialog } from '$lib/stores/confirmDialog.svelte';
  import { chatStore } from '$lib/stores/chat.svelte';
  import { formatChangeValue, formatFieldName } from '$lib/formatUtils';
  import Skeleton from '$components/ui/Skeleton.svelte';
  import type { ChatAction, ChatMessage } from '$lib/types';

  let systemPrompt = $state('');
  let configLoading = $state(true);
  let historyLoading = $state(true);
  let saved = $state(false);
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let savedTimer: ReturnType<typeof setTimeout> | undefined;

  // Base prompt editing
  let showBasePrompt = $state(false);
  let basePromptText = $state('');
  let basePromptDefault = $state('');
  let basePromptLoaded = $state(false);
  let basePromptEditing = $state(false);
  let basePromptSaved = $state(false);
  let basePromptTimer: ReturnType<typeof setTimeout> | undefined;
  let basePromptSavedTimer: ReturnType<typeof setTimeout> | undefined;
  let hasBaseOverride = $state(false);

  // Tools
  let showTools = $state(false);
  let tools = $state<Array<{ name: string; description: string; parameters: Record<string, unknown> }>>([]);
  let toolsLoaded = $state(false);

  // Chat history
  let chatHistory = $state<Array<{ id: string; snippet: string; created_at: string; message_count: number }>>([]);
  let expandedConvId = $state<string | null>(null);
  let expandedMessages = $state<ChatMessage[]>([]);
  let loadingConv = $state(false);

  function timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }

  onMount(async () => {
    try {
      const config = await configApi.get();
      systemPrompt = config.system_prompt_override ?? '';
      hasBaseOverride = !!config.base_prompt_override;
    } catch {
      // ignore
    } finally {
      configLoading = false;
    }

    try {
      const res = await chatApi.listHistory();
      chatHistory = res.conversations;
    } catch {
      // ignore
    } finally {
      historyLoading = false;
    }
  });

  async function toggleBasePrompt() {
    showBasePrompt = !showBasePrompt;
    if (showBasePrompt && !basePromptLoaded) {
      try {
        const [promptRes, configRes] = await Promise.all([
          configApi.getSystemPrompt(),
          hasBaseOverride ? configApi.get() : Promise.resolve(null),
        ]);
        basePromptDefault = promptRes.prompt;
        // If there's a base override, show that; otherwise show default
        if (configRes?.base_prompt_override) {
          basePromptText = configRes.base_prompt_override;
          basePromptEditing = true;
        } else {
          basePromptText = basePromptDefault;
        }
        basePromptLoaded = true;
      } catch {
        basePromptText = 'Failed to load system prompt.';
      }
    }
  }

  function handleBasePromptInput() {
    basePromptEditing = true;
    clearTimeout(basePromptTimer);
    basePromptTimer = setTimeout(async () => {
      try {
        await configApi.update({ base_prompt_override: basePromptText || null });
        hasBaseOverride = !!basePromptText;
        basePromptSaved = true;
        clearTimeout(basePromptSavedTimer);
        basePromptSavedTimer = setTimeout(() => { basePromptSaved = false; }, 2000);
      } catch {
        addToast('Failed to save base prompt', 'error');
      }
    }, 800);
  }

  async function resetBasePrompt() {
    try {
      await configApi.update({ base_prompt_override: null });
      basePromptText = basePromptDefault;
      hasBaseOverride = false;
      basePromptEditing = false;
      basePromptSaved = true;
      clearTimeout(basePromptSavedTimer);
      basePromptSavedTimer = setTimeout(() => { basePromptSaved = false; }, 2000);
    } catch {
      addToast('Failed to reset prompt', 'error');
    }
  }

  async function toggleTools() {
    showTools = !showTools;
    if (showTools && !toolsLoaded) {
      try {
        const res = await configApi.getTools();
        tools = res.tools;
        toolsLoaded = true;
      } catch {
        tools = [];
      }
    }
  }

  function handleInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        await configApi.update({ system_prompt_override: systemPrompt || null });
        saved = true;
        clearTimeout(savedTimer);
        savedTimer = setTimeout(() => { saved = false; }, 2000);
      } catch {
        // save failed silently
      }
    }, 500);
  }

  async function toggleConversation(convId: string) {
    if (expandedConvId === convId) {
      expandedConvId = null;
      expandedMessages = [];
      return;
    }
    expandedConvId = convId;
    loadingConv = true;
    expandedMessages = [];
    try {
      const res = await chatApi.getConversation(convId);
      expandedMessages = res.messages;
    } catch {
      expandedMessages = [];
    } finally {
      loadingConv = false;
    }
  }

  const actionTypeLabels: Record<string, string> = {
    create: 'Created',
    complete: 'Completed',
    update: 'Updated',
    move: 'Moved',
    delete: 'Deleted',
  };

  const SKIP_FIELDS = new Set(['title', 'task_title', 'task_id', 'id']);

  function actionDetails(action: ChatAction): { key: string; value: string }[] {
    if (!action.changes) return [];
    return Object.entries(action.changes)
      .filter(([k]) => !SKIP_FIELDS.has(k))
      .map(([k, v]) => ({ key: formatFieldName(k), value: formatChangeValue(k, v) }));
  }

  async function deleteConversation(convId: string, e: MouseEvent) {
    e.stopPropagation();
    const confirmed = await showConfirmDialog({
      title: 'Delete conversation',
      message: 'This conversation will be permanently deleted.',
      confirmLabel: 'Delete',
      destructive: true,
    });
    if (!confirmed) return;
    try {
      await chatApi.deleteConversation(convId);
      chatHistory = chatHistory.filter((c) => c.id !== convId);
      if (expandedConvId === convId) {
        expandedConvId = null;
        expandedMessages = [];
      }
      addToast('Conversation deleted', 'success');
    } catch {
      addToast('Failed to delete conversation', 'error');
    }
  }

  function resumeConversation(convId: string) {
    chatStore.loadConversation(convId, expandedMessages);
    goto('/');
    window.dispatchEvent(new CustomEvent('open-thinking-margin'));
  }
</script>

<div style="display: flex; flex-direction: column; gap: 16px;">
  <!-- Base System Prompt -->
  <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden;">
    <button
      onclick={toggleBasePrompt}
      style="width: 100%; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; background: none; border: none; cursor: pointer; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; font-weight: 500;"
    >
      <span style="display: flex; align-items: center; gap: 8px;">
        Base System Prompt
        {#if hasBaseOverride}
          <span style="font-size: 10px; padding: 1px 6px; border-radius: 4px; background: var(--accent-subtle); color: var(--accent);">customized</span>
        {/if}
      </span>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate({showBasePrompt ? 180 : 0}deg); transition: transform 200ms;">
        <path d="m6 9 6 6 6-6"/>
      </svg>
    </button>
    {#if showBasePrompt}
      <div style="padding: 0 16px 16px;">
        {#if !basePromptLoaded}
          <div style="padding: 12px 0; display: flex; flex-direction: column; gap: 8px;">
            <Skeleton width="100%" height={14} />
            <Skeleton width="90%" height={14} />
            <Skeleton width="70%" height={14} />
          </div>
        {:else}
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-size: 11px; color: var(--text-tertiary);">
              {basePromptEditing ? 'Edit the prompt below. Changes auto-save.' : 'Click to edit this prompt.'}
            </span>
            <span style="display: flex; align-items: center; gap: 8px;">
              {#if basePromptSaved}
                <span style="font-size: 12px; color: var(--accent);">Saved</span>
              {/if}
              {#if hasBaseOverride}
                <button
                  onclick={resetBasePrompt}
                  style="font-size: 11px; padding: 2px 8px; background: none; border: 1px solid var(--border-default); border-radius: 4px; color: var(--text-tertiary); cursor: pointer; font-family: var(--font-sans); transition: color 150ms, border-color 150ms;"
                  onmouseenter={(e) => { (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)'; (e.currentTarget as HTMLElement).style.borderColor = 'var(--text-tertiary)'; }}
                  onmouseleave={(e) => { (e.currentTarget as HTMLElement).style.color = 'var(--text-tertiary)'; (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-default)'; }}
                >
                  Reset to default
                </button>
              {/if}
            </span>
          </div>
          <textarea
            bind:value={basePromptText}
            oninput={handleBasePromptInput}
            spellcheck="false"
            style="width: 100%; min-height: 300px; padding: 12px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px; font-size: 12px; line-height: 1.6; color: var(--text-secondary); white-space: pre-wrap; word-break: break-word; font-family: 'IBM Plex Mono', monospace; resize: vertical; outline: none; box-sizing: border-box; transition: border-color 150ms;"
          ></textarea>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Custom Instructions -->
  <div style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
      <span style="font-size: 13px; font-weight: 500; color: var(--text-primary);">Custom Instructions</span>
      {#if saved}
        <span style="font-size: 12px; color: var(--accent); transition: opacity 150ms;">Saved</span>
      {/if}
    </div>
    {#if configLoading}
      <div style="display: flex; flex-direction: column; gap: 8px; padding: 10px 0;">
        <Skeleton width="100%" height={14} />
        <Skeleton width="80%" height={14} />
        <Skeleton width="40%" height={14} />
      </div>
    {:else}
      <textarea
        bind:value={systemPrompt}
        oninput={handleInput}
        placeholder="Custom instructions for task extraction, e.g.:&#10;&#8226; Always categorize tasks into specific projects&#10;&#8226; Prefer high priority for deadline-sensitive items"
        style="width: 100%; min-height: 100px; padding: 10px 12px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; color: var(--text-primary); font-size: 14px; font-family: inherit; line-height: 1.5; resize: vertical; outline: none; transition: border-color 150ms; box-sizing: border-box;"
      ></textarea>
    {/if}
    <span style="font-size: 12px; color: var(--text-tertiary); margin-top: 8px; display: block;">
      These instructions are appended to the base prompt as additional guidance.
    </span>
  </div>

  <!-- Available Tools -->
  <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; overflow: hidden;">
    <button
      onclick={toggleTools}
      style="width: 100%; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; background: none; border: none; cursor: pointer; color: var(--text-primary); font-family: var(--font-sans); font-size: 13px; font-weight: 500;"
    >
      Available Tools
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate({showTools ? 180 : 0}deg); transition: transform 200ms;">
        <path d="m6 9 6 6 6-6"/>
      </svg>
    </button>
    {#if showTools}
      <div style="padding: 0 16px 16px; display: flex; flex-direction: column; gap: 8px;">
        {#each tools as tool (tool.name)}
          <div style="padding: 10px 12px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 6px;">
            <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); font-family: 'IBM Plex Mono', monospace;">{tool.name}</div>
            <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px; line-height: 1.4;">{tool.description}</div>
            {#if tool.parameters && Object.keys(tool.parameters).length > 0}
              <div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px;">
                {#each Object.entries(tool.parameters) as [paramName, paramDef] (paramName)}
                  <span style="font-size: 10px; padding: 1px 6px; border-radius: 3px; background: rgba(255,255,255,0.05); color: var(--text-tertiary); font-family: 'IBM Plex Mono', monospace;">
                    {paramName}: {typeof paramDef === 'object' && paramDef !== null && 'type' in paramDef ? (paramDef as Record<string, string>).type : 'any'}
                  </span>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
        {#if tools.length === 0}
          <span style="font-size: 13px; color: var(--text-tertiary);">Loading...</span>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Chat History -->
  <div style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px;">
    <span style="font-size: 13px; font-weight: 500; color: var(--text-primary); margin-bottom: 10px; display: block;">Chat History</span>
    {#if historyLoading}
      <div style="display: flex; flex-direction: column; gap: 6px;">
        {#each [1, 2, 3] as _ (_)}
          <div style="display: flex; align-items: center; gap: 10px; padding: 8px 10px;">
            <Skeleton width="60%" height={13} />
            <Skeleton width={40} height={12} />
            <Skeleton width={50} height={12} />
          </div>
        {/each}
      </div>
    {:else if chatHistory.length === 0}
      <span style="font-size: 13px; color: var(--text-tertiary);">No conversations yet.</span>
    {:else}
      <div style="display: flex; flex-direction: column; gap: 6px; max-height: 600px; overflow-y: auto;">
        {#each chatHistory as conv (conv.id)}
          <!-- Conversation header row -->
          <div
            role="button"
            tabindex="0"
            class="conv-row"
            class:conv-expanded={expandedConvId === conv.id}
            onclick={() => toggleConversation(conv.id)}
            onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter') toggleConversation(conv.id); }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; transform: rotate({expandedConvId === conv.id ? 90 : 0}deg); transition: transform 150ms; color: var(--text-tertiary);">
              <path d="m9 18 6-6-6-6"/>
            </svg>
            <span style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary);">{conv.snippet || 'Empty conversation'}</span>
            <span style="flex-shrink: 0; font-size: 12px; color: var(--text-tertiary);">{conv.message_count} msg{conv.message_count !== 1 ? 's' : ''}</span>
            <span style="flex-shrink: 0; font-size: 12px; color: var(--text-tertiary); width: 60px; text-align: right;">{timeAgo(conv.created_at)}</span>
            <button
              class="conv-delete-btn"
              title="Delete conversation"
              onclick={(e: MouseEvent) => deleteConversation(conv.id, e)}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
              </svg>
            </button>
          </div>

          <!-- Expanded conversation -->
          {#if expandedConvId === conv.id}
            <div class="conv-detail">
              {#if loadingConv}
                <div style="display: flex; flex-direction: column; gap: 10px; padding: 8px;">
                  {#each [1, 2, 3] as _ (_)}
                    <div style="display: flex; gap: 8px; align-items: flex-start;">
                      <Skeleton width={24} height={24} radius={12} />
                      <div style="flex: 1; display: flex; flex-direction: column; gap: 4px;">
                        <Skeleton width="80%" height={13} />
                        <Skeleton width="50%" height={13} />
                      </div>
                    </div>
                  {/each}
                </div>
              {:else}
                <!-- Resume button -->
                {#if expandedMessages.length > 0}
                  <div style="display: flex; justify-content: flex-end; margin-bottom: 4px;">
                    <button class="resume-btn" onclick={() => resumeConversation(conv.id)}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
                      </svg>
                      Resume
                    </button>
                  </div>
                {/if}
                {#each expandedMessages as msg, i (i)}
                  <div class="msg" class:msg-user={msg.role === 'user'} class:msg-assistant={msg.role === 'assistant'}>
                    <!-- Role indicator -->
                    <div class="msg-header">
                      <span class="msg-role" class:msg-role-user={msg.role === 'user'} class:msg-role-assistant={msg.role === 'assistant'}>
                        {msg.role === 'user' ? 'You' : 'AI'}
                      </span>
                      {#if msg.created_at}
                        <span style="font-size: 11px; color: var(--text-tertiary);">{timeAgo(msg.created_at)}</span>
                      {/if}
                    </div>

                    <!-- Content -->
                    <div class="msg-content">{msg.content}</div>

                    <!-- Actions performed -->
                    {#if msg.actions && msg.actions.length > 0}
                      <div class="msg-actions">
                        {#each msg.actions as action, j (j)}
                          {@const details = actionDetails(action)}
                          <div class="action-chip" class:action-chip-expanded={details.length > 0}>
                            <div class="action-chip-header">
                              <span class="action-type">{actionTypeLabels[action.type] ?? action.type}</span>
                              <span class="action-title">{action.title || action.task_title || `Task #${action.task_id}`}</span>
                              {#if action.type === 'move' && action.project_id && details.length === 0}
                                <span class="action-detail">to project #{action.project_id}</span>
                              {/if}
                            </div>
                            {#if details.length > 0}
                              <div class="action-changes">
                                {#each details as d (d.key)}
                                  <span class="action-change-row">{d.key} &rarr; {d.value}</span>
                                {/each}
                              </div>
                            {/if}
                          </div>
                        {/each}
                      </div>
                    {/if}

                    <!-- Proposals -->
                    {#if msg.proposals && msg.proposals.length > 0}
                      <div class="msg-actions">
                        {#each msg.proposals as proposal, j (j)}
                          <div class="action-chip proposal-chip">
                            <span class="action-type">Proposed</span>
                            <span class="action-title">{proposal.title}</span>
                            {#if proposal.project_name}
                              <span class="action-detail">in {proposal.project_name}</span>
                            {/if}
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/each}

                {#if expandedMessages.length === 0}
                  <span style="font-size: 12px; color: var(--text-tertiary); padding: 8px;">No messages found.</span>
                {/if}
              {/if}
            </div>
          {/if}
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .conv-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    background: var(--bg-base);
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    width: 100%;
    text-align: left;
    font-family: var(--font-sans);
    transition: background 150ms, border-color 150ms;
  }

  .conv-row:hover {
    background: var(--bg-surface-hover);
  }

  .conv-expanded {
    border-color: var(--accent);
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
  }

  .conv-detail {
    border: 1px solid var(--accent);
    border-top: none;
    border-radius: 0 0 6px 6px;
    background: var(--bg-base);
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 400px;
    overflow-y: auto;
  }

  .msg {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .msg-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .msg-role {
    font-size: 11px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 3px;
  }

  .msg-role-user {
    background: rgba(91, 141, 239, 0.15);
    color: rgb(130, 165, 255);
  }

  .msg-role-assistant {
    background: var(--accent-subtle);
    color: var(--accent);
  }

  .msg-content {
    font-size: 13px;
    line-height: 1.5;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-word;
    padding: 4px 0 2px;
  }

  .msg-actions {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 4px;
  }

  .action-chip {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 4px 8px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: 4px;
    font-size: 12px;
  }

  .action-chip:not(.action-chip-expanded) {
    flex-direction: row;
    align-items: center;
    gap: 6px;
  }

  .action-chip-header {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .action-changes {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding-left: 4px;
    margin-top: 2px;
  }

  .action-change-row {
    font-size: 11px;
    color: var(--text-tertiary);
    line-height: 1.4;
  }

  .action-type {
    font-weight: 600;
    color: var(--accent);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .proposal-chip .action-type {
    color: rgb(190, 150, 255);
  }

  .action-title {
    color: var(--text-primary);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .action-detail {
    color: var(--text-tertiary);
    font-size: 11px;
    flex-shrink: 0;
  }

  .conv-delete-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 4px;
    border: none;
    background: none;
    color: var(--text-tertiary);
    cursor: pointer;
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 150ms, color 150ms, background 150ms;
  }

  .conv-row:hover .conv-delete-btn {
    opacity: 1;
  }

  .conv-delete-btn:hover {
    color: var(--danger, #e55);
    background: rgba(255, 80, 80, 0.1);
  }

  .resume-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: 4px;
    border: 1px solid var(--border-default);
    background: none;
    color: var(--accent);
    font-size: 12px;
    font-family: var(--font-sans);
    cursor: pointer;
    transition: background 150ms, border-color 150ms;
  }

  .resume-btn:hover {
    background: var(--accent-subtle);
    border-color: var(--accent);
  }
</style>

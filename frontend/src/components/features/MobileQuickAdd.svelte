<script lang="ts">
  import BottomSheet from '$components/ui/BottomSheet.svelte';
  import { tasksStore, projectsStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';

  let {
    open = false,
    onclose,
  }: {
    open: boolean;
    onclose?: () => void;
  } = $props();

  let title = $state('');
  let description = $state('');
  let chatMessage = $state('');
  let saving = $state(false);

  async function handleSave() {
    if (!title.trim()) return;
    saving = true;
    try {
      const projectId = projectsStore.projects[0]?.id ?? 1;
      await tasksStore.create({
        project_id: projectId,
        title: title.trim(),
        description: description.trim(),
      });
      addToast('Task created — AI will sort & label', 'success');
      title = '';
      description = '';
      onclose?.();
    } catch {
      addToast('Failed to create task', 'error');
    } finally {
      saving = false;
    }
  }

  async function handleChat() {
    // TODO: Wire up to ChatAgent in a future iteration
    addToast('Chat coming soon', 'info');
    chatMessage = '';
  }
</script>

<BottomSheet {open} {onclose} snapPoints={[0.45, 0.85]} initialSnap={0}>
  <div class="quick-add">
    <div class="quick-add-header">
      <span class="quick-add-icon">&#9670;</span>
      <span class="quick-add-title">New thought</span>
    </div>

    <input
      class="quick-add-input"
      type="text"
      placeholder="What needs to be done?"
      bind:value={title}
      onkeydown={(e) => { if (e.key === 'Enter' && title.trim()) handleSave(); }}
    />

    <textarea
      class="quick-add-textarea"
      placeholder="Add details (optional)..."
      bind:value={description}
      rows="2"
    ></textarea>

    <div class="quick-add-footer">
      <span class="quick-add-hint">&#9670; AI will sort & label</span>
      <button
        class="quick-add-save"
        disabled={!title.trim() || saving}
        onclick={handleSave}
      >{saving ? 'Saving...' : 'Save'}</button>
    </div>

    <div class="quick-add-divider">
      <span>or chat</span>
    </div>

    <div class="quick-add-chat">
      <input
        class="quick-add-chat-input"
        type="text"
        placeholder="Ask AI anything..."
        bind:value={chatMessage}
        onkeydown={(e) => { if (e.key === 'Enter' && chatMessage.trim()) handleChat(); }}
      />
      <button class="quick-add-chat-send" disabled={!chatMessage.trim()} onclick={handleChat} aria-label="Send chat message">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
      </button>
    </div>
  </div>
</BottomSheet>

<style>
  .quick-add {
    padding: 4px 20px 24px;
    display: flex;
    flex-direction: column;
    height: 100%;
    box-sizing: border-box;
    overflow: hidden;
  }

  .quick-add-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
  }

  .quick-add-icon {
    color: var(--accent);
    font-size: 16px;
  }

  .quick-add-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .quick-add-input {
    width: 100%;
    padding: 12px 14px;
    font-size: 15px;
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 10px;
    outline: none;
    font-family: var(--font-sans);
    margin-bottom: 10px;
    box-sizing: border-box;
  }

  .quick-add-input:focus {
    border-color: var(--accent);
  }

  .quick-add-textarea {
    width: 100%;
    padding: 10px 14px;
    font-size: 14px;
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 10px;
    outline: none;
    font-family: var(--font-sans);
    resize: none;
    margin-bottom: 12px;
    box-sizing: border-box;
  }

  .quick-add-textarea:focus {
    border-color: var(--accent);
  }

  .quick-add-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .quick-add-hint {
    font-size: 12px;
    color: var(--text-tertiary);
  }

  .quick-add-save {
    height: 36px;
    padding: 0 20px;
    font-size: 14px;
    font-weight: 500;
    font-family: var(--font-sans);
    border-radius: 8px;
    border: none;
    background: var(--accent);
    color: var(--text-on-accent);
    cursor: pointer;
    transition: opacity var(--transition-fast);
  }

  .quick-add-save:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .quick-add-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: auto;
    padding-top: 16px;
    margin-bottom: 16px;
    color: var(--text-tertiary);
    font-size: 12px;
  }

  .quick-add-divider::before,
  .quick-add-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border-subtle);
  }

  .quick-add-chat {
    display: flex;
    gap: 8px;
  }

  .quick-add-chat-input {
    flex: 1;
    padding: 10px 14px;
    font-size: 14px;
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 10px;
    outline: none;
    font-family: var(--font-sans);
    box-sizing: border-box;
  }

  .quick-add-chat-input:focus {
    border-color: var(--accent);
  }

  .quick-add-chat-send {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    border: none;
    background: var(--accent);
    color: var(--text-on-accent);
    cursor: pointer;
    flex-shrink: 0;
    transition: opacity var(--transition-fast);
  }

  .quick-add-chat-send:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
</style>

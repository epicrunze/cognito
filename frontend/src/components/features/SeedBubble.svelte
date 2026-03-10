<script lang="ts">
  import { tasksStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import { tick } from 'svelte';

  let { projectId }: { projectId: number } = $props();

  let editing = $state(false);
  let title = $state('');
  let inputEl = $state<HTMLInputElement | null>(null);

  async function startEditing() {
    editing = true;
    await tick();
    inputEl?.focus();
  }

  async function submit() {
    const trimmed = title.trim();
    if (!trimmed) {
      cancel();
      return;
    }
    try {
      await tasksStore.create({ project_id: projectId, title: trimmed });
      addToast('Task created', 'success');
    } catch {
      addToast('Failed to create task', 'error');
    }
    title = '';
    editing = false;
  }

  function cancel() {
    title = '';
    editing = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      submit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancel();
    }
  }

  function handleBlur() {
    if (!title.trim()) {
      cancel();
    }
  }
</script>

{#if editing}
  <div class="seed-bubble seed-editing">
    <input
      bind:this={inputEl}
      bind:value={title}
      onkeydown={handleKeydown}
      onblur={handleBlur}
      placeholder="what's on your mind..."
      class="seed-input"
    />
  </div>
{:else}
  <button class="seed-bubble" onclick={startEditing} aria-label="Add new thought">
    <span class="seed-placeholder">new thought...</span>
  </button>
{/if}

<style>
  .seed-bubble {
    width: 175px;
    min-height: 82px;
    border-radius: 10px;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    padding: 14px 16px;
    cursor: pointer;
    opacity: 0.4;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: opacity var(--transition-fast), border-color var(--transition-fast),
                translate var(--transition-fast), background var(--transition-normal);
    font-family: var(--font-sans);
    color: inherit;
  }

  .seed-bubble:hover {
    opacity: 0.6;
    border-color: var(--border-strong);
    translate: 0 -1px;
  }

  .seed-editing {
    opacity: 1;
    background: var(--bg-elevated);
    border-color: var(--border-strong);
    cursor: text;
  }

  .seed-placeholder {
    font-size: 13.5px;
    font-style: italic;
    color: var(--text-tertiary);
    user-select: none;
  }

  .seed-input {
    width: 100%;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text-primary);
    font-size: 13.5px;
    font-family: var(--font-sans);
    padding: 0;
    line-height: 1.4;
  }

  .seed-input::placeholder {
    color: var(--text-tertiary);
    opacity: 0.7;
    font-style: italic;
  }
</style>

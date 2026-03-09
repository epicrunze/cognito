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
  <div
    style="
      width: 120px;
      min-height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 8px;
      border: 1px solid var(--accent);
      border-radius: 12px;
      background: var(--bg-surface);
    "
  >
    <input
      bind:this={inputEl}
      bind:value={title}
      onkeydown={handleKeydown}
      onblur={handleBlur}
      placeholder="Task title..."
      style="
        width: 100%;
        background: transparent;
        border: none;
        outline: none;
        color: var(--text-primary);
        font-size: 0.8rem;
        font-family: inherit;
      "
    />
  </div>
{:else}
  <button
    onclick={startEditing}
    style="
      width: 100px;
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2px dashed var(--accent);
      border-radius: 12px;
      background: transparent;
      opacity: 0.4;
      cursor: pointer;
      transition: opacity var(--transition-fast), border-style var(--transition-fast);
      color: var(--accent);
      font-size: 1.4rem;
      font-weight: 300;
      line-height: 1;
    "
    onmouseenter={(e) => { e.currentTarget.style.opacity = '0.7'; e.currentTarget.style.borderStyle = 'solid'; }}
    onmouseleave={(e) => { e.currentTarget.style.opacity = '0.4'; e.currentTarget.style.borderStyle = 'dashed'; }}
    aria-label="Add new task"
  >
    +
  </button>
{/if}

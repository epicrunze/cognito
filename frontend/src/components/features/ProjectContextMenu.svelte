<script lang="ts">
  import { onMount } from 'svelte';
  import type { Project } from '$lib/types';
  import { projectsStore } from '$lib/stores/projects.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import { projectIconStore, ICON_EMOJIS } from '$lib/stores/projectIcons.svelte';
  import { PRESET_COLORS } from '$lib/constants';

  let {
    project,
    position,
    onclose,
    ondelete,
  }: {
    project: Project;
    position: { x: number; y: number };
    onclose: () => void;
    ondelete?: () => void;
  } = $props();

  type View = 'menu' | 'rename' | 'color' | 'icon' | 'delete';
  let view = $state<View>('menu');

  let renameValue = $state('');
  let confirmText = $state('');
  let renameInput = $state<HTMLInputElement | null>(null);
  let confirmInput = $state<HTMLInputElement | null>(null);
  const confirmMatch = $derived(confirmText === project.title);
  let menuEl = $state<HTMLDivElement | null>(null);

  let debounceTimer: ReturnType<typeof setTimeout> | undefined;

  // Clamp position to viewport
  const clampedX = $derived(Math.min(position.x, window.innerWidth - 280));
  const clampedY = $derived(Math.min(position.y, window.innerHeight - 300));

  function handleClickOutside(e: MouseEvent) {
    if (menuEl && !menuEl.contains(e.target as Node)) {
      onclose();
    }
  }

  onMount(() => {
    document.addEventListener('mousedown', handleClickOutside, true);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside, true);
      if (debounceTimer) clearTimeout(debounceTimer);
    };
  });

  function showRename() {
    renameValue = project.title;
    view = 'rename';
    requestAnimationFrame(() => renameInput?.focus());
  }

  function saveRename() {
    const trimmed = renameValue.trim();
    if (!trimmed || trimmed === project.title) {
      onclose();
      return;
    }
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        await projectsStore.update(project.id, { title: trimmed });
        addToast('Project renamed', 'success');
      } catch {
        // store handles rollback + toast
      }
      onclose();
    }, 500);
  }

  function handleRenameKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveRename();
    } else if (e.key === 'Escape') {
      onclose();
    }
  }

  async function selectColor(hex: string) {
    try {
      await projectsStore.update(project.id, { hex_color: hex });
      addToast('Color updated', 'success');
    } catch {
      // store handles rollback + toast
    }
    onclose();
  }

  async function handleArchive() {
    try {
      await projectsStore.archive(project.id);
      addToast('Project archived', 'success');
    } catch {
      // store handles rollback + toast
    }
    onclose();
  }

  async function handleDelete() {
    try {
      await projectsStore.delete(project.id);
      addToast('Project deleted', 'success');
      ondelete?.();
    } catch {
      // store handles rollback + toast
    }
    onclose();
  }
</script>

<div
  bind:this={menuEl}
  class="context-menu"
  style="left: {clampedX}px; top: {clampedY}px;"
>
  {#if view === 'menu'}
    <button class="menu-item" onclick={showRename}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
      </svg>
      Rename
    </button>
    <button class="menu-item" onclick={() => view = 'icon'}>
      <span style="font-size: 14px; width: 14px; text-align: center; line-height: 1;">{projectIconStore.get(project.id, project.title)}</span>
      Icon
    </button>
    <button class="menu-item" onclick={() => view = 'color'}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <circle cx="12" cy="12" r="4" fill="currentColor"/>
      </svg>
      Color
    </button>
    <button class="menu-item" onclick={handleArchive}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="3" width="20" height="5" rx="1"/>
        <path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/>
        <path d="M10 12h4"/>
      </svg>
      Archive
    </button>
    <div class="divider"></div>
    <button class="menu-item destructive" onclick={() => { confirmText = ''; view = 'delete'; requestAnimationFrame(() => confirmInput?.focus()); }}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 6h18"/>
        <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
      </svg>
      Delete
    </button>

  {:else if view === 'rename'}
    <div class="rename-panel">
      <input
        bind:this={renameInput}
        bind:value={renameValue}
        onkeydown={handleRenameKeydown}
        onblur={saveRename}
        class="rename-input"
        type="text"
        spellcheck="false"
      />
    </div>

  {:else if view === 'color'}
    <div class="color-panel">
      <button class="back-btn" onclick={() => view = 'menu'}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 12H5"/>
          <path d="m12 19-7-7 7-7"/>
        </svg>
        Color
      </button>
      <div class="swatch-grid">
        {#each PRESET_COLORS as color (color.hex)}
          <button
            class="swatch"
            class:selected={project.hex_color === color.hex}
            style="background: {color.hex};"
            title={color.name}
            onclick={() => selectColor(color.hex)}
          ></button>
        {/each}
        <button
          class="swatch clear-swatch"
          class:selected={!project.hex_color}
          title="Clear color"
          onclick={() => selectColor('')}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 6 6 18"/>
            <path d="m6 6 12 12"/>
          </svg>
        </button>
      </div>
    </div>

  {:else if view === 'icon'}
    <div class="icon-panel">
      <button class="back-btn" onclick={() => view = 'menu'}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 12H5"/>
          <path d="m12 19-7-7 7-7"/>
        </svg>
        Icon
      </button>
      <div class="icon-grid">
        {#each ICON_EMOJIS as emoji (emoji)}
          <button
            class="icon-btn"
            class:selected={projectIconStore.get(project.id, project.title) === emoji}
            onclick={() => { projectIconStore.set(project.id, emoji); onclose(); }}
          >{emoji}</button>
        {/each}
      </div>
      {#if projectIconStore.hasOverride(project.id)}
        <button class="reset-icon-btn" onclick={() => { projectIconStore.clear(project.id); onclose(); }}>
          Reset to auto
        </button>
      {/if}
    </div>

  {:else if view === 'delete'}
    <div class="delete-panel">
      <button class="back-btn" onclick={() => { confirmText = ''; view = 'menu'; }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 12H5"/>
          <path d="m12 19-7-7 7-7"/>
        </svg>
        Back
      </button>
      <div class="delete-info">
        <span class="delete-warning">All tasks will be permanently deleted.</span>
        <span class="delete-confirm-hint">Type <strong>{project.title}</strong> to confirm</span>
        <input
          bind:this={confirmInput}
          bind:value={confirmText}
          onkeydown={(e) => { if (e.key === 'Enter' && confirmMatch) handleDelete(); else if (e.key === 'Escape') { confirmText = ''; view = 'menu'; } }}
          class="confirm-input"
          type="text"
          placeholder={project.title}
          spellcheck="false"
          autocomplete="off"
        />
      </div>
      <div class="delete-actions">
        <button class="cancel-btn" onclick={() => { confirmText = ''; view = 'menu'; }}>Cancel</button>
        <button class="confirm-delete-btn" disabled={!confirmMatch} onclick={handleDelete}>Delete</button>
      </div>
    </div>
  {/if}
</div>

<style>
  .context-menu {
    position: fixed;
    z-index: 300;
    min-width: 180px;
    max-width: 280px;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    padding: 4px;
    font-family: var(--font-sans);
  }

  .menu-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 8px 12px;
    font-size: 13px;
    color: var(--text-primary);
    background: none;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    text-align: left;
    font-family: var(--font-sans);
    transition: background 150ms;
  }

  .menu-item:hover {
    background: var(--bg-surface-hover);
  }

  .menu-item.destructive {
    color: #E85D5D;
  }

  .menu-item.destructive:hover {
    background: rgba(232, 93, 93, 0.1);
  }

  .divider {
    height: 1px;
    background: var(--border-default);
    margin: 4px 8px;
  }

  .rename-panel {
    padding: 6px;
  }

  .rename-input {
    width: 100%;
    padding: 7px 10px;
    font-size: 13px;
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 6px;
    outline: none;
    font-family: var(--font-sans);
    box-sizing: border-box;
  }

  .rename-input:focus {
    border-color: var(--accent);
  }

  .color-panel {
    padding: 4px;
  }

  .back-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 6px 8px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    background: none;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    text-align: left;
    font-family: var(--font-sans);
    margin-bottom: 4px;
  }

  .back-btn:hover {
    background: var(--bg-surface-hover);
  }

  .swatch-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 6px;
    padding: 4px 4px 8px;
    justify-items: center;
  }

  .swatch {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    border: 2px solid transparent;
    cursor: pointer;
    transition: border-color 150ms, transform 150ms;
    padding: 0;
  }

  .swatch:hover {
    transform: scale(1.15);
  }

  .swatch.selected {
    border-color: var(--text-primary);
  }

  .clear-swatch {
    background: none;
    border: 2px dashed var(--text-tertiary);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-tertiary);
  }

  .clear-swatch:hover {
    border-color: var(--text-secondary);
    color: var(--text-secondary);
  }

  .icon-panel {
    padding: 4px;
  }

  .icon-grid {
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    gap: 2px;
    padding: 4px 2px 8px;
    justify-items: center;
  }

  .icon-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    background: none;
    border: 2px solid transparent;
    border-radius: 6px;
    cursor: pointer;
    padding: 0;
    transition: background 150ms, border-color 150ms, transform 150ms;
  }

  .icon-btn:hover {
    background: var(--bg-surface-hover);
    transform: scale(1.15);
  }

  .icon-btn.selected {
    border-color: var(--accent);
    background: var(--accent-subtle);
  }

  .reset-icon-btn {
    width: 100%;
    padding: 6px 8px;
    font-size: 12px;
    color: var(--text-tertiary);
    background: none;
    border: none;
    border-top: 1px solid var(--border-default);
    cursor: pointer;
    font-family: var(--font-sans);
    text-align: center;
    transition: color 150ms;
  }

  .reset-icon-btn:hover {
    color: var(--text-secondary);
  }

  .delete-panel {
    padding: 4px;
  }

  .delete-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 8px 12px;
  }

  .delete-warning {
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.4;
  }

  .delete-confirm-hint {
    font-size: 12px;
    color: var(--text-tertiary);
    line-height: 1.4;
  }

  .confirm-input {
    width: 100%;
    padding: 7px 10px;
    font-size: 13px;
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 6px;
    outline: none;
    font-family: var(--font-sans);
    box-sizing: border-box;
  }

  .confirm-input:focus {
    border-color: #E85D5D;
  }

  .delete-actions {
    display: flex;
    gap: 8px;
    padding: 0 4px 4px;
  }

  .cancel-btn,
  .confirm-delete-btn {
    flex: 1;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-family: var(--font-sans);
    transition: background 150ms;
  }

  .cancel-btn {
    background: var(--bg-surface-hover);
    color: var(--text-primary);
  }

  .cancel-btn:hover {
    background: var(--border-default);
  }

  .confirm-delete-btn {
    background: #E85D5D;
    color: #fff;
  }

  .confirm-delete-btn:hover:not(:disabled) {
    background: #d14a4a;
  }

  .confirm-delete-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
</style>

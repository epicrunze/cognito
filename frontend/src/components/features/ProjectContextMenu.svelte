<script lang="ts">
  import { onMount } from 'svelte';
  import type { Project } from '$lib/types';
  import { projectsStore } from '$lib/stores/projects.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import { projectIdentifierStore } from '$lib/stores/projectIdentifiers.svelte';
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

  let identifierValue = $state('');
  let identifierInput = $state<HTMLInputElement | null>(null);
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;

  // Custom color picker state
  let showCustom = $state(false);
  let hexInput = $state('');
  let hexValid = $state(true);
  let hue = $state(0);
  let saturation = $state(100);
  let lightness = $state(50);
  let dragging = $state<'hue' | 'sl' | null>(null);
  let hueEl = $state<HTMLDivElement | null>(null);
  let slEl = $state<HTMLDivElement | null>(null);

  function hslToHex(h: number, s: number, l: number): string {
    s /= 100;
    l /= 100;
    const a = s * Math.min(l, 1 - l);
    const f = (n: number) => {
      const k = (n + h / 30) % 12;
      const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
      return Math.round(255 * color).toString(16).padStart(2, '0');
    };
    return `#${f(0)}${f(8)}${f(4)}`.toUpperCase();
  }

  function hexToHsl(hex: string): [number, number, number] {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    let h = 0;
    let s = 0;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
        case g: h = ((b - r) / d + 2) / 6; break;
        case b: h = ((r - g) / d + 4) / 6; break;
      }
    }
    return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
  }

  const customHex = $derived(hslToHex(hue, saturation, lightness));

  function initCustomFromProject() {
    const hex = project.hex_color ? (project.hex_color.startsWith('#') ? project.hex_color : `#${project.hex_color}`) : '#E8772E';
    if (/^#[0-9A-Fa-f]{6}$/.test(hex)) {
      const [h, s, l] = hexToHsl(hex);
      hue = h;
      saturation = s;
      lightness = l;
      hexInput = hex.toUpperCase();
    }
  }

  function applyCustomColor(hex: string) {
    projectsStore.update(project.id, { hex_color: hex }).catch(() => {});
  }

  function updateHue(clientX: number) {
    if (!hueEl) return;
    const rect = hueEl.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    hue = Math.round((x / rect.width) * 360);
    hexInput = hslToHex(hue, saturation, lightness);
    hexValid = true;
    applyCustomColor(hexInput);
  }

  function handleHueDown(e: MouseEvent) {
    e.preventDefault();
    dragging = 'hue';
    updateHue(e.clientX);
  }

  function updateSL(clientX: number, clientY: number) {
    if (!slEl) return;
    const rect = slEl.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    const y = Math.max(0, Math.min(clientY - rect.top, rect.height));
    saturation = Math.round((x / rect.width) * 100);
    lightness = Math.round((1 - y / rect.height) * 100);
    hexInput = hslToHex(hue, saturation, lightness);
    hexValid = true;
    applyCustomColor(hexInput);
  }

  function handleSLDown(e: MouseEvent) {
    e.preventDefault();
    dragging = 'sl';
    updateSL(e.clientX, e.clientY);
  }

  $effect(() => {
    if (!dragging) return;
    function handleMove(e: MouseEvent) {
      e.preventDefault();
      if (dragging === 'hue') {
        updateHue(e.clientX);
      } else if (dragging === 'sl') {
        updateSL(e.clientX, e.clientY);
      }
    }
    function handleUp() {
      dragging = null;
    }
    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
    return () => {
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };
  });

  function handleHexInput(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    hexInput = val;
    if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
      hexValid = true;
      applyCustomColor(val);
    } else {
      hexValid = false;
    }
  }

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
    <button class="menu-item" onclick={() => { identifierValue = projectIdentifierStore.get(project.id, project.title); view = 'icon'; requestAnimationFrame(() => identifierInput?.focus()); }}>
      <span style="font-size: 12px; font-weight: 600; width: 14px; text-align: center; line-height: 1;">{projectIdentifierStore.get(project.id, project.title)}</span>
      Identifier
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
      <button class="back-btn" onclick={() => { showCustom = false; view = 'menu'; }}>
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

      <!-- Custom color toggle -->
      <button class="custom-toggle" onclick={() => { showCustom = !showCustom; if (showCustom) initCustomFromProject(); }}>
        {showCustom ? 'Hide custom' : 'Custom...'}
      </button>

      {#if showCustom}
        <div class="custom-section">
          <!-- Hue strip -->
          <div
            bind:this={hueEl}
            class="hue-strip"
            role="slider"
            tabindex="0"
            aria-label="Hue"
            aria-valuemin={0}
            aria-valuemax={360}
            aria-valuenow={hue}
            onmousedown={handleHueDown}
          >
            <div class="hue-thumb" style="left: {(hue / 360) * 100}%;"></div>
          </div>

          <!-- Saturation/Lightness pad -->
          <div
            bind:this={slEl}
            class="sl-pad"
            role="slider"
            tabindex="0"
            aria-label="Saturation and Lightness"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={saturation}
            style="background: linear-gradient(to top, #000, transparent, #fff), linear-gradient(to right, #888, hsl({hue}, 100%, 50%));"
            onmousedown={handleSLDown}
          >
            <div
              class="sl-thumb"
              style="left: {saturation}%; top: {100 - lightness}%; background: {customHex};"
            ></div>
          </div>

          <!-- Hex input -->
          <div class="hex-row">
            <div class="hex-preview" style="background: {customHex};"></div>
            <input
              class="hex-input"
              class:invalid={!hexValid}
              type="text"
              value={hexInput}
              oninput={handleHexInput}
              spellcheck="false"
              maxlength={7}
              placeholder="#000000"
            />
          </div>
        </div>
      {/if}
    </div>

  {:else if view === 'icon'}
    <div class="icon-panel">
      <button class="back-btn" onclick={() => view = 'menu'}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 12H5"/>
          <path d="m12 19-7-7 7-7"/>
        </svg>
        Identifier
      </button>
      <div class="identifier-edit">
        <input
          bind:this={identifierInput}
          bind:value={identifierValue}
          class="identifier-input"
          type="text"
          maxlength="3"
          placeholder={project.title.charAt(0).toUpperCase()}
          oninput={() => { identifierValue = identifierValue.toUpperCase(); }}
          onkeydown={(e) => { if (e.key === 'Enter') { const v = identifierValue.trim(); if (v) projectIdentifierStore.set(project.id, v); onclose(); } else if (e.key === 'Escape') { onclose(); } }}
          spellcheck="false"
        />
        <span class="identifier-hint">1–3 characters</span>
      </div>
      <div class="identifier-actions">
        <button class="identifier-save-btn" onclick={() => { const v = identifierValue.trim(); if (v) projectIdentifierStore.set(project.id, v); onclose(); }}>
          Save
        </button>
        {#if projectIdentifierStore.hasOverride(project.id)}
          <button class="reset-icon-btn" onclick={() => { projectIdentifierStore.clear(project.id); onclose(); }}>
            Reset
          </button>
        {/if}
      </div>
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

  .identifier-edit {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 4px 8px 8px;
  }

  .identifier-input {
    width: 80px;
    padding: 7px 10px;
    font-size: 14px;
    font-weight: 600;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 6px;
    outline: none;
    font-family: var(--font-sans);
    box-sizing: border-box;
  }

  .identifier-input:focus {
    border-color: var(--accent);
  }

  .identifier-hint {
    font-size: 11px;
    color: var(--text-tertiary);
  }

  .identifier-actions {
    display: flex;
    gap: 8px;
    padding: 0 8px 4px;
  }

  .identifier-save-btn {
    flex: 1;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-family: var(--font-sans);
    background: var(--accent);
    color: #fff;
    transition: background 150ms;
  }

  .identifier-save-btn:hover {
    background: var(--accent-hover);
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

  .custom-toggle {
    width: 100%;
    padding: 4px 8px;
    font-size: 11px;
    color: var(--text-tertiary);
    background: none;
    border: none;
    cursor: pointer;
    font-family: var(--font-sans);
    text-align: center;
    border-radius: 4px;
    transition: color 150ms, background 150ms;
  }

  .custom-toggle:hover {
    color: var(--text-secondary);
    background: var(--bg-surface-hover);
  }

  .custom-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 0 4px 4px;
  }

  .hue-strip {
    position: relative;
    width: 100%;
    height: 14px;
    border-radius: 7px;
    background: linear-gradient(
      to right,
      hsl(0, 100%, 50%),
      hsl(60, 100%, 50%),
      hsl(120, 100%, 50%),
      hsl(180, 100%, 50%),
      hsl(240, 100%, 50%),
      hsl(300, 100%, 50%),
      hsl(360, 100%, 50%)
    );
    cursor: crosshair;
    user-select: none;
  }

  .hue-thumb {
    position: absolute;
    top: 50%;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid rgba(0, 0, 0, 0.3);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
    transform: translate(-50%, -50%);
    pointer-events: none;
  }

  .sl-pad {
    position: relative;
    width: 100%;
    height: 120px;
    border-radius: 6px;
    cursor: crosshair;
    background-blend-mode: normal, overlay;
    user-select: none;
  }

  .sl-thumb {
    position: absolute;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid #fff;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.4);
    transform: translate(-50%, -50%);
    pointer-events: none;
  }

  .hex-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .hex-preview {
    width: 24px;
    height: 24px;
    border-radius: 4px;
    border: 1px solid var(--border-default);
    flex-shrink: 0;
  }

  .hex-input {
    flex: 1;
    padding: 5px 8px;
    font-size: 12px;
    font-family: var(--font-mono, monospace);
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 4px;
    outline: none;
    transition: border-color 150ms;
  }

  .hex-input:focus {
    border-color: var(--accent);
  }

  .hex-input.invalid {
    border-color: #E85D5D;
  }
</style>

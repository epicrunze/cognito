<script lang="ts">
  import { onMount } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import { labelsStore } from '$lib/stores/labels.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import { showConfirmDialog } from '$lib/stores/confirmDialog.svelte';
  import ColorPicker from '$components/ui/ColorPicker.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';

  let editedDescriptions = new SvelteMap<number, string>();
  let saveTimeouts = new SvelteMap<number, ReturnType<typeof setTimeout>>();
  let cleaningUp = $state(false);
  let generatingFor = $state<number | null>(null);

  onMount(() => {
    labelsStore.fetchAll();
    labelsStore.fetchDescriptions();
    labelsStore.fetchStats();
  });

  function getDescription(labelId: number): string {
    if (editedDescriptions.has(labelId)) return editedDescriptions.get(labelId)!;
    const desc = labelsStore.descriptions.find(d => d.label_id === labelId);
    return desc?.description ?? '';
  }

  function getLabelStats(labelId: number) {
    return labelsStore.stats[labelId] ?? null;
  }

  async function handleDeleteLabel(labelId: number, title: string) {
    const confirmed = await showConfirmDialog({
      title: 'Delete label',
      message: `Delete "${title}"? This will remove it from all tasks.`,
      confirmLabel: 'Delete',
      destructive: true,
    });
    if (!confirmed) return;
    try {
      await labelsStore.delete(labelId);
      addToast('Label deleted', 'success');
    } catch {
      addToast('Failed to delete label', 'error');
    }
  }

  async function handleCleanup() {
    cleaningUp = true;
    try {
      const count = await labelsStore.cleanup();
      if (count > 0) {
        addToast(`Removed ${count} unused label${count === 1 ? '' : 's'}`, 'success');
        labelsStore.fetchStats();
      } else {
        addToast('No unused labels found', 'info');
      }
    } catch {
      addToast('Failed to clean up labels', 'error');
    } finally {
      cleaningUp = false;
    }
  }

  function handleInput(labelId: number, title: string, value: string) {
    editedDescriptions.set(labelId, value);

    if (saveTimeouts.has(labelId)) clearTimeout(saveTimeouts.get(labelId)!);
    saveTimeouts.set(labelId, setTimeout(async () => {
      if (value.trim()) {
        await labelsStore.upsertDescription(labelId, { title, description: value });
      } else {
        await labelsStore.deleteDescription(labelId);
      }
      saveTimeouts.delete(labelId);
    }, 500));
  }

  let colorTimeouts = new SvelteMap<number, ReturnType<typeof setTimeout>>();

  function handleColorChange(labelId: number, hex: string) {
    if (colorTimeouts.has(labelId)) clearTimeout(colorTimeouts.get(labelId)!);
    colorTimeouts.set(labelId, setTimeout(async () => {
      colorTimeouts.delete(labelId);
      try {
        await labelsStore.update(labelId, { hex_color: hex });
      } catch {
        addToast('Failed to update color', 'error');
      }
    }, 300));
  }

  async function handleGenerate(labelId: number) {
    generatingFor = labelId;
    try {
      const desc = await labelsStore.generateDescription(labelId);
      editedDescriptions.set(labelId, desc);
      addToast('Description generated', 'success');
    } catch {
      addToast('Failed to generate description', 'error');
    } finally {
      generatingFor = null;
    }
  }
</script>

<div>
  <p style="font-size: 14px; color: var(--text-tertiary); margin-bottom: 16px; line-height: 1.5;">
    Add descriptions to help the AI understand what each label means. This improves auto-tagging accuracy.
  </p>

  {#if labelsStore.labels.length > 0}
    <div style="margin-bottom: 20px;">
      <button
        onclick={handleCleanup}
        disabled={cleaningUp}
        style="padding: 6px 14px; font-size: 12px; font-weight: 500; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 6px; cursor: pointer; font-family: var(--font-sans); transition: background var(--transition-fast); opacity: {cleaningUp ? 0.5 : 1};"
      >
        {cleaningUp ? 'Cleaning up...' : 'Clean up unused labels'}
      </button>
    </div>
  {/if}

  {#if labelsStore.loading}
    <div style="display: flex; flex-direction: column; gap: 16px;">
      {#each [1, 2, 3] as _ (_)}
        <div style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px;">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <Skeleton width={20} height={20} radius={10} />
            <Skeleton width="40%" height={14} />
          </div>
          <div style="margin-bottom: 10px;">
            <Skeleton width="30%" height={12} />
            <div style="margin-top: 6px;">
              <Skeleton width="100%" height={4} radius={2} />
            </div>
          </div>
          <Skeleton width="100%" height={48} radius={8} />
        </div>
      {/each}
    </div>
  {:else if labelsStore.labels.length === 0}
    <div style="padding: 32px; text-align: center; color: var(--text-tertiary); font-size: 14px;">
      No labels found. Create labels in Vikunja first.
    </div>
  {:else}
    <div style="display: flex; flex-direction: column; gap: 16px;">
      {#each labelsStore.labels as label (label.id)}
        {@const stats = getLabelStats(label.id)}
        <div style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px;">
          <!-- Header: color picker + title + stats + delete -->
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <ColorPicker value={label.hex_color || '#888888'} onchange={(hex) => handleColorChange(label.id, hex)} />
            <span style="font-size: 14px; font-weight: 500; color: var(--text-primary); flex: 1; min-width: 0;">{label.title}</span>
            <button
              onclick={() => handleDeleteLabel(label.id, label.title)}
              title="Delete label"
              style="padding: 6px; background: none; border: none; border-radius: 6px; cursor: pointer; color: var(--text-tertiary); transition: color var(--transition-fast), background var(--transition-fast); flex-shrink: 0;"
              onmouseenter={(e) => { (e.currentTarget as HTMLElement).style.color = '#E85D5D'; (e.currentTarget as HTMLElement).style.background = 'rgba(232, 93, 93, 0.1)'; }}
              onmouseleave={(e) => { (e.currentTarget as HTMLElement).style.color = 'var(--text-tertiary)'; (e.currentTarget as HTMLElement).style.background = 'none'; }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 6h18"/>
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
              </svg>
            </button>
          </div>

          <!-- Stats bar -->
          {#if stats}
            <div style="margin-bottom: 10px;">
              <span style="font-size: 12px; color: var(--text-tertiary);">
                {stats.total} task{stats.total !== 1 ? 's' : ''} ({stats.open} open / {stats.done} done)
              </span>
              {#if stats.total > 0}
                <div style="height: 4px; border-radius: 2px; background: rgba(255,255,255,0.05); margin-top: 4px; overflow: hidden; display: flex;">
                  {#if stats.open > 0}
                    <div style="width: {(stats.open / stats.total) * 100}%; background: {label.hex_color || 'var(--text-tertiary)'}; border-radius: 2px;"></div>
                  {/if}
                  {#if stats.done > 0}
                    <div style="width: {(stats.done / stats.total) * 100}%; background: {label.hex_color || 'var(--text-tertiary)'}; opacity: 0.3; border-radius: 2px;"></div>
                  {/if}
                </div>
              {/if}
            </div>
          {:else}
            <div style="margin-bottom: 10px;">
              <span style="font-size: 12px; color: var(--text-tertiary);">No tasks</span>
            </div>
          {/if}

          <!-- Description textarea + generate button -->
          <div style="display: flex; gap: 8px; align-items: flex-start;">
            <textarea
              value={getDescription(label.id)}
              oninput={(e) => handleInput(label.id, label.title, (e.target as HTMLTextAreaElement).value)}
              placeholder="Describe when this label should be applied..."
              rows="2"
              style="flex: 1; padding: 8px 12px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 8px; color: var(--text-secondary); font-size: 13px; font-family: var(--font-sans); resize: vertical; line-height: 1.5; outline: none; min-height: 48px;"
            ></textarea>
            <button
              onclick={() => handleGenerate(label.id)}
              disabled={generatingFor === label.id}
              title="Generate description with AI"
              style="padding: 6px 10px; background: var(--accent-subtle); border: 1px solid transparent; border-radius: 6px; cursor: pointer; color: var(--accent); font-size: 12px; font-family: var(--font-sans); transition: background var(--transition-fast); flex-shrink: 0; display: flex; align-items: center; gap: 4px; opacity: {generatingFor === label.id ? 0.5 : 1};"
            >
              {#if generatingFor === label.id}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                </svg>
              {:else}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
                </svg>
              {/if}
              Generate
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
</style>

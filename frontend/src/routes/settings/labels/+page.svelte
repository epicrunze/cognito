<script lang="ts">
  import { onMount } from 'svelte';
  import { labelsStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import { showConfirmDialog } from '$lib/stores/confirmDialog.svelte';
  import Button from '$components/ui/Button.svelte';

  let editedDescriptions = $state<Map<number, string>>(new Map());
  let saveTimeouts = new Map<number, ReturnType<typeof setTimeout>>();
  let cleaningUp = $state(false);

  onMount(() => {
    labelsStore.fetchAll();
    labelsStore.fetchDescriptions();
  });

  function getDescription(labelId: number): string {
    if (editedDescriptions.has(labelId)) return editedDescriptions.get(labelId)!;
    const desc = labelsStore.descriptions.find(d => d.label_id === labelId);
    return desc?.description ?? '';
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
    editedDescriptions = new Map(editedDescriptions).set(labelId, value);

    // Debounced auto-save
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
</script>

<div style="max-width: 640px; margin: 0 auto; padding: 32px 24px;">
  <div style="margin-bottom: 8px;">
    <span style="font-size: 20px; font-weight: 600; color: var(--text-primary);">Label Descriptions</span>
  </div>
  <p style="font-size: 14px; color: var(--text-tertiary); margin-bottom: 16px; line-height: 1.5;">
    Add descriptions to help the AI understand what each label means. This improves auto-tagging accuracy.
  </p>

  {#if labelsStore.labels.length > 0}
    <div style="margin-bottom: 20px;">
      <button
        onclick={handleCleanup}
        disabled={cleaningUp}
        style="padding: 6px 14px; font-size: 12px; font-weight: 500; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 6px; cursor: pointer; font-family: var(--font-sans); transition: background 150ms; opacity: {cleaningUp ? 0.5 : 1};"
      >
        {cleaningUp ? 'Cleaning up...' : 'Clean up unused labels'}
      </button>
    </div>
  {/if}

  {#if labelsStore.labels.length === 0}
    <div style="padding: 32px; text-align: center; color: var(--text-tertiary); font-size: 14px;">
      No labels found. Create labels in Vikunja first.
    </div>
  {:else}
    <div style="display: flex; flex-direction: column; gap: 16px;">
      {#each labelsStore.labels as label (label.id)}
        <div style="display: flex; gap: 14px; align-items: flex-start; padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 10px;">
          <div style="display: flex; align-items: center; gap: 8px; min-width: 120px; padding-top: 6px; flex-shrink: 0;">
            <div style="width: 12px; height: 12px; border-radius: 50%; background: {label.hex_color || 'var(--text-tertiary)'}; flex-shrink: 0;"></div>
            <span style="font-size: 14px; font-weight: 500; color: var(--text-primary);">{label.title}</span>
          </div>
          <textarea
            value={getDescription(label.id)}
            oninput={(e) => handleInput(label.id, label.title, (e.target as HTMLTextAreaElement).value)}
            placeholder="Describe when this label should be applied..."
            rows="2"
            style="flex: 1; padding: 8px 12px; background: var(--bg-base); border: 1px solid var(--border-subtle); border-radius: 8px; color: var(--text-secondary); font-size: 13px; font-family: var(--font-sans); resize: vertical; line-height: 1.5; outline: none; min-height: 48px;"
          ></textarea>
          <button
            onclick={() => handleDeleteLabel(label.id, label.title)}
            title="Delete label"
            style="padding: 6px; background: none; border: none; border-radius: 6px; cursor: pointer; color: var(--text-tertiary); transition: color 150ms, background 150ms; flex-shrink: 0; margin-top: 4px;"
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
      {/each}
    </div>
  {/if}
</div>

<script lang="ts">
  import { onMount } from 'svelte';
  import { labelsStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import Button from '$components/ui/Button.svelte';

  let editedDescriptions = $state<Map<number, string>>(new Map());
  let saveTimeouts = new Map<number, ReturnType<typeof setTimeout>>();

  onMount(() => {
    labelsStore.fetchAll();
    labelsStore.fetchDescriptions();
  });

  function getDescription(labelId: number): string {
    if (editedDescriptions.has(labelId)) return editedDescriptions.get(labelId)!;
    const desc = labelsStore.descriptions.find(d => d.label_id === labelId);
    return desc?.description ?? '';
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
  <p style="font-size: 14px; color: var(--text-tertiary); margin-bottom: 28px; line-height: 1.5;">
    Add descriptions to help the AI understand what each label means. This improves auto-tagging accuracy.
  </p>

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
        </div>
      {/each}
    </div>
  {/if}
</div>

import { labelsApi } from '$lib/api';
import { addToast } from '$lib/stores/toast.svelte';
import type { Label, LabelDescription, LabelStats } from '$lib/types';

function createLabelsStore() {
  let labels = $state<Label[]>([]);
  let loading = $state(false);
  let descriptions = $state<LabelDescription[]>([]);
  let stats = $state<LabelStats>({});

  return {
    get labels() {
      return labels;
    },
    get loading() {
      return loading;
    },
    get descriptions() {
      return descriptions;
    },
    get stats() {
      return stats;
    },

    async fetchAll() {
      loading = true;
      try {
        const res = await labelsApi.list();
        labels = res.labels;
      } catch {
        // Silent failure — labels are non-critical
      } finally {
        loading = false;
      }
    },

    async create(data: { title: string; hex_color?: string }): Promise<Label> {
      const label = await labelsApi.create(data);
      labels = [...labels, label];
      return label;
    },

    async fetchDescriptions() {
      try {
        const res = await labelsApi.descriptions();
        descriptions = res.descriptions;
      } catch {
        // Silent
      }
    },

    async upsertDescription(labelId: number, data: { title: string; description: string }) {
      try {
        const result = await labelsApi.upsertDescription(labelId, data);
        const idx = descriptions.findIndex((d) => d.label_id === labelId);
        if (idx >= 0) {
          descriptions = [...descriptions.slice(0, idx), result, ...descriptions.slice(idx + 1)];
        } else {
          descriptions = [...descriptions, result];
        }
      } catch (e) {
        addToast('Failed to save description', 'error');
      }
    },

    async deleteDescription(labelId: number) {
      try {
        await labelsApi.deleteDescription(labelId);
        descriptions = descriptions.filter((d) => d.label_id !== labelId);
      } catch (e) {
        addToast('Failed to delete description', 'error');
      }
    },

    async fetchStats() {
      try {
        const res = await labelsApi.stats();
        stats = res.stats;
      } catch {
        // Silent
      }
    },

    async update(labelId: number, data: { title?: string; hex_color?: string; description?: string }) {
      const updated = await labelsApi.update(labelId, data);
      labels = labels.map((l) => (l.id === labelId ? { ...l, ...updated } : l));
      return updated;
    },

    async generateDescription(labelId: number): Promise<string> {
      const res = await labelsApi.generateDescription(labelId);
      // Update descriptions store too
      const idx = descriptions.findIndex((d) => d.label_id === labelId);
      const desc = { label_id: labelId, title: labels.find(l => l.id === labelId)?.title ?? '', description: res.description };
      if (idx >= 0) {
        descriptions = [...descriptions.slice(0, idx), { ...descriptions[idx], ...desc }, ...descriptions.slice(idx + 1)];
      } else {
        descriptions = [...descriptions, desc];
      }
      return res.description;
    },

    async delete(labelId: number) {
      await labelsApi.delete(labelId);
      labels = labels.filter((l) => l.id !== labelId);
      descriptions = descriptions.filter((d) => d.label_id !== labelId);
    },

    async cleanup(): Promise<number> {
      const res = await labelsApi.cleanup();
      if (res.deleted.length > 0) {
        const deletedSet = new Set(res.deleted);
        labels = labels.filter((l) => !deletedSet.has(l.id));
        descriptions = descriptions.filter((d) => !deletedSet.has(d.label_id));
      }
      return res.count;
    },
  };
}

export const labelsStore = createLabelsStore();

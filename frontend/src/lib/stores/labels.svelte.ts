import { labelsApi } from '$lib/api';
import type { Label } from '$lib/types';

function createLabelsStore() {
  let labels = $state<Label[]>([]);
  let loading = $state(false);

  return {
    get labels() {
      return labels;
    },
    get loading() {
      return loading;
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
  };
}

export const labelsStore = createLabelsStore();

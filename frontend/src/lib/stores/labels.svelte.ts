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
  };
}

export const labelsStore = createLabelsStore();

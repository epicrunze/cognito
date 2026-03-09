import { proposalsApi } from '$lib/api';
import { optimisticUpdate } from '$lib/optimistic';
import { filterStore } from '$lib/stores/filter.svelte';
import type { TaskProposal } from '$lib/types';

function createProposalsStore() {
  let proposals = $state<TaskProposal[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  return {
    get proposals() {
      return proposals;
    },
    get loading() {
      return loading;
    },
    get error() {
      return error;
    },

    async fetchPending() {
      loading = true;
      error = null;
      try {
        const res = await proposalsApi.list('pending');
        proposals = res.proposals;
      } catch (e) {
        error = e instanceof Error ? e.message : 'Failed to load proposals';
      } finally {
        loading = false;
      }
    },

    add(proposal: TaskProposal) {
      proposals = [...proposals, proposal];
    },

    async approve(id: string) {
      const original = [...proposals];

      await optimisticUpdate({
        apply: () => {
          proposals = proposals.map((p) => (p.id === id ? { ...p, status: 'approved' as const } : p));
        },
        apiCall: async () => {
          const res = await proposalsApi.approve(id);
          if (res.vikunja_task_id) {
            filterStore.addAiTagged(res.vikunja_task_id);
          }
          return res;
        },
        rollback: () => {
          proposals = original;
        },
        errorMessage: 'Failed to approve proposal',
      });
    },

    async reject(id: string) {
      const original = [...proposals];

      await optimisticUpdate({
        apply: () => {
          proposals = proposals.filter((p) => p.id !== id);
        },
        apiCall: () => proposalsApi.reject(id),
        rollback: () => {
          proposals = original;
        },
        errorMessage: 'Failed to reject proposal',
      });
    },

    async approveAll(ids?: string[]) {
      const original = [...proposals];
      const targetIds = ids ? new Set(ids) : new Set(proposals.filter((p) => p.status === 'pending').map((p) => p.id));
      if (targetIds.size === 0) return { approved: 0, errors: [] as Array<{ id: string; title?: string; error: string }>, task_ids: [] as number[] };

      const res = await optimisticUpdate({
        apply: () => {
          proposals = proposals.map((p) =>
            targetIds.has(p.id) && p.status === 'pending' ? { ...p, status: 'approved' as const } : p,
          );
        },
        apiCall: async () => {
          const res = await proposalsApi.approveAll(ids);
          if (res.task_ids && res.task_ids.length > 0) {
            filterStore.addAiTaggedBatch(res.task_ids);
          }
          return res;
        },
        rollback: () => {
          proposals = original;
        },
        errorMessage: 'Failed to approve proposals',
      });

      return res ?? { approved: 0, errors: [] as Array<{ id: string; title?: string; error: string }>, task_ids: [] as number[] };
    },
  };
}

export const proposalsStore = createProposalsStore();

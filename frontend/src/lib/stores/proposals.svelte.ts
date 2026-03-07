import { proposalsApi } from '$lib/api';
import { optimisticUpdate } from '$lib/optimistic';
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
        apiCall: () => proposalsApi.approve(id),
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

    async approveAll() {
      const pending = proposals.filter((p) => p.status === 'pending');
      if (pending.length === 0) return { approved: 0, errors: [] };

      const original = [...proposals];

      await optimisticUpdate({
        apply: () => {
          proposals = proposals.map((p) =>
            p.status === 'pending' ? { ...p, status: 'approved' as const } : p,
          );
        },
        apiCall: () => proposalsApi.approveAll(),
        rollback: () => {
          proposals = original;
        },
        errorMessage: 'Failed to approve proposals',
      });
    },
  };
}

export const proposalsStore = createProposalsStore();

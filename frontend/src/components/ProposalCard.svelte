<script lang="ts">
  import type { Proposal } from '$lib/stores.svelte';
  import { approveProposal, rejectProposal } from '$lib/api';
  import { appState } from '$lib/stores.svelte';

  type Props = {
    proposal: Proposal;
    selected: boolean;
    onSelect: (id: string, selected: boolean) => void;
  };

  let { proposal, selected, onSelect }: Props = $props();

  let isApproving = $state(false);
  let isRejecting = $state(false);
  let error = $state<string | null>(null);

  const PRIORITY_LABELS = ['', '⭐', '⭐⭐', '⭐⭐⭐', '⭐⭐⭐⭐', '🔴'];
  const PRIORITY_NAMES = ['', 'Low', 'Low', 'Normal', 'High', 'Urgent'];

  async function handleApprove() {
    isApproving = true;
    error = null;
    try {
      await approveProposal(proposal.id);
      appState.updateProposal(proposal.id, { status: 'created' });
      // Remove from pending view after brief delay
      setTimeout(() => appState.removeProposal(proposal.id), 600);
    } catch (e: any) {
      error = e?.detail ?? 'Approval failed';
    } finally {
      isApproving = false;
    }
  }

  async function handleReject() {
    isRejecting = true;
    error = null;
    try {
      await rejectProposal(proposal.id);
      appState.removeProposal(proposal.id);
    } catch (e: any) {
      error = e?.detail ?? 'Rejection failed';
    } finally {
      isRejecting = false;
    }
  }

  function formatMinutes(m: number | null): string {
    if (!m) return '';
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    const rem = m % 60;
    return rem ? `${h}h ${rem}m` : `${h}h`;
  }
</script>

<div
  class="card p-4 transition-all duration-300 {proposal.status === 'created'
    ? 'opacity-50 scale-95'
    : 'hover:border-surface-700'}">
  <div class="flex items-start gap-3">
    <!-- Checkbox -->
    <input
      type="checkbox"
      checked={selected}
      onchange={(e) => onSelect(proposal.id, (e.target as HTMLInputElement).checked)}
      class="mt-1 accent-brand-600 w-4 h-4 cursor-pointer flex-shrink-0" />

    <div class="flex-1 min-w-0">
      <!-- Title + priority -->
      <div class="flex items-start justify-between gap-2 mb-1.5">
        <h3 class="text-surface-100 font-medium text-sm leading-snug">{proposal.title}</h3>
        <span
          class="text-xs flex-shrink-0 {proposal.priority >= 5
            ? 'text-red-400'
            : proposal.priority >= 4
              ? 'text-amber-400'
              : 'text-surface-500'}"
          title={PRIORITY_NAMES[proposal.priority] ?? ''}>
          {PRIORITY_LABELS[proposal.priority] ?? ''}
        </span>
      </div>

      {#if proposal.description}
        <p class="text-surface-400 text-xs leading-relaxed mb-2">{proposal.description}</p>
      {/if}

      <!-- Metadata row -->
      <div class="flex flex-wrap items-center gap-2 text-xs">
        {#if proposal.project_name}
          <span class="badge-blue">📁 {proposal.project_name}</span>
        {:else}
          <span class="badge-red">📁 No project</span>
        {/if}

        {#if proposal.due_date}
          <span class="badge-gray">📅 {proposal.due_date}</span>
        {/if}

        {#if proposal.estimated_minutes}
          <span class="badge-gray">⏱ {formatMinutes(proposal.estimated_minutes)}</span>
        {/if}

        {#each proposal.labels as label}
          <span class="badge bg-surface-800 text-surface-400 border border-surface-700">{label}</span>
        {/each}
      </div>

      <!-- Error -->
      {#if error}
        <p class="mt-2 text-red-400 text-xs">{error}</p>
      {/if}
    </div>

    <!-- Action buttons -->
    <div class="flex items-center gap-1 flex-shrink-0">
      <button
        class="btn-success text-xs py-1 px-2"
        onclick={handleApprove}
        disabled={isApproving || isRejecting}
        title="Approve — creates task in Vikunja">
        {#if isApproving}
          <span class="w-3 h-3 border border-emerald-400 border-t-transparent rounded-full animate-spin inline-block"></span>
        {:else}
          ✓
        {/if}
      </button>
      <button
        class="btn-danger text-xs py-1 px-2"
        onclick={handleReject}
        disabled={isApproving || isRejecting}
        title="Reject">
        {#if isRejecting}
          <span class="w-3 h-3 border border-red-400 border-t-transparent rounded-full animate-spin inline-block"></span>
        {:else}
          ✗
        {/if}
      </button>
    </div>
  </div>
</div>

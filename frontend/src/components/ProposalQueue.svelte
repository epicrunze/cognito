<script lang="ts">
    import { approveAll } from "$lib/api";
    import { appState } from "$lib/stores.svelte";
    import ProposalCard from "./ProposalCard.svelte";

    let selected = $state<Set<string>>(new Set());
    let isApprovingAll = $state(false);
    let bulkError = $state<string | null>(null);
    let bulkSuccess = $state<string | null>(null);

    function handleSelect(id: string, isSelected: boolean) {
        const next = new Set(selected);
        if (isSelected) {
            next.add(id);
        } else {
            next.delete(id);
        }
        selected = next;
    }

    function selectAll() {
        selected = new Set(appState.pendingProposals.map((p) => p.id));
    }

    function clearSelection() {
        selected = new Set();
    }

    async function handleApproveAll() {
        isApprovingAll = true;
        bulkError = null;
        bulkSuccess = null;
        try {
            const result = await approveAll();
            // Remove all proposals that were approved
            appState.proposals = appState.proposals.filter(
                (p) => p.status !== "pending",
            );
            const errCount = result.errors.length;
            if (errCount > 0) {
                bulkError = `${result.approved} approved, ${errCount} failed`;
            } else {
                bulkSuccess = `${result.approved} tasks created in Vikunja! ✓`;
                setTimeout(() => (bulkSuccess = null), 3000);
            }
        } catch (e: any) {
            bulkError = e?.detail ?? "Bulk approve failed";
        } finally {
            isApprovingAll = false;
        }
    }

    const pending = $derived(appState.pendingProposals);
</script>

<section class="card overflow-hidden">
    <!-- Header -->
    <div
        class="px-5 py-4 border-b border-surface-800 flex items-center justify-between"
    >
        <h2 class="text-surface-100 font-semibold flex items-center gap-2">
            <span class="text-lg">📋</span>
            Proposals
            {#if pending.length > 0}
                <span class="badge-blue">{pending.length} pending</span>
            {/if}
        </h2>

        {#if pending.length > 0}
            <div class="flex items-center gap-2">
                {#if selected.size > 0}
                    <span class="text-surface-400 text-xs"
                        >{selected.size} selected</span
                    >
                    <button class="btn-ghost text-xs" onclick={clearSelection}
                        >Clear</button
                    >
                {:else}
                    <button class="btn-ghost text-xs" onclick={selectAll}
                        >Select all</button
                    >
                {/if}

                <button
                    class="btn-primary text-sm flex items-center gap-2"
                    onclick={handleApproveAll}
                    disabled={isApprovingAll}
                >
                    {#if isApprovingAll}
                        <span
                            class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"
                        ></span>
                        Approving…
                    {:else}
                        ✓ Approve All
                    {/if}
                </button>
            </div>
        {/if}
    </div>

    <!-- Feedback banners -->
    {#if bulkSuccess}
        <div
            class="px-5 py-2 bg-emerald-950/60 border-b border-emerald-800 text-emerald-300 text-sm"
        >
            {bulkSuccess}
        </div>
    {/if}
    {#if bulkError}
        <div
            class="px-5 py-2 bg-red-950/60 border-b border-red-800 text-red-300 text-sm"
        >
            ⚠️ {bulkError}
        </div>
    {/if}

    <!-- Proposal list -->
    <div class="divide-y divide-surface-800">
        {#if pending.length === 0}
            <div class="px-5 py-10 text-center">
                {#if appState.isExtracting}
                    <div class="flex flex-col items-center gap-3">
                        <div
                            class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"
                        ></div>
                        <p class="text-surface-400 text-sm">
                            Extracting tasks…
                        </p>
                    </div>
                {:else}
                    <p class="text-surface-600 text-sm">
                        No pending proposals. Paste some notes above and click <strong
                            class="text-surface-400">Extract Tasks</strong
                        >.
                    </p>
                {/if}
            </div>
        {:else}
            {#each pending as proposal (proposal.id)}
                <div class="p-3">
                    <ProposalCard
                        {proposal}
                        selected={selected.has(proposal.id)}
                        onSelect={handleSelect}
                    />
                </div>
            {/each}
        {/if}
    </div>
</section>

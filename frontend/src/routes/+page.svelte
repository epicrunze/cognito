<script lang="ts">
    import { onMount } from "svelte";
    import { getProjects } from "$lib/api";
    import { appState } from "$lib/stores.svelte";
    import InputPanel from "../components/InputPanel.svelte";
    import ProposalQueue from "../components/ProposalQueue.svelte";

    onMount(async () => {
        try {
            appState.projects = await getProjects();
        } catch (e) {
            console.error("Failed to load projects", e);
        }
    });
</script>

<svelte:head>
    <title>Cognito — Task Agent</title>
</svelte:head>

<div class="flex flex-col gap-6 pb-12">
    <InputPanel />
    <ProposalQueue />

    <!-- Phase 3 placeholder -->
    <section class="card p-4 opacity-40 cursor-not-allowed">
        <div class="flex items-center gap-3">
            <span class="text-2xl">📅</span>
            <div>
                <h2 class="text-surface-200 font-semibold">
                    Schedule Tomorrow
                </h2>
                <p class="text-surface-500 text-sm mt-0.5">
                    Google Calendar integration — coming in Phase 3
                </p>
            </div>
        </div>
    </section>
</div>

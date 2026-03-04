<script lang="ts">
    import { ingestStream } from "$lib/api";
    import { appState } from "$lib/stores.svelte";

    let text = $state("");
    let sourceType = $state("notes");
    let projectHint = $state("");
    let error = $state<string | null>(null);
    let streamCancel: (() => void) | null = null;

    const SOURCE_TYPES = [
        { value: "notes", label: "📋 Notes" },
        { value: "email", label: "📧 Email" },
        { value: "idea", label: "💡 Idea" },
    ];

    function handleExtract() {
        if (!text.trim() || appState.isExtracting) return;

        error = null;
        appState.isExtracting = true;

        streamCancel = ingestStream(
            {
                text,
                source_type: sourceType,
                project_hint: projectHint || undefined,
            },
            (proposal) => {
                appState.addProposal(proposal);
            },
            (count) => {
                appState.isExtracting = false;
                streamCancel = null;
                if (count > 0) text = "";
            },
            (detail) => {
                error = detail;
                appState.isExtracting = false;
                streamCancel = null;
            },
        );
    }

    function handleCancel() {
        streamCancel?.();
        streamCancel = null;
        appState.isExtracting = false;
    }

    function handleKeydown(e: KeyboardEvent) {
        if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
            e.preventDefault();
            handleExtract();
        }
    }
</script>

<section class="card p-5">
    <div class="flex items-center justify-between mb-4">
        <h2 class="text-surface-100 font-semibold flex items-center gap-2">
            <span class="text-lg">✍️</span>
            Input
        </h2>

        <!-- Source type selector -->
        <div class="flex gap-1 bg-surface-800 rounded-lg p-1">
            {#each SOURCE_TYPES as type}
                <button
                    class="px-3 py-1 rounded-md text-sm font-medium transition-colors {sourceType ===
                    type.value
                        ? 'bg-brand-600 text-white'
                        : 'text-surface-400 hover:text-surface-200'}"
                    onclick={() => (sourceType = type.value)}
                >
                    {type.label}
                </button>
            {/each}
        </div>
    </div>

    <!-- Text area -->
    <textarea
        bind:value={text}
        onkeydown={handleKeydown}
        placeholder="Paste your meeting notes, email, or ideas here…"
        rows="6"
        class="input resize-none text-sm leading-relaxed font-mono mb-3"
        disabled={appState.isExtracting}
    ></textarea>

    <!-- Project hint -->
    <div class="mb-4">
        <input
            bind:value={projectHint}
            type="text"
            placeholder="Project hint (optional) — e.g. PhD"
            class="input text-sm"
            disabled={appState.isExtracting}
        />
    </div>

    <!-- Error message -->
    {#if error}
        <div
            class="mb-3 px-3 py-2 bg-red-950/60 border border-red-800 rounded-lg text-red-300 text-sm"
        >
            ⚠️ {error}
        </div>
    {/if}

    <!-- Confidential toggle (Phase 2) + Extract button -->
    <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
            <button
                class="flex items-center gap-2 text-surface-500 cursor-not-allowed text-sm"
                title="Confidential mode (Ollama) — coming in Phase 2"
                disabled
            >
                <span
                    class="w-8 h-4 bg-surface-700 rounded-full relative flex items-center px-0.5"
                >
                    <span class="w-3 h-3 bg-surface-500 rounded-full"></span>
                </span>
                🔒 Confidential
                <span class="badge-gray text-xs">Phase 2</span>
            </button>
        </div>

        <div class="flex items-center gap-2">
            {#if appState.isExtracting}
                <button class="btn-ghost text-sm" onclick={handleCancel}
                    >Cancel</button
                >
                <button class="btn-primary flex items-center gap-2" disabled>
                    <span
                        class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"
                    ></span>
                    Extracting…
                </button>
            {:else}
                <span class="text-surface-600 text-xs hidden sm:block"
                    >⌘↵ to extract</span
                >
                <button
                    class="btn-primary"
                    onclick={handleExtract}
                    disabled={!text.trim()}
                >
                    Extract Tasks →
                </button>
            {/if}
        </div>
    </div>
</section>

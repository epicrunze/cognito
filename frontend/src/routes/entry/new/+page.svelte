<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { getAllEntries, createEntry } from '$lib/db/entries';
	import Chat from '$lib/components/Chat.svelte';
	import type { Entry } from '$lib/db';

	// State
	let loading = true;
	let entry: Entry | null = null;
	let error: string | null = null;

	// Redirect to login if not authenticated
	$: if ($isAuthenticated === false) {
		goto('/login');
	}

	onMount(async () => {
		await initializeEntry();
	});

	async function initializeEntry() {
		loading = true;
		error = null;

		try {
			// Get today's date in YYYY-MM-DD format
			const today = new Date();
			const todayStr = today.toISOString().split('T')[0];

			// Check if entry for today already exists
			const existingEntries = await getAllEntries();
			const todayEntry = existingEntries.find((e) => e.date === todayStr);

			if (todayEntry) {
				// Redirect to existing entry
				goto(`/entry/${todayEntry.id}`);
				return;
			}

			// Create new entry for today
			const newEntry = await createEntry({
				date: todayStr,
				conversations: [],
				refined_output: '',
				relevance_score: 1.0,
				last_interacted_at: new Date().toISOString(),
				interaction_count: 0,
				status: 'active',
				version: 1
			});

			entry = newEntry;
		} catch (e: any) {
			error = e?.message || 'Failed to create entry';
		} finally {
			loading = false;
		}
	}

	// Format today's date nicely
	function formatToday(): string {
		return new Date().toLocaleDateString('en-US', {
			weekday: 'long',
			month: 'long',
			day: 'numeric'
		});
	}
</script>

<svelte:head>
	<title>New Entry - Cognito</title>
</svelte:head>

{#if $isAuthenticated}
	<div class="max-w-4xl mx-auto">
		{#if loading}
			<div class="flex flex-col items-center justify-center py-16">
				<div
					class="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mb-4"
				></div>
				<p class="text-text-secondary">Creating today's entry...</p>
			</div>
		{:else if error}
			<div class="surface bg-error/10 text-error text-center py-8">
				<p>{error}</p>
				<button on:click={() => goto('/')} class="btn-primary mt-4">Go Back</button>
			</div>
		{:else if entry}
			<!-- Header -->
			<div class="flex items-center gap-4 mb-6">
				<button
					on:click={() => goto('/')}
					class="p-2 hover:bg-primary-light/10 rounded-lg transition-colors"
					title="Back to journal"
				>
					<svg
						class="w-6 h-6 text-text-secondary"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M15 19l-7-7 7-7"
						/>
					</svg>
				</button>
				<div>
					<h1 class="text-2xl font-bold text-primary-dark">{formatToday()}</h1>
					<p class="text-sm text-text-secondary">New journal entry</p>
				</div>
			</div>

			<!-- Welcome Message -->
			<div class="surface mb-6 text-center">
				<div class="py-4">
					<svg
						class="w-16 h-16 mx-auto mb-4 text-primary opacity-70"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
						/>
					</svg>
					<h2 class="text-xl font-semibold text-primary-dark mb-2">Welcome to your journal</h2>
					<p class="text-text-secondary max-w-md mx-auto">
						Share what's on your mind. I'm here to help you explore your thoughts through
						conversation.
					</p>
				</div>
			</div>

			<!-- Chat Interface -->
			<div class="surface overflow-hidden" style="height: 500px;">
				<Chat entryId={entry.id} existingConversation={null} />
			</div>
		{/if}
	</div>
{/if}

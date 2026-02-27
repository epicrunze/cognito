<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { isAuthenticated } from '$lib/stores/auth';
	import { getEntry, updateEntry } from '$lib/db/entries';
	import { refineEntry } from '$lib/api/chat';
	import Chat from '$lib/components/Chat.svelte';
	import type { Entry, Conversation } from '$lib/db';

	// Get entry ID from route params
	$: entryId = $page.params.id;

	// State
	let entry: Entry | null = null;
	let loading = true;
	let error: string | null = null;
	let showChat = false;
	let showRawConversations = false;
	let refining = false;
	let currentConversation: Conversation | null = null;

	// Redirect to login if not authenticated
	$: if ($isAuthenticated === false) {
		goto('/login');
	}

	// Load entry on mount and when ID changes
	onMount(() => {
		loadEntry();
	});

	$: if (entryId) {
		loadEntry();
	}

	async function loadEntry() {
		loading = true;
		error = null;

		try {
			if (!entryId) {
				error = 'Invalid entry ID';
				return;
			}
			const loadedEntry = await getEntry(entryId);
			if (loadedEntry) {
				entry = loadedEntry;
			} else {
				error = 'Entry not found';
			}
		} catch (e: any) {
			error = e?.message || 'Failed to load entry';
		} finally {
			loading = false;
		}
	}

	// Format date nicely
	function formatDate(dateStr: string): string {
		const [year, month, day] = dateStr.split('-').map(Number);
		const date = new Date(year, month - 1, day);

		const today = new Date();
		const yesterday = new Date(today);
		yesterday.setDate(yesterday.getDate() - 1);

		const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
		const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());
		const yesterdayOnly = new Date(
			yesterday.getFullYear(),
			yesterday.getMonth(),
			yesterday.getDate()
		);

		if (dateOnly.getTime() === todayOnly.getTime()) {
			return 'Today';
		} else if (dateOnly.getTime() === yesterdayOnly.getTime()) {
			return 'Yesterday';
		} else {
			return date.toLocaleDateString('en-US', {
				weekday: 'long',
				month: 'long',
				day: 'numeric',
				year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
			});
		}
	}

	// Open chat for continuing conversation
	function openChat(conversation?: Conversation) {
		currentConversation = conversation || null;
		showChat = true;
		// Lock body scroll when modal is open
		document.body.style.overflow = 'hidden';
	}

	async function closeChat() {
		showChat = false;
		currentConversation = null;
		// Restore body scroll
		document.body.style.overflow = '';
		// Reload entry to get updated conversations
		await loadEntry();
	}

	// Handle refine action
	async function handleRefine() {
		if (!entry || refining) return;

		refining = true;
		try {
			const response = await refineEntry(entry.id);
			// Update local entry
			await updateEntry(entry.id, { refined_output: response.refined_output });
			await loadEntry();
		} catch (e: any) {
			error = e?.message || 'Failed to refine entry';
		} finally {
			refining = false;
		}
	}

	// Toggle archive status
	async function toggleArchive() {
		if (!entry) return;

		const newStatus = entry.status === 'active' ? 'archived' : 'active';
		await updateEntry(entry.id, { status: newStatus });
		await loadEntry();
	}

	// Format message timestamp
	function formatMessageTime(timestamp: string): string {
		return new Date(timestamp).toLocaleTimeString('en-US', {
			hour: 'numeric',
			minute: '2-digit',
			hour12: true
		});
	}
</script>

<svelte:head>
	<title>{entry ? formatDate(entry.date) : 'Entry'} - Cognito</title>
</svelte:head>

{#if $isAuthenticated}
	<div class="max-w-4xl mx-auto">
		<!-- Header -->
		<div class="flex items-center justify-between mb-6">
			<div class="flex items-center gap-4">
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
				{#if entry}
					<div>
						<h1 class="text-2xl font-bold text-primary-dark">{formatDate(entry.date)}</h1>
						<p class="text-sm text-text-secondary">
							{entry.conversations.length} conversation{entry.conversations.length !== 1 ? 's' : ''}
						</p>
					</div>
				{/if}
			</div>

			{#if entry}
				<div class="flex items-center gap-2">
					<!-- Archive button -->
					<button
						on:click={toggleArchive}
						class="p-2 hover:bg-primary-light/10 rounded-lg transition-colors"
						title={entry.status === 'active' ? 'Archive' : 'Unarchive'}
					>
						<svg
							class="w-5 h-5 text-text-secondary"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
							/>
						</svg>
					</button>

					<!-- Status badge -->
					<span
						class="text-xs px-2 py-1 rounded-full {entry.status === 'active'
							? 'bg-success/10 text-success'
							: 'bg-text-secondary/10 text-text-secondary'}"
					>
						{entry.status}
					</span>
				</div>
			{/if}
		</div>

		{#if loading}
			<div class="surface animate-pulse">
				<div class="h-8 bg-primary-light/20 rounded w-1/3 mb-4"></div>
				<div class="h-4 bg-primary-light/20 rounded w-full mb-2"></div>
				<div class="h-4 bg-primary-light/20 rounded w-2/3"></div>
			</div>
		{:else if error}
			<div class="surface bg-error/10 text-error text-center py-8">
				<p>{error}</p>
				<button on:click={() => goto('/')} class="btn-primary mt-4">Go Back</button>
			</div>
		{:else if entry}
			<!-- Refined Output Section -->
			<div class="surface mb-6">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg font-semibold text-primary-dark">Summary</h2>
					{#if entry.conversations.length > 0}
						<button
							on:click={handleRefine}
							disabled={refining}
							class="text-sm px-3 py-1 bg-primary/10 text-primary rounded-lg hover:bg-primary/20 disabled:opacity-50 transition-colors"
						>
							{refining ? 'Refining...' : 'Refine'}
						</button>
					{/if}
				</div>

				{#if entry.refined_output}
					<div class="prose prose-sm max-w-none text-text-primary">
						<!-- Simple markdown rendering - just preserve line breaks for now -->
						{#each entry.refined_output.split('\n') as line}
							{#if line.startsWith('# ')}
								<h1 class="text-xl font-bold mt-4 mb-2">{line.slice(2)}</h1>
							{:else if line.startsWith('## ')}
								<h2 class="text-lg font-semibold mt-3 mb-2">{line.slice(3)}</h2>
							{:else if line.startsWith('- ')}
								<li class="ml-4">{line.slice(2)}</li>
							{:else if line.trim()}
								<p class="mb-2">{line}</p>
							{/if}
						{/each}
					</div>
				{:else}
					<p class="text-text-secondary italic">
						{entry.conversations.length > 0
							? 'Click "Refine" to generate a summary from your conversations.'
							: 'Start a conversation to create content for this entry.'}
					</p>
				{/if}
			</div>

			<!-- Conversations Section -->
			{#if entry.conversations.length > 0}
				<div class="surface mb-6">
					<div class="flex items-center justify-between mb-4">
						<h2 class="text-lg font-semibold text-primary-dark">Conversations</h2>
						<button
							on:click={() => (showRawConversations = !showRawConversations)}
							class="text-sm text-primary hover:underline"
						>
							{showRawConversations ? 'Hide' : 'Show'} details
						</button>
					</div>

					<div class="space-y-3">
						{#each entry.conversations as conversation, i}
							<div class="border border-primary-light/20 rounded-lg p-4">
								<div class="flex items-center justify-between mb-2">
									<span class="text-sm font-medium text-primary-dark">
										Conversation {i + 1}
									</span>
									<span class="text-xs text-text-secondary">
										{conversation.messages.length} messages
									</span>
								</div>

								{#if showRawConversations}
									<div class="mt-3 space-y-2 text-sm">
										{#each conversation.messages as message}
											<div class="flex gap-2">
												<span
													class="font-medium {message.role === 'user'
														? 'text-primary'
														: 'text-text-secondary'}"
												>
													{message.role === 'user' ? 'You:' : 'AI:'}
												</span>
												<span class="text-text-primary">{message.content}</span>
											</div>
										{/each}
									</div>
								{/if}

								<button
									on:click={() => openChat(conversation)}
									class="mt-3 text-sm text-primary hover:underline"
								>
									Continue this conversation →
								</button>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- FAB: Continue Conversation -->
			<button
				on:click={() => openChat()}
				class="fixed bottom-8 right-8 flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white rounded-full shadow-2xl transition-all hover:scale-105 z-10"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
					/>
				</svg>
				<span>New Conversation</span>
			</button>
		{/if}
	</div>

	<!-- Chat Modal -->
	{#if showChat && entry}
		<div class="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center">
			<div
				class="bg-surface w-full sm:max-w-2xl sm:mx-4 sm:rounded-t-2xl sm:rounded-b-2xl rounded-t-2xl max-h-[90vh] flex flex-col"
			>
				<!-- Chat Header -->
				<div class="flex items-center justify-between p-4 border-b border-primary-light/20">
					<div>
						<h3 class="font-semibold text-primary-dark">
							{currentConversation ? 'Continue Conversation' : 'New Conversation'}
						</h3>
						<p class="text-sm text-text-secondary">{formatDate(entry.date)}</p>
					</div>
					<button
						on:click={closeChat}
						class="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-primary-light/10 hover:bg-primary-light/20 text-primary-dark rounded-lg transition-colors"
						aria-label="Close chat"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
						Close
					</button>
				</div>

				<!-- Chat Component -->
				<div class="flex-1 min-h-0">
					<Chat entryId={entry.id} existingConversation={currentConversation} />
				</div>
			</div>
		</div>
	{/if}
{/if}

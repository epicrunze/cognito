<script lang="ts">
	import { isAuthenticated } from '$lib/stores/auth';
	import { activeEntries } from '$lib/stores/entries';
	import { refreshEntries } from '$lib/stores/entries';
	import { goto } from '$app/navigation';
	import EntryCard from '$lib/components/EntryCard.svelte';
	import { onMount } from 'svelte';

	// Redirect to login if not authenticated
	$: if ($isAuthenticated === false) {
		goto('/login');
	}

	function createNewEntry() {
		// TODO: Navigate to new entry page when implemented
		console.log('Create new entry - to be implemented');
	}

	function openEntry(entryId: string) {
		// TODO: Navigate to entry detail page when implemented
		console.log('Open entry:', entryId);
	}

	// Pull-to-refresh state
	let pullStartY = 0;
	let pullDistance = 0;
	let isPulling = false;
	let isRefreshing = false;
	const pullThreshold = 80;
	const maxPullDistance = 120;

	function handleTouchStart(e: TouchEvent) {
		// Only trigger if we're at the top of the page
		if (window.scrollY === 0 && !isRefreshing) {
			pullStartY = e.touches[0].clientY;
			isPulling = true;
		}
	}

	function handleTouchMove(e: TouchEvent) {
		if (!isPulling || isRefreshing) return;

		const touchY = e.touches[0].clientY;
		const distance = touchY - pullStartY;

		// Only pull down (positive distance)
		if (distance > 0) {
			// Prevent default scrolling when pulling
			e.preventDefault();

			// Apply resistance curve - slows down as it gets longer
			pullDistance = Math.min(distance * 0.5, maxPullDistance);
		} else {
			// Reset if user scrolls up
			resetPull();
		}
	}

	async function handleTouchEnd() {
		if (!isPulling) return;

		isPulling = false;

		// Trigger refresh if pulled past threshold
		if (pullDistance >= pullThreshold && !isRefreshing) {
			isRefreshing = true;

			try {
				await refreshEntries();

				// Keep the indicator visible for a moment to show success
				setTimeout(() => {
					resetPull();
					isRefreshing = false;
				}, 500);
			} catch (error) {
				console.error('Refresh failed:', error);
				resetPull();
				isRefreshing = false;
			}
		} else {
			resetPull();
		}
	}

	function resetPull() {
		pullDistance = 0;
		isPulling = false;
	}

	onMount(() => {
		// Add touch event listeners to window for pull-to-refresh
		window.addEventListener('touchstart', handleTouchStart, { passive: true });
		window.addEventListener('touchmove', handleTouchMove, { passive: false });
		window.addEventListener('touchend', handleTouchEnd);

		return () => {
			window.removeEventListener('touchstart', handleTouchStart);
			window.removeEventListener('touchmove', handleTouchMove);
			window.removeEventListener('touchend', handleTouchEnd);
		};
	});
</script>

{#if $isAuthenticated}
	<div class="max-w-4xl mx-auto relative">
		<!-- Pull-to-Refresh Indicator -->
		<div
			class="fixed top-0 left-0 right-0 flex justify-center pointer-events-none z-50 transition-all duration-200"
			style="transform: translateY({pullDistance > 0
				? pullDistance - 60
				: -60}px); opacity: {pullDistance / pullThreshold}"
		>
			<div class="bg-primary text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-2">
				{#if isRefreshing}
					<svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
						/>
					</svg>
					<span class="text-sm font-medium">Refreshing...</span>
				{:else if pullDistance >= pullThreshold}
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M5 13l4 4L19 7"
						/>
					</svg>
					<span class="text-sm font-medium">Release to refresh</span>
				{:else}
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M19 14l-7 7m0 0l-7-7m7 7V3"
						/>
					</svg>
					<span class="text-sm font-medium">Pull to refresh</span>
				{/if}
			</div>
		</div>

		<div class="mb-8">
			<h1 class="text-3xl font-bold text-primary-dark mb-2">Your Journal</h1>
			<p class="text-text-secondary">Capture your thoughts and insights</p>
		</div>

		{#if $activeEntries.length === 0}
			<!-- Empty State -->
			<div class="surface text-center py-16">
				<div class="mb-6">
					<svg
						class="w-20 h-20 mx-auto text-primary-light opacity-50"
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
				</div>
				<h2 class="text-2xl font-semibold text-text-primary mb-2">No entries yet</h2>
				<p class="text-text-secondary mb-6 max-w-md mx-auto">
					Start your journaling journey by creating your first entry. Share your thoughts, ideas,
					and reflections with AI-powered insights.
				</p>
				<button on:click={createNewEntry} class="btn-primary px-8 py-3">
					<span class="flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 4v16m8-8H4"
							/>
						</svg>
						Create First Entry
					</span>
				</button>
			</div>
		{:else}
			<!-- Entry List -->
			<div class="space-y-4 pb-24">
				{#each $activeEntries as entry (entry.id)}
					<EntryCard {entry} onClick={() => openEntry(entry.id)} />
				{/each}
			</div>
		{/if}

		<!-- Floating Action Button -->
		{#if $activeEntries.length > 0}
			<button
				on:click={createNewEntry}
				class="fixed bottom-8 right-8 w-14 h-14 bg-primary hover:bg-primary-dark text-white rounded-full shadow-2xl flex items-center justify-center transition-all hover:scale-110 z-10"
				title="Create new entry"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 4v16m8-8H4"
					/>
				</svg>
			</button>
		{/if}
	</div>
{/if}

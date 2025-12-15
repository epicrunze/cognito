<script lang="ts">
	import { isAuthenticated } from '$lib/stores/auth';
	import { activeEntries } from '$lib/stores/entries';
	import { goto } from '$app/navigation';

	// Redirect to login if not authenticated
	$: if ($isAuthenticated === false) {
		goto('/login');
	}
</script>

{#if $isAuthenticated}
	<div class="max-w-4xl mx-auto">
		<div class="mb-8">
			<h1 class="text-3xl font-bold text-primary-dark mb-2">Your Journal</h1>
			<p class="text-text-secondary">Capture your thoughts and insights</p>
		</div>

		{#if $activeEntries.length === 0}
			<div class="surface text-center py-12">
				<h2 class="text-xl font-semibold text-text-primary mb-2">No entries yet</h2>
				<p class="text-text-secondary mb-4">Start journaling to capture your thoughts</p>
				<button class="btn-primary"> Create First Entry </button>
			</div>
		{:else}
			<div class="space-y-4">
				{#each $activeEntries as entry}
					<div class="surface hover:shadow-lg transition-shadow cursor-pointer">
						<div class="flex justify-between items-start mb-2">
							<h3 class="font-semibold text-lg">{entry.date}</h3>
							<span class="text-sm text-text-secondary">
								{entry.conversations.length} conversation{entry.conversations.length !== 1
									? 's'
									: ''}
							</span>
						</div>
						{#if entry.refined_output}
							<p class="text-text-secondary line-clamp-3">{entry.refined_output}</p>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}

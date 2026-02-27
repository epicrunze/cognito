<script lang="ts">
	import { isAuthenticated } from '$lib/stores/auth';
	import { goto } from '$app/navigation';

	// Redirect to login if not authenticated
	$: if ($isAuthenticated === false) {
		goto('/login');
	}
</script>

<svelte:head>
	<title>Chat - Cognito</title>
</svelte:head>

{#if $isAuthenticated}
	<div class="max-w-4xl mx-auto">
		<div class="mb-8">
			<h1 class="text-3xl font-bold text-primary-dark mb-2">Quick Chat</h1>
			<p class="text-text-secondary">Chat with context from your journal entries and goals</p>
		</div>

		<!-- Coming Soon Card -->
		<div class="surface text-center py-16">
			<div class="mb-6">
				<span class="text-6xl">💬</span>
			</div>
			<h2 class="text-2xl font-semibold text-text-primary mb-2">Coming Soon</h2>
			<p class="text-text-secondary max-w-md mx-auto">
				Quick chat will allow you to have conversations backed by context from today's journal entry
				and your goals. Stay tuned!
			</p>
		</div>
	</div>
{/if}

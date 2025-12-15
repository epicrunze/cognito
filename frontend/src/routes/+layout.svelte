<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { checkAuth, authLoading, isAuthenticated } from '$lib/stores/auth';
	import { initSync, isOnline, syncIndicator } from '$lib/stores/sync';
	import { loadEntries } from '$lib/stores/entries';
	
	onMount(async () => {
		// Check authentication status
		await checkAuth();
		
		// Initialize sync store
		await initSync();
		
		// Load entries if authenticated
		if ($isAuthenticated) {
			await loadEntries();
		}
	});
</script>

{#if $authLoading}
	<div class="flex items-center justify-center min-h-screen">
		<div class="text-center">
			<p class="text-lg">Loading...</p>
		</div>
	</div>
{:else}
	<div class="min-h-screen flex flex-col">
		<!-- Offline Indicator -->
		{#if !$isOnline}
			<div class="bg-warning text-white px-4 py-2 text-center">
				You are offline. Changes will be saved locally and synced when back online.
			</div>
		{/if}
		
		<!-- Header -->
		<header class="bg-primary-dark text-white shadow-lg">
			<div class="container mx-auto px-4 py-4 flex justify-between items-center">
				<h1 class="text-2xl font-bold">Cognito</h1>
				
				<div class="flex items-center gap-4">
					<!-- Sync Indicator -->
					<div class="text-sm">
						{$syncIndicator}
					</div>
					
					<!-- Navigation would go here -->
					{#if $isAuthenticated}
						<nav class="flex gap-4">
							<a href="/" class="hover:text-primary-light transition-colors">Journal</a>
							<a href="/goals" class="hover:text-primary-light transition-colors">Goals</a>
						</nav>
					{/if}
				</div>
			</div>
		</header>
		
		<!-- Main Content -->
		<main class="flex-1 container mx-auto px-4 py-8">
			<slot />
		</main>
		
		<!-- Footer -->
		<footer class="bg-surface border-t border-primary-light py-4 text-center text-text-secondary text-sm">
			<p>&copy; 2024 Cognito - Your Thought Journal</p>
		</footer>
	</div>
{/if}

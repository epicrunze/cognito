<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { checkAuth } from '$lib/stores/auth';

	let loading = true;
	let error: string | null = null;

	onMount(async () => {
		// Get URL params
		const errorParam = $page.url.searchParams.get('error');
		const errorDescription = $page.url.searchParams.get('error_description');

		// Check if there's an error from OAuth
		if (errorParam) {
			loading = false;
			if (errorParam === 'access_denied') {
				error = 'You cancelled the login process. Please try again.';
			} else if (errorParam === 'not_authorized') {
				error = 'Your email is not authorized to access this application.';
			} else {
				error = errorDescription || 'Authentication failed. Please try again.';
			}
			return;
		}

		// The backend handles the OAuth code exchange and sets the JWT cookie
		// We just need to check if we're now authenticated
		try {
			await checkAuth();

			// If we have a user, redirect to home
			// The checkAuth will set the user in the store
			// Give it a moment to complete
			setTimeout(() => {
				goto('/');
			}, 500);
		} catch (err) {
			loading = false;
			error = 'Failed to verify authentication. Please try logging in again.';
			console.error('Auth callback error:', err);
		}
	});

	function retry() {
		goto('/login');
	}
</script>

<div class="flex items-center justify-center min-h-screen bg-background">
	<div class="surface max-w-md w-full p-8 text-center">
		{#if loading}
			<div class="mb-4">
				<div
					class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"
				></div>
			</div>
			<h2 class="text-2xl font-semibold text-primary-dark mb-2">Signing you in...</h2>
			<p class="text-text-secondary">Please wait while we complete your authentication.</p>
		{:else if error}
			<div class="mb-4">
				<svg
					class="inline-block w-12 h-12 text-error"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
			</div>
			<h2 class="text-2xl font-semibold text-error mb-2">Authentication Failed</h2>
			<p class="text-text-secondary mb-6">{error}</p>
			<button on:click={retry} class="btn-primary w-full">Try Again</button>
		{/if}
	</div>
</div>

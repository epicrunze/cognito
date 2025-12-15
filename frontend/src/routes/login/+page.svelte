<script lang="ts">
	import { isAuthenticated } from '$lib/stores/auth';
	import { login } from '$lib/api/auth';
	import { goto } from '$app/navigation';

	// Redirect to login if not authenticated
	$: if ($isAuthenticated === false) {
		// User is not authenticated, show login page
	} else if ($isAuthenticated === true) {
		// User is authenticated, redirect to main app
		goto('/');
	}
</script>

<div class="flex items-center justify-center min-h-screen bg-background">
	<div class="surface max-w-md w-full p-8 text-center">
		<h1 class="text-4xl font-bold text-primary-dark mb-4">Cognito</h1>
		<p class="text-text-secondary mb-8">Your personal thought journal with AI integration</p>

		<button on:click={login} class="btn-primary w-full py-3 text-lg"> Sign in with Google </button>

		<p class="text-sm text-text-secondary mt-4">
			Offline-first journaling with intelligent insights
		</p>
	</div>
</div>

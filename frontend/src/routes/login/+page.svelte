<script lang="ts">
	import { onMount } from 'svelte';
	import { isAuthenticated } from '$lib/stores/auth';
	import { login } from '$lib/api/auth';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	let errorMessage: string | null = null;
	let isLoading = false;

	onMount(() => {
		// Check for error message in URL params
		const error = $page.url.searchParams.get('error');
		if (error === 'not_authorized') {
			errorMessage = 'Your email is not authorized to access this application.';
		} else if (error === 'access_denied') {
			errorMessage = 'You cancelled the login process.';
		} else if (error) {
			errorMessage = 'Authentication failed. Please try again.';
		}
	});

	// Redirect to home if authenticated
	$: if ($isAuthenticated === true) {
		goto('/');
	}

	function handleLogin() {
		isLoading = true;
		login();
	}
</script>

<div
	class="flex items-center justify-center min-h-screen bg-gradient-to-br from-primary-light via-primary to-primary-dark"
>
	<div class="surface max-w-md w-full p-8 text-center shadow-2xl">
		<!-- Logo/Branding -->
		<div class="mb-6">
			<div
				class="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary to-primary-dark rounded-full mb-4 shadow-lg"
			>
				<svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
					/>
				</svg>
			</div>
			<h1 class="text-4xl font-bold text-primary-dark mb-2">Cognito</h1>
			<p class="text-text-secondary">Your personal thought journal with AI</p>
		</div>

		<!-- Error Message -->
		{#if errorMessage}
			<div class="mb-6 p-4 bg-error/10 border border-error/30 rounded-lg" role="alert">
				<div class="flex items-start gap-3">
					<svg
						class="w-5 h-5 text-error flex-shrink-0 mt-0.5"
						fill="currentColor"
						viewBox="0 0 20 20"
					>
						<path
							fill-rule="evenodd"
							d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
							clip-rule="evenodd"
						/>
					</svg>
					<p class="text-error text-sm font-medium">{errorMessage}</p>
				</div>
			</div>
		{/if}

		<!-- Sign In Button -->
		<button
			on:click={handleLogin}
			disabled={isLoading}
			class="btn-primary w-full py-3 text-lg font-semibold flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:shadow-lg"
		>
			{#if isLoading}
				<div class="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
				<span>Redirecting...</span>
			{:else}
				<svg class="w-6 h-6" viewBox="0 0 24 24">
					<path
						fill="currentColor"
						d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
					/>
					<path
						fill="currentColor"
						d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
					/>
					<path
						fill="currentColor"
						d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
					/>
					<path
						fill="currentColor"
						d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
					/>
				</svg>
				<span>Sign in with Google</span>
			{/if}
		</button>

		<!-- Features List -->
		<div class="mt-8 pt-6 border-t border-primary-light/20">
			<p class="text-sm text-text-secondary mb-4 font-semibold">Why Cognito?</p>
			<div class="space-y-2 text-left">
				<div class="flex items-center gap-2 text-sm text-text-secondary">
					<svg class="w-4 h-4 text-success flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
						<path
							fill-rule="evenodd"
							d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
							clip-rule="evenodd"
						/>
					</svg>
					<span>Offline-first journaling</span>
				</div>
				<div class="flex items-center gap-2 text-sm text-text-secondary">
					<svg class="w-4 h-4 text-success flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
						<path
							fill-rule="evenodd"
							d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
							clip-rule="evenodd"
						/>
					</svg>
					<span>AI-powered insights</span>
				</div>
				<div class="flex items-center gap-2 text-sm text-text-secondary">
					<svg class="w-4 h-4 text-success flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
						<path
							fill-rule="evenodd"
							d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
							clip-rule="evenodd"
						/>
					</svg>
					<span>Secure & private</span>
				</div>
			</div>
		</div>
	</div>
</div>

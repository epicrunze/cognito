<script lang="ts">
	import '../app.css';
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		checkAuth,
		authLoading,
		isAuthenticated,
		user,
		clearAuth,
		authSource
	} from '$lib/stores/auth';
	import { isOnline } from '$lib/stores/sync';
	import { loadEntries } from '$lib/stores/entries';
	import { logout } from '$lib/api/auth';
	import { setupBackgroundSync, cleanupBackgroundSync } from '$lib/sync';
	import SyncIndicator from '$lib/components/SyncIndicator.svelte';
	import AuthStatusBadge from '$lib/components/AuthStatusBadge.svelte';

	onMount(async () => {
		// Check authentication status
		await checkAuth();

		// Setup background sync (initializes sync store and sets up triggers)
		setupBackgroundSync();

		// Load entries if authenticated
		if ($isAuthenticated) {
			await loadEntries();
		}
	});

	onDestroy(() => {
		cleanupBackgroundSync();
	});

	async function handleLogout() {
		try {
			await logout();
			await clearAuth();
			goto('/login');
		} catch (error) {
			console.error('Logout failed:', error);
			// Still clear local auth on API failure
			await clearAuth();
			goto('/login');
		}
	}
</script>

{#if $authLoading}
	<div class="flex items-center justify-center min-h-screen">
		<div class="text-center">
			<p class="text-lg">Loading...</p>
		</div>
	</div>
{:else}
	<div class="min-h-screen flex flex-col">
		<!-- Enhanced Offline Banner -->
		{#if !$isOnline}
			<div class="bg-warning/90 text-white px-4 py-2 text-center text-sm">
				<span class="font-medium">📡 You're offline</span>
				{#if $authSource === 'stale'}
					— Using cached session. Some features may be limited.
				{:else}
					— Changes will sync when back online.
				{/if}
			</div>
		{/if}

		<!-- Header -->
		<header class="bg-primary-dark text-white shadow-lg">
			<div class="container mx-auto px-4 py-4 flex justify-between items-center">
				<h1 class="text-2xl font-bold">Cognito</h1>

				<div class="flex items-center gap-4">
					<!-- Auth Status Badge -->
					<AuthStatusBadge />

					<!-- Sync Indicator Component -->
					<SyncIndicator />

					<!-- Navigation and User Info -->
					{#if $isAuthenticated}
						<nav class="hidden md:flex gap-4">
							<a href="/" class="hover:text-primary-light transition-colors">Journal</a>
							<a href="/goals" class="hover:text-primary-light transition-colors">Goals</a>
						</nav>

						<!-- User Avatar and Menu -->
						<div class="flex items-center gap-3">
							{#if $user}
								<div class="flex items-center gap-2">
									<img
										src={$user.picture}
										alt={$user.name}
										class="w-8 h-8 rounded-full border-2 border-white/20"
									/>
									<span class="hidden sm:inline text-sm">{$user.name}</span>
								</div>

								<button
									on:click={handleLogout}
									class="text-sm px-3 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors"
									title="Logout"
								>
									Logout
								</button>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</header>

		<!-- Main Content -->
		<main class="flex-1 container mx-auto px-4 py-8">
			<slot />
		</main>

		<!-- Footer -->
		<footer
			class="bg-surface border-t border-primary-light py-4 text-center text-text-secondary text-sm"
		>
			<p>&copy; 2024 Cognito - Your Thought Journal</p>
		</footer>
	</div>
{/if}

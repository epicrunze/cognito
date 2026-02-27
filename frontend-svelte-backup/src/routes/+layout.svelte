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
	import { registerServiceWorker, updateApplying } from '$lib/sw-registration';
	import SyncIndicator from '$lib/components/SyncIndicator.svelte';
	import AuthStatusBadge from '$lib/components/AuthStatusBadge.svelte';
	import BottomNav from '$lib/components/BottomNav.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';

	onMount(async () => {
		// Register service worker and set up update detection
		registerServiceWorker();

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

{#if $updateApplying}
	<!-- Update Overlay -->
	<div class="fixed inset-0 bg-primary-dark/90 flex items-center justify-center z-50">
		<div class="text-center text-white">
			<div
				class="animate-spin w-8 h-8 border-4 border-white border-t-transparent rounded-full mx-auto mb-4"
			></div>
			<p class="text-lg font-medium">Updating to new version...</p>
			<p class="text-sm text-white/70 mt-1">Please wait</p>
		</div>
	</div>
{:else if $authLoading}
	<div class="flex items-center justify-center min-h-screen">
		<div class="text-center">
			<p class="text-lg">Loading...</p>
		</div>
	</div>
{:else}
	<div class="min-h-screen flex">
		<!-- Desktop Sidebar -->
		{#if $isAuthenticated}
			<Sidebar />
		{/if}

		<!-- Main Content Area -->
		<div class="flex-1 flex flex-col lg:ml-16 has-bottom-nav lg:has-bottom-nav-none">
			<!-- Offline Banner -->
			{#if !$isOnline}
				<div class="bg-warning text-white px-4 py-2 text-center text-sm">
					<span class="font-medium">📡 You're offline</span>
					{#if $authSource === 'stale'}
						— Using cached session. Some features may be limited.
					{:else}
						— Changes will sync when back online.
					{/if}
				</div>
			{/if}

			<!-- Mobile Header (hidden on desktop) -->
			<header class="bg-primary-dark text-white shadow-lg lg:hidden">
				<div class="px-4 py-3 flex justify-between items-center">
					<h1 class="text-xl font-bold">🧠 Cognito</h1>

					<div class="flex items-center gap-3">
						<AuthStatusBadge />
						<SyncIndicator />

						{#if $isAuthenticated && $user}
							<img
								src={$user.picture}
								alt={$user.name}
								class="w-8 h-8 rounded-full border-2 border-white/20"
							/>
						{/if}
					</div>
				</div>
			</header>

			<!-- Desktop Header (hidden on mobile) -->
			<header
				class="hidden lg:block bg-surface border-b border-surface-300 dark:border-surface-700"
			>
				<div class="px-6 py-4 flex justify-between items-center">
					<div>
						<!-- Breadcrumb or page title will go here -->
					</div>

					<div class="flex items-center gap-4">
						<AuthStatusBadge />
						<SyncIndicator />

						{#if $isAuthenticated && $user}
							<div class="flex items-center gap-3">
								<img
									src={$user.picture}
									alt={$user.name}
									class="w-8 h-8 rounded-full border-2 border-primary/20"
								/>
								<span class="text-sm font-medium text-text-primary">{$user.name}</span>
								<button
									on:click={handleLogout}
									class="text-sm px-3 py-1.5 rounded-lg bg-surface-200 hover:bg-surface-300 dark:bg-surface-700 dark:hover:bg-surface-600 text-text-secondary transition-colors"
								>
									Logout
								</button>
							</div>
						{/if}
					</div>
				</div>
			</header>

			<!-- Main Content -->
			<main class="flex-1 px-4 py-6 lg:px-8 lg:py-8 pb-24 lg:pb-8">
				<slot />
			</main>

			<!-- Footer (desktop only) -->
			<footer
				class="hidden lg:block bg-surface border-t border-surface-300 dark:border-surface-700 py-4 text-center text-text-secondary text-sm"
			>
				<p>&copy; 2024 Cognito - Your Thought Journal</p>
			</footer>
		</div>

		<!-- Mobile Bottom Navigation -->
		{#if $isAuthenticated}
			<BottomNav />
		{/if}
	</div>
{/if}

<style>
	/* Override for desktop - remove bottom nav padding */
	@media (min-width: 1024px) {
		.has-bottom-nav-none {
			padding-bottom: 0;
		}
	}
</style>

<script lang="ts">
	import { isAuthenticated, user } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { logout } from '$lib/api/auth';
	import { clearAuth } from '$lib/stores/auth';

	// Redirect to login if not authenticated
	$: if ($isAuthenticated === false) {
		goto('/login');
	}

	async function handleLogout() {
		try {
			await logout();
			await clearAuth();
			goto('/login');
		} catch (error) {
			console.error('Logout failed:', error);
			await clearAuth();
			goto('/login');
		}
	}
</script>

<svelte:head>
	<title>Settings - Cognito</title>
</svelte:head>

{#if $isAuthenticated}
	<div class="max-w-2xl mx-auto">
		<div class="mb-8">
			<h1 class="text-3xl font-bold text-primary-dark mb-2">Settings</h1>
			<p class="text-text-secondary">Manage your account and preferences</p>
		</div>

		<!-- Account Section -->
		<div class="surface mb-6">
			<h2 class="text-lg font-semibold text-primary-dark mb-4">Account</h2>

			{#if $user}
				<div class="flex items-center gap-4 mb-6">
					<img
						src={$user.picture}
						alt={$user.name}
						class="w-16 h-16 rounded-full border-2 border-primary/20"
					/>
					<div>
						<p class="font-medium text-text-primary">{$user.name}</p>
						<p class="text-sm text-text-secondary">{$user.email}</p>
					</div>
				</div>
			{/if}

			<button
				on:click={handleLogout}
				class="w-full px-4 py-3 rounded-lg border border-error/30 text-error hover:bg-error/10 transition-colors"
			>
				Sign Out
			</button>
		</div>

		<!-- Preferences Section (Coming Soon) -->
		<div class="surface mb-6">
			<h2 class="text-lg font-semibold text-primary-dark mb-4">Preferences</h2>
			<p class="text-text-secondary text-sm">More settings coming soon...</p>
		</div>

		<!-- About Section -->
		<div class="surface">
			<h2 class="text-lg font-semibold text-primary-dark mb-4">About</h2>
			<div class="space-y-2 text-sm text-text-secondary">
				<p><span class="font-medium">Version:</span> 1.0.0</p>
				<p><span class="font-medium">Built with:</span> SvelteKit, Skeleton UI, Tailwind CSS</p>
			</div>
		</div>
	</div>
{/if}

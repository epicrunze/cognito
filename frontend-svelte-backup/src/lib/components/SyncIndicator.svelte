<script lang="ts">
	/**
	 * SyncIndicator Component
	 *
	 * Displays sync status in a compact format for the header.
	 * Shows synced/syncing/pending/error states with visual indicators.
	 */

	import { onMount } from 'svelte';
	import { syncStatus, pendingCount, lastSynced, isOnline, initSync } from '$lib/stores/sync';
	import { performFullSync } from '$lib/sync';
	import { formatRelative } from '$lib/utils/timestamp';

	// Handle manual sync
	async function handleSync() {
		if ($syncStatus === 'syncing') return;
		await performFullSync();
	}

	// Initialize on mount
	onMount(async () => {
		await initSync();
	});
</script>

<div class="sync-indicator">
	{#if !$isOnline}
		<!-- Offline state -->
		<div class="indicator offline" title="You are offline. Changes will sync when back online.">
			<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path
					d="M1 1l22 22M9 9a3 3 0 0 0 4.24 4.24M6.34 6.34A8 8 0 0 0 4 12a8 8 0 0 0 8 8c1.8 0 3.47-.6 4.8-1.6M12 4a8 8 0 0 1 7.6 10.5"
				/>
			</svg>
			<span class="label">Offline</span>
		</div>
	{:else if $syncStatus === 'syncing'}
		<!-- Syncing state -->
		<div class="indicator syncing" title="Syncing...">
			<svg class="icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path
					d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
				/>
			</svg>
			<span class="label">Syncing</span>
		</div>
	{:else if $syncStatus === 'error'}
		<!-- Error state -->
		<button class="indicator error" on:click={handleSync} title="Sync failed. Click to retry.">
			<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<circle cx="12" cy="12" r="10" />
				<line x1="12" y1="8" x2="12" y2="12" />
				<line x1="12" y1="16" x2="12.01" y2="16" />
			</svg>
			<span class="label">Sync Error</span>
		</button>
	{:else if $pendingCount > 0}
		<!-- Pending changes -->
		<button
			class="indicator pending"
			on:click={handleSync}
			title="Click to sync {$pendingCount} pending change(s)"
		>
			<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path
					d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"
				/>
			</svg>
			<span class="label">{$pendingCount} pending</span>
		</button>
	{:else}
		<!-- Synced state -->
		<button
			class="indicator synced"
			on:click={handleSync}
			title="Last synced: {formatRelative($lastSynced)}. Click to sync now."
		>
			<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<polyline points="20 6 9 17 4 12" />
			</svg>
			<span class="label">{formatRelative($lastSynced)}</span>
		</button>
	{/if}
</div>

<style>
	.sync-indicator {
		display: flex;
		align-items: center;
	}

	.indicator {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.375rem 0.625rem;
		border-radius: 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		transition: all 0.2s ease;
		border: none;
		background: transparent;
		cursor: pointer;
	}

	.indicator:hover {
		background: rgba(0, 0, 0, 0.05);
	}

	.icon {
		width: 1rem;
		height: 1rem;
		flex-shrink: 0;
	}

	.label {
		white-space: nowrap;
	}

	/* States */
	.offline {
		color: #6b7280;
		cursor: default;
	}

	.syncing {
		color: #2563eb;
		cursor: default;
	}

	.error {
		color: #dc2626;
	}

	.pending {
		color: #d97706;
	}

	.synced {
		color: #16a34a;
	}

	/* Spin animation */
	.spin {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	/* Responsive: hide label on small screens */
	@media (max-width: 640px) {
		.label {
			display: none;
		}

		.indicator {
			padding: 0.375rem;
		}
	}
</style>

<script lang="ts">
	import { confirmDialogState, resolveDialog } from '$lib/stores/confirmDialog.svelte';
	import { fade, fly } from 'svelte/transition';
	import { DURATION } from '$lib/transitions';

	const request = $derived(confirmDialogState.request);

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			resolveDialog(false);
		}
	}
</script>

{#if request}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="confirm-backdrop"
		transition:fade={{ duration: DURATION.fast }}
		onclick={() => resolveDialog(false)}
		onkeydown={handleKeydown}
	>
		{#key request.id}
			<div
				class="confirm-card"
				transition:fly={{ y: 8, duration: DURATION.normal }}
				onclick={(e) => e.stopPropagation()}
				onkeydown={(e) => e.stopPropagation()}
			>
				<h3 class="confirm-title">{request.title}</h3>
				<p class="confirm-message">{request.message}</p>
				<div class="confirm-actions">
					<button
						class="confirm-btn cancel"
						onclick={() => resolveDialog(false)}
					>
						Cancel
					</button>
					<button
						class="confirm-btn confirm"
						class:destructive={request.destructive}
						onclick={() => resolveDialog(true)}
					>
						{request.confirmLabel ?? 'Confirm'}
					</button>
				</div>
			</div>
		{/key}
	</div>
{/if}

<style>
	.confirm-backdrop {
		position: fixed;
		inset: 0;
		z-index: 100;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.6);
	}

	.confirm-card {
		background: var(--bg-elevated);
		border: 1px solid var(--border-default);
		border-radius: 10px;
		padding: 24px;
		min-width: 340px;
		max-width: 420px;
		box-shadow: var(--shadow-lg);
	}

	.confirm-title {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 8px 0;
	}

	.confirm-message {
		font-size: 14px;
		color: var(--text-secondary);
		line-height: 1.5;
		margin: 0 0 20px 0;
	}

	.confirm-actions {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
	}

	.confirm-btn {
		border-radius: 8px;
		padding: 8px 16px;
		cursor: pointer;
		font-family: var(--font-sans);
		font-size: 14px;
		transition: opacity var(--transition-fast) ease;
	}

	.confirm-btn:hover {
		opacity: 0.85;
	}

	.confirm-btn.cancel {
		background: none;
		border: 1px solid var(--border-default);
		color: var(--text-secondary);
	}

	.confirm-btn.cancel:hover {
		background: var(--bg-hover, rgba(255, 255, 255, 0.05));
	}

	.confirm-btn.confirm {
		background: var(--accent);
		color: white;
		border: none;
	}

	.confirm-btn.confirm.destructive {
		background: var(--priority-urgent);
	}
</style>

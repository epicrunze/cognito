<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Goal } from '$lib/api/goals';

	export let goal: Goal;

	const dispatch = createEventDispatcher<{
		toggle: { id: string };
		edit: { goal: Goal };
		delete: { id: string };
	}>();

	// Category color mapping
	function getCategoryClass(category: string): string {
		const colors: Record<string, string> = {
			health: 'bg-green-500/10 text-green-600 border-green-500/30',
			productivity: 'bg-blue-500/10 text-blue-600 border-blue-500/30',
			skills: 'bg-purple-500/10 text-purple-600 border-purple-500/30'
		};
		return colors[category.toLowerCase()] || 'bg-gray-500/10 text-gray-600 border-gray-500/30';
	}

	// Format relative time
	function formatRelativeTime(timestamp: string): string {
		const date = new Date(timestamp);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffDays === 0) return 'today';
		if (diffDays === 1) return 'yesterday';
		if (diffDays < 7) return `${diffDays} days ago`;
		if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	function handleToggle() {
		dispatch('toggle', { id: goal.id });
	}

	function handleEdit() {
		dispatch('edit', { goal });
	}

	function handleDelete() {
		dispatch('delete', { id: goal.id });
	}
</script>

<div class="surface hover:shadow-lg transition-shadow {goal.active ? '' : 'opacity-60'}">
	<div class="flex items-start gap-4">
		<!-- Toggle Switch -->
		<button
			on:click={handleToggle}
			class="mt-1 relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 {goal.active
				? 'bg-primary'
				: 'bg-gray-300'}"
			role="switch"
			aria-checked={goal.active}
			title={goal.active ? 'Mark as inactive' : 'Mark as active'}
		>
			<span
				class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out {goal.active
					? 'translate-x-5'
					: 'translate-x-0'}"
			></span>
		</button>

		<!-- Content -->
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 mb-2">
				<!-- Category Badge -->
				<span
					class="text-xs px-2 py-0.5 rounded-full border capitalize {getCategoryClass(
						goal.category
					)}"
				>
					{goal.category}
				</span>
			</div>

			<!-- Description -->
			<p class="text-text-primary {goal.active ? 'font-medium' : ''}">{goal.description}</p>

			<!-- Footer -->
			<div class="flex items-center justify-between mt-3 text-xs text-text-secondary">
				<span>Created {formatRelativeTime(goal.created_at)}</span>
			</div>
		</div>

		<!-- Actions -->
		<div class="flex items-center gap-1">
			<button
				on:click={handleEdit}
				class="p-2 hover:bg-primary-light/10 rounded-lg transition-colors"
				title="Edit goal"
			>
				<svg
					class="w-4 h-4 text-text-secondary"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
					/>
				</svg>
			</button>
			<button
				on:click={handleDelete}
				class="p-2 hover:bg-error/10 rounded-lg transition-colors"
				title="Delete goal"
			>
				<svg
					class="w-4 h-4 text-text-secondary hover:text-error"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
					/>
				</svg>
			</button>
		</div>
	</div>
</div>

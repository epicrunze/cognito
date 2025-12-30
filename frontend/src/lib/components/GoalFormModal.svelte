<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Goal } from '$lib/api/goals';

	export let goal: Goal | null = null;

	const dispatch = createEventDispatcher<{
		submit: { category: string; description: string };
		close: void;
	}>();

	// Form state
	let category = goal?.category || '';
	let description = goal?.description || '';
	let customCategory = '';
	let showCustom = !['health', 'productivity', 'skills'].includes(
		goal?.category?.toLowerCase() || ''
	);

	// Preset categories
	const presetCategories = [
		{ value: 'health', label: 'Health & Wellness', icon: '💪' },
		{ value: 'productivity', label: 'Productivity', icon: '⚡' },
		{ value: 'skills', label: 'Skills & Learning', icon: '📚' }
	];

	// Initialize custom category if editing non-preset
	$: if (goal && !presetCategories.some((p) => p.value === goal.category.toLowerCase())) {
		customCategory = goal.category;
		showCustom = true;
	}

	function handleSubmit(e: Event) {
		e.preventDefault();

		const finalCategory = showCustom ? customCategory.trim() : category;
		if (!finalCategory || !description.trim()) return;

		dispatch('submit', {
			category: finalCategory,
			description: description.trim()
		});
	}

	function handleClose() {
		dispatch('close');
	}

	function selectCategory(value: string) {
		category = value;
		showCustom = false;
	}

	function enableCustom() {
		showCustom = true;
		category = '';
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<!-- Modal Backdrop -->
<div
	class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
	on:click={handleClose}
	on:keydown={(e) => e.key === 'Escape' && handleClose()}
	role="dialog"
	aria-modal="true"
	tabindex="-1"
	aria-labelledby="modal-title"
>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- Modal Content -->
	<div
		class="bg-surface rounded-2xl shadow-2xl w-full max-w-md"
		on:click|stopPropagation
		on:keydown|stopPropagation
	>
		<!-- Header -->
		<div class="flex items-center justify-between p-6 border-b border-primary-light/20">
			<h2 id="modal-title" class="text-xl font-semibold text-primary-dark">
				{goal ? 'Edit Goal' : 'New Goal'}
			</h2>
			<button
				on:click={handleClose}
				class="p-2 hover:bg-primary-light/10 rounded-lg transition-colors"
				aria-label="Close"
			>
				<svg
					class="w-5 h-5 text-text-secondary"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					/>
				</svg>
			</button>
		</div>

		<!-- Form -->
		<form on:submit={handleSubmit} class="p-6 space-y-6">
			<!-- Category Selection -->
			<fieldset>
				<legend class="block text-sm font-medium text-text-primary mb-3">Category</legend>
				<div class="grid grid-cols-2 gap-2 mb-2">
					{#each presetCategories as preset}
						<button
							type="button"
							on:click={() => selectCategory(preset.value)}
							class="p-3 rounded-lg border-2 text-left transition-all {category === preset.value &&
							!showCustom
								? 'border-primary bg-primary/10'
								: 'border-primary-light/30 hover:border-primary/50'}"
						>
							<span class="text-lg">{preset.icon}</span>
							<span class="block text-sm font-medium mt-1">{preset.label}</span>
						</button>
					{/each}
					<button
						type="button"
						on:click={enableCustom}
						class="p-3 rounded-lg border-2 text-left transition-all {showCustom
							? 'border-primary bg-primary/10'
							: 'border-primary-light/30 hover:border-primary/50'}"
					>
						<span class="text-lg">✨</span>
						<span class="block text-sm font-medium mt-1">Custom</span>
					</button>
				</div>

				{#if showCustom}
					<input
						type="text"
						bind:value={customCategory}
						placeholder="Enter custom category..."
						class="w-full px-4 py-3 rounded-xl border border-primary-light/30 bg-surface text-text-primary placeholder:text-text-secondary focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
						aria-label="Custom category name"
					/>
				{/if}
			</fieldset>

			<!-- Description -->
			<div>
				<label for="description" class="block text-sm font-medium text-text-primary mb-2">
					What do you want to achieve?
				</label>
				<textarea
					id="description"
					bind:value={description}
					placeholder="e.g., Exercise for 30 minutes every day, Learn to play piano..."
					rows="3"
					class="w-full px-4 py-3 rounded-xl border border-primary-light/30 bg-surface text-text-primary placeholder:text-text-secondary focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
				></textarea>
			</div>

			<!-- Actions -->
			<div class="flex gap-3">
				<button
					type="button"
					on:click={handleClose}
					class="flex-1 px-4 py-3 rounded-xl border border-primary-light/30 text-text-secondary hover:bg-primary-light/10 transition-colors"
				>
					Cancel
				</button>
				<button
					type="submit"
					disabled={!(showCustom ? customCategory.trim() : category) || !description.trim()}
					class="flex-1 px-4 py-3 rounded-xl bg-primary text-white hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
				>
					{goal ? 'Update' : 'Create'} Goal
				</button>
			</div>
		</form>
	</div>
</div>

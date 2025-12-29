<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import {
		goals,
		activeGoals,
		inactiveGoals,
		goalsLoading,
		goalsError,
		loadGoals,
		refreshGoals,
		createGoal,
		updateGoal,
		deleteGoal,
		toggleGoalActive
	} from '$lib/stores/goals';
	import GoalCard from '$lib/components/GoalCard.svelte';
	import GoalFormModal from '$lib/components/GoalFormModal.svelte';
	import type { Goal } from '$lib/api/goals';

	// Redirect to login if not authenticated
	$: if ($isAuthenticated === false) {
		goto('/login');
	}

	// Modal state
	let showModal = false;
	let editingGoal: Goal | null = null;

	// Inactive goals visibility
	let showInactive = false;

	// Load goals on mount
	onMount(() => {
		loadGoals();
	});

	// Open modal for new goal
	function openNewGoalModal() {
		editingGoal = null;
		showModal = true;
	}

	// Open modal for editing
	function openEditModal(goal: Goal) {
		editingGoal = goal;
		showModal = true;
	}

	// Close modal
	function closeModal() {
		showModal = false;
		editingGoal = null;
	}

	// Handle form submit
	async function handleSubmit(event: CustomEvent<{ category: string; description: string }>) {
		const { category, description } = event.detail;

		if (editingGoal) {
			await updateGoal(editingGoal.id, { category, description });
		} else {
			await createGoal({ category, description });
		}

		closeModal();
	}

	// Handle toggle active
	async function handleToggle(event: CustomEvent<{ id: string }>) {
		await toggleGoalActive(event.detail.id);
	}

	// Handle edit
	function handleEdit(event: CustomEvent<{ goal: Goal }>) {
		openEditModal(event.detail.goal);
	}

	// Handle delete
	async function handleDelete(event: CustomEvent<{ id: string }>) {
		if (confirm('Are you sure you want to delete this goal?')) {
			await deleteGoal(event.detail.id);
		}
	}

	// Category colors
	const categoryColors: Record<string, string> = {
		health: 'bg-green-500',
		productivity: 'bg-blue-500',
		skills: 'bg-purple-500'
	};

	function getCategoryColor(category: string): string {
		return categoryColors[category.toLowerCase()] || 'bg-gray-500';
	}
</script>

<svelte:head>
	<title>Goals - Cognito</title>
</svelte:head>

{#if $isAuthenticated}
	<div class="max-w-4xl mx-auto">
		<!-- Header -->
		<div class="mb-8">
			<h1 class="text-3xl font-bold text-primary-dark mb-2">Your Goals</h1>
			<p class="text-text-secondary">
				Define what matters to you. Goals help guide your journaling.
			</p>
		</div>

		<!-- Error Message -->
		{#if $goalsError}
			<div class="surface bg-error/10 text-error mb-6 flex items-center gap-2">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<span>{$goalsError}</span>
			</div>
		{/if}

		<!-- Loading State -->
		{#if $goalsLoading && $goals.length === 0}
			<div class="space-y-4">
				{#each [1, 2, 3] as _}
					<div class="surface animate-pulse">
						<div class="h-6 bg-primary-light/20 rounded w-1/4 mb-3"></div>
						<div class="h-4 bg-primary-light/20 rounded w-3/4"></div>
					</div>
				{/each}
			</div>
		{:else if $activeGoals.length === 0 && $inactiveGoals.length === 0}
			<!-- Empty State -->
			<div class="surface text-center py-16">
				<div class="mb-6">
					<svg
						class="w-20 h-20 mx-auto text-primary-light opacity-50"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
						/>
					</svg>
				</div>
				<h2 class="text-2xl font-semibold text-text-primary mb-2">No goals yet</h2>
				<p class="text-text-secondary mb-6 max-w-md mx-auto">
					Goals help focus your journaling. Add goals like "Learn piano", "Exercise more", or
					"Practice mindfulness".
				</p>
				<button on:click={openNewGoalModal} class="btn-primary px-8 py-3">
					<span class="flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 4v16m8-8H4"
							/>
						</svg>
						Add Your First Goal
					</span>
				</button>
			</div>
		{:else}
			<!-- Active Goals -->
			{#if $activeGoals.length > 0}
				<div class="mb-8">
					<h2 class="text-lg font-semibold text-primary-dark mb-4 flex items-center gap-2">
						<span class="w-2 h-2 bg-success rounded-full"></span>
						Active Goals
						<span class="text-sm font-normal text-text-secondary">({$activeGoals.length})</span>
					</h2>
					<div class="space-y-4">
						{#each $activeGoals as goal (goal.id)}
							<GoalCard
								{goal}
								on:toggle={handleToggle}
								on:edit={handleEdit}
								on:delete={handleDelete}
							/>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Inactive Goals -->
			{#if $inactiveGoals.length > 0}
				<div class="mb-8">
					<button
						on:click={() => (showInactive = !showInactive)}
						class="flex items-center gap-2 text-text-secondary hover:text-primary transition-colors mb-4"
					>
						<svg
							class="w-4 h-4 transition-transform {showInactive ? 'rotate-90' : ''}"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 5l7 7-7 7"
							/>
						</svg>
						<span class="text-sm font-medium">
							Inactive Goals ({$inactiveGoals.length})
						</span>
					</button>

					{#if showInactive}
						<div class="space-y-4 opacity-70">
							{#each $inactiveGoals as goal (goal.id)}
								<GoalCard
									{goal}
									on:toggle={handleToggle}
									on:edit={handleEdit}
									on:delete={handleDelete}
								/>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		{/if}

		<!-- FAB: Add Goal -->
		{#if $activeGoals.length > 0 || $inactiveGoals.length > 0}
			<button
				on:click={openNewGoalModal}
				class="fixed bottom-8 right-8 w-14 h-14 bg-primary hover:bg-primary-dark text-white rounded-full shadow-2xl flex items-center justify-center transition-all hover:scale-110 z-10"
				title="Add new goal"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 4v16m8-8H4"
					/>
				</svg>
			</button>
		{/if}
	</div>

	<!-- Goal Form Modal -->
	{#if showModal}
		<GoalFormModal goal={editingGoal} on:submit={handleSubmit} on:close={closeModal} />
	{/if}
{/if}

<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	// Props
	export let open = false;
	export let title = '';

	const dispatch = createEventDispatcher<{ close: void }>();

	// Handle backdrop click
	function handleBackdropClick() {
		dispatch('close');
	}

	// Handle swipe down to close
	let startY = 0;
	let currentY = 0;
	let isDragging = false;

	function handleTouchStart(e: TouchEvent) {
		startY = e.touches[0].clientY;
		isDragging = true;
	}

	function handleTouchMove(e: TouchEvent) {
		if (!isDragging) return;
		currentY = e.touches[0].clientY;
	}

	function handleTouchEnd() {
		if (!isDragging) return;
		isDragging = false;

		// If swiped down more than 100px, close
		if (currentY - startY > 100) {
			dispatch('close');
		}

		startY = 0;
		currentY = 0;
	}

	// Close on escape
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			dispatch('close');
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
	<!-- Backdrop -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 bg-black/50 z-40 transition-opacity"
		onclick={handleBackdropClick}
		onkeydown={(e) => e.key === 'Enter' && handleBackdropClick()}
	></div>

	<!-- Bottom Sheet -->
	<div
		class="bottom-sheet open"
		style="height: 85vh;"
		ontouchstart={handleTouchStart}
		ontouchmove={handleTouchMove}
		ontouchend={handleTouchEnd}
		role="dialog"
		aria-modal="true"
		aria-labelledby="bottom-sheet-title"
	>
		<!-- Handle -->
		<div class="flex justify-center pt-3 pb-2">
			<div class="w-12 h-1.5 bg-surface-300 dark:bg-surface-600 rounded-full"></div>
		</div>

		<!-- Header -->
		{#if title}
			<div
				class="flex items-center justify-between px-4 pb-3 border-b border-surface-200 dark:border-surface-700"
			>
				<h2 id="bottom-sheet-title" class="text-lg font-semibold text-text-primary">{title}</h2>
				<button
					onclick={() => dispatch('close')}
					class="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
					aria-label="Close"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
		{/if}

		<!-- Content -->
		<div class="flex-1 overflow-hidden">
			<slot />
		</div>
	</div>
{/if}

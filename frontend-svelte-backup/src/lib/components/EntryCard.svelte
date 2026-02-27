<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Entry } from '$lib/db';

	// Props using Svelte 5 $props() syntax
	interface Props {
		entry: Entry;
		onClick?: () => void;
	}
	let { entry, onClick }: Props = $props();

	const dispatch = createEventDispatcher<{
		swipeChat: Entry;
		swipeArchive: Entry;
		longPress: Entry;
	}>();

	// Swipe gesture state
	let startX = $state(0);
	let currentX = $state(0);
	let isSwiping = $state(false);
	let swipeOffset = $state(0);

	// Long press state
	let isPressed = $state(false);
	let pressTimer: ReturnType<typeof setTimeout> | null = $state(null);

	const MIN_SWIPE_DISTANCE = 60;

	// Handle touch/pointer events for swipe
	function handlePointerDown(event: PointerEvent) {
		startX = event.clientX;
		currentX = event.clientX;
		isSwiping = true;
		isPressed = true;

		// Long press detection
		pressTimer = setTimeout(() => {
			if (isPressed && Math.abs(currentX - startX) < 10) {
				dispatch('longPress', entry);
				isSwiping = false;
			}
		}, 500);
	}

	function handlePointerMove(event: PointerEvent) {
		if (!isSwiping) return;
		currentX = event.clientX;
		swipeOffset = Math.max(-100, Math.min(100, currentX - startX));
	}

	function handlePointerUp() {
		if (pressTimer) {
			clearTimeout(pressTimer);
			pressTimer = null;
		}
		isPressed = false;

		if (isSwiping) {
			const distance = currentX - startX;

			if (distance > MIN_SWIPE_DISTANCE) {
				dispatch('swipeChat', entry);
			} else if (distance < -MIN_SWIPE_DISTANCE) {
				dispatch('swipeArchive', entry);
			}

			isSwiping = false;
			swipeOffset = 0;
		}
	}

	function handleClick() {
		// Only trigger click if not swiping
		if (Math.abs(swipeOffset) < 10 && onClick) {
			onClick();
		}
	}

	// Format date nicely
	function formatDate(dateStr: string): string {
		const [year, month, day] = dateStr.split('-').map(Number);
		const date = new Date(year, month - 1, day);

		const today = new Date();
		const yesterday = new Date(today);
		yesterday.setDate(yesterday.getDate() - 1);

		const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
		const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());
		const yesterdayOnly = new Date(
			yesterday.getFullYear(),
			yesterday.getMonth(),
			yesterday.getDate()
		);

		if (dateOnly.getTime() === todayOnly.getTime()) {
			return 'Today';
		} else if (dateOnly.getTime() === yesterdayOnly.getTime()) {
			return 'Yesterday';
		} else {
			return date.toLocaleDateString('en-US', {
				month: 'long',
				day: 'numeric',
				year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
			});
		}
	}

	// Format relative time
	function formatRelativeTime(timestamp: string): string {
		const date = new Date(timestamp);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMins / 60);
		const diffDays = Math.floor(diffHours / 24);

		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	// Truncate text
	function truncate(text: string, maxLength: number): string {
		if (text.length <= maxLength) return text;
		return text.substring(0, maxLength).trim() + '...';
	}

	// Get relevance color
	function getRelevanceColor(score: number): string {
		if (score >= 0.8) return 'bg-success';
		if (score >= 0.5) return 'bg-warning';
		return 'bg-text-secondary';
	}

	// Get status badge color
	function getStatusBadgeClass(status: string): string {
		return status === 'active'
			? 'bg-success/10 text-success border-success/30'
			: 'bg-text-secondary/10 text-text-secondary border-text-secondary/30';
	}
</script>

<!-- Card with swipe gesture -->
<div
	class="surface hover:shadow-lg transition-all cursor-pointer relative overflow-hidden touch-pan-y"
	style="transform: translateX({swipeOffset}px); transition: {isSwiping
		? 'none'
		: 'transform 0.2s ease-out'}"
	onpointerdown={handlePointerDown}
	onpointermove={handlePointerMove}
	onpointerup={handlePointerUp}
	onpointerleave={handlePointerUp}
	onclick={handleClick}
	onkeydown={(e) => e.key === 'Enter' && onClick?.()}
	role="button"
	tabindex="0"
>
	<!-- Swipe action hints -->
	{#if swipeOffset > 30}
		<div class="absolute left-2 top-1/2 -translate-y-1/2 text-primary text-sm font-medium">
			💬 Chat
		</div>
	{/if}
	{#if swipeOffset < -30}
		<div class="absolute right-2 top-1/2 -translate-y-1/2 text-warning text-sm font-medium">
			Archive 📦
		</div>
	{/if}

	<!-- Header -->
	<div class="flex justify-between items-start mb-3">
		<div class="flex items-center gap-2">
			<!-- Relevance Indicator -->
			<div
				class="w-2 h-2 rounded-full {getRelevanceColor(entry.relevance_score)}"
				title="Relevance: {entry.relevance_score.toFixed(2)}"
			></div>
			<h3 class="font-semibold text-lg text-primary-dark">{formatDate(entry.date)}</h3>
		</div>

		<!-- Status Badge -->
		<span class="text-xs px-2 py-1 rounded-full border {getStatusBadgeClass(entry.status)}">
			{entry.status}
		</span>
	</div>

	<!-- Preview Text -->
	{#if entry.refined_output}
		<p class="text-text-secondary line-clamp-3 mb-3 text-sm">
			{truncate(entry.refined_output, 150)}
		</p>
	{:else}
		<p class="text-text-secondary italic mb-3 text-sm">No summary yet</p>
	{/if}

	<!-- Footer Metadata -->
	<div
		class="flex justify-between items-center text-xs text-text-secondary pt-2 border-t border-primary-light/10"
	>
		<div class="flex items-center gap-3">
			<!-- Conversation Count -->
			<div class="flex items-center gap-1">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
					/>
				</svg>
				<span
					>{entry.conversations.length}
					{entry.conversations.length === 1 ? 'conversation' : 'conversations'}</span
				>
			</div>

			<!-- Interaction Count -->
			<div class="flex items-center gap-1" title="Times accessed">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
					/>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
					/>
				</svg>
				<span>{entry.interaction_count}</span>
			</div>
		</div>

		<!-- Last Interacted -->
		<span class="text-xs">
			{formatRelativeTime(entry.last_interacted_at)}
		</span>
	</div>
</div>

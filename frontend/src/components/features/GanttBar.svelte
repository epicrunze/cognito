<script lang="ts">
	import type { Task } from '$lib/types';
	import { getBarColor } from '$lib/ganttUtils';
	import { taskDetailStore } from '$lib/stores/taskDetail.svelte';

	const ROW_HEIGHT = 38;
	const BAR_HEIGHT = 32;
	const EDGE_ZONE = 8;

	interface Props {
		task: Task;
		x: number;
		width: number;
		row: number;
		isSingleDay: boolean;
		isDragging?: boolean;
		ondragstart?: (taskId: number, type: 'move' | 'resize-start' | 'resize-end', startX: number) => void;
	}

	let { task, x, width, row, isSingleDay, isDragging = false, ondragstart }: Props = $props();

	let hovered = $state(false);

	const barColor = $derived(getBarColor(task.priority));
	const isDone = $derived(task.done);
	const effectiveWidth = $derived(Math.max(width, 24));
	const percentDone = $derived(task.percent_done ?? 0);

	function handleMouseDown(e: MouseEvent) {
		if (e.button !== 0) return;

		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		const localX = e.clientX - rect.left;

		if (!isSingleDay && localX <= EDGE_ZONE) {
			e.preventDefault();
			e.stopPropagation();
			ondragstart?.(task.id, 'resize-start', e.clientX);
		} else if (!isSingleDay && localX >= rect.width - EDGE_ZONE) {
			e.preventDefault();
			e.stopPropagation();
			ondragstart?.(task.id, 'resize-end', e.clientX);
		} else {
			e.preventDefault();
			e.stopPropagation();
			ondragstart?.(task.id, 'move', e.clientX);
		}
	}

	function handleClick() {
		// Don't open detail if we just finished dragging
		if (isDragging) return;
		taskDetailStore.open(task.id);
	}

	function getCursor(e: MouseEvent): string {
		if (isSingleDay) return 'grab';
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		const localX = e.clientX - rect.left;
		if (localX <= EDGE_ZONE || localX >= rect.width - EDGE_ZONE) {
			return 'col-resize';
		}
		return 'grab';
	}

	function handleMouseMove(e: MouseEvent) {
		const el = e.currentTarget as HTMLElement;
		el.style.cursor = getCursor(e);
	}
</script>

{#if isSingleDay}
	<!-- Single-day marker: small pill -->
	<div
		role="button"
		tabindex="0"
		class="gantt-bar gantt-bar--single"
		style="
			position: absolute;
			left: {x}px;
			top: {row * ROW_HEIGHT}px;
			width: 24px;
			height: {BAR_HEIGHT}px;
			background: {barColor};
			border-radius: 12px;
			cursor: grab;
			display: flex;
			align-items: center;
			justify-content: center;
			opacity: {isDone ? 0.5 : 1};
			transition: box-shadow var(--transition-fast), opacity var(--transition-fast);
			box-shadow: {hovered ? '0 2px 8px rgba(0,0,0,0.3)' : 'none'};
			z-index: {hovered ? 2 : 1};
		"
		onmouseenter={() => hovered = true}
		onmouseleave={() => hovered = false}
		onmousedown={handleMouseDown}
		onclick={handleClick}
		onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') taskDetailStore.open(task.id); }}
		title={task.title}
	>
		<div style="
			width: 8px;
			height: 8px;
			background: white;
			border-radius: 2px;
			transform: rotate(45deg);
			opacity: 0.9;
		"></div>
	</div>
{:else}
	<!-- Duration bar -->
	<div
		role="button"
		tabindex="0"
		class="gantt-bar"
		style="
			position: absolute;
			left: {x}px;
			top: {row * ROW_HEIGHT}px;
			width: {effectiveWidth}px;
			height: {BAR_HEIGHT}px;
			background: var(--bg-elevated);
			border-radius: 8px;
			border-left: 3px solid {barColor};
			display: flex;
			align-items: center;
			padding: 0 10px;
			overflow: hidden;
			opacity: {isDone ? 0.5 : 1};
			transition: box-shadow var(--transition-fast), opacity var(--transition-fast);
			box-shadow: {hovered ? '0 2px 8px rgba(0,0,0,0.3)' : 'var(--shadow-sm)'};
			z-index: {hovered ? 2 : 1};
			user-select: none;
		"
		onmouseenter={() => hovered = true}
		onmouseleave={() => hovered = false}
		onmousedown={handleMouseDown}
		onmousemove={handleMouseMove}
		onclick={handleClick}
		onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') taskDetailStore.open(task.id); }}
	>
		<!-- Progress fill -->
		{#if percentDone > 0}
			<div style="
				position: absolute;
				top: 0;
				left: 0;
				width: {percentDone * 100}%;
				height: 100%;
				background: rgba(232, 119, 46, 0.1);
				border-radius: 8px 0 0 8px;
				pointer-events: none;
			"></div>
		{/if}

		<!-- Title -->
		<span style="
			font-size: 13px;
			font-family: var(--font-sans);
			color: var(--text-primary);
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
			text-decoration: {isDone ? 'line-through' : 'none'};
			position: relative;
			z-index: 1;
			flex: 1;
			min-width: 0;
		">{task.title}</span>

		<!-- Labels on hover -->
		{#if hovered && task.labels && task.labels.length > 0}
			<div style="
				display: flex;
				gap: 3px;
				margin-left: 6px;
				flex-shrink: 0;
				position: relative;
				z-index: 1;
			">
				{#each task.labels.slice(0, 3) as label (label.id)}
					<span style="
						font-size: 10px;
						font-family: var(--font-sans);
						color: var(--text-secondary);
						background: var(--bg-surface);
						border: 1px solid var(--border-subtle);
						border-radius: 4px;
						padding: 1px 5px;
						white-space: nowrap;
					">{label.title}</span>
				{/each}
			</div>
		{/if}
	</div>
{/if}

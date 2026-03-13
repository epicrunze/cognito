<script lang="ts">
	import { onMount } from 'svelte';
	import type { Task } from '$lib/types';
	import { tasksStore, projectsStore } from '$lib/stores.svelte';
	import { updateTask } from '$lib/stores/taskMutations';
	import { ganttStore } from '$lib/stores/gantt.svelte';
	import { applyClientFilters } from '$lib/filterUtils';
	import {
		getTaskDateRange, dateToX, xToDate, getColumnWidth, generateTimeColumns,
		addDays, startOfDay, snapToGrid,
		type ZoomLevel
	} from '$lib/ganttUtils';
	import GanttTimeline from './GanttTimeline.svelte';
	import GanttBar from './GanttBar.svelte';
	import GanttUnscheduled from './GanttUnscheduled.svelte';

	const ROW_HEIGHT = 38;

	let { projectId }: { projectId?: number } = $props();

	let scrollContainer = $state<HTMLElement | null>(null);
	let scrollLeft = $state(0);
	let dragStarted = $state(false);
	let lastAppliedDelta = $state(0);

	interface BarData {
		task: Task;
		x: number;
		width: number;
		row: number;
		isSingleDay: boolean;
	}

	// Fetch tasks
	$effect(() => {
		if (projectId != null) {
			tasksStore.fetchByProject(projectId);
		} else {
			tasksStore.fetchAll();
		}
	});

	// Filter
	const filteredTasks = $derived.by(() => {
		let t = tasksStore.tasks;
		if (projectId != null) t = t.filter(task => task.project_id === projectId);
		return applyClientFilters(t);
	});

	// Separate scheduled / unscheduled
	const scheduledTasks = $derived(filteredTasks.filter(t => getTaskDateRange(t) !== null));
	const unscheduledTasks = $derived(filteredTasks.filter(t => getTaskDateRange(t) === null));

	// Current zoom column width
	const colWidth = $derived(getColumnWidth(ganttStore.zoom));

	// View range computation
	const viewRange = $derived.by(() => {
		const today = startOfDay(new Date());
		let earliest = today;
		let latest = today;

		for (const task of scheduledTasks) {
			const range = getTaskDateRange(task);
			if (range) {
				if (range.start < earliest) earliest = range.start;
				if (range.end > latest) latest = range.end;
			}
		}

		return {
			start: addDays(earliest, -14),
			end: addDays(latest, 14),
		};
	});

	const columns = $derived(generateTimeColumns(viewRange.start, viewRange.end, ganttStore.zoom));
	const totalWidth = $derived(columns.reduce((sum, c) => sum + c.width, 0));

	// Precompute cumulative X offsets for grid lines (avoids O(n^2) in template)
	const columnOffsets = $derived(columns.reduce<number[]>((acc, col, i) => {
		acc.push(i === 0 ? 0 : acc[i - 1] + columns[i - 1].width);
		return acc;
	}, []));

	// Shared sort: group by project, then priority desc, then start date
	function ganttSort(a: Task, b: Task): number {
		if (a.project_id !== b.project_id) return a.project_id - b.project_id;
		if (a.priority !== b.priority) return b.priority - a.priority;
		const ra = getTaskDateRange(a);
		const rb = getTaskDateRange(b);
		if (ra && rb) return ra.start.getTime() - rb.start.getTime();
		return 0;
	}

	// Sorted scheduled tasks (shared by allBars + projectHeaders)
	const sortedScheduled = $derived([...scheduledTasks].sort(ganttSort));

	// Compute bar positions, grouped by project when no projectId
	const allBars = $derived.by((): BarData[] => {
		const sorted = sortedScheduled;

		let currentRow = 0;
		let lastProjectId = -1;
		const bars: BarData[] = [];

		for (const task of sorted) {
			// Add project header row (when viewing all tasks)
			if (projectId == null && task.project_id !== lastProjectId) {
				if (lastProjectId !== -1) currentRow++; // gap between groups
				lastProjectId = task.project_id;
				currentRow++; // header row
			}

			const range = getTaskDateRange(task);
			if (!range) continue;

			const x = dateToX(range.start, viewRange.start, ganttStore.zoom);
			const endX = dateToX(range.end, viewRange.start, ganttStore.zoom);
			const isSingleDay = range.start.getTime() === range.end.getTime();
			const barWidth = isSingleDay ? colWidth : (endX - x + colWidth);

			bars.push({ task, x, width: barWidth, row: currentRow, isSingleDay });
			currentRow++;
		}

		return bars;
	});

	// Project headers for the "all tasks" view
	const projectHeaders = $derived.by(() => {
		if (projectId != null) return [];

		const headers: { projectId: number; name: string; color: string; row: number }[] = [];
		let currentRow = 0;
		let lastPid = -1;

		for (const task of sortedScheduled) {
			if (task.project_id !== lastPid) {
				if (lastPid !== -1) currentRow++;
				lastPid = task.project_id;
				const project = projectsStore.projects.find(p => p.id === task.project_id);
				headers.push({
					projectId: task.project_id,
					name: project?.title ?? `Project ${task.project_id}`,
					color: project?.hex_color ? `#${project.hex_color}` : 'var(--text-tertiary)',
					row: currentRow,
				});
				currentRow++;
			} else {
				currentRow++;
			}
		}

		return headers;
	});

	const totalRows = $derived(allBars.length > 0 ? Math.max(...allBars.map(b => b.row)) + 1 : 0);
	const todayX = $derived(dateToX(new Date(), viewRange.start, ganttStore.zoom));

	// Drag handling
	function handleDragStart(taskId: number, type: 'move' | 'resize-start' | 'resize-end', startX: number) {
		const task = scheduledTasks.find(t => t.id === taskId);
		if (!task) return;
		const range = getTaskDateRange(task);
		if (!range) return;
		dragStarted = false;
		lastAppliedDelta = 0;
		ganttStore.startDrag({ taskId, type, startX, originalStart: range.start, originalEnd: range.end });
	}

	function handleMouseMove(e: MouseEvent) {
		if (!ganttStore.dragState) return;
		const dx = e.clientX - ganttStore.dragState.startX;

		if (!dragStarted && Math.abs(dx) < 4) return;
		dragStarted = true;

		const daysDelta = Math.round(dx / colWidth);
		if (daysDelta === lastAppliedDelta) return;
		lastAppliedDelta = daysDelta;

		const { taskId, type, originalStart, originalEnd } = ganttStore.dragState;

		if (type === 'move') {
			const newStart = addDays(originalStart, daysDelta);
			const newEnd = addDays(originalEnd, daysDelta);
			tasksStore.patchTask(taskId, {
				start_date: newStart.toISOString(),
				end_date: newEnd.toISOString()
			});
		} else if (type === 'resize-end') {
			const newEnd = addDays(originalEnd, daysDelta);
			if (newEnd >= originalStart) {
				tasksStore.patchTask(taskId, { end_date: newEnd.toISOString() });
			}
		} else if (type === 'resize-start') {
			const newStart = addDays(originalStart, daysDelta);
			if (newStart <= originalEnd) {
				tasksStore.patchTask(taskId, { start_date: newStart.toISOString() });
			}
		}
	}

	function handleMouseUp() {
		if (!ganttStore.dragState) return;
		const { taskId } = ganttStore.dragState;

		if (dragStarted) {
			const task = tasksStore.tasks.find(t => t.id === taskId);
			if (task) {
				updateTask(taskId, {
					start_date: task.start_date,
					end_date: task.end_date
				});
			}
		}

		ganttStore.endDrag();
		dragStarted = false;
		lastAppliedDelta = 0;
	}

	// Drop from unscheduled sidebar
	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		const taskId = Number(e.dataTransfer?.getData('text/plain'));
		if (!taskId || !scrollContainer) return;
		const rect = scrollContainer.getBoundingClientRect();
		const x = e.clientX - rect.left + scrollContainer.scrollLeft;
		const dropDate = xToDate(x, viewRange.start, ganttStore.zoom);
		const snapped = snapToGrid(dropDate, ganttStore.zoom);
		const endDate = addDays(snapped, 1);
		updateTask(taskId, {
			start_date: snapped.toISOString(),
			end_date: endDate.toISOString(),
		});
	}

	// Keyboard handler
	function handleKeydown(e: KeyboardEvent) {
		if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

		switch (e.key) {
			case 't':
			case 'T':
				e.preventDefault();
				if (scrollContainer) {
					scrollContainer.scrollLeft = Math.max(0, todayX - scrollContainer.clientWidth / 2);
				}
				break;
			case '+':
			case '=':
				e.preventDefault();
				ganttStore.zoomIn();
				break;
			case '-':
				e.preventDefault();
				ganttStore.zoomOut();
				break;
		}
	}

	// Scroll to today on mount
	onMount(() => {
		requestAnimationFrame(() => {
			if (scrollContainer) {
				scrollContainer.scrollLeft = Math.max(0, todayX - scrollContainer.clientWidth / 2);
			}
		});
	});
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions a11y_no_noninteractive_tabindex -->
<div
	role="application"
	style="display: flex; flex-direction: column; height: 100%; overflow: hidden;"
	onkeydown={handleKeydown}
	tabindex="0"
>
	<div style="display: flex; flex: 1; overflow: hidden;">
		<!-- Unscheduled sidebar -->
		<GanttUnscheduled tasks={unscheduledTasks} />

		<!-- Chart area -->
		<div style="flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative;">
			{#if tasksStore.loading}
				<!-- Loading skeleton -->
				<div style="padding: 48px 24px;">
					{#each [1, 2, 3, 4, 5] as i (i)}
						<div style="
							height: 32px;
							margin-bottom: 6px;
							background: var(--bg-elevated);
							border-radius: 8px;
							opacity: {0.6 - i * 0.08};
							width: {120 + i * 60}px;
							margin-left: {40 + i * 30}px;
							animation: pulse 1.5s ease-in-out infinite;
						"></div>
					{/each}
				</div>
			{:else if scheduledTasks.length === 0 && unscheduledTasks.length === 0}
				<!-- Empty state -->
				<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 24px; gap: 12px; flex: 1;">
					<span style="font-size: 40px; opacity: 0.3;">&#128197;</span>
					<span style="font-size: 15px; color: var(--text-tertiary);">No tasks to display</span>
					<span style="font-size: 13px; color: var(--text-tertiary);">Tasks with dates will appear on the timeline</span>
				</div>
			{:else}
				<!-- Timeline header -->
				<GanttTimeline {columns} {scrollLeft} sidebarWidth={0} />

				<!-- Scrollable chart body -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					bind:this={scrollContainer}
					onscroll={(e) => { scrollLeft = (e.currentTarget as HTMLElement).scrollLeft; }}
					onmousemove={handleMouseMove}
					onmouseup={handleMouseUp}
					onmouseleave={handleMouseUp}
					ondragover={handleDragOver}
					ondrop={handleDrop}
					style="flex: 1; overflow: auto; position: relative;"
				>
					<div style="position: relative; min-width: {totalWidth}px; height: {Math.max(totalRows * ROW_HEIGHT + 40, 200)}px;">

						<!-- Grid lines (vertical) -->
						{#each columns as col, i (col.date.getTime())}
							<div style="
								position: absolute;
								left: {columnOffsets[i]}px;
								top: 0;
								bottom: 0;
								width: {col.width}px;
								border-right: 1px solid var(--border-subtle);
								background: {col.isToday ? 'rgba(232, 119, 46, 0.05)' : col.isWeekend ? 'rgba(0,0,0,0.15)' : 'transparent'};
								pointer-events: none;
							"></div>
						{/each}

						<!-- Project group headers (when viewing all tasks) -->
						{#each projectHeaders as header (header.projectId)}
							<div style="
								position: absolute;
								left: {scrollLeft + 8}px;
								top: {header.row * ROW_HEIGHT}px;
								height: {ROW_HEIGHT}px;
								display: flex;
								align-items: center;
								gap: 6px;
								z-index: 6;
								pointer-events: none;
							">
								<span style="
									width: 8px;
									height: 8px;
									border-radius: 50%;
									background: {header.color};
									flex-shrink: 0;
								"></span>
								<span style="
									font-size: 12px;
									font-weight: 600;
									color: var(--text-secondary);
									font-family: var(--font-sans);
									white-space: nowrap;
								">{header.name}</span>
							</div>
						{/each}

						<!-- Gantt bars -->
						{#each allBars as bar (bar.task.id)}
							<GanttBar
								task={bar.task}
								x={bar.x}
								width={bar.width}
								row={bar.row}
								isSingleDay={bar.isSingleDay}
								isDragging={dragStarted && ganttStore.dragState?.taskId === bar.task.id}
								ondragstart={handleDragStart}
							/>
						{/each}

						<!-- Today line -->
						<div style="
							position: absolute;
							left: {todayX}px;
							top: 0;
							bottom: 0;
							width: 2px;
							background: var(--accent);
							opacity: 0.4;
							z-index: 5;
							pointer-events: none;
						">
							<span style="
								position: absolute;
								top: 4px;
								left: 6px;
								font-size: 10px;
								color: var(--accent);
								font-family: var(--font-sans);
								white-space: nowrap;
								font-weight: 500;
							">Today</span>
						</div>
					</div>
				</div>

				<!-- Zoom controls -->
				<div style="
					position: absolute;
					bottom: 16px;
					right: 16px;
					display: flex;
					gap: 2px;
					background: var(--bg-elevated);
					border: 1px solid var(--border-default);
					border-radius: 8px;
					padding: 2px;
					z-index: 15;
				">
					{#each (['day', 'week', 'month'] as const) as level (level)}
						<button
							onclick={() => ganttStore.setZoom(level)}
							style="
								padding: 4px 12px;
								font-size: 11px;
								border-radius: 6px;
								border: none;
								cursor: pointer;
								font-family: var(--font-sans);
								background: {ganttStore.zoom === level ? 'rgba(232,119,46,0.15)' : 'transparent'};
								color: {ganttStore.zoom === level ? 'var(--accent)' : 'var(--text-secondary)'};
								font-weight: {ganttStore.zoom === level ? '600' : '400'};
							"
						>{level.charAt(0).toUpperCase() + level.slice(1)}</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	@keyframes pulse {
		0%, 100% { opacity: 0.4; }
		50% { opacity: 0.7; }
	}
</style>

<script lang="ts">
	import type { Task } from '$lib/types';
	import { ganttStore } from '$lib/stores/gantt.svelte';
	import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { getBarColor } from '$lib/ganttUtils';

	let { tasks }: { tasks: Task[] } = $props();

	let collapsed = $derived(ganttStore.unscheduledCollapsed);

	function getProjectName(projectId: number): string {
		const project = projectsStore.projects.find((p) => p.id === projectId);
		return project?.title ?? '';
	}

	function handleDragStart(e: DragEvent, task: Task) {
		if (!e.dataTransfer) return;
		e.dataTransfer.setData('text/plain', String(task.id));
		e.dataTransfer.effectAllowed = 'move';
	}
</script>

<div
	style="
		width: {collapsed ? 32 : 200}px;
		background: var(--bg-surface);
		border-right: 1px solid var(--border-default);
		transition: width 200ms ease;
		overflow: hidden;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		height: 100%;
	"
>
	{#if collapsed}
		<!-- Collapsed state: vertical label with count -->
		<button
			onclick={() => ganttStore.toggleUnscheduled()}
			style="
				width: 32px;
				height: 100%;
				display: flex;
				align-items: center;
				justify-content: center;
				background: none;
				border: none;
				cursor: pointer;
				padding: 0;
			"
		>
			<span
				style="
					writing-mode: vertical-rl;
					text-orientation: mixed;
					font-family: var(--font-sans);
					font-size: 11px;
					font-weight: 600;
					color: var(--text-tertiary);
					letter-spacing: 0.5px;
					white-space: nowrap;
					user-select: none;
				"
			>
				Unscheduled ({tasks.length})
			</span>
		</button>
	{:else}
		<!-- Header -->
		<div
			style="
				display: flex;
				align-items: center;
				justify-content: space-between;
				padding: 12px;
				border-bottom: 1px solid var(--border-subtle);
				flex-shrink: 0;
			"
		>
			<span
				style="
					font-family: var(--font-sans);
					font-size: 12px;
					font-weight: 600;
					color: var(--text-secondary);
					white-space: nowrap;
				"
			>
				Unscheduled
				<span style="color: var(--text-tertiary); font-weight: 400;">({tasks.length})</span>
			</span>
			<button
				onclick={() => ganttStore.toggleUnscheduled()}
				style="
					background: none;
					border: none;
					cursor: pointer;
					padding: 2px;
					display: flex;
					align-items: center;
					justify-content: center;
					color: var(--text-tertiary);
					border-radius: 4px;
				"
				title="Collapse"
			>
				<!-- Chevron left SVG -->
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<polyline points="15 18 9 12 15 6"></polyline>
				</svg>
			</button>
		</div>

		<!-- Task list -->
		<div
			style="
				flex: 1;
				overflow-y: auto;
				overflow-x: hidden;
			"
		>
			{#each tasks as task (task.id)}
				<div
					role="button"
					tabindex="0"
					draggable="true"
					ondragstart={(e) => handleDragStart(e, task)}
					onclick={() => taskDetailStore.open(task.id)}
					onkeydown={(e) => {
						if (e.key === 'Enter' || e.key === ' ') {
							e.preventDefault();
							taskDetailStore.open(task.id);
						}
					}}
					style="
						padding: 8px 12px;
						border-bottom: 1px solid var(--border-subtle);
						cursor: grab;
						transition: background 150ms ease;
					"
					onmouseenter={(e) => {
						(e.currentTarget as HTMLElement).style.background = 'var(--bg-elevated)';
					}}
					onmouseleave={(e) => {
						(e.currentTarget as HTMLElement).style.background = 'transparent';
					}}
				>
					<!-- Task title -->
					<div
						style="
							font-family: var(--font-sans);
							font-size: 13px;
							color: var(--text-primary);
							white-space: nowrap;
							overflow: hidden;
							text-overflow: ellipsis;
							line-height: 1.4;
						"
					>
						{task.title}
					</div>

					<!-- Priority dot + project name -->
					<div
						style="
							display: flex;
							align-items: center;
							gap: 5px;
							margin-top: 3px;
						"
					>
						<span
							style="
								width: 6px;
								height: 6px;
								border-radius: 50%;
								background: {getBarColor(task.priority)};
								flex-shrink: 0;
								display: inline-block;
							"
						></span>
						<span
							style="
								font-family: var(--font-sans);
								font-size: 11px;
								color: var(--text-tertiary);
								white-space: nowrap;
								overflow: hidden;
								text-overflow: ellipsis;
							"
						>
							{getProjectName(task.project_id)}
						</span>
					</div>
				</div>
			{/each}

			{#if tasks.length === 0}
				<div
					style="
						padding: 16px 12px;
						font-family: var(--font-sans);
						font-size: 12px;
						color: var(--text-tertiary);
						text-align: center;
					"
				>
					No unscheduled tasks
				</div>
			{/if}
		</div>
	{/if}
</div>

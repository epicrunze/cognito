<script lang="ts">
	import type { TimeColumn } from '$lib/ganttUtils';
	import { formatMonthHeader } from '$lib/ganttUtils';

	type MonthSpan = {
		label: string;
		width: number;
	};

	let {
		columns,
		scrollLeft,
		sidebarWidth
	}: {
		columns: TimeColumn[];
		scrollLeft: number;
		sidebarWidth: number;
	} = $props();

	let monthSpans: MonthSpan[] = $derived.by(() => {
		if (columns.length === 0) return [];

		const spans: MonthSpan[] = [];
		let currentLabel = formatMonthHeader(columns[0].date);
		let currentWidth = columns[0].width;

		for (let i = 1; i < columns.length; i++) {
			const label = formatMonthHeader(columns[i].date);
			if (label === currentLabel) {
				currentWidth += columns[i].width;
			} else {
				spans.push({ label: currentLabel, width: currentWidth });
				currentLabel = label;
				currentWidth = columns[i].width;
			}
		}
		spans.push({ label: currentLabel, width: currentWidth });

		return spans;
	});
</script>

<div
	style="
		position: sticky;
		top: 0;
		z-index: 10;
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border-subtle);
		font-family: var(--font-sans);
		margin-left: {sidebarWidth}px;
		overflow: hidden;
	"
>
	<!-- Month row -->
	<div
		style="
			display: flex;
			transform: translateX(-{scrollLeft}px);
			border-bottom: 1px solid var(--border-subtle);
		"
	>
		{#each monthSpans as month, i (i)}
			<div
				style="
					width: {month.width}px;
					min-width: {month.width}px;
					padding: 6px 8px;
					font-size: 12px;
					font-weight: 600;
					color: var(--text-secondary);
					box-sizing: border-box;
					white-space: nowrap;
					overflow: hidden;
					text-overflow: ellipsis;
				"
			>
				{month.label}
			</div>
		{/each}
	</div>

	<!-- Day row -->
	<div
		style="
			display: flex;
			transform: translateX(-{scrollLeft}px);
		"
	>
		{#each columns as col (col.date.getTime())}
			<div
				style="
					width: {col.width}px;
					min-width: {col.width}px;
					padding: 4px 0;
					font-size: 11px;
					color: {col.isToday ? 'var(--accent)' : 'var(--text-tertiary)'};
					text-align: center;
					box-sizing: border-box;
					border-right: 1px solid var(--border-subtle);
					background: {col.isToday
					? 'rgba(232, 119, 46, 0.08)'
					: col.isWeekend
						? 'var(--bg-base)'
						: 'transparent'};
				"
			>
				{col.label}
			</div>
		{/each}
	</div>
</div>

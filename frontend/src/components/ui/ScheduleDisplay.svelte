<script lang="ts">
	let { startDate = null, endDate = null, done = false }: { startDate: string | null; endDate: string | null; done?: boolean } = $props();

	const formatTime = (d: Date) => {
		let h = d.getHours(), m = d.getMinutes();
		let period = h >= 12 ? 'pm' : 'am';
		h = h % 12 || 12;
		return m ? `${h}:${m.toString().padStart(2, '0')}${period}` : `${h}${period}`;
	};

	const formatDay = (d: Date) => {
		const now = new Date(), today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
		const target = new Date(d.getFullYear(), d.getMonth(), d.getDate());
		const diff = (target.getTime() - today.getTime()) / 86400000;
		if (diff === 0) return 'Today';
		if (diff === 1) return 'Tomorrow';
		if (diff === -1) return 'Yesterday';
		return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	};

	const formatDuration = (ms: number) => {
		const mins = Math.round(ms / 60000);
		if (mins < 60) return `${mins}m`;
		const hrs = mins / 60;
		return hrs % 1 ? `${parseFloat(hrs.toFixed(1))}h` : `${hrs}h`;
	};

	let display = $derived.by(() => {
		if (!startDate || !endDate) return null;
		const s = new Date(startDate), e = new Date(endDate);
		return `${formatDay(s)} ${formatTime(s)} – ${formatTime(e)} · ${formatDuration(e.getTime() - s.getTime())}`;
	});

	let overdue = $derived(!done && startDate ? new Date(startDate) < new Date() : false);
</script>

{#if display}
	<span class="schedule" class:overdue>
		<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
		{display}
	</span>
{/if}

<style>
	.schedule {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 12.5px;
		color: var(--text-secondary);
		font-family: var(--font-sans);
	}
	.overdue {
		opacity: 0.5;
		text-decoration: line-through;
		color: var(--text-tertiary);
	}
</style>

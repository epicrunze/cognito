<script lang="ts">
	interface Props {
		hour: number;
		minute: number;
		period: 'AM' | 'PM';
		onchange: (h: number, m: number, p: 'AM' | 'PM') => void;
		oncomplete?: () => void;
		disabledBefore?: { hour: number; minute: number; period: 'AM' | 'PM' };
	}

	let { hour, minute, period, onchange, oncomplete, disabledBefore }: Props = $props();

	let mode: 'hour' | 'minute' = $state('hour');

	const cx = 100;
	const cy = 100;
	const radius = 78;

	const hours = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
	const minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];

	function toAngle(index: number): number {
		return (index * 30 - 90) * (Math.PI / 180);
	}

	function numPos(index: number) {
		const angle = toAngle(index);
		return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
	}

	function to24(h: number, p: 'AM' | 'PM'): number {
		if (p === 'AM') return h === 12 ? 0 : h;
		return h === 12 ? 12 : h + 12;
	}

	function isHourDisabled(h: number): boolean {
		if (!disabledBefore) return false;
		const val = to24(h, period);
		const limit = to24(disabledBefore.hour, disabledBefore.period);
		return val < limit;
	}

	function isMinuteDisabled(m: number): boolean {
		if (!disabledBefore) return false;
		const val = to24(hour, period);
		const limit = to24(disabledBefore.hour, disabledBefore.period);
		if (val > limit) return false;
		if (val < limit) return true;
		return m < disabledBefore.minute;
	}

	let selectedAngle = $derived.by(() => {
		if (mode === 'hour') {
			const idx = hours.indexOf(hour);
			return toAngle(idx >= 0 ? idx : 0);
		}
		const idx = Math.round(minute / 5) % 12;
		return toAngle(idx);
	});

	let handEnd = $derived.by(() => {
		return { x: cx + radius * Math.cos(selectedAngle), y: cy + radius * Math.sin(selectedAngle) };
	});

	function selectHour(h: number) {
		if (isHourDisabled(h)) return;
		onchange(h, minute, period);
		mode = 'minute';
	}

	function selectMinute(m: number) {
		if (isMinuteDisabled(m)) return;
		onchange(hour, m, period);
		oncomplete?.();
	}

	function togglePeriod(p: 'AM' | 'PM') {
		onchange(hour, minute, p);
	}

	function pad(n: number): string {
		return n.toString().padStart(2, '0');
	}
</script>

<div class="clock-picker">
	<div class="header">
		<div class="time-display">
			<button class="time-segment" class:active={mode === 'hour'} onclick={() => (mode = 'hour')}>
				{pad(hour)}
			</button>
			<span class="colon">:</span>
			<button class="time-segment" class:active={mode === 'minute'} onclick={() => (mode = 'minute')}>
				{pad(minute)}
			</button>
		</div>
		<div class="period-toggle">
			<button class="period-btn" class:active={period === 'AM'} onclick={() => togglePeriod('AM')}>AM</button>
			<button class="period-btn" class:active={period === 'PM'} onclick={() => togglePeriod('PM')}>PM</button>
		</div>
	</div>

	<svg viewBox="0 0 200 200" width="200" height="200" class="face">
		<circle cx={cx} cy={cy} r="92" fill="var(--bg-surface)" stroke="var(--border-default)" stroke-width="1" />
		<line
			x1={cx} y1={cy}
			x2={handEnd.x} y2={handEnd.y}
			stroke="var(--accent)" stroke-width="2" stroke-linecap="round"
			style="transition: x2 0.2s, y2 0.2s"
		/>
		<circle cx={cx} cy={cy} r="3" fill="var(--accent)" />

		{#each (mode === 'hour' ? hours : minutes) as value, i (mode + '-' + value)}
			{@const pos = numPos(i)}
			{@const isSelected = mode === 'hour' ? value === hour : value === minute}
			{@const disabled = mode === 'hour' ? isHourDisabled(value) : isMinuteDisabled(value)}
			<g
				role="button"
				tabindex="0"
				style="cursor: {disabled ? 'default' : 'pointer'}; outline: none; opacity: {disabled ? 0.3 : 1}; transition: opacity 0.15s;"
				onclick={() => mode === 'hour' ? selectHour(value) : selectMinute(value)}
				onkeydown={(e) => { if (e.key === 'Enter') { mode === 'hour' ? selectHour(value) : selectMinute(value); } }}
			>
				<circle cx={pos.x} cy={pos.y} r="16" fill={isSelected ? 'var(--accent)' : 'transparent'} style="transition: fill 0.15s" />
				<text
					x={pos.x} y={pos.y}
					text-anchor="middle" dominant-baseline="central"
					fill={isSelected ? 'var(--text-on-accent)' : 'var(--text-primary)'}
					font-size="13" font-weight="500" font-family="var(--font-sans, 'IBM Plex Sans', sans-serif)"
					style="transition: fill 0.15s; user-select: none"
				>
					{mode === 'minute' ? pad(value) : value}
				</text>
			</g>
		{/each}
	</svg>
</div>

<style>
	.clock-picker {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
	}
	.header {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.time-display {
		display: flex;
		align-items: baseline;
	}
	.time-segment {
		background: var(--bg-elevated);
		border: 1px solid var(--border-default);
		border-radius: 6px;
		color: var(--text-secondary);
		font-size: 22px;
		font-weight: 600;
		font-family: var(--font-sans, 'IBM Plex Sans', sans-serif);
		padding: 2px 6px;
		cursor: pointer;
		transition: color 0.15s, border-color 0.15s;
	}
	.time-segment.active {
		color: var(--accent);
		border-color: var(--accent);
	}
	.colon {
		color: var(--text-tertiary);
		font-size: 22px;
		font-weight: 600;
		margin: 0 2px;
	}
	.period-toggle {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.period-btn {
		background: var(--bg-elevated);
		border: 1px solid var(--border-default);
		color: var(--text-tertiary);
		font-size: 10px;
		font-weight: 600;
		padding: 1px 6px;
		border-radius: 4px;
		cursor: pointer;
		transition: color 0.15s, border-color 0.15s, background 0.15s;
	}
	.period-btn.active {
		color: var(--text-on-accent);
		background: var(--accent);
		border-color: var(--accent);
	}
	.face {
		display: block;
	}
</style>

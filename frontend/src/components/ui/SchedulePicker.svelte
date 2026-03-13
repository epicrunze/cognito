<script lang="ts">
	import { onMount } from 'svelte';
	import DatePicker from '$components/ui/DatePicker.svelte';
	import ClockPicker from '$components/ui/ClockPicker.svelte';

	interface Props {
		startDate: string | null;
		endDate: string | null;
		onchange: (start: string | null, end: string | null) => void;
	}

	let { startDate, endDate, onchange }: Props = $props();

	let open = $state(false);
	let activeTime = $state<'start' | 'end'>('start');
	let showDurationPicker = $state(false);
	let triggerRef = $state<HTMLButtonElement | undefined>(undefined);
	let portalRef = $state<HTMLDivElement | null>(null);
	let portalStyle = $state('');

	// Internal state — only committed on "Set"
	let schedDate = $state('');
	let startHour = $state(9);
	let startMinute = $state(0);
	let startPeriod = $state<'AM' | 'PM'>('AM');
	let endHour = $state(10);
	let endMinute = $state(0);
	let endPeriod = $state<'AM' | 'PM'>('AM');

	const DURATION_OPTIONS = [15, 30, 45, 60, 90, 120, 180, 240, 360, 480];

	// --- Conversion helpers ---

	function to24(h: number, p: 'AM' | 'PM'): number {
		if (p === 'AM') return h === 12 ? 0 : h;
		return h === 12 ? 12 : h + 12;
	}

	function to12(h24: number): { hour: number; period: 'AM' | 'PM' } {
		if (h24 === 0) return { hour: 12, period: 'AM' };
		if (h24 < 12) return { hour: h24, period: 'AM' };
		if (h24 === 12) return { hour: 12, period: 'PM' };
		return { hour: h24 - 12, period: 'PM' };
	}

	function toMinutes(h: number, m: number, p: 'AM' | 'PM'): number {
		return to24(h, p) * 60 + m;
	}

	function fromMinutes(total: number): { hour: number; minute: number; period: 'AM' | 'PM' } {
		const clamped = ((total % 1440) + 1440) % 1440;
		const h24 = Math.floor(clamped / 60);
		const { hour, period } = to12(h24);
		return { hour, minute: clamped % 60, period };
	}

	function toISO(dateStr: string, h: number, m: number, p: 'AM' | 'PM'): string {
		const h24 = to24(h, p);
		const d = new Date(Number(dateStr.slice(0, 4)), Number(dateStr.slice(5, 7)) - 1, Number(dateStr.slice(8, 10)), h24, m, 0);
		return d.toISOString();
	}

	function formatTime(h: number, m: number, p: 'AM' | 'PM'): string {
		return `${h}:${String(m).padStart(2, '0')} ${p}`;
	}

	function formatDurationMins(mins: number): string {
		if (mins < 60) return `${mins}m`;
		const hours = mins / 60;
		if (hours === Math.floor(hours)) return `${hours}h`;
		return `${hours.toFixed(1).replace(/\.0$/, '')}h`;
	}

	function currentDurationMins(): number {
		let diff = toMinutes(endHour, endMinute, endPeriod) - toMinutes(startHour, startMinute, startPeriod);
		if (diff <= 0) diff += 1440;
		return diff;
	}

	function formatDateLabel(dateStr: string): string {
		const now = new Date();
		const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
		const tomorrow = new Date(now);
		tomorrow.setDate(tomorrow.getDate() + 1);
		const tomorrowStr = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, '0')}-${String(tomorrow.getDate()).padStart(2, '0')}`;
		if (dateStr === todayStr) return 'Today';
		if (dateStr === tomorrowStr) return 'Tomorrow';
		const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
		const d = new Date(dateStr + 'T00:00:00');
		return `${MONTHS[d.getMonth()]} ${d.getDate()}`;
	}

	function getTodayStr(): string {
		const now = new Date();
		return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
	}

	function getTomorrowStr(): string {
		const t = new Date();
		t.setDate(t.getDate() + 1);
		return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`;
	}

	// --- Parse props into internal state ---

	function parseISO(iso: string): { date: string; hour: number; minute: number; period: 'AM' | 'PM' } {
		const d = new Date(iso);
		const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
		const { hour, period } = to12(d.getHours());
		return { date, hour, minute: d.getMinutes(), period };
	}

	// Sync from props when popover is closed (external changes only).
	$effect(() => {
		if (open) return;
		if (startDate) {
			const s = parseISO(startDate);
			schedDate = s.date;
			startHour = s.hour;
			startMinute = s.minute;
			startPeriod = s.period;
		}
		if (endDate) {
			const e = parseISO(endDate);
			endHour = e.hour;
			endMinute = e.minute;
			endPeriod = e.period;
		}
	});

	// --- Derived ---

	let hasValue = $derived(startDate !== null && endDate !== null);

	let triggerLabel = $derived.by(() => {
		if (!hasValue) return '';
		return `${formatDateLabel(schedDate)} ${formatTime(startHour, startMinute, startPeriod)} \u2013 ${formatTime(endHour, endMinute, endPeriod)}`;
	});

	let durationLabel = $derived(formatDurationMins(currentDurationMins()));

	let disabledBefore = $derived.by(() => {
		if (activeTime !== 'end') return undefined;
		return { hour: startHour, minute: startMinute, period: startPeriod };
	});

	let clockHour = $derived(activeTime === 'start' ? startHour : endHour);
	let clockMinute = $derived(activeTime === 'start' ? startMinute : endMinute);
	let clockPeriod = $derived(activeTime === 'start' ? startPeriod : endPeriod);

	// --- Portal positioning ---

	function updatePortalPosition() {
		if (!triggerRef) return;
		const rect = triggerRef.getBoundingClientRect();
		const right = window.innerWidth - rect.right;
		portalStyle = `position: fixed; top: ${rect.bottom + 4}px; right: ${Math.max(right, 8)}px; z-index: 9999;`;
	}

	// --- Actions ---

	function commitAndClose() {
		onchange(
			toISO(schedDate, startHour, startMinute, startPeriod),
			toISO(schedDate, endHour, endMinute, endPeriod)
		);
		open = false;
	}

	function openPopover() {
		updatePortalPosition();
		showDurationPicker = false;
		open = true;
	}

	function handleTriggerClick() {
		if (!hasValue) {
			const now = new Date();
			let nextH = now.getHours() + 1;
			schedDate = getTodayStr();
			const s = to12(nextH % 24);
			startHour = s.hour;
			startMinute = 0;
			startPeriod = s.period;
			const e = to12((nextH + 1) % 24);
			endHour = e.hour;
			endMinute = 0;
			endPeriod = e.period;
			activeTime = 'start';
			openPopover();
		} else {
			if (open) {
				open = false;
			} else {
				openPopover();
			}
		}
	}

	function handleDateChange(date: string | null) {
		if (!date) return;
		schedDate = date;
	}

	function handleClockChange(h: number, m: number, p: 'AM' | 'PM') {
		if (activeTime === 'start') {
			const oldDuration = currentDurationMins();

			startHour = h;
			startMinute = m;
			startPeriod = p;

			// Shift end to maintain duration
			const newEndMins = toMinutes(h, m, p) + oldDuration;
			const end = fromMinutes(newEndMins);
			endHour = end.hour;
			endMinute = end.minute;
			endPeriod = end.period;
		} else {
			endHour = h;
			endMinute = m;
			endPeriod = p;
		}
	}

	function handleClockComplete() {
		// After selecting minutes for start time, auto-advance to end time
		if (activeTime === 'start') {
			activeTime = 'end';
		}
	}

	function setDuration(mins: number) {
		const newEndMins = toMinutes(startHour, startMinute, startPeriod) + mins;
		const end = fromMinutes(newEndMins);
		endHour = end.hour;
		endMinute = end.minute;
		endPeriod = end.period;
		showDurationPicker = false;
	}

	function quickTodayNextHr() {
		const now = new Date();
		let nextH = now.getHours() + 1;
		schedDate = getTodayStr();
		const s = to12(nextH % 24);
		startHour = s.hour;
		startMinute = 0;
		startPeriod = s.period;
		const e = to12((nextH + 1) % 24);
		endHour = e.hour;
		endMinute = 0;
		endPeriod = e.period;
		commitAndClose();
	}

	function quickTomorrow9am() {
		schedDate = getTomorrowStr();
		startHour = 9;
		startMinute = 0;
		startPeriod = 'AM';
		endHour = 10;
		endMinute = 0;
		endPeriod = 'AM';
		commitAndClose();
	}

	function clearSchedule() {
		onchange(null, null);
		open = false;
	}

	// --- Outside click (portal-aware) ---

	function handleOutsideClick(e: MouseEvent) {
		if (triggerRef?.contains(e.target as Node)) return;
		if (portalRef?.contains(e.target as Node)) return;
		open = false;
	}

	$effect(() => {
		if (open) {
			const timer = setTimeout(() => {
				document.addEventListener('mousedown', handleOutsideClick);
			}, 0);
			return () => {
				clearTimeout(timer);
				document.removeEventListener('mousedown', handleOutsideClick);
			};
		}
	});
</script>

<!-- Trigger (inline in metadata row) -->
<div style="display: inline-flex; align-items: center;">
	<button
		bind:this={triggerRef}
		type="button"
		onclick={handleTriggerClick}
		style="display: inline-flex; align-items: center; gap: 6px; background: none; border: none; cursor: pointer; padding: 4px 8px; border-radius: 6px; font-family: var(--font-sans); font-size: 13px; transition: background 150ms; color: {hasValue ? 'var(--text-primary)' : 'var(--text-tertiary)'}; opacity: {hasValue ? 1 : 0.5};"
		class="trigger-btn"
	>
		{#if hasValue}
			<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<circle cx="12" cy="12" r="10" />
				<polyline points="12 6 12 12 16 14" />
			</svg>
			<span>{triggerLabel} &middot; {durationLabel}</span>
		{:else}
			<span>+ schedule</span>
		{/if}
	</button>
	{#if hasValue}
		<button
			type="button"
			onclick={(e) => { e.stopPropagation(); clearSchedule(); }}
			style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; padding: 0 2px; font-size: 14px; line-height: 1; display: flex; align-items: center; margin-left: -4px;"
			aria-label="Clear schedule"
		>&times;</button>
	{/if}
</div>

<!-- Portal popover -->
{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div bind:this={portalRef} style={portalStyle} onclick={(e) => e.stopPropagation()}>
		<div style="background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: 10px; box-shadow: var(--shadow-lg); padding: 12px; width: 280px; animation: fadeIn 100ms ease-out;">
			<!-- Date picker -->
			<DatePicker value={schedDate} onchange={handleDateChange} initialOpen={false} />

			<!-- Time rows -->
			<div style="margin-top: 10px; display: flex; flex-direction: column; gap: 2px;">
				<button
					type="button"
					onclick={() => { activeTime = 'start'; showDurationPicker = false; }}
					style="display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: {activeTime === 'start' && !showDurationPicker ? 'var(--bg-surface-hover)' : 'transparent'}; border: none; border-left: 3px solid {activeTime === 'start' && !showDurationPicker ? 'var(--accent)' : 'transparent'}; border-radius: 0 6px 6px 0; cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
				>
					<span style="font-size: 12px; color: var(--text-tertiary); min-width: 32px;">Start</span>
					<span style="font-size: 13.5px; font-weight: 500; color: {activeTime === 'start' && !showDurationPicker ? 'var(--accent)' : 'var(--text-primary)'};">
						{formatTime(startHour, startMinute, startPeriod)}
					</span>
				</button>
				<button
					type="button"
					onclick={() => { activeTime = 'end'; showDurationPicker = false; }}
					style="display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: {activeTime === 'end' && !showDurationPicker ? 'var(--bg-surface-hover)' : 'transparent'}; border: none; border-left: 3px solid {activeTime === 'end' && !showDurationPicker ? 'var(--accent)' : 'transparent'}; border-radius: 0 6px 6px 0; cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
				>
					<span style="font-size: 12px; color: var(--text-tertiary); min-width: 32px;">End</span>
					<span style="font-size: 13.5px; font-weight: 500; color: {activeTime === 'end' && !showDurationPicker ? 'var(--accent)' : 'var(--text-primary)'};">
						{formatTime(endHour, endMinute, endPeriod)}
					</span>
				</button>
				<!-- Duration row -->
				<button
					type="button"
					onclick={() => showDurationPicker = !showDurationPicker}
					style="display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: {showDurationPicker ? 'var(--bg-surface-hover)' : 'transparent'}; border: none; border-left: 3px solid {showDurationPicker ? 'var(--accent)' : 'transparent'}; border-radius: 0 6px 6px 0; cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
				>
					<span style="font-size: 12px; color: var(--text-tertiary); min-width: 32px;">For</span>
					<span style="font-size: 13.5px; font-weight: 500; color: {showDurationPicker ? 'var(--accent)' : 'var(--text-primary)'};">
						{durationLabel}
					</span>
				</button>
			</div>

			<!-- Clock or Duration picker -->
			{#if showDurationPicker}
				<div style="margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; justify-content: center;">
					{#each DURATION_OPTIONS as mins (mins)}
						{@const isActive = currentDurationMins() === mins}
						<button
							type="button"
							onclick={() => setDuration(mins)}
							style="padding: 6px 12px; border-radius: 8px; border: 1px solid {isActive ? 'var(--accent)' : 'var(--border-default)'}; background: {isActive ? 'var(--accent)' : 'var(--bg-surface)'}; color: {isActive ? 'white' : 'var(--text-primary)'}; font-size: 13px; font-family: var(--font-sans); cursor: pointer; transition: all 150ms; font-weight: {isActive ? 600 : 400};"
						>
							{formatDurationMins(mins)}
						</button>
					{/each}
				</div>
			{:else}
				<div style="margin-top: 10px; display: flex; justify-content: center;">
					<ClockPicker
						hour={clockHour}
						minute={clockMinute}
						period={clockPeriod}
						onchange={handleClockChange}
						oncomplete={handleClockComplete}
						disabledBefore={disabledBefore}
					/>
				</div>
			{/if}

			<!-- Footer: Clear / Quick actions / Set -->
			<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--border-subtle);">
				<button
					type="button"
					onclick={clearSchedule}
					style="background: none; border: none; color: var(--text-tertiary); font-size: 12.5px; cursor: pointer; font-family: var(--font-sans); padding: 4px 0;"
				>Clear</button>
				<div style="display: flex; gap: 8px; align-items: center;">
					<button
						type="button"
						onclick={quickTodayNextHr}
						class="quick-btn"
					>Now</button>
					<button
						type="button"
						onclick={quickTomorrow9am}
						class="quick-btn"
					>Tom 9a</button>
					<button
						type="button"
						onclick={commitAndClose}
						class="set-btn"
					>Set</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.trigger-btn:hover {
		background: var(--bg-surface-hover);
	}
	.quick-btn {
		background: none;
		border: none;
		color: var(--text-tertiary);
		font-size: 12px;
		cursor: pointer;
		font-family: var(--font-sans);
		padding: 4px 6px;
		border-radius: 4px;
		transition: color 150ms;
	}
	.quick-btn:hover {
		color: var(--accent);
	}
	.set-btn {
		background: var(--accent);
		border: none;
		color: white;
		font-size: 12.5px;
		font-weight: 600;
		cursor: pointer;
		font-family: var(--font-sans);
		padding: 5px 14px;
		border-radius: 6px;
		transition: opacity 150ms;
	}
	.set-btn:hover {
		opacity: 0.85;
	}
</style>

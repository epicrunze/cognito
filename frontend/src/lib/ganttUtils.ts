import type { Task } from '$lib/types';

// ─── Types ───────────────────────────────────────────────────────────────────

export type ZoomLevel = 'day' | 'week' | 'month';

export type TimeColumn = {
	date: Date;
	label: string;
	subLabel: string;
	isToday: boolean;
	isWeekend: boolean;
	width: number;
};

// ─── Date Helpers ─────────────────────────────────────────────────────────────

export function startOfDay(date: Date): Date {
	const d = new Date(date);
	d.setHours(0, 0, 0, 0);
	return d;
}

export function addDays(date: Date, n: number): Date {
	const d = new Date(date);
	d.setDate(d.getDate() + n);
	return d;
}

export function getDaysDiff(a: Date, b: Date): number {
	const msPerDay = 1000 * 60 * 60 * 24;
	return (b.getTime() - a.getTime()) / msPerDay;
}

// ─── Null / zero-date guard ───────────────────────────────────────────────────

function isValidDate(value: string | null | undefined): boolean {
	if (!value) return false;
	// Vikunja uses 0001-01-01T... as a zero/null date
	if (value.startsWith('0001-01-01')) return false;
	const d = new Date(value);
	return !isNaN(d.getTime());
}

// ─── Task Date Range ──────────────────────────────────────────────────────────

export function getTaskDateRange(task: Task): { start: Date; end: Date } | null {
	const hasStart = isValidDate(task.start_date);
	const hasEnd = isValidDate(task.end_date);
	const hasDue = isValidDate(task.due_date);

	if (hasStart && hasEnd) {
		return {
			start: startOfDay(new Date(task.start_date!)),
			end: startOfDay(new Date(task.end_date!))
		};
	}

	if (hasStart && hasDue) {
		return {
			start: startOfDay(new Date(task.start_date!)),
			end: startOfDay(new Date(task.due_date!))
		};
	}

	if (hasStart) {
		const start = startOfDay(new Date(task.start_date!));
		return { start, end: addDays(start, 1) };
	}

	if (hasDue) {
		const due = startOfDay(new Date(task.due_date!));
		return { start: due, end: due };
	}

	return null;
}

// ─── Column Width ─────────────────────────────────────────────────────────────

export function getColumnWidth(zoom: ZoomLevel): number {
	switch (zoom) {
		case 'day':
			return 80;
		case 'week':
			return 48;
		case 'month':
			return 16;
	}
}

// ─── Time Columns ─────────────────────────────────────────────────────────────

export function generateTimeColumns(
	startDate: Date,
	endDate: Date,
	zoom: ZoomLevel
): TimeColumn[] {
	const columns: TimeColumn[] = [];
	const today = startOfDay(new Date());
	const width = getColumnWidth(zoom);

	const MONTH_NAMES = [
		'January', 'February', 'March', 'April', 'May', 'June',
		'July', 'August', 'September', 'October', 'November', 'December'
	];
	const DAY_ABBRS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

	let current = startOfDay(startDate);
	const end = startOfDay(endDate);

	while (current <= end) {
		const dayOfWeek = current.getDay(); // 0=Sun, 6=Sat
		const dayOfMonth = current.getDate();
		const isToday = current.getTime() === today.getTime();
		const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;

		let label: string;
		let subLabel: string;

		switch (zoom) {
			case 'day':
				label = `${DAY_ABBRS[dayOfWeek]} ${dayOfMonth}`;
				// subLabel: month name on first of month
				subLabel = dayOfMonth === 1
					? MONTH_NAMES[current.getMonth()]
					: '';
				break;

			case 'week':
				label = String(dayOfMonth);
				// subLabel: month name on first of month or on Monday (week start)
				subLabel = dayOfMonth === 1 || dayOfWeek === 1
					? MONTH_NAMES[current.getMonth()]
					: '';
				break;

			case 'month':
				label = String(dayOfMonth);
				// subLabel: month name on first of month
				subLabel = dayOfMonth === 1
					? MONTH_NAMES[current.getMonth()]
					: '';
				break;
		}

		columns.push({ date: new Date(current), label, subLabel, isToday, isWeekend, width });

		current = addDays(current, 1);
	}

	return columns;
}

// ─── Snap to Grid ─────────────────────────────────────────────────────────────

export function snapToGrid(date: Date, zoom: ZoomLevel): Date {
	const d = startOfDay(date);

	switch (zoom) {
		case 'day':
			return d;

		case 'week': {
			// Snap to Monday (getDay: 0=Sun, 1=Mon, ..., 6=Sat)
			const day = d.getDay();
			const daysToMonday = day === 0 ? -6 : 1 - day;
			return addDays(d, daysToMonday);
		}

		case 'month': {
			const first = new Date(d);
			first.setDate(1);
			return first;
		}
	}
}

// ─── Format Month Header ──────────────────────────────────────────────────────

export function formatMonthHeader(date: Date): string {
	return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

// ─── Bar Color by Priority ────────────────────────────────────────────────────

export function getBarColor(priority: number): string {
	switch (priority) {
		case 5:
			return '#E53E3E'; // urgent
		case 4:
			return '#E8772E'; // high — tangerine accent
		case 3:
			return '#ECC94B'; // medium
		case 2:
			return '#48BB78'; // low
		case 1:
			return '#4299E1'; // lowest
		default:
			return '#A0AEC0'; // none (0 or unknown)
	}
}

// ─── Coordinate Conversion ────────────────────────────────────────────────────

export function dateToX(date: Date, viewStart: Date, zoom: ZoomLevel): number {
	const days = getDaysDiff(startOfDay(viewStart), startOfDay(date));
	return days * getColumnWidth(zoom);
}

export function xToDate(x: number, viewStart: Date, zoom: ZoomLevel): Date {
	const days = x / getColumnWidth(zoom);
	return addDays(startOfDay(viewStart), days);
}

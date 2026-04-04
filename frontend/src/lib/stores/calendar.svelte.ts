import { scheduleApi } from '$lib/api';
import { addToast } from '$lib/stores/toast.svelte';
import type { CalendarEvent, ScheduleSuggestion } from '$lib/types';

let _selectedDate = $state(new Date());
let _events = $state<CalendarEvent[]>([]);
let _suggestions = $state<ScheduleSuggestion[]>([]);
let _loading = $state(false);
let _suggestLoading = $state(false);
let _error = $state<string | null>(null);

function toDateKey(d: Date): string {
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${y}-${m}-${day}`;
}

function dayBounds(d: Date): { start: string; end: string } {
	const key = toDateKey(d);
	return {
		start: `${key}T00:00:00Z`,
		end: `${key}T23:59:59Z`,
	};
}

export const calendarStore = {
	get selectedDate() { return _selectedDate; },
	get dateKey() { return toDateKey(_selectedDate); },
	get events() { return _events; },
	get suggestions() { return _suggestions; },
	get loading() { return _loading; },
	get suggestLoading() { return _suggestLoading; },
	get error() { return _error; },

	setDate(d: Date) {
		_selectedDate = d;
		_suggestions = [];
		void this.fetchEvents();
	},

	navigateDay(delta: number) {
		const d = new Date(_selectedDate);
		d.setDate(d.getDate() + delta);
		this.setDate(d);
	},

	goToday() {
		this.setDate(new Date());
	},

	async fetchEvents() {
		_loading = true;
		_error = null;
		const { start, end } = dayBounds(_selectedDate);
		try {
			const data = await scheduleApi.listEvents(start, end);
			_events = data.events;
		} catch (e: unknown) {
			_error = e instanceof Error ? e.message : 'Failed to load events';
			_events = [];
		} finally {
			_loading = false;
		}
	},

	async createEvent(data: { summary: string; start: string; end: string; description?: string; task_id?: number }) {
		const event = await scheduleApi.createEvent(data);
		_events = [..._events, event];
		return event;
	},

	async deleteEvent(eventId: string) {
		await scheduleApi.deleteEvent(eventId);
		_events = _events.filter(e => e.id !== eventId);
	},

	async suggestSchedule() {
		_suggestLoading = true;
		try {
			const data = await scheduleApi.suggestSchedule(toDateKey(_selectedDate));
			_suggestions = data.suggestions;
		} catch (e: unknown) {
			_suggestions = [];
			const msg = e instanceof Error ? e.message : 'Failed to get suggestions';
			addToast(msg, 'error');
		} finally {
			_suggestLoading = false;
		}
	},

	clearSuggestions() {
		_suggestions = [];
	},

	removeSuggestion(taskId: number) {
		_suggestions = _suggestions.filter(s => s.task_id !== taskId);
	},
};

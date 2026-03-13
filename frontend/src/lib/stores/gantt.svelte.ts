import type { ZoomLevel } from '$lib/ganttUtils';

type DragState = {
	taskId: number;
	type: 'move' | 'resize-start' | 'resize-end';
	startX: number;
	originalStart: Date;
	originalEnd: Date;
} | null;

const UNSCHEDULED_COLLAPSED_KEY = 'cognito:gantt-unscheduled-collapsed';

function loadUnscheduledCollapsed(): boolean {
	if (typeof localStorage === 'undefined') return false;
	try {
		return localStorage.getItem(UNSCHEDULED_COLLAPSED_KEY) === 'true';
	} catch {
		return false;
	}
}

let _zoomLevel = $state<ZoomLevel>('week');
let _dragState = $state<DragState>(null);
let _unscheduledCollapsed = $state<boolean>(loadUnscheduledCollapsed());

const ZOOM_ORDER: ZoomLevel[] = ['day', 'week', 'month'];

export const ganttStore = {
	get zoom() {
		return _zoomLevel;
	},
	get dragState() {
		return _dragState;
	},
	get unscheduledCollapsed() {
		return _unscheduledCollapsed;
	},

	setZoom(level: ZoomLevel) {
		_zoomLevel = level;
	},

	zoomIn() {
		const idx = ZOOM_ORDER.indexOf(_zoomLevel);
		if (idx > 0) {
			_zoomLevel = ZOOM_ORDER[idx - 1];
		}
	},

	zoomOut() {
		const idx = ZOOM_ORDER.indexOf(_zoomLevel);
		if (idx < ZOOM_ORDER.length - 1) {
			_zoomLevel = ZOOM_ORDER[idx + 1];
		}
	},

	startDrag(state: NonNullable<DragState>) {
		_dragState = state;
	},

	endDrag() {
		_dragState = null;
	},

	toggleUnscheduled() {
		_unscheduledCollapsed = !_unscheduledCollapsed;
		try {
			localStorage.setItem(UNSCHEDULED_COLLAPSED_KEY, String(_unscheduledCollapsed));
		} catch {
			// ignore storage errors
		}
	}
};

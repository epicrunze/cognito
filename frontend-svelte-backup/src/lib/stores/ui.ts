/**
 * UI state store
 * 
 * Manages loading states, errors, and toast notifications.
 */

import { writable } from 'svelte/store';

export interface Toast {
id: string;
type: 'success' | 'error' | 'info' | 'warning';
message: string;
duration?: number;
}

// Loading indicator
export const isLoading = writable<boolean>(false);

// Error messages
export const error = writable<string | null>(null);

// Toast notifications
export const toasts = writable<Toast[]>([]);

/**
 * Show a toast notification
 */
export function showToast(
type: Toast['type'],
message: string,
duration = 5000
): void {
const id = crypto.randomUUID();
const toast: Toast = { id, type, message, duration };

toasts.update(t => [...t, toast]);

// Auto-dismiss after duration
if (duration > 0) {
setTimeout(() => {
dismissToast(id);
}, duration);
}
}

/**
 * Dismiss a toast by ID
 */
export function dismissToast(id: string): void {
toasts.update(t => t.filter(toast => toast.id !== id));
}

/**
 * Clear all toasts
 */
export function clearToasts(): void {
toasts.set([]);
}

/**
 * Set error message
 */
export function setError(message: string | null): void {
error.set(message);

// Auto-clear after 10 seconds
if (message) {
setTimeout(() => {
error.set(null);
}, 10000);
}
}

/**
 * Entries store
 * 
 * Manages journal entries state with reactive updates.
 */

import { writable, derived } from 'svelte/store';
import type { Entry } from '$lib/db';
import { getAllEntries } from '$lib/db/entries';

// Entries list
export const entries = writable<Entry[]>([]);

// Currently selected entry
export const currentEntry = writable<Entry | null>(null);

// Active entries (not archived)
export const activeEntries = derived(entries, $entries =>
$entries.filter(e => e.status === 'active')
);

// Archived entries
export const archivedEntries = derived(entries, $entries =>
$entries.filter(e => e.status === 'archived')
);

/**
 * Load entries from IndexedDB
 */
export async function loadEntries(filter?: {
status?: 'active' | 'archived';
after_date?: string;
before_date?: string;
}): Promise<void> {
try {
const loadedEntries = await getAllEntries(filter);
entries.set(loadedEntries);
} catch (error) {
console.error('Failed to load entries:', error);
entries.set([]);
}
}

/**
 * Refresh entries (reload from IndexedDB)
 */
export async function refreshEntries(): Promise<void> {
await loadEntries();
}

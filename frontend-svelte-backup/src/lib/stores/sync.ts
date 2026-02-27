/**
 * Sync status store
 * 
 * Tracks synchronization state and online/offline status.
 */

import { writable, derived } from 'svelte/store';
import { getPendingCount, getLastSyncedAt } from '$lib/db/sync';
import { browser } from '$app/environment';

export type SyncStatus = 'idle' | 'syncing' | 'error';

// Sync status
export const syncStatus = writable<SyncStatus>('idle');

// Pending changes count
export const pendingCount = writable<number>(0);

// Last synced timestamp
export const lastSynced = writable<string | null>(null);

// Online status
export const isOnline = writable<boolean>(browser ? navigator.onLine : true);

// Derived sync indicator
export const syncIndicator = derived(
[syncStatus, pendingCount],
([$syncStatus, $pendingCount]) => {
if ($syncStatus === 'syncing') return 'Syncing...';
if ($syncStatus === 'error') return 'Sync error';
if ($pendingCount > 0) return `${$pendingCount} pending`;
return 'Synced';
}
);

/**
 * Initialize sync store
 */
export async function initSync(): Promise<void> {
// Load pending count
const count = await getPendingCount();
pendingCount.set(count);

// Load last synced timestamp
const lastSyncedAt = await getLastSyncedAt();
lastSynced.set(lastSyncedAt);

// Set up online/offline listeners
if (browser) {
window.addEventListener('online', () => isOnline.set(true));
window.addEventListener('offline', () => isOnline.set(false));
}
}

/**
 * Update pending count
 */
export async function updatePendingCount(): Promise<void> {
const count = await getPendingCount();
pendingCount.set(count);
}

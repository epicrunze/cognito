/**
 * Sync and pending changes queue management
 */

import { db, type PendingChange } from './index';

/**
 * Queue a change for sync
 */
export async function queueChange(change: PendingChange): Promise<void> {
await db.pendingChanges.add(change);
}

/**
 * Get all pending changes ordered by timestamp
 */
export async function getPendingChanges(): Promise<PendingChange[]> {
return await db.pendingChanges.orderBy('timestamp').toArray();
}

/**
 * Clear a pending change after successful sync
 */
export async function clearPendingChange(id: string): Promise<void> {
await db.pendingChanges.delete(id);
}

/**
 * Clear all pending changes
 */
export async function clearAllPendingChanges(): Promise<void> {
await db.pendingChanges.clear();
}

/**
 * Get number of pending changes
 */
export async function getPendingCount(): Promise<number> {
return await db.pendingChanges.count();
}

/**
 * Get last synced timestamp
 */
export async function getLastSyncedAt(): Promise<string | null> {
const settings = await db.settings.get('settings');
return settings?.lastSyncedAt || null;
}

/**
 * Update last synced timestamp
 */
export async function setLastSyncedAt(timestamp: string): Promise<void> {
await db.settings.put({
id: 'settings',
lastSyncedAt: timestamp
});
}

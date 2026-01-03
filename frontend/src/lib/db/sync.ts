/**
 * Sync and pending changes queue management
 */

import { db, type PendingChange, type Entry, type Goal } from './index';
import { utcNow } from '$lib/utils/timestamp';
import logger from '$lib/logger';

/**
 * Queue a change for sync
 */
export async function queueChange(change: PendingChange): Promise<void> {
    await db.pendingChanges.add(change);
    logger.debug('Queued change', { entity: change.entity, type: change.type, id: change.entity_id });
}

/**
 * Queue an entry change with base_version tracking
 */
export async function queueEntryChange(
    type: 'create' | 'update' | 'delete',
    entry: Entry
): Promise<void> {
    await queueChange({
        id: crypto.randomUUID(),
        type,
        entity: 'entry',
        entity_id: entry.id,
        data: entry,
        base_version: entry.version,
        timestamp: utcNow(),
    });
}

/**
 * Queue a goal change
 */
export async function queueGoalChange(
    type: 'create' | 'update' | 'delete',
    goal: Goal
): Promise<void> {
    await queueChange({
        id: crypto.randomUUID(),
        type,
        entity: 'goal',
        entity_id: goal.id,
        data: goal,
        timestamp: utcNow(),
    });
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
 * Clear pending changes by entity IDs
 */
export async function clearPendingChangesByEntityIds(entityIds: string[]): Promise<void> {
    const changes = await db.pendingChanges
        .where('entity_id')
        .anyOf(entityIds)
        .toArray();

    const idsToDelete = changes.map(c => c.id);
    await Promise.all(idsToDelete.map(id => db.pendingChanges.delete(id)));

    logger.debug('Cleared pending changes', { count: idsToDelete.length });
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

/**
 * Apply a server entry to IndexedDB.
 * Updates if exists and server is newer, creates if not exists.
 */
export async function applyServerEntry(serverEntry: Entry): Promise<void> {
    const existing = await db.entries.get(serverEntry.id);

    if (!existing) {
        // New entry from server
        await db.entries.add(serverEntry);
        logger.debug('Added server entry', { id: serverEntry.id });
    } else if (serverEntry.updated_at > existing.updated_at) {
        // Server is newer, update local
        await db.entries.put(serverEntry);
        logger.debug('Updated local entry from server', { id: serverEntry.id });
    } else {
        logger.debug('Skipped server entry - local is newer', { id: serverEntry.id });
    }
}

/**
 * Apply a server goal to IndexedDB.
 */
export async function applyServerGoal(serverGoal: Goal): Promise<void> {
    const existing = await db.goals.get(serverGoal.id);

    if (!existing) {
        await db.goals.add(serverGoal);
        logger.debug('Added server goal', { id: serverGoal.id });
    } else if (serverGoal.updated_at > existing.updated_at) {
        await db.goals.put(serverGoal);
        logger.debug('Updated local goal from server', { id: serverGoal.id });
    } else {
        logger.debug('Skipped server goal - local is newer', { id: serverGoal.id });
    }
}

/**
 * Get base versions for all entries with pending changes.
 */
export async function getBaseVersions(): Promise<Record<string, number>> {
    const changes = await getPendingChanges();
    const versions: Record<string, number> = {};

    for (const change of changes) {
        if (change.entity === 'entry' && change.base_version !== undefined) {
            versions[change.entity_id] = change.base_version;
        }
    }

    return versions;
}


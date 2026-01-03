/**
 * Sync Orchestrator
 *
 * Manages the sync lifecycle including background sync, offline detection,
 * and coordinating between local storage and the server.
 */

import { get } from 'svelte/store';
import { performSync } from '$lib/api/sync';
import {
    getPendingChanges,
    getLastSyncedAt,
    setLastSyncedAt,
    clearPendingChangesByEntityIds,
    applyServerEntry,
    applyServerGoal,
    getBaseVersions,
} from '$lib/db/sync';
import { syncStatus, pendingCount, lastSynced, isOnline, updatePendingCount } from '$lib/stores/sync';
import logger from '$lib/logger';

// Sync debounce timer
let syncTimeoutId: ReturnType<typeof setTimeout> | null = null;
const SYNC_DEBOUNCE_MS = 1000;

// Periodic sync interval (5 minutes)
const PERIODIC_SYNC_INTERVAL_MS = 5 * 60 * 1000;
let periodicSyncIntervalId: ReturnType<typeof setInterval> | null = null;

/**
 * Perform a full sync cycle.
 *
 * 1. Gather pending changes
 * 2. Send to server
 * 3. Apply server changes locally
 * 4. Clear applied pending changes
 * 5. Update sync timestamp
 */
export async function performFullSync(): Promise<boolean> {
    // Check if online
    if (!get(isOnline)) {
        logger.info('Skipping sync - offline');
        return false;
    }

    // Check if already syncing
    if (get(syncStatus) === 'syncing') {
        logger.debug('Sync already in progress');
        return false;
    }

    syncStatus.set('syncing');

    try {
        // Gather pending changes
        const pendingChanges = await getPendingChanges();
        const lastSyncedAt = await getLastSyncedAt();
        const baseVersions = await getBaseVersions();

        logger.info('Starting sync', {
            pending: pendingChanges.length,
            lastSynced: lastSyncedAt,
        });

        // Perform sync with server
        const response = await performSync({
            last_synced_at: lastSyncedAt,
            pending_changes: pendingChanges,
            base_versions: baseVersions,
        });

        // Clear successfully applied changes
        if (response.applied.length > 0) {
            await clearPendingChangesByEntityIds(response.applied);
        }

        // Apply server changes locally
        for (const entry of response.server_changes.entries) {
            await applyServerEntry(entry);
        }

        for (const goal of response.server_changes.goals) {
            await applyServerGoal(goal);
        }

        // Update sync timestamp
        await setLastSyncedAt(response.sync_timestamp);
        lastSynced.set(response.sync_timestamp);

        // Update pending count
        await updatePendingCount();

        syncStatus.set('idle');

        logger.info('Sync completed successfully', {
            applied: response.applied.length,
            skipped: response.skipped.length,
            serverEntries: response.server_changes.entries.length,
            serverGoals: response.server_changes.goals.length,
        });

        return true;
    } catch (error) {
        logger.error('Sync failed', { error: String(error) });
        syncStatus.set('error');
        return false;
    }
}

/**
 * Trigger a debounced sync.
 *
 * Multiple rapid calls will be consolidated into a single sync.
 */
export function triggerSync(): void {
    if (syncTimeoutId) {
        clearTimeout(syncTimeoutId);
    }

    syncTimeoutId = setTimeout(async () => {
        syncTimeoutId = null;
        await performFullSync();
    }, SYNC_DEBOUNCE_MS);
}

/**
 * Setup background sync triggers.
 *
 * - Syncs when the app gains focus
 * - Syncs when coming back online
 * - Periodic sync every 5 minutes
 */
export function setupBackgroundSync(): void {
    if (typeof window === 'undefined') {
        return; // Skip in SSR
    }

    // Sync on window focus
    window.addEventListener('focus', handleFocus);

    // Sync when coming back online
    window.addEventListener('online', handleOnline);

    // Update offline status
    window.addEventListener('offline', handleOffline);

    // Start periodic sync
    startPeriodicSync();

    logger.info('Background sync initialized');
}

/**
 * Cleanup background sync listeners.
 */
export function cleanupBackgroundSync(): void {
    if (typeof window === 'undefined') {
        return;
    }

    window.removeEventListener('focus', handleFocus);
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);

    stopPeriodicSync();

    logger.info('Background sync cleanup');
}

// Event handlers
function handleFocus(): void {
    logger.debug('Window focused - triggering sync');
    triggerSync();
}

function handleOnline(): void {
    logger.info('Back online - triggering sync');
    isOnline.set(true);
    triggerSync();
}

function handleOffline(): void {
    logger.info('Went offline');
    isOnline.set(false);
}

// Periodic sync
function startPeriodicSync(): void {
    if (periodicSyncIntervalId) {
        clearInterval(periodicSyncIntervalId);
    }

    periodicSyncIntervalId = setInterval(() => {
        logger.debug('Periodic sync triggered');
        performFullSync();
    }, PERIODIC_SYNC_INTERVAL_MS);
}

function stopPeriodicSync(): void {
    if (periodicSyncIntervalId) {
        clearInterval(periodicSyncIntervalId);
        periodicSyncIntervalId = null;
    }
}

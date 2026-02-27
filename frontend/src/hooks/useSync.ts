/**
 * Sync Hook
 * 
 * Provides sync state management and background sync functionality.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { performSync } from '../api/sync';
import {
    getPendingChanges,
    getPendingCount,
    getLastSyncedAt,
    setLastSyncedAt,
    clearPendingChangesByEntityIds,
    applyServerEntry,
    applyServerGoal,
    getBaseVersions,
} from '../db/sync';

export type SyncStatus = 'idle' | 'syncing' | 'error';

interface UseSyncResult {
    syncStatus: SyncStatus;
    pendingCount: number;
    lastSynced: string | null;
    isOnline: boolean;
    triggerSync: () => void;
    performFullSync: () => Promise<boolean>;
}

const SYNC_DEBOUNCE_MS = 1000;
const PERIODIC_SYNC_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export function useSync(): UseSyncResult {
    const [syncStatus, setSyncStatus] = useState<SyncStatus>('idle');
    const [pendingCount, setPendingCount] = useState(0);
    const [lastSynced, setLastSyncedState] = useState<string | null>(null);
    const [isOnline, setIsOnline] = useState(navigator.onLine);

    const syncTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const periodicIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Update pending count
    const updatePendingCount = useCallback(async () => {
        const count = await getPendingCount();
        setPendingCount(count);
    }, []);

    // Perform full sync
    const performFullSync = useCallback(async (): Promise<boolean> => {
        if (!isOnline) {
            console.log('Skipping sync - offline');
            return false;
        }

        if (syncStatus === 'syncing') {
            console.log('Sync already in progress');
            return false;
        }

        setSyncStatus('syncing');

        try {
            const pendingChanges = await getPendingChanges();
            const lastSyncedAt = await getLastSyncedAt();
            const baseVersions = await getBaseVersions();

            console.log('Starting sync', {
                pending: pendingChanges.length,
                lastSynced: lastSyncedAt,
            });

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
            setLastSyncedState(response.sync_timestamp);

            // Update pending count
            await updatePendingCount();

            setSyncStatus('idle');

            console.log('Sync completed successfully', {
                applied: response.applied.length,
                skipped: response.skipped.length,
                serverEntries: response.server_changes.entries.length,
                serverGoals: response.server_changes.goals.length,
            });

            return true;
        } catch (error) {
            console.error('Sync failed:', error);
            setSyncStatus('error');
            return false;
        }
    }, [isOnline, syncStatus, updatePendingCount]);

    // Trigger debounced sync
    const triggerSync = useCallback(() => {
        if (syncTimeoutRef.current) {
            clearTimeout(syncTimeoutRef.current);
        }

        syncTimeoutRef.current = setTimeout(async () => {
            syncTimeoutRef.current = null;
            await performFullSync();
        }, SYNC_DEBOUNCE_MS);
    }, [performFullSync]);

    // Initialize and setup event listeners
    useEffect(() => {
        // Load initial state
        const init = async () => {
            await updatePendingCount();
            const lastSync = await getLastSyncedAt();
            setLastSyncedState(lastSync);
        };
        init();

        // Online/offline handlers
        const handleOnline = () => {
            setIsOnline(true);
            triggerSync();
        };
        const handleOffline = () => {
            setIsOnline(false);
        };
        const handleFocus = () => {
            triggerSync();
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);
        window.addEventListener('focus', handleFocus);

        // Periodic sync
        periodicIntervalRef.current = setInterval(() => {
            performFullSync();
        }, PERIODIC_SYNC_INTERVAL_MS);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
            window.removeEventListener('focus', handleFocus);

            if (syncTimeoutRef.current) {
                clearTimeout(syncTimeoutRef.current);
            }
            if (periodicIntervalRef.current) {
                clearInterval(periodicIntervalRef.current);
            }
        };
    }, [updatePendingCount, triggerSync, performFullSync]);

    return {
        syncStatus,
        pendingCount,
        lastSynced,
        isOnline,
        triggerSync,
        performFullSync,
    };
}

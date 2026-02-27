/**
 * Sync API client
 *
 * Handles communication with the sync endpoint for offline-first synchronization.
 */

import { api } from './client';
import type { Entry, Goal, PendingChange } from '$lib/db';
import logger from '$lib/logger';

/**
 * Sync request payload.
 */
export interface SyncRequest {
    last_synced_at: string | null;
    pending_changes: PendingChange[];
    base_versions: Record<string, number>;
}

/**
 * Server changes returned from sync.
 */
export interface ServerChanges {
    entries: Entry[];
    goals: Goal[];
}

/**
 * Sync response from server.
 */
export interface SyncResponse {
    applied: string[];
    skipped: string[];
    server_changes: ServerChanges;
    sync_timestamp: string;
    pending_messages_processed: string[];
}

/**
 * Perform sync with the server.
 *
 * Sends pending changes and receives server changes.
 */
export async function performSync(request: SyncRequest): Promise<SyncResponse> {
    logger.info('Performing sync', {
        pending_count: request.pending_changes.length,
        last_synced: request.last_synced_at,
    });

    try {
        const response = await api.post<SyncResponse>('/sync', request);

        logger.info('Sync completed', {
            applied: response.applied.length,
            skipped: response.skipped.length,
            server_entries: response.server_changes.entries.length,
            server_goals: response.server_changes.goals.length,
            pending_messages: response.pending_messages_processed.length,
        });

        return response;
    } catch (error) {
        logger.error('Sync failed', { error: String(error) });
        throw error;
    }
}

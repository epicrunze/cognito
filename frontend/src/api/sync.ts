/**
 * Sync API module
 * 
 * Handles synchronization with backend.
 */

import { api } from './client';
import type { Entry, Goal, PendingChange } from '../db';

export interface SyncRequest {
    last_synced_at: string | null;
    pending_changes: PendingChange[];
    base_versions: Record<string, number>;
}

export interface SyncResponse {
    applied: string[];
    skipped: string[];
    server_changes: {
        entries: Entry[];
        goals: Goal[];
    };
    sync_timestamp: string;
}

/**
 * Perform sync with backend
 */
export async function performSync(request: SyncRequest): Promise<SyncResponse> {
    return await api.post<SyncResponse>('/sync', request);
}

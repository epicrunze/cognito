/**
 * Sync queue operations for IndexedDB
 */

import { db, type PendingChange, type Entry, type Goal, type AuthProfile } from './index';

// Cache validity durations
const CACHE_STALE_MS = 60 * 60 * 1000; // 1 hour
const CACHE_EXPIRED_MS = 7 * 24 * 60 * 60 * 1000; // 1 week
const PROACTIVE_REFRESH_MS = 24 * 60 * 60 * 1000; // 1 day before expiry

/**
 * Queue a change for sync
 */
export async function queueChange(change: PendingChange): Promise<void> {
    await db.pendingChanges.add(change);
}

/**
 * Get all pending changes
 */
export async function getPendingChanges(): Promise<PendingChange[]> {
    return await db.pendingChanges.orderBy('timestamp').toArray();
}

/**
 * Get pending changes count
 */
export async function getPendingCount(): Promise<number> {
    return await db.pendingChanges.count();
}

/**
 * Clear pending changes by entity IDs
 */
export async function clearPendingChangesByEntityIds(
    entityIds: string[]
): Promise<void> {
    await db.pendingChanges.where('entity_id').anyOf(entityIds).delete();
}

/**
 * Get last synced timestamp
 */
export async function getLastSyncedAt(): Promise<string | null> {
    const settings = await db.settings.get('settings');
    return settings?.lastSyncedAt ?? null;
}

/**
 * Set last synced timestamp
 */
export async function setLastSyncedAt(timestamp: string): Promise<void> {
    await db.settings.update('settings', { lastSyncedAt: timestamp });
}

/**
 * Get base versions for conflict detection
 */
export async function getBaseVersions(): Promise<Record<string, number>> {
    const entries = await db.entries.toArray();
    const versions: Record<string, number> = {};
    for (const entry of entries) {
        versions[entry.id] = entry.version;
    }
    return versions;
}

/**
 * Apply server entry (upsert)
 */
export async function applyServerEntry(entry: Entry): Promise<void> {
    await db.entries.put(entry);
}

/**
 * Apply server goal (upsert)
 */
export async function applyServerGoal(goal: Goal): Promise<void> {
    await db.goals.put(goal);
}

// Auth profile caching functions

/**
 * Cache auth profile
 */
export async function cacheAuthProfile(
    user: { email: string; name: string; picture: string },
    jwtExpiresAt?: string
): Promise<void> {
    await db.authProfile.put({
        id: 'current',
        email: user.email,
        name: user.name,
        picture: user.picture,
        cachedAt: new Date().toISOString(),
        jwtExpiresAt
    });
}

/**
 * Get cached auth profile
 */
export async function getCachedAuthProfile(): Promise<{
    email: string;
    name: string;
    picture: string;
} | null> {
    const profile = await db.authProfile.get('current');
    if (!profile) return null;
    return {
        email: profile.email,
        name: profile.name,
        picture: profile.picture
    };
}

/**
 * Get full cached auth profile with metadata
 */
export async function getFullCachedAuthProfile(): Promise<AuthProfile | null> {
    return (await db.authProfile.get('current')) ?? null;
}

/**
 * Clear cached auth
 */
export async function clearCachedAuth(): Promise<void> {
    await db.authProfile.delete('current');
}

/**
 * Check if auth cache is stale (> 1 hour old)
 */
export async function isAuthCacheStale(): Promise<boolean> {
    const profile = await db.authProfile.get('current');
    if (!profile) return true;

    const cachedTime = new Date(profile.cachedAt).getTime();
    const now = Date.now();
    return now - cachedTime > CACHE_STALE_MS;
}

/**
 * Check if auth cache is expired (> 1 week old)
 */
export async function isAuthCacheExpired(): Promise<boolean> {
    const profile = await db.authProfile.get('current');
    if (!profile) return true;

    const cachedTime = new Date(profile.cachedAt).getTime();
    const now = Date.now();
    return now - cachedTime > CACHE_EXPIRED_MS;
}

/**
 * Check if proactive token refresh is needed (JWT expires within 1 day)
 */
export async function needsProactiveRefresh(): Promise<boolean> {
    const profile = await db.authProfile.get('current');
    if (!profile?.jwtExpiresAt) return false;

    const expiryTime = new Date(profile.jwtExpiresAt).getTime();
    const now = Date.now();
    return expiryTime - now < PROACTIVE_REFRESH_MS;
}

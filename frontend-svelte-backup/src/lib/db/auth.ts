/**
 * Auth persistence utilities for offline support
 * 
 * Caches user profile in IndexedDB for offline access.
 * Uses stale-while-revalidate pattern with 1 hour staleness and 1 week expiry.
 */

import { db, type AuthProfile } from './index';
import type { User } from '$lib/api/auth';
import { utcNow } from '$lib/utils/timestamp';

// Cache staleness threshold (1 hour in ms)
const STALE_THRESHOLD_MS = 60 * 60 * 1000;

// Cache expiry threshold (1 week in ms)
const EXPIRY_THRESHOLD_MS = 7 * 24 * 60 * 60 * 1000;

// Proactive refresh threshold (1 day in ms)
const PROACTIVE_REFRESH_THRESHOLD_MS = 24 * 60 * 60 * 1000;

/**
 * Cache user profile after successful authentication
 * 
 * @param user User profile to cache
 * @param jwtExpiresAt Optional JWT expiry time for proactive refresh
 */
export async function cacheAuthProfile(user: User, jwtExpiresAt?: string): Promise<void> {
    const profile: AuthProfile = {
        id: 'current',
        email: user.email,
        name: user.name,
        picture: user.picture,
        cachedAt: utcNow(),
        jwtExpiresAt,
    };
    await db.authProfile.put(profile);
}

/**
 * Get cached auth profile
 */
export async function getCachedAuthProfile(): Promise<AuthProfile | null> {
    const profile = await db.authProfile.get('current');
    return profile ?? null;
}

/**
 * Clear cached auth on logout
 */
export async function clearCachedAuth(): Promise<void> {
    await db.authProfile.delete('current');
}

/**
 * Check if cache is stale (should refresh if online)
 * Stale = cached more than 1 hour ago
 */
export function isAuthCacheStale(profile: AuthProfile): boolean {
    const cachedAt = new Date(profile.cachedAt).getTime();
    const now = Date.now();
    return now - cachedAt > STALE_THRESHOLD_MS;
}

/**
 * Check if cache is expired (can't trust without backend verification)
 * Expired = cached more than 1 week ago
 */
export function isAuthCacheExpired(profile: AuthProfile): boolean {
    const cachedAt = new Date(profile.cachedAt).getTime();
    const now = Date.now();
    return now - cachedAt > EXPIRY_THRESHOLD_MS;
}

/**
 * Check if JWT needs proactive refresh (expires within 1 day)
 */
export function needsProactiveRefresh(profile: AuthProfile): boolean {
    if (!profile.jwtExpiresAt) {
        return false; // No expiry info, can't determine
    }

    const expiresAt = new Date(profile.jwtExpiresAt).getTime();
    const now = Date.now();
    const timeUntilExpiry = expiresAt - now;

    return timeUntilExpiry > 0 && timeUntilExpiry < PROACTIVE_REFRESH_THRESHOLD_MS;
}

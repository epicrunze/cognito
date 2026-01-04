/**
 * Authentication store
 * 
 * Manages user authentication state with offline support.
 * Uses cache-first, stale-while-revalidate pattern with proactive token refresh.
 */

import { writable, derived } from 'svelte/store';
import type { User } from '$lib/api/auth';
import { getMe, refreshToken } from '$lib/api/auth';
import {
    cacheAuthProfile,
    getCachedAuthProfile,
    clearCachedAuth,
    isAuthCacheStale,
    isAuthCacheExpired,
    needsProactiveRefresh,
} from '$lib/db/auth';

// User state
export const user = writable<User | null>(null);

// Derived authenticated state
export const isAuthenticated = derived(user, $user => $user !== null);

// Loading state for auth check
export const authLoading = writable(true);

// Auth source tracking for UI indicators
export type AuthSource = 'verified' | 'cached' | 'stale' | null;
export const authSource = writable<AuthSource>(null);

// Calculate JWT expiry time (7 days from now)
function calculateJwtExpiry(): string {
    const expiry = new Date();
    expiry.setDate(expiry.getDate() + 7);
    return expiry.toISOString();
}

/**
 * Check authentication status
 * 
 * Uses cache-first, stale-while-revalidate pattern:
 * 1. Fresh cache (< 1 hour): use immediately, no network
 * 2. Stale cache (1h - 1 week): use cache, refresh from backend
 * 3. Expired cache (> 1 week): must verify with backend
 * 4. Offline: use any cache (user keeps access to local data)
 * 
 * Also performs proactive token refresh if JWT expires within 1 day.
 */
export async function checkAuth(): Promise<void> {
    authLoading.set(true);
    try {
        // 1. Always check cache first (instant response)
        const cached = await getCachedAuthProfile();

        // 2. If offline: use cache regardless of staleness
        //    (User keeps access to local data)
        if (!navigator.onLine) {
            if (cached) {
                user.set(cached);
                authSource.set('stale');
            } else {
                user.set(null);
                authSource.set(null);
            }
            return;
        }

        // 3. Proactive refresh: if JWT expires within 1 day, refresh silently
        if (cached && needsProactiveRefresh(cached)) {
            console.log('🔄 JWT expires soon, proactively refreshing...');
            const refreshed = await refreshToken();
            if (refreshed) {
                console.log('✅ Proactive token refresh successful');
                // Update cache with new expiry
                await cacheAuthProfile(cached, calculateJwtExpiry());
                user.set(cached);
                authSource.set('verified');
                return;
            }
            // If refresh fails, continue with normal flow
            console.log('⚠️ Proactive refresh failed, continuing with normal auth check');
        }

        // 4. If we have fresh cache: use it, skip network
        if (cached && !isAuthCacheStale(cached)) {
            user.set(cached);
            authSource.set('cached');
            return;
        }

        // 5. Cache missing or stale: verify with backend
        try {
            const timeoutPromise = new Promise<never>((_, reject) =>
                setTimeout(() => reject(new Error('Auth check timeout')), 3000)
            );
            const currentUser = await Promise.race([getMe(), timeoutPromise]);

            if (currentUser) {
                await cacheAuthProfile(currentUser, calculateJwtExpiry());
                user.set(currentUser);
                authSource.set('verified');
            } else {
                user.set(null);
                authSource.set(null);
            }
        } catch (error) {
            // 6. Backend failed: fall back to cache if not expired
            console.error('Auth check failed:', error);
            if (cached && !isAuthCacheExpired(cached)) {
                console.log('💡 Using cached credentials (backend unreachable)');
                user.set(cached);
                authSource.set('stale');
            } else {
                console.log('💡 Tip: Start the backend or you can develop with mock data');
                user.set(null);
                authSource.set(null);
            }
        }
    } finally {
        authLoading.set(false);
    }
}

/**
 * Clear user session (called after logout)
 */
export async function clearAuth(): Promise<void> {
    user.set(null);
    authSource.set(null);
    await clearCachedAuth();
}

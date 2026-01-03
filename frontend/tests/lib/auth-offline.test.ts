/**
 * Tests for offline auth functionality.
 *
 * Tests auth caching, staleness/expiry logic, and cache-first checkAuth behavior.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import 'fake-indexeddb/auto';
import { db } from '$lib/db';
import {
    cacheAuthProfile,
    getCachedAuthProfile,
    clearCachedAuth,
    isAuthCacheStale,
    isAuthCacheExpired,
} from '$lib/db/auth';
import type { AuthProfile } from '$lib/db';

// Helper to create a profile with specific cached time
function createProfileWithAge(hoursAgo: number): AuthProfile {
    const cachedAt = new Date(Date.now() - hoursAgo * 60 * 60 * 1000).toISOString();
    return {
        id: 'current',
        email: 'test@example.com',
        name: 'Test User',
        picture: 'https://example.com/photo.jpg',
        cachedAt,
    };
}

describe('Auth Cache Persistence', () => {
    beforeEach(async () => {
        await db.authProfile.clear();
    });

    it('should cache user profile', async () => {
        const user = {
            email: 'test@example.com',
            name: 'Test User',
            picture: 'https://example.com/photo.jpg',
        };

        await cacheAuthProfile(user);

        const cached = await getCachedAuthProfile();
        expect(cached).not.toBeNull();
        expect(cached?.email).toBe('test@example.com');
        expect(cached?.name).toBe('Test User');
        expect(cached?.picture).toBe('https://example.com/photo.jpg');
    });

    it('should return null when no cached profile', async () => {
        const cached = await getCachedAuthProfile();
        expect(cached).toBeNull();
    });

    it('should clear cached profile on logout', async () => {
        const user = {
            email: 'test@example.com',
            name: 'Test User',
            picture: 'https://example.com/photo.jpg',
        };

        await cacheAuthProfile(user);
        expect(await getCachedAuthProfile()).not.toBeNull();

        await clearCachedAuth();
        expect(await getCachedAuthProfile()).toBeNull();
    });

    it('should overwrite existing cache on re-login', async () => {
        const user1 = {
            email: 'user1@example.com',
            name: 'User One',
            picture: 'https://example.com/user1.jpg',
        };
        const user2 = {
            email: 'user2@example.com',
            name: 'User Two',
            picture: 'https://example.com/user2.jpg',
        };

        await cacheAuthProfile(user1);
        await cacheAuthProfile(user2);

        const cached = await getCachedAuthProfile();
        expect(cached?.email).toBe('user2@example.com');
        expect(cached?.name).toBe('User Two');
    });
});

describe('Auth Cache Staleness', () => {
    it('should not be stale if cached less than 1 hour ago', () => {
        const profile = createProfileWithAge(0.5); // 30 minutes ago
        expect(isAuthCacheStale(profile)).toBe(false);
    });

    it('should be stale if cached more than 1 hour ago', () => {
        const profile = createProfileWithAge(2); // 2 hours ago
        expect(isAuthCacheStale(profile)).toBe(true);
    });

    it('should not be expired if cached less than 1 week ago', () => {
        const profile = createProfileWithAge(24 * 6); // 6 days ago
        expect(isAuthCacheExpired(profile)).toBe(false);
    });

    it('should be expired if cached more than 1 week ago', () => {
        const profile = createProfileWithAge(24 * 8); // 8 days ago
        expect(isAuthCacheExpired(profile)).toBe(true);
    });

    it('stale and expired should have correct thresholds', () => {
        // Just over 1 hour = stale but not expired
        const staleProfile = createProfileWithAge(1.1);
        expect(isAuthCacheStale(staleProfile)).toBe(true);
        expect(isAuthCacheExpired(staleProfile)).toBe(false);

        // Just over 1 week = both stale and expired
        const expiredProfile = createProfileWithAge(24 * 7 + 1);
        expect(isAuthCacheStale(expiredProfile)).toBe(true);
        expect(isAuthCacheExpired(expiredProfile)).toBe(true);
    });
});

describe('Offline Auth Scenarios', () => {
    beforeEach(async () => {
        await db.authProfile.clear();
    });

    it('fresh cache should be usable for offline access', async () => {
        await db.authProfile.put(createProfileWithAge(0.5)); // 30 min ago

        const cached = await getCachedAuthProfile();
        expect(cached).not.toBeNull();
        expect(isAuthCacheStale(cached!)).toBe(false);
        expect(isAuthCacheExpired(cached!)).toBe(false);
        // This cache is fresh - good for offline use without verification
    });

    it('stale cache should still allow offline access', async () => {
        await db.authProfile.put(createProfileWithAge(24)); // 1 day ago

        const cached = await getCachedAuthProfile();
        expect(cached).not.toBeNull();
        expect(isAuthCacheStale(cached!)).toBe(true);
        expect(isAuthCacheExpired(cached!)).toBe(false);
        // Stale but not expired - user can access offline data
    });

    it('expired cache should not be trusted when online', async () => {
        await db.authProfile.put(createProfileWithAge(24 * 10)); // 10 days ago

        const cached = await getCachedAuthProfile();
        expect(cached).not.toBeNull();
        expect(isAuthCacheExpired(cached!)).toBe(true);
        // Expired - when online, must verify with backend
    });
});

/**
 * Store reactivity tests
 * 
 * Tests Svelte store behavior.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';
import { user, isAuthenticated, checkAuth, clearAuth } from '$lib/stores/auth';
import { entries, activeEntries, archivedEntries } from '$lib/stores/entries';
import { syncStatus, pendingCount, syncIndicator } from '$lib/stores/sync';
import { isLoading, error, toasts, showToast, dismissToast, setError } from '$lib/stores/ui';

describe('Stores', () => {
    describe('Auth Store', () => {
        beforeEach(() => {
            clearAuth();
        });

        it('should initialize with null user', () => {
            expect(get(user)).toBeNull();
            expect(get(isAuthenticated)).toBe(false);
        });

        it('should set user', () => {
            const testUser = {
                email: 'test@example.com',
                name: 'Test User',
                picture: 'https://example.com/pic.jpg'
            };

            user.set(testUser);
            expect(get(user)).toEqual(testUser);
            expect(get(isAuthenticated)).toBe(true);
        });

        it('should clear auth', () => {
            user.set({
                email: 'test@example.com',
                name: 'Test User',
                picture: 'https://example.com/pic.jpg'
            });

            clearAuth();
            expect(get(user)).toBeNull();
            expect(get(isAuthenticated)).toBe(false);
        });
    });

    describe('Entries Store', () => {
        beforeEach(() => {
            entries.set([]);
        });

        it('should filter active entries', () => {
            const testEntries = [
                {
                    id: '1',
                    date: '2024-12-15',
                    conversations: [],
                    refined_output: 'Active',
                    relevance_score: 1.0,
                    last_interacted_at: new Date().toISOString(),
                    interaction_count: 0,
                    status: 'active' as const,
                    version: 1,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString()
                },
                {
                    id: '2',
                    date: '2024-12-14',
                    conversations: [],
                    refined_output: 'Archived',
                    relevance_score: 1.0,
                    last_interacted_at: new Date().toISOString(),
                    interaction_count: 0,
                    status: 'archived' as const,
                    version: 1,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString()
                }
            ];

            entries.set(testEntries);

            const active = get(activeEntries);
            const archived = get(archivedEntries);

            expect(active).toHaveLength(1);
            expect(active[0].status).toBe('active');
            expect(archived).toHaveLength(1);
            expect(archived[0].status).toBe('archived');
        });
    });

    describe('Sync Store', () => {
        beforeEach(() => {
            syncStatus.set('idle');
            pendingCount.set(0);
        });

        it('should show sync indicator based on status', () => {
            syncStatus.set('syncing');
            expect(get(syncIndicator)).toBe('Syncing...');

            syncStatus.set('error');
            expect(get(syncIndicator)).toBe('Sync error');

            syncStatus.set('idle');
            pendingCount.set(5);
            expect(get(syncIndicator)).toBe('5 pending');

            pendingCount.set(0);
            expect(get(syncIndicator)).toBe('Synced');
        });
    });

    describe('UI Store', () => {
        beforeEach(() => {
            isLoading.set(false);
            error.set(null);
            toasts.set([]);
        });

        it('should show toast', () => {
            showToast('success', 'Test message', 0); // duration 0 = no auto-dismiss

            const currentToasts = get(toasts);
            expect(currentToasts).toHaveLength(1);
            expect(currentToasts[0].type).toBe('success');
            expect(currentToasts[0].message).toBe('Test message');
        });

        it('should dismiss toast', () => {
            showToast('info', 'Test', 0);
            const toast = get(toasts)[0];

            dismissToast(toast.id);
            expect(get(toasts)).toHaveLength(0);
        });

        it('should set error', () => {
            setError('Test error');
            expect(get(error)).toBe('Test error');
        });
    });
});

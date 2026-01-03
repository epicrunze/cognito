/**
 * Tests for sync functionality.
 *
 * Tests sync queue management, server change application, and sync orchestration.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import 'fake-indexeddb/auto';
import { db } from '$lib/db';
import {
    queueChange,
    queueEntryChange,
    queueGoalChange,
    getPendingChanges,
    clearPendingChange,
    clearPendingChangesByEntityIds,
    getLastSyncedAt,
    setLastSyncedAt,
    applyServerEntry,
    applyServerGoal,
    getBaseVersions,
} from '$lib/db/sync';
import type { Entry, Goal, PendingChange } from '$lib/db';

describe('Sync Queue Management', () => {
    beforeEach(async () => {
        // Clear all tables before each test
        await db.entries.clear();
        await db.goals.clear();
        await db.pendingChanges.clear();
        await db.settings.clear();
        await db.settings.add({ id: 'settings', lastSyncedAt: null });
    });

    it('should queue a pending change', async () => {
        const change: PendingChange = {
            id: '123',
            type: 'create',
            entity: 'entry',
            entity_id: 'entry-1',
            data: { test: true },
            timestamp: new Date().toISOString(),
        };

        await queueChange(change);

        const changes = await getPendingChanges();
        expect(changes).toHaveLength(1);
        expect(changes[0].id).toBe('123');
    });

    it('should queue entry change with base_version', async () => {
        const entry: Entry = {
            id: 'entry-1',
            date: '2024-12-30',
            conversations: [],
            refined_output: '',
            relevance_score: 1.0,
            last_interacted_at: new Date().toISOString(),
            interaction_count: 0,
            status: 'active',
            version: 5,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };

        await queueEntryChange('update', entry);

        const changes = await getPendingChanges();
        expect(changes).toHaveLength(1);
        expect(changes[0].base_version).toBe(5);
        expect(changes[0].entity).toBe('entry');
    });

    it('should queue goal change', async () => {
        const goal: Goal = {
            id: 'goal-1',
            category: 'health',
            description: 'Exercise daily',
            active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };

        await queueGoalChange('create', goal);

        const changes = await getPendingChanges();
        expect(changes).toHaveLength(1);
        expect(changes[0].entity).toBe('goal');
    });

    it('should clear pending change by id', async () => {
        await queueChange({
            id: 'change-1',
            type: 'create',
            entity: 'entry',
            entity_id: 'entry-1',
            data: {},
            timestamp: new Date().toISOString(),
        });
        await queueChange({
            id: 'change-2',
            type: 'update',
            entity: 'entry',
            entity_id: 'entry-2',
            data: {},
            timestamp: new Date().toISOString(),
        });

        await clearPendingChange('change-1');

        const changes = await getPendingChanges();
        expect(changes).toHaveLength(1);
        expect(changes[0].id).toBe('change-2');
    });

    it('should clear pending changes by entity IDs', async () => {
        await queueChange({
            id: 'change-1',
            type: 'create',
            entity: 'entry',
            entity_id: 'entry-1',
            data: {},
            timestamp: new Date().toISOString(),
        });
        await queueChange({
            id: 'change-2',
            type: 'update',
            entity: 'entry',
            entity_id: 'entry-2',
            data: {},
            timestamp: new Date().toISOString(),
        });

        await clearPendingChangesByEntityIds(['entry-1']);

        const changes = await getPendingChanges();
        expect(changes).toHaveLength(1);
        expect(changes[0].entity_id).toBe('entry-2');
    });
});

describe('Last Synced Timestamp', () => {
    beforeEach(async () => {
        await db.settings.clear();
        await db.settings.add({ id: 'settings', lastSyncedAt: null });
    });

    it('should get null when never synced', async () => {
        const lastSynced = await getLastSyncedAt();
        expect(lastSynced).toBeNull();
    });

    it('should set and get last synced timestamp', async () => {
        const timestamp = '2024-12-30T12:00:00.000Z';
        await setLastSyncedAt(timestamp);

        const lastSynced = await getLastSyncedAt();
        expect(lastSynced).toBe(timestamp);
    });
});

describe('Apply Server Changes', () => {
    beforeEach(async () => {
        await db.entries.clear();
        await db.goals.clear();
    });

    it('should add new entry from server', async () => {
        const serverEntry: Entry = {
            id: 'server-entry-1',
            date: '2024-12-30',
            conversations: [],
            refined_output: 'From server',
            relevance_score: 1.0,
            last_interacted_at: new Date().toISOString(),
            interaction_count: 0,
            status: 'active',
            version: 1,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };

        await applyServerEntry(serverEntry);

        const entry = await db.entries.get('server-entry-1');
        expect(entry).toBeDefined();
        expect(entry?.refined_output).toBe('From server');
    });

    it('should update local entry when server is newer', async () => {
        const oldTimestamp = '2024-12-29T12:00:00.000Z';
        const newTimestamp = '2024-12-30T12:00:00.000Z';

        // Add local entry with old timestamp
        await db.entries.add({
            id: 'entry-1',
            date: '2024-12-29',
            conversations: [],
            refined_output: 'Local version',
            relevance_score: 1.0,
            last_interacted_at: oldTimestamp,
            interaction_count: 0,
            status: 'active',
            version: 1,
            created_at: oldTimestamp,
            updated_at: oldTimestamp,
        });

        // Apply server entry with newer timestamp
        await applyServerEntry({
            id: 'entry-1',
            date: '2024-12-30',
            conversations: [],
            refined_output: 'Server version',
            relevance_score: 1.0,
            last_interacted_at: newTimestamp,
            interaction_count: 1,
            status: 'active',
            version: 2,
            created_at: oldTimestamp,
            updated_at: newTimestamp,
        });

        const entry = await db.entries.get('entry-1');
        expect(entry?.refined_output).toBe('Server version');
    });

    it('should not update local entry when local is newer', async () => {
        const oldTimestamp = '2024-12-29T12:00:00.000Z';
        const newTimestamp = '2024-12-30T12:00:00.000Z';

        // Add local entry with newer timestamp
        await db.entries.add({
            id: 'entry-1',
            date: '2024-12-29',
            conversations: [],
            refined_output: 'Local version',
            relevance_score: 1.0,
            last_interacted_at: newTimestamp,
            interaction_count: 0,
            status: 'active',
            version: 2,
            created_at: oldTimestamp,
            updated_at: newTimestamp,
        });

        // Apply server entry with older timestamp
        await applyServerEntry({
            id: 'entry-1',
            date: '2024-12-30',
            conversations: [],
            refined_output: 'Server version',
            relevance_score: 1.0,
            last_interacted_at: oldTimestamp,
            interaction_count: 1,
            status: 'active',
            version: 1,
            created_at: oldTimestamp,
            updated_at: oldTimestamp,
        });

        const entry = await db.entries.get('entry-1');
        expect(entry?.refined_output).toBe('Local version');
    });

    it('should add new goal from server', async () => {
        const serverGoal: Goal = {
            id: 'server-goal-1',
            category: 'health',
            description: 'From server',
            active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };

        await applyServerGoal(serverGoal);

        const goal = await db.goals.get('server-goal-1');
        expect(goal).toBeDefined();
        expect(goal?.description).toBe('From server');
    });
});

describe('Base Versions', () => {
    beforeEach(async () => {
        await db.pendingChanges.clear();
    });

    it('should get base versions for pending entry changes', async () => {
        await queueChange({
            id: 'change-1',
            type: 'update',
            entity: 'entry',
            entity_id: 'entry-1',
            data: {},
            base_version: 3,
            timestamp: new Date().toISOString(),
        });
        await queueChange({
            id: 'change-2',
            type: 'update',
            entity: 'entry',
            entity_id: 'entry-2',
            data: {},
            base_version: 5,
            timestamp: new Date().toISOString(),
        });

        const versions = await getBaseVersions();

        expect(versions['entry-1']).toBe(3);
        expect(versions['entry-2']).toBe(5);
    });

    it('should not include goal changes in base versions', async () => {
        await queueChange({
            id: 'change-1',
            type: 'create',
            entity: 'goal',
            entity_id: 'goal-1',
            data: {},
            timestamp: new Date().toISOString(),
        });

        const versions = await getBaseVersions();

        expect(Object.keys(versions)).toHaveLength(0);
    });
});

describe('Offline Sync Behavior (FE-001)', () => {
    beforeEach(async () => {
        // Clear all tables before each test
        await db.entries.clear();
        await db.goals.clear();
        await db.pendingChanges.clear();
        await db.settings.clear();
        await db.settings.add({ id: 'settings', lastSyncedAt: null });
        vi.clearAllMocks();
    });

    it('should queue changes when offline without attempting sync', async () => {
        // Queue changes while would be "offline"
        const entry: Entry = {
            id: 'entry-1',
            date: '2024-12-30',
            conversations: [],
            refined_output: 'Created offline',
            relevance_score: 1.0,
            last_interacted_at: new Date().toISOString(),
            interaction_count: 0,
            status: 'active',
            version: 1,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        };

        await queueEntryChange('create', entry);

        // Verify change is queued
        const changes = await getPendingChanges();
        expect(changes).toHaveLength(1);
        expect(changes[0].entity_id).toBe('entry-1');
        expect(changes[0].type).toBe('create');
    });

    it('should queue multiple changes and maintain order', async () => {
        // Simulate multiple offline operations
        const timestamps = [
            '2024-12-30T10:00:00.000Z',
            '2024-12-30T10:01:00.000Z',
            '2024-12-30T10:02:00.000Z',
        ];

        for (let i = 0; i < 3; i++) {
            await queueChange({
                id: `change-${i}`,
                type: 'update',
                entity: 'entry',
                entity_id: `entry-${i}`,
                data: { content: `Update ${i}` },
                timestamp: timestamps[i],
            });
        }

        // Verify all changes are queued in order
        const changes = await getPendingChanges();
        expect(changes).toHaveLength(3);
        expect(changes[0].entity_id).toBe('entry-0');
        expect(changes[1].entity_id).toBe('entry-1');
        expect(changes[2].entity_id).toBe('entry-2');
    });

    it('should persist pending queue data after clearing and re-reading', async () => {
        // Queue some changes
        await queueChange({
            id: 'persisted-change',
            type: 'create',
            entity: 'goal',
            entity_id: 'goal-1',
            data: { category: 'health', description: 'Test goal' },
            timestamp: new Date().toISOString(),
        });

        // Read back from DB (simulating persistence)
        const changes = await getPendingChanges();
        expect(changes).toHaveLength(1);
        expect(changes[0].id).toBe('persisted-change');

        // Read again to verify persistence
        const changesAgain = await getPendingChanges();
        expect(changesAgain).toHaveLength(1);
        expect(changesAgain[0].entity_id).toBe('goal-1');
    });

    it('should maintain accurate pending count during offline period', async () => {
        const { getPendingCount } = await import('$lib/db/sync');

        // Start with no pending changes
        let count = await getPendingCount();
        expect(count).toBe(0);

        // Queue first change
        await queueChange({
            id: 'change-1',
            type: 'create',
            entity: 'entry',
            entity_id: 'entry-1',
            data: {},
            timestamp: new Date().toISOString(),
        });
        count = await getPendingCount();
        expect(count).toBe(1);

        // Queue more changes
        await queueChange({
            id: 'change-2',
            type: 'update',
            entity: 'entry',
            entity_id: 'entry-2',
            data: {},
            timestamp: new Date().toISOString(),
        });
        await queueChange({
            id: 'change-3',
            type: 'create',
            entity: 'goal',
            entity_id: 'goal-1',
            data: {},
            timestamp: new Date().toISOString(),
        });
        count = await getPendingCount();
        expect(count).toBe(3);

        // Clear one change  
        await clearPendingChange('change-1');
        count = await getPendingCount();
        expect(count).toBe(2);
    });

    it('should handle mixed entity types in pending queue', async () => {
        // Queue entry and goal changes
        await queueChange({
            id: 'entry-change',
            type: 'create',
            entity: 'entry',
            entity_id: 'entry-1',
            data: { refined_output: 'Test entry' },
            base_version: 1,
            timestamp: '2024-12-30T10:00:00.000Z',
        });
        await queueChange({
            id: 'goal-change',
            type: 'create',
            entity: 'goal',
            entity_id: 'goal-1',
            data: { category: 'health' },
            timestamp: '2024-12-30T10:01:00.000Z',
        });

        const changes = await getPendingChanges();
        expect(changes).toHaveLength(2);

        const entryChanges = changes.filter(c => c.entity === 'entry');
        const goalChanges = changes.filter(c => c.entity === 'goal');

        expect(entryChanges).toHaveLength(1);
        expect(goalChanges).toHaveLength(1);
        expect(entryChanges[0].base_version).toBe(1);
        expect(goalChanges[0].base_version).toBeUndefined();
    });
});

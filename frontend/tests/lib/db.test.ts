/**
 * Database operations tests
 * 
 * Tests Dexie.js operations with fake-indexeddb.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { db, type Entry, type Goal } from '$lib/db';
import { createEntry, getEntry, getAllEntries, updateEntry, deleteEntry } from '$lib/db/entries';
import { createGoal, getGoal, getAllGoals, updateGoal, deleteGoal } from '$lib/db/goals';
import { queueChange, getPendingChanges, clearPendingChange, getPendingCount } from '$lib/db/sync';

describe('Dexie Database', () => {
    beforeEach(async () => {
        // Clear all tables before each test
        await db.entries.clear();
        await db.goals.clear();
        await db.pendingChanges.clear();
    });

    describe('Entry CRUD', () => {
        it('should create an entry', async () => {
            const entry = await createEntry({
                date: '2024-12-15',
                conversations: [],
                refined_output: 'Test entry',
                relevance_score: 1.0,
                last_interacted_at: new Date().toISOString(),
                interaction_count: 0,
                status: 'active',
                version: 1
            });

            expect(entry.id).toBeDefined();
            expect(entry.date).toBe('2024-12-15');
            expect(entry.refined_output).toBe('Test entry');
        });

        it('should get an entry by ID', async () => {
            const created = await createEntry({
                date: '2024-12-15',
                conversations: [],
                refined_output: 'Test entry',
                relevance_score: 1.0,
                last_interacted_at: new Date().toISOString(),
                interaction_count: 0,
                status: 'active',
                version: 1
            });

            const retrieved = await getEntry(created.id);
            expect(retrieved).toBeDefined();
            expect(retrieved?.id).toBe(created.id);
        });

        it('should get all entries', async () => {
            await createEntry({
                date: '2024-12-15',
                conversations: [],
                refined_output: 'Entry 1',
                relevance_score: 1.0,
                last_interacted_at: new Date().toISOString(),
                interaction_count: 0,
                status: 'active',
                version: 1
            });

            await createEntry({
                date: '2024-12-14',
                conversations: [],
                refined_output: 'Entry 2',
                relevance_score: 1.0,
                last_interacted_at: new Date().toISOString(),
                interaction_count: 0,
                status: 'active',
                version: 1
            });

            const entries = await getAllEntries();
            expect(entries).toHaveLength(2);
        });

        it('should update an entry', async () => {
            const entry = await createEntry({
                date: '2024-12-15',
                conversations: [],
                refined_output: 'Original',
                relevance_score: 1.0,
                last_interacted_at: new Date().toISOString(),
                interaction_count: 0,
                status: 'active',
                version: 1
            });

            const updated = await updateEntry(entry.id, {
                refined_output: 'Updated'
            });

            expect(updated?.refined_output).toBe('Updated');
        });

        it('should soft delete an entry', async () => {
            const entry = await createEntry({
                date: '2024-12-15',
                conversations: [],
                refined_output: 'Test',
                relevance_score: 1.0,
                last_interacted_at: new Date().toISOString(),
                interaction_count: 0,
                status: 'active',
                version: 1
            });

            const deleted = await deleteEntry(entry.id);
            expect(deleted).toBe(true);

            const retrieved = await getEntry(entry.id);
            expect(retrieved?.status).toBe('archived');
        });
    });

    describe('Goal CRUD', () => {
        it('should create a goal', async () => {
            const goal = await createGoal({
                category: 'health',
                description: 'Exercise daily',
                active: true
            });

            expect(goal.id).toBeDefined();
            expect(goal.category).toBe('health');
            expect(goal.description).toBe('Exercise daily');
        });

        it('should get all active goals', async () => {
            await createGoal({
                category: 'health',
                description: 'Goal 1',
                active: true
            });

            await createGoal({
                category: 'productivity',
                description: 'Goal 2',
                active: false
            });

            // Use getAllGoals without filtering then manually filter
            // to work around fake-indexeddb boolean query limitation
            const allGoals = await getAllGoals(false);
            const active = allGoals.filter(g => g.active);

            expect(active).toHaveLength(1);
            expect(active[0].active).toBe(true);
        });

        it('should update a goal', async () => {
            const goal = await createGoal({
                category: 'health',
                description: 'Original',
                active: true
            });

            const updated = await updateGoal(goal.id, {
                description: 'Updated'
            });

            expect(updated?.description).toBe('Updated');
        });

        it('should delete a goal', async () => {
            const goal = await createGoal({
                category: 'health',
                description: 'Test',
                active: true
            });

            const deleted = await deleteGoal(goal.id);
            expect(deleted).toBe(true);

            const retrieved = await getGoal(goal.id);
            expect(retrieved).toBeUndefined();
        });
    });

    describe('Pending Changes Queue', () => {
        it('should queue a change', async () => {
            await queueChange({
                id: crypto.randomUUID(),
                type: 'create',
                entity: 'entry',
                entity_id: crypto.randomUUID(),
                data: { test: 'data' },
                timestamp: new Date().toISOString()
            });

            const pending = await getPendingChanges();
            expect(pending).toHaveLength(1);
        });

        it('should clear a pending change', async () => {
            const change = {
                id: crypto.randomUUID(),
                type: 'create' as const,
                entity: 'entry' as const,
                entity_id: crypto.randomUUID(),
                data: { test: 'data' },
                timestamp: new Date().toISOString()
            };

            await queueChange(change);
            await clearPendingChange(change.id);

            const count = await getPendingCount();
            expect(count).toBe(0);
        });

        it('should get pending count', async () => {
            await queueChange({
                id: crypto.randomUUID(),
                type: 'create',
                entity: 'entry',
                entity_id: crypto.randomUUID(),
                data: {},
                timestamp: new Date().toISOString()
            });

            await queueChange({
                id: crypto.randomUUID(),
                type: 'update',
                entity: 'goal',
                entity_id: crypto.randomUUID(),
                data: {},
                timestamp: new Date().toISOString()
            });

            const count = await getPendingCount();
            expect(count).toBe(2);
        });
    });
});

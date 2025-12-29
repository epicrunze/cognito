/**
 * Goal CRUD operations for IndexedDB
 */

import { db, type Goal } from './index';
import { queueChange } from './sync';

/**
 * Create a new goal
 */
export async function createGoal(goal: Omit<Goal, 'id' | 'created_at' | 'updated_at'>): Promise<Goal> {
    const now = new Date().toISOString();
    const newGoal: Goal = {
        ...goal,
        id: crypto.randomUUID(),
        created_at: now,
        updated_at: now
    };

    await db.goals.add(newGoal);
    await queueChange({
        id: crypto.randomUUID(),
        type: 'create',
        entity: 'goal',
        entity_id: newGoal.id,
        data: newGoal,
        timestamp: now
    });

    return newGoal;
}

/**
 * Get goal by ID
 */
export async function getGoal(id: string): Promise<Goal | undefined> {
    return await db.goals.get(id);
}

/**
 * Get all goals with optional filtering
 */
export async function getAllGoals(activeOnly = false): Promise<Goal[]> {
    if (activeOnly) {
        // Dexie indexes booleans as 1/0
        return await db.goals.filter((g) => g.active === true).toArray();
    }
    return await db.goals.toArray();
}

/**
 * Update an existing goal
 */
export async function updateGoal(
    id: string,
    data: Partial<Omit<Goal, 'id' | 'created_at'>>
): Promise<Goal | undefined> {
    const existing = await db.goals.get(id);
    if (!existing) return undefined;

    const updated: Goal = {
        ...existing,
        ...data,
        updated_at: new Date().toISOString()
    };

    await db.goals.put(updated);
    await queueChange({
        id: crypto.randomUUID(),
        type: 'update',
        entity: 'goal',
        entity_id: id,
        data: updated,
        timestamp: updated.updated_at
    });

    return updated;
}

/**
 * Delete a goal
 */
export async function deleteGoal(id: string): Promise<boolean> {
    const goal = await db.goals.get(id);
    if (!goal) return false;

    await db.goals.delete(id);
    await queueChange({
        id: crypto.randomUUID(),
        type: 'delete',
        entity: 'goal',
        entity_id: id,
        data: null,
        timestamp: new Date().toISOString()
    });

    return true;
}

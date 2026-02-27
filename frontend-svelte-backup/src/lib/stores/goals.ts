/**
 * Goals store
 *
 * Manages goals state with reactive updates.
 */

import { writable, derived } from 'svelte/store';
import type { Goal } from '$lib/api/goals';
import {
    getGoals as getGoalsApi,
    createGoal as createGoalApi,
    updateGoal as updateGoalApi,
    deleteGoal as deleteGoalApi,
    type GoalCreate,
    type GoalUpdate
} from '$lib/api/goals';
import { getAllGoals as getAllGoalsLocal, createGoal as createGoalLocal, updateGoal as updateGoalLocal, deleteGoal as deleteGoalLocal } from '$lib/db/goals';
import { isOnline } from '$lib/api/client';

// Goals list
export const goals = writable<Goal[]>([]);

// Loading state
export const goalsLoading = writable<boolean>(false);

// Error state
export const goalsError = writable<string | null>(null);

// Active goals (filtered)
export const activeGoals = derived(goals, ($goals) => $goals.filter((g) => g.active));

// Inactive goals (filtered)
export const inactiveGoals = derived(goals, ($goals) => $goals.filter((g) => !g.active));

// Goals grouped by category
export const goalsByCategory = derived(goals, ($goals) => {
    const grouped: Record<string, Goal[]> = {};
    for (const goal of $goals) {
        if (!grouped[goal.category]) {
            grouped[goal.category] = [];
        }
        grouped[goal.category].push(goal);
    }
    return grouped;
});

/**
 * Load goals from IndexedDB (offline-first)
 */
export async function loadGoals(): Promise<void> {
    goalsLoading.set(true);
    goalsError.set(null);

    try {
        // Try local first
        const localGoals = await getAllGoalsLocal();
        if (localGoals.length > 0) {
            goals.set(localGoals);
        }

        // If online, sync with server
        if (isOnline()) {
            const response = await getGoalsApi();
            goals.set(response.goals);

            // Update local storage
            // TODO: Implement bulk sync
        }
    } catch (error: any) {
        console.error('Failed to load goals:', error);
        goalsError.set(error?.message || 'Failed to load goals');
    } finally {
        goalsLoading.set(false);
    }
}

/**
 * Refresh goals from server
 */
export async function refreshGoals(): Promise<void> {
    if (!isOnline()) {
        goalsError.set('Cannot refresh while offline');
        return;
    }

    goalsLoading.set(true);
    goalsError.set(null);

    try {
        const response = await getGoalsApi();
        goals.set(response.goals);
    } catch (error: any) {
        console.error('Failed to refresh goals:', error);
        goalsError.set(error?.message || 'Failed to refresh goals');
    } finally {
        goalsLoading.set(false);
    }
}

/**
 * Create a new goal
 */
export async function createGoal(data: GoalCreate): Promise<Goal | null> {
    goalsError.set(null);

    try {
        if (isOnline()) {
            const newGoal = await createGoalApi(data);
            goals.update((g) => [...g, newGoal]);
            return newGoal;
        } else {
            // Create locally
            const localGoal = await createGoalLocal({ ...data, active: true });
            goals.update((g) => [...g, localGoal]);
            return localGoal;
        }
    } catch (error: any) {
        console.error('Failed to create goal:', error);
        goalsError.set(error?.message || 'Failed to create goal');
        return null;
    }
}

/**
 * Update an existing goal
 */
export async function updateGoal(id: string, data: GoalUpdate): Promise<Goal | null> {
    goalsError.set(null);

    try {
        if (isOnline()) {
            const updatedGoal = await updateGoalApi(id, data);
            goals.update((g) => g.map((goal) => (goal.id === id ? updatedGoal : goal)));
            return updatedGoal;
        } else {
            // Update locally
            const localGoal = await updateGoalLocal(id, data);
            if (localGoal) {
                goals.update((g) => g.map((goal) => (goal.id === id ? localGoal : goal)));
            }
            return localGoal || null;
        }
    } catch (error: any) {
        console.error('Failed to update goal:', error);
        goalsError.set(error?.message || 'Failed to update goal');
        return null;
    }
}

/**
 * Delete a goal (soft delete)
 */
export async function deleteGoal(id: string): Promise<boolean> {
    goalsError.set(null);

    try {
        if (isOnline()) {
            await deleteGoalApi(id);
        } else {
            await deleteGoalLocal(id);
        }

        // Update local state (soft delete sets active=false)
        goals.update((g) => g.map((goal) => (goal.id === id ? { ...goal, active: false } : goal)));
        return true;
    } catch (error: any) {
        console.error('Failed to delete goal:', error);
        goalsError.set(error?.message || 'Failed to delete goal');
        return false;
    }
}

/**
 * Toggle goal active status
 */
export async function toggleGoalActive(id: string): Promise<boolean> {
    const currentGoals = await new Promise<Goal[]>((resolve) => {
        const unsubscribe = goals.subscribe((g) => {
            resolve(g);
            unsubscribe();
        });
    });

    const goal = currentGoals.find((g) => g.id === id);
    if (!goal) return false;

    const updated = await updateGoal(id, { active: !goal.active });
    return updated !== null;
}

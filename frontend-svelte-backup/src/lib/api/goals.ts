/**
 * Goals API client
 *
 * Handles communication with goals endpoints.
 */

import { api } from './client';

export interface Goal {
    id: string;
    category: string;
    description: string;
    active: boolean;
    created_at: string;
    updated_at: string;
}

export interface GoalCreate {
    category: string;
    description: string;
}

export interface GoalUpdate {
    category?: string;
    description?: string;
    active?: boolean;
}

export interface GoalsResponse {
    goals: Goal[];
}

/**
 * Get all goals with optional filtering.
 */
export async function getGoals(active?: boolean): Promise<GoalsResponse> {
    const params = active !== undefined ? `?active=${active}` : '';
    return api.get<GoalsResponse>(`/goals${params}`);
}

/**
 * Get a single goal by ID.
 */
export async function getGoal(id: string): Promise<Goal> {
    return api.get<Goal>(`/goals/${id}`);
}

/**
 * Create a new goal.
 */
export async function createGoal(data: GoalCreate): Promise<Goal> {
    return api.post<Goal>('/goals', data);
}

/**
 * Update an existing goal.
 */
export async function updateGoal(id: string, data: GoalUpdate): Promise<Goal> {
    return api.put<Goal>(`/goals/${id}`, data);
}

/**
 * Delete a goal (soft delete - sets active=false).
 */
export async function deleteGoal(id: string): Promise<{ success: boolean }> {
    return api.delete<{ success: boolean }>(`/goals/${id}`);
}

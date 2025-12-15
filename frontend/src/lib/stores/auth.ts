/**
 * Authentication store
 * 
 * Manages user authentication state.
 */

import { writable, derived } from 'svelte/store';
import type { User } from '$lib/api/auth';
import { getMe } from '$lib/api/auth';

// User state
export const user = writable<User | null>(null);

// Derived authenticated state
export const isAuthenticated = derived(user, $user => $user !== null);

// Loading state for auth check
export const authLoading = writable(true);

/**
 * Check authentication status
 */
export async function checkAuth(): Promise<void> {
    authLoading.set(true);
    try {
        // Add timeout for backend check (3 seconds)
        const timeoutPromise = new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error('Auth check timeout')), 3000)
        );

        const currentUser = await Promise.race([getMe(), timeoutPromise]);
        user.set(currentUser);
    } catch (error) {
        console.error('Auth check failed:', error);
        console.log('💡 Tip: Start the backend or you can develop with mock data');
        user.set(null);
    } finally {
        authLoading.set(false);
    }
}

/**
 * Clear user session (called after logout)
 */
export function clearAuth(): void {
    user.set(null);
}

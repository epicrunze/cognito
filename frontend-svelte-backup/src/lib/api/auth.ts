/**
 * Authentication API module
 * 
 * Handles Google OAuth flow and user session management.
 */

import { api, type ApiError } from './client';

export interface User {
    email: string;
    name: string;
    picture: string;
}

/**
 * Redirect to Google OAuth login
 */
export function login(): void {
    const apiUrl = import.meta.env.VITE_PUBLIC_API_URL || 'http://localhost:8000/api';
    window.location.href = `${apiUrl}/auth/login`;
}

/**
 * Logout current user
 */
export async function logout(): Promise<{ success: boolean }> {
    try {
        return await api.post('/auth/logout');
    } catch (error) {
        console.error('Logout failed:', error);
        throw error;
    }
}

/**
 * Get current authenticated user
 */
export async function getMe(): Promise<User | null> {
    try {
        return await api.get<User>('/auth/me');
    } catch (error) {
        const apiError = error as ApiError;
        // If 401/403, user is not authenticated
        if (apiError.status === 401 || apiError.status === 403) {
            return null;
        }
        throw error;
    }
}

/**
 * Silent token refresh - calls backend /auth/refresh to get new JWT
 * 
 * @returns true if refresh successful, false otherwise
 */
export async function refreshToken(): Promise<boolean> {
    try {
        await api.post('/auth/refresh');
        return true;
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    }
}

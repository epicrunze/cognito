/**
 * Base API client with offline detection, request queuing, and automatic token refresh
 */

// API base URL from environment variable
const API_URL = import.meta.env.VITE_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface ApiError {
    message: string;
    status?: number;
}

/**
 * Check if online
 */
export function isOnline(): boolean {
    return navigator.onLine;
}

// Track if a refresh is in progress to prevent multiple simultaneous refreshes
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt to refresh the authentication token
 * Prevents multiple simultaneous refresh attempts
 */
async function attemptTokenRefresh(): Promise<boolean> {
    if (isRefreshing && refreshPromise) {
        return refreshPromise;
    }

    isRefreshing = true;
    refreshPromise = (async () => {
        try {
            const response = await fetch(`${API_URL}/auth/refresh`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            });
            return response.ok;
        } catch {
            return false;
        } finally {
            isRefreshing = false;
            refreshPromise = null;
        }
    })();

    return refreshPromise;
}

/**
 * Base fetch wrapper with credentials, error handling, and 401 retry
 */
export async function apiClient<T>(
    endpoint: string,
    options?: RequestInit,
    isRetry = false
): Promise<T> {
    if (!isOnline()) {
        throw {
            message: 'You are offline. Changes will be saved locally and synced when back online.',
            status: 0
        } as ApiError;
    }

    const url = `${API_URL}${endpoint}`;
    const response = await fetch(url, {
        ...options,
        credentials: 'include', // Include cookies for JWT
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers
        }
    });

    // Handle 401 - attempt refresh and retry once
    if (response.status === 401 && !isRetry && !endpoint.includes('/auth/')) {
        console.log('🔄 Token expired, attempting refresh...');
        const refreshed = await attemptTokenRefresh();

        if (refreshed) {
            console.log('✅ Token refreshed, retrying request');
            return apiClient<T>(endpoint, options, true);
        } else {
            console.log('❌ Token refresh failed');
        }
    }

    if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

        try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.detail || errorJson.message || errorMessage;
        } catch {
            // If not JSON, use text
            errorMessage = errorText || errorMessage;
        }

        throw {
            message: errorMessage,
            status: response.status
        } as ApiError;
    }

    // Handle empty responses (e.g., 204 No Content)
    const contentLength = response.headers.get('content-length');
    if (contentLength === '0') {
        return {} as T;
    }

    return await response.json();
}

/**
 * Helper methods
 */
export const api = {
    get: <T>(endpoint: string) => apiClient<T>(endpoint, { method: 'GET' }),

    post: <T>(endpoint: string, body?: any) =>
        apiClient<T>(endpoint, {
            method: 'POST',
            body: body ? JSON.stringify(body) : undefined
        }),

    put: <T>(endpoint: string, body?: any) =>
        apiClient<T>(endpoint, {
            method: 'PUT',
            body: body ? JSON.stringify(body) : undefined
        }),

    delete: <T>(endpoint: string) => apiClient<T>(endpoint, { method: 'DELETE' })
};

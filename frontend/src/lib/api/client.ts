/**
 * Base API client with offline detection and request queuing
 */

// API base URL from environment variable
const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000/api';

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

/**
 * Base fetch wrapper with credentials and error handling
 */
export async function apiClient<T>(
endpoint: string,
options?: RequestInit
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

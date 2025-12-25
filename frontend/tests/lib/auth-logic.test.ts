/**
 * Authentication logic tests
 * 
 * Tests auth flow logic without component rendering.
 */

import { describe, it, expect } from 'vitest';

// Auth error handling logic
function getAuthErrorMessage(errorParam: string | null, errorDescription?: string | null): string | null {
    if (!errorParam) return null;

    if (errorParam === 'access_denied') {
        return 'You cancelled the login process. Please try again.';
    } else if (errorParam === 'not_authorized') {
        return 'Your email is not authorized to access this application.';
    } else {
        return errorDescription || 'Authentication failed. Please try again.';
    }
}

// OAuth callback state parsing
function parseCallbackState(searchParams: URLSearchParams): {
    error: string | null;
    errorDescription: string | null;
    hasError: boolean;
} {
    const error = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    return {
        error,
        errorDescription,
        hasError: error !== null
    };
}

describe('Authentication Logic', () => {
    describe('getAuthErrorMessage', () => {
        it('should return null for no error', () => {
            expect(getAuthErrorMessage(null)).toBeNull();
        });

        it('should handle access_denied error', () => {
            const message = getAuthErrorMessage('access_denied');
            expect(message).toBe('You cancelled the login process. Please try again.');
        });

        it('should handle not_authorized error', () => {
            const message = getAuthErrorMessage('not_authorized');
            expect(message).toBe('Your email is not authorized to access this application.');
        });

        it('should use error description for unknown errors', () => {
            const message = getAuthErrorMessage('unknown_error', 'Custom error description');
            expect(message).toBe('Custom error description');
        });

        it('should use generic message if no description provided', () => {
            const message = getAuthErrorMessage('unknown_error');
            expect(message).toBe('Authentication failed. Please try again.');
        });
    });

    describe('parseCallbackState', () => {
        it('should parse error from URL params', () => {
            const params = new URLSearchParams('error=access_denied');
            const state = parseCallbackState(params);

            expect(state.error).toBe('access_denied');
            expect(state.hasError).toBe(true);
        });

        it('should parse error description', () => {
            const params = new URLSearchParams('error=server_error&error_description=Internal+error');
            const state = parseCallbackState(params);

            expect(state.error).toBe('server_error');
            expect(state.errorDescription).toBe('Internal error');
            expect(state.hasError).toBe(true);
        });

        it('should handle success state with no errors', () => {
            const params = new URLSearchParams('code=abc123');
            const state = parseCallbackState(params);

            expect(state.error).toBeNull();
            expect(state.errorDescription).toBeNull();
            expect(state.hasError).toBe(false);
        });

        it('should handle empty params', () => {
            const params = new URLSearchParams('');
            const state = parseCallbackState(params);

            expect(state.error).toBeNull();
            expect(state.hasError).toBe(false);
        });
    });
});

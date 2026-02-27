/**
 * Authentication Context and Hook
 * 
 * Provides authentication state management with offline support.
 * Uses cache-first, stale-while-revalidate pattern.
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { getMe, refreshToken, logout as apiLogout, type User } from '../api/auth';
import {
    cacheAuthProfile,
    getCachedAuthProfile,
    clearCachedAuth,
    isAuthCacheStale,
    isAuthCacheExpired,
    needsProactiveRefresh,
} from '../db/sync';

export type AuthSource = 'verified' | 'cached' | 'stale' | null;

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    authSource: AuthSource;
    checkAuth: () => Promise<void>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Calculate JWT expiry time (7 days from now)
function calculateJwtExpiry(): string {
    const expiry = new Date();
    expiry.setDate(expiry.getDate() + 7);
    return expiry.toISOString();
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [authSource, setAuthSource] = useState<AuthSource>(null);

    const checkAuth = useCallback(async () => {
        setIsLoading(true);
        try {
            // 1. Always check cache first (instant response)
            const cached = await getCachedAuthProfile();

            // 2. If offline: use cache regardless of staleness
            if (!navigator.onLine) {
                if (cached) {
                    setUser(cached);
                    setAuthSource('stale');
                } else {
                    setUser(null);
                    setAuthSource(null);
                }
                return;
            }

            // 3. Proactive refresh: if JWT expires within 1 day, refresh silently
            if (cached && await needsProactiveRefresh()) {
                console.log('🔄 JWT expires soon, proactively refreshing...');
                const refreshed = await refreshToken();
                if (refreshed) {
                    console.log('✅ Proactive token refresh successful');
                    await cacheAuthProfile(cached, calculateJwtExpiry());
                    setUser(cached);
                    setAuthSource('verified');
                    return;
                }
                console.log('⚠️ Proactive refresh failed, continuing with normal auth check');
            }

            // 4. If we have fresh cache: use it, skip network
            if (cached && !(await isAuthCacheStale())) {
                setUser(cached);
                setAuthSource('cached');
                return;
            }

            // 5. Cache missing or stale: verify with backend
            try {
                const timeoutPromise = new Promise<never>((_, reject) =>
                    setTimeout(() => reject(new Error('Auth check timeout')), 3000)
                );
                const currentUser = await Promise.race([getMe(), timeoutPromise]);

                if (currentUser) {
                    await cacheAuthProfile(currentUser, calculateJwtExpiry());
                    setUser(currentUser);
                    setAuthSource('verified');
                } else {
                    setUser(null);
                    setAuthSource(null);
                }
            } catch (error) {
                // 6. Backend failed: fall back to cache if not expired
                console.error('Auth check failed:', error);
                if (cached && !(await isAuthCacheExpired())) {
                    console.log('💡 Using cached credentials (backend unreachable)');
                    setUser(cached);
                    setAuthSource('stale');
                } else {
                    setUser(null);
                    setAuthSource(null);
                }
            }
        } finally {
            setIsLoading(false);
        }
    }, []);

    const logout = useCallback(async () => {
        try {
            await apiLogout();
        } catch (error) {
            console.error('Logout API call failed:', error);
        }
        setUser(null);
        setAuthSource(null);
        await clearCachedAuth();
    }, []);

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated: user !== null,
                isLoading,
                authSource,
                checkAuth,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

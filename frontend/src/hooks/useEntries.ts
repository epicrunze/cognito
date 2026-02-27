/**
 * Entries Hook
 * 
 * Provides entries state management with local IndexedDB storage.
 */

import { useState, useEffect, useCallback } from 'react';
import type { Entry } from '../db';
import { getAllEntries } from '../db/entries';

interface UseEntriesOptions {
    status?: 'active' | 'archived';
}

interface UseEntriesResult {
    entries: Entry[];
    activeEntries: Entry[];
    archivedEntries: Entry[];
    isLoading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
}

export function useEntries(options?: UseEntriesOptions): UseEntriesResult {
    const [entries, setEntries] = useState<Entry[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadEntries = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const loadedEntries = await getAllEntries({ status: options?.status });
            setEntries(loadedEntries);
        } catch (err) {
            console.error('Failed to load entries:', err);
            setError('Failed to load entries');
            setEntries([]);
        } finally {
            setIsLoading(false);
        }
    }, [options?.status]);

    useEffect(() => {
        loadEntries();
    }, [loadEntries]);

    const activeEntries = entries.filter((e) => e.status === 'active');
    const archivedEntries = entries.filter((e) => e.status === 'archived');

    return {
        entries,
        activeEntries,
        archivedEntries,
        isLoading,
        error,
        refresh: loadEntries,
    };
}

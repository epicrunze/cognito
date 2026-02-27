/**
 * Timestamp utilities for consistent UTC handling.
 *
 * Provides centralized timestamp functions to ensure consistent timezone handling
 * across all frontend modules. All timestamps are stored and transmitted as UTC.
 */

/**
 * Get current time as ISO 8601 UTC string.
 * Format: "2024-12-30T12:00:00.000Z"
 */
export function utcNow(): string {
    return new Date().toISOString();
}

/**
 * Parse an ISO 8601 timestamp string to a Date object.
 *
 * @param ts - ISO 8601 timestamp string (e.g., "2024-12-30T12:00:00.000Z")
 * @returns Date object
 * @throws Error if the timestamp is invalid
 */
export function parseTimestamp(ts: string): Date {
    const date = new Date(ts);
    if (isNaN(date.getTime())) {
        throw new Error(`Invalid timestamp: ${ts}`);
    }
    return date;
}

/**
 * Format a UTC timestamp for display in the user's local timezone.
 *
 * @param ts - ISO 8601 UTC timestamp string
 * @param options - Intl.DateTimeFormat options (defaults to short date and time)
 * @returns Formatted string in user's local timezone
 */
export function formatLocal(
    ts: string,
    options?: Intl.DateTimeFormatOptions
): string {
    const date = parseTimestamp(ts);
    const defaultOptions: Intl.DateTimeFormatOptions = {
        dateStyle: 'short',
        timeStyle: 'short',
    };
    return date.toLocaleString(undefined, options || defaultOptions);
}

/**
 * Format a UTC timestamp as relative time ("Just now", "5m ago", "2h ago", "3d ago").
 *
 * @param ts - ISO 8601 UTC timestamp string
 * @returns Relative time string
 */
export function formatRelative(ts: string | null): string {
    if (!ts) return 'Never';

    const date = parseTimestamp(ts);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

/**
 * Compare two ISO 8601 timestamps.
 *
 * @param ts1 - First timestamp
 * @param ts2 - Second timestamp
 * @returns Negative if ts1 < ts2, positive if ts1 > ts2, 0 if equal
 */
export function compareTimestamps(ts1: string, ts2: string): number {
    const date1 = parseTimestamp(ts1);
    const date2 = parseTimestamp(ts2);
    return date1.getTime() - date2.getTime();
}

/**
 * Check if timestamp1 is newer than or equal to timestamp2.
 *
 * @param ts1 - First timestamp
 * @param ts2 - Second timestamp
 * @returns true if ts1 >= ts2
 */
export function isNewerOrEqual(ts1: string, ts2: string): boolean {
    return compareTimestamps(ts1, ts2) >= 0;
}

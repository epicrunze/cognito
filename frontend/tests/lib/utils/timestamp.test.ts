/**
 * Tests for timestamp utilities.
 *
 * Verifies UTC timestamp handling, parsing, formatting, and comparison functions.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    utcNow,
    parseTimestamp,
    formatLocal,
    formatRelative,
    compareTimestamps,
    isNewerOrEqual,
} from '$lib/utils/timestamp';

describe('utcNow', () => {
    it('should return ISO 8601 formatted string', () => {
        const result = utcNow();
        // Should match ISO 8601 format with Z suffix
        expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });

    it('should return current time', () => {
        const before = new Date().getTime();
        const result = utcNow();
        const after = new Date().getTime();

        const resultTime = new Date(result).getTime();
        expect(resultTime).toBeGreaterThanOrEqual(before);
        expect(resultTime).toBeLessThanOrEqual(after);
    });
});

describe('parseTimestamp', () => {
    it('should parse valid ISO 8601 timestamp', () => {
        const ts = '2024-12-30T12:00:00.000Z';
        const date = parseTimestamp(ts);

        expect(date.getUTCFullYear()).toBe(2024);
        expect(date.getUTCMonth()).toBe(11); // December is 11
        expect(date.getUTCDate()).toBe(30);
        expect(date.getUTCHours()).toBe(12);
    });

    it('should parse timestamp with offset', () => {
        const ts = '2024-12-30T12:00:00-05:00';
        const date = parseTimestamp(ts);

        // 12:00 EST = 17:00 UTC
        expect(date.getUTCHours()).toBe(17);
    });

    it('should throw error for invalid timestamp', () => {
        expect(() => parseTimestamp('invalid')).toThrow('Invalid timestamp');
        expect(() => parseTimestamp('')).toThrow('Invalid timestamp');
    });
});

describe('formatLocal', () => {
    it('should format timestamp for local display', () => {
        const ts = '2024-12-30T12:00:00.000Z';
        const result = formatLocal(ts);

        // Should be a non-empty string (actual format depends on locale)
        expect(result).toBeTruthy();
        expect(typeof result).toBe('string');
    });

    it('should accept custom format options', () => {
        const ts = '2024-12-30T12:00:00.000Z';
        const result = formatLocal(ts, { weekday: 'long' });

        // Should contain a weekday name
        expect(result).toBeTruthy();
    });
});

describe('formatRelative', () => {
    beforeEach(() => {
        // Mock Date.now to ensure consistent tests
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-12-30T12:00:00.000Z'));
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('should return "Never" for null', () => {
        expect(formatRelative(null)).toBe('Never');
    });

    it('should return "Just now" for recent timestamp', () => {
        const ts = '2024-12-30T11:59:30.000Z'; // 30 seconds ago
        expect(formatRelative(ts)).toBe('Just now');
    });

    it('should return minutes ago', () => {
        const ts = '2024-12-30T11:55:00.000Z'; // 5 minutes ago
        expect(formatRelative(ts)).toBe('5m ago');
    });

    it('should return hours ago', () => {
        const ts = '2024-12-30T10:00:00.000Z'; // 2 hours ago
        expect(formatRelative(ts)).toBe('2h ago');
    });

    it('should return days ago', () => {
        const ts = '2024-12-28T12:00:00.000Z'; // 2 days ago
        expect(formatRelative(ts)).toBe('2d ago');
    });
});

describe('compareTimestamps', () => {
    it('should return negative when first is older', () => {
        const older = '2024-12-29T12:00:00.000Z';
        const newer = '2024-12-30T12:00:00.000Z';
        expect(compareTimestamps(older, newer)).toBeLessThan(0);
    });

    it('should return positive when first is newer', () => {
        const newer = '2024-12-30T12:00:00.000Z';
        const older = '2024-12-29T12:00:00.000Z';
        expect(compareTimestamps(newer, older)).toBeGreaterThan(0);
    });

    it('should return zero for equal timestamps', () => {
        const ts = '2024-12-30T12:00:00.000Z';
        expect(compareTimestamps(ts, ts)).toBe(0);
    });
});

describe('isNewerOrEqual', () => {
    it('should return true when first is newer', () => {
        const newer = '2024-12-30T12:00:00.000Z';
        const older = '2024-12-29T12:00:00.000Z';
        expect(isNewerOrEqual(newer, older)).toBe(true);
    });

    it('should return true when equal', () => {
        const ts = '2024-12-30T12:00:00.000Z';
        expect(isNewerOrEqual(ts, ts)).toBe(true);
    });

    it('should return false when first is older', () => {
        const older = '2024-12-29T12:00:00.000Z';
        const newer = '2024-12-30T12:00:00.000Z';
        expect(isNewerOrEqual(older, newer)).toBe(false);
    });
});

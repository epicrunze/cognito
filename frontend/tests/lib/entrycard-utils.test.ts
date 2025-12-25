/**
 * EntryCard utility functions tests
 * 
 * Tests date formatting, text truncation, and other utility functions
 * without requiring component mounting.
 */

import { describe, it, expect } from 'vitest';

// Utility functions extracted for testing
function formatDate(dateStr: string): string {
	// Parse as local date, not UTC
	const [year, month, day] = dateStr.split('-').map(Number);
	const date = new Date(year, month - 1, day);

	const today = new Date();
	const yesterday = new Date(today);
	yesterday.setDate(yesterday.getDate() - 1);

	// Reset time for comparison
	const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
	const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());
	const yesterdayOnly = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate());

	if (dateOnly.getTime() === todayOnly.getTime()) {
		return 'Today';
	} else if (dateOnly.getTime() === yesterdayOnly.getTime()) {
		return 'Yesterday';
	} else {
		return date.toLocaleDateString('en-US', {
			month: 'long',
			day: 'numeric',
			year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
		});
	}
}

function formatRelativeTime(timestamp: string): string {
	const date = new Date(timestamp);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / 60000);
	const diffHours = Math.floor(diffMins / 60);
	const diffDays = Math.floor(diffHours / 24);

	if (diffMins < 1) return 'just now';
	if (diffMins < 60) return `${diffMins}m ago`;
	if (diffHours < 24) return `${diffHours}h ago`;
	if (diffDays < 7) return `${diffDays}d ago`;
	return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function truncate(text: string, maxLength: number): string {
	if (text.length <= maxLength) return text;
	return text.substring(0, maxLength).trim() + '...';
}

function getRelevanceColor(score: number): string {
	if (score >= 0.8) return 'bg-success';
	if (score >= 0.5) return 'bg-warning';
	return 'bg-text-secondary';
}

describe('EntryCard Utilities', () => {
	describe('formatDate', () => {
		it('should format today as "Today"', () => {
			const today = new Date();
			const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
			expect(formatDate(dateStr)).toBe('Today');
		});

		it('should format yesterday as "Yesterday"', () => {
			const yesterday = new Date();
			yesterday.setDate(yesterday.getDate() - 1);
			const dateStr = `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`;
			expect(formatDate(dateStr)).toBe('Yesterday');
		});

		it('should format past dates with month and day', () => {
			const result = formatDate('2024-12-24');
			expect(result).toContain('December');
			expect(result).toContain('24');
		});

		it('should include year for dates from previous years', () => {
			const result = formatDate('2023-01-15');
			expect(result).toContain('2023');
		});
	});

	describe('formatRelativeTime', () => {
		it('should return "just now" for very recent timestamps', () => {
			const now = new Date().toISOString();
			expect(formatRelativeTime(now)).toBe('just now');
		});

		it('should return minutes for recent timestamps', () => {
			const fiveMinutesAgo = new Date(Date.now() - 5 * 60000).toISOString();
			expect(formatRelativeTime(fiveMinutesAgo)).toBe('5m ago');
		});

		it('should return hours for timestamps within last day', () => {
			const threeHoursAgo = new Date(Date.now() - 3 * 3600000).toISOString();
			expect(formatRelativeTime(threeHoursAgo)).toBe('3h ago');
		});

		it('should return days for timestamps within last week', () => {
			const twoDaysAgo = new Date(Date.now() - 2 * 86400000).toISOString();
			expect(formatRelativeTime(twoDaysAgo)).toBe('2d ago');
		});

		it('should return formatted date for older timestamps', () => {
			const twoWeeksAgo = new Date(Date.now() - 14 * 86400000).toISOString();
			const result = formatRelativeTime(twoWeeksAgo);
			expect(result).toMatch(/[A-Z][a-z]{2} \d{1,2}/); // e.g., "Dec 10"
		});
	});

	describe('truncate', () => {
		it('should return original text if shorter than max length', () => {
			const text = 'Short text';
			expect(truncate(text, 50)).toBe(text);
		});

		it('should truncate long text and add ellipsis', () => {
			const text = 'This is a very long text that needs to be truncated';
			const result = truncate(text, 20);
			expect(result).toHaveLength(22); // "This is a very long" (19) trimmed + '...' (3) = 22
			expect(result.endsWith('...')).toBe(true);
		});

		it('should trim whitespace before adding ellipsis', () => {
			const text = 'This is a text with spaces';
			const result = truncate(text, 10);
			expect(result).toMatch(/^\S.*\.\.\.$/); // No space before ...
		});
	});

	describe('getRelevanceColor', () => {
		it('should return success color for high relevance (≥0.8)', () => {
			expect(getRelevanceColor(0.8)).toBe('bg-success');
			expect(getRelevanceColor(0.9)).toBe('bg-success');
			expect(getRelevanceColor(1.0)).toBe('bg-success');
		});

		it('should return warning color for medium relevance (≥0.5, <0.8)', () => {
			expect(getRelevanceColor(0.5)).toBe('bg-warning');
			expect(getRelevanceColor(0.7)).toBe('bg-warning');
		});

		it('should return secondary color for low relevance (<0.5)', () => {
			expect(getRelevanceColor(0.0)).toBe('bg-text-secondary');
			expect(getRelevanceColor(0.3)).toBe('bg-text-secondary');
		});
	});
});

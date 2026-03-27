/**
 * Unified date utilities for Cognito.
 *
 * Due dates are date-only concepts — they represent a calendar day, not a moment
 * in time. Vikunja stores them as `YYYY-MM-DDT00:00:00Z` (midnight UTC), but
 * displaying them via `new Date()` then `.getDate()` shifts the day for users
 * west of UTC. All functions here extract the YYYY-MM-DD portion and create
 * local-midnight Date objects to avoid this.
 */

/** Vikunja's zero-epoch sentinel for "no date". */
export function isZeroEpoch(dateStr: string | null | undefined): boolean {
  return !dateStr || dateStr.startsWith('0001-01-01');
}

/**
 * Parse a date-only string into a local-midnight Date.
 * Handles "2026-03-27", "2026-03-27T00:00:00Z", "2026-03-27T05:00:00.000Z", etc.
 * Always extracts the YYYY-MM-DD portion — ignores time and timezone.
 */
export function parseDateOnly(dateStr: string): Date {
  const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return new Date(dateStr); // fallback for unexpected formats
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

/** Today at local midnight. */
export function localToday(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

/** Difference in calendar days between a date string and a reference (default: today). */
export function diffDays(dateStr: string, reference?: Date): number {
  const target = parseDateOnly(dateStr);
  const ref = reference ?? localToday();
  return Math.round((target.getTime() - ref.getTime()) / 86400000);
}

/** Format a date-only string as a relative label. */
export function formatRelativeDate(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = parseDateOnly(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const diff = diffDays(dateStr);
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Tomorrow';
  if (diff === -1) return 'Yesterday';
  if (diff > 1 && diff <= 7) return `In ${diff} days`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** True if a date-only due date is before today. */
export function isOverdue(dateStr: string | null | undefined): boolean {
  if (isZeroEpoch(dateStr)) return false;
  return diffDays(dateStr!) < 0;
}

/** True if a date-only due date is within the next N days (inclusive of today). */
export function isUpcoming(dateStr: string | null | undefined, withinDays: number = 7): boolean {
  if (isZeroEpoch(dateStr)) return false;
  const d = diffDays(dateStr!);
  return d >= 0 && d <= withinDays;
}

/**
 * Build a `YYYY-MM-DDT00:00:00Z` boundary string from a local Date.
 * Used for Vikunja filter queries — matches how Vikunja stores date-only values.
 */
export function dateBoundaryUTC(localDate: Date): string {
  const y = localDate.getFullYear();
  const m = String(localDate.getMonth() + 1).padStart(2, '0');
  const d = String(localDate.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}T00:00:00Z`;
}

/**
 * Shared formatting utilities for chat action display.
 */

const PRIORITY_LABELS: Record<number, string> = {
  1: 'Low',
  2: 'Low',
  3: 'Medium',
  4: 'High',
  5: 'Urgent',
};

export function formatChangeValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return 'none';
  if (key === 'due_date' && typeof value === 'string') return value.split('T')[0];
  if (key === 'done') return value ? 'Yes' : 'No';
  if (key === 'priority' && typeof value === 'number') return PRIORITY_LABELS[value] ?? String(value);
  if (key === 'labels' && Array.isArray(value)) return value.join(', ') || 'none';
  return String(value);
}

export function hexToRgb(hex: string): string {
  hex = hex.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return `${r},${g},${b}`;
}

export function formatFieldName(key: string): string {
  switch (key) {
    case 'due_date': return 'due date';
    case 'project_id': return 'project';
    case 'hex_color': return 'color';
    case 'bucket_id': return 'bucket';
    case 'task_title': return 'title';
    default: return key.replace(/_/g, ' ');
  }
}

import type { Task } from '$lib/types';
import { isZeroEpoch, parseDateOnly, localToday, diffDays } from '$lib/dateUtils';

const MS_PER_DAY = 86_400_000;

function daysBetween(a: Date, b: Date): number {
  return (a.getTime() - b.getTime()) / MS_PER_DAY;
}

function urgencyScore(task: Task): number {
  if (isZeroEpoch(task.due_date)) return 0.15;
  const daysUntil = diffDays(task.due_date!);

  if (daysUntil < 0) return Math.min(1.0 + 0.02 * Math.abs(daysUntil), 1.5); // overdue
  if (daysUntil < 1) return 0.9;   // due today
  if (daysUntil <= 3) return 0.7;  // 1-3 days
  if (daysUntil <= 7) return 0.5;  // within a week
  if (daysUntil <= 30) return 0.3; // within a month
  return 0.15;
}

function priorityScore(task: Task): number {
  return task.priority / 5;
}

function recencyScore(task: Task): number {
  if (isZeroEpoch(task.updated)) return 0;
  const daysSince = daysBetween(new Date(), new Date(task.updated));
  return 1 / (1 + daysSince / 7);
}

export function computeScore(task: Task): number {
  return 0.5 * urgencyScore(task) + 0.35 * priorityScore(task) + 0.15 * recencyScore(task);
}

export function smartSort(tasks: Task[]): Task[] {
  return [...tasks].sort((a, b) => computeScore(b) - computeScore(a));
}

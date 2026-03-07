/**
 * Frontend API client for the Cognito backend.
 *
 * All requests go to /api/* which the SvelteKit dev server proxies to the
 * FastAPI backend. Credentials (JWT HttpOnly cookie) are always included.
 */

import { goto } from '$app/navigation';
import { PUBLIC_API_URL } from '$env/static/public';
import type { Label, Project, Task, TaskProposal } from '$lib/types';

const BASE = PUBLIC_API_URL ? `${PUBLIC_API_URL}/api` : '/api';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  options?: RequestInit & {
    params?: Record<string, string | number | boolean | undefined | null>;
  },
): Promise<T> {
  let url = BASE + path;

  const { params, ...fetchOptions } = options ?? {};
  if (params) {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) q.set(k, String(v));
    }
    const qs = q.toString();
    if (qs) url += '?' + qs;
  }

  const fetchOnce = (u: string) =>
    fetch(u, {
      ...fetchOptions,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    });

  let res = await fetchOnce(url);

  if (res.status === 401) {
    // Try silent refresh
    const refreshRes = await fetch(BASE + '/auth/refresh', {
      method: 'POST',
      credentials: 'include',
    });
    if (refreshRes.ok) {
      res = await fetchOnce(url);
    } else {
      goto('/login');
      throw new ApiError(401, 'Session expired');
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? `Request failed (${res.status})`);
  }

  return res.json() as Promise<T>;
}

// ── Auth ───────────────────────────────────────────────────────────────────

export const authApi = {
  me() {
    return request<{ email: string; name: string; picture?: string }>('/auth/me');
  },
  loginUrl() {
    return `${BASE}/auth/login`;
  },
  logout() {
    return request<{ success: boolean }>('/auth/logout', { method: 'POST' });
  },
};

// ── Tasks ──────────────────────────────────────────────────────────────────

export const tasksApi = {
  list(params?: {
    project_id?: number;
    s?: string;
    filter?: string;
    sort_by?: string;
    order_by?: string;
    page?: number;
    per_page?: number;
  }) {
    return request<{ tasks: Task[] }>('/tasks', { params });
  },

  get(id: number) {
    return request<Task>(`/tasks/${id}`);
  },

  /** PUT creates in Vikunja */
  create(data: { project_id: number; title: string; priority?: number; due_date?: string; description?: string }) {
    return request<Task>('/tasks', { method: 'PUT', body: JSON.stringify(data) });
  },

  /** POST updates in Vikunja */
  update(id: number, data: Partial<Task>) {
    return request<Task>(`/tasks/${id}`, { method: 'POST', body: JSON.stringify(data) });
  },

  delete(id: number) {
    return request<{ success: boolean }>(`/tasks/${id}`, { method: 'DELETE' });
  },

  /** Add an existing label to a task. PUT creates in Vikunja. */
  addLabel(taskId: number, labelId: number) {
    return request<Label>(`/tasks/${taskId}/labels`, {
      method: 'PUT',
      body: JSON.stringify({ label_id: labelId }),
    });
  },

  /** Remove a label from a task. */
  removeLabel(taskId: number, labelId: number) {
    return request<void>(`/tasks/${taskId}/labels/${labelId}`, { method: 'DELETE' });
  },
};

// ── Projects ───────────────────────────────────────────────────────────────

export const projectsApi = {
  list() {
    return request<{ projects: Project[] }>('/projects');
  },

  sync() {
    return request<{ synced: number }>('/projects/sync', { method: 'POST' });
  },
};

// ── Labels ─────────────────────────────────────────────────────────────────

export const labelsApi = {
  list() {
    return request<{ labels: Label[] }>('/labels');
  },
};

// ── Proposals ──────────────────────────────────────────────────────────────

export const proposalsApi = {
  list(statusFilter?: string) {
    return request<{ proposals: TaskProposal[]; count: number }>('/proposals', {
      params: statusFilter ? { status: statusFilter } : undefined,
    });
  },

  update(id: string, data: Partial<TaskProposal>) {
    return request<TaskProposal>(`/proposals/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  approve(id: string) {
    return request<{ success: boolean; vikunja_task_id: number }>(`/proposals/${id}/approve`, {
      method: 'POST',
    });
  },

  reject(id: string) {
    return request<{ success: boolean }>(`/proposals/${id}/reject`, { method: 'POST' });
  },

  approveAll() {
    return request<{ approved: number; errors: Array<{ id: string; error: string }> }>(
      '/proposals/approve-all',
      { method: 'POST' },
    );
  },
};

// ── Ingest (SSE streaming) ─────────────────────────────────────────────────

export interface IngestEvent {
  type: 'proposal' | 'done' | 'error';
  proposal?: TaskProposal;
  count?: number;
  detail?: string;
}

/**
 * Stream task extraction from the backend via SSE.
 *
 * Usage:
 *   for await (const event of extractTasks(text)) {
 *     if (event.type === 'proposal') { ... }
 *   }
 */
export async function* extractTasks(
  text: string,
  opts?: {
    source_type?: string;
    confidential?: boolean;
    project_hint?: string;
    model?: string;
  },
): AsyncGenerator<IngestEvent> {
  const doFetch = () =>
    fetch(BASE + '/ingest', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ text, ...opts }),
    });

  let res = await doFetch();

  if (res.status === 401) {
    const refreshRes = await fetch(BASE + '/auth/refresh', {
      method: 'POST',
      credentials: 'include',
    });
    if (refreshRes.ok) {
      res = await doFetch();
    } else {
      goto('/login');
      throw new ApiError(401, 'Session expired');
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? 'Extraction failed');
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        const rawData = line.slice(5).trim();
        try {
          const data = JSON.parse(rawData);
          if (currentEvent === 'proposal') {
            yield { type: 'proposal', proposal: data as TaskProposal };
          } else if (currentEvent === 'done') {
            yield { type: 'done', count: data.count };
          } else if (currentEvent === 'error') {
            yield { type: 'error', detail: data.detail };
          }
        } catch (parseErr) {
          console.warn('[SSE] Failed to parse:', rawData, parseErr);
        }
        currentEvent = '';
      }
    }
  }
}

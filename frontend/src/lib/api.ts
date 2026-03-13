/**
 * Frontend API client for the Cognito backend.
 *
 * All requests go to /api/* which the SvelteKit dev server proxies to the
 * FastAPI backend. Credentials (JWT HttpOnly cookie) are always included.
 */

import { goto } from '$app/navigation';
import { PUBLIC_API_URL } from '$env/static/public';
import type { Bucket, ChatAction, ChatMessage, Label, LabelDescription, LabelStats, Project, ProjectView, Revision, Subtask, Task, TaskAttachment, TaskProposal } from '$lib/types';

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

  let res: Response;
  try {
    res = await fetchOnce(url);
  } catch {
    throw new ApiError(0, 'Unable to reach the server');
  }

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
  create(data: { project_id: number; title: string; priority?: number; due_date?: string; start_date?: string; end_date?: string; description?: string }) {
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

  /** Auto-tag tasks using LLM + label descriptions. */
  autoTag(taskIds?: number[], model?: string) {
    return request<{ tagged: number; results: Array<{ task_id: number; labels_added: number[] }> }>(
      '/tasks/auto-tag',
      { method: 'POST', body: JSON.stringify({ task_ids: taskIds, model }) },
    );
  },
};

// ── Projects ───────────────────────────────────────────────────────────────

export const projectsApi = {
  list(params?: { include_archived?: boolean }) {
    return request<{ projects: Project[] }>('/projects', { params });
  },

  create(data: { title: string; description?: string; hex_color?: string }) {
    return request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) });
  },

  update(id: number, data: Partial<Pick<Project, 'title' | 'description' | 'hex_color' | 'is_archived' | 'position'>>) {
    return request<Project>(`/projects/${id}`, { method: 'POST', body: JSON.stringify(data) });
  },

  delete(id: number) {
    return request<{ success: boolean }>(`/projects/${id}`, { method: 'DELETE' });
  },

  sync() {
    return request<{ synced: number }>('/projects/sync', { method: 'POST' });
  },
};

// ── Kanban ─────────────────────────────────────────────────────────────

export const kanbanApi = {
  listViews(projectId: number) {
    return request<{ views: ProjectView[] }>(`/projects/${projectId}/views`);
  },

  createView(projectId: number, title: string, viewKind: string = 'kanban') {
    return request<ProjectView>(`/projects/${projectId}/views`, {
      method: 'PUT',
      body: JSON.stringify({ title, view_kind: viewKind }),
    });
  },

  listBuckets(projectId: number, viewId: number) {
    return request<{ buckets: Bucket[] }>(`/projects/${projectId}/views/${viewId}/buckets`);
  },

  createBucket(projectId: number, viewId: number, title: string) {
    return request<Bucket>(`/projects/${projectId}/views/${viewId}/buckets`, {
      method: 'PUT',
      body: JSON.stringify({ title }),
    });
  },

  updateBucket(projectId: number, viewId: number, bucketId: number, data: Partial<Bucket>) {
    return request<Bucket>(`/projects/${projectId}/views/${viewId}/buckets/${bucketId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  deleteBucket(projectId: number, viewId: number, bucketId: number) {
    return request<{ success: boolean }>(`/projects/${projectId}/views/${viewId}/buckets/${bucketId}`, {
      method: 'DELETE',
    });
  },

  listViewTasks(projectId: number, viewId: number) {
    return request<Bucket[]>(`/projects/${projectId}/views/${viewId}/tasks`);
  },

  moveTaskToBucket(projectId: number, viewId: number, bucketId: number, taskId: number) {
    return request<unknown>(`/projects/${projectId}/views/${viewId}/buckets/${bucketId}/tasks`, {
      method: 'POST',
      body: JSON.stringify({ task_id: taskId }),
    });
  },

  updateTaskPosition(taskId: number, position: number, viewId: number) {
    return request<unknown>(`/tasks/${taskId}/position`, {
      method: 'POST',
      body: JSON.stringify({ position, project_view_id: viewId }),
    });
  },
};

// ── Subtasks ──────────────────────────────────────────────────────────────

export const subtasksApi = {
  list(taskId: number) {
    return request<{ subtasks: Subtask[] }>(`/tasks/${taskId}/subtasks`).then(r => r.subtasks);
  },

  create(taskId: number, data: { title: string; project_id?: number }) {
    return request<Subtask>(`/tasks/${taskId}/subtasks`, { method: 'PUT', body: JSON.stringify(data) });
  },

  update(taskId: number, subtaskId: number, data: Partial<Subtask>) {
    return request<Subtask>(`/tasks/${taskId}/subtasks/${subtaskId}`, { method: 'POST', body: JSON.stringify(data) });
  },

  delete(taskId: number, subtaskId: number) {
    return request<void>(`/tasks/${taskId}/subtasks/${subtaskId}`, { method: 'DELETE' });
  },
};

// ── Attachments ────────────────────────────────────────────────────────────

export const attachmentsApi = {
  list(taskId: number) {
    return request<TaskAttachment[]>(`/tasks/${taskId}/attachments`);
  },

  async upload(taskId: number, file: File): Promise<TaskAttachment> {
    const formData = new FormData();
    formData.append('files', file);

    const doFetch = (url: string) =>
      fetch(url, {
        method: 'PUT',
        credentials: 'include',
        body: formData,
      });

    const url = BASE + `/tasks/${taskId}/attachments`;
    let res = await doFetch(url);

    if (res.status === 401) {
      const refreshRes = await fetch(BASE + '/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      });
      if (refreshRes.ok) {
        res = await doFetch(url);
      } else {
        goto('/login');
        throw new ApiError(401, 'Session expired');
      }
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail ?? `Upload failed (${res.status})`);
    }

    return res.json() as Promise<TaskAttachment>;
  },

  downloadUrl(taskId: number, attachmentId: number) {
    return `${BASE}/tasks/${taskId}/attachments/${attachmentId}`;
  },

  previewUrl(taskId: number, attachmentId: number, size: 'sm' | 'md' | 'lg' | 'xl' = 'md') {
    return `${BASE}/tasks/${taskId}/attachments/${attachmentId}?preview_size=${size}`;
  },

  delete(taskId: number, attachmentId: number) {
    return request<{ success: boolean }>(`/tasks/${taskId}/attachments/${attachmentId}`, {
      method: 'DELETE',
    });
  },
};

// ── Labels ─────────────────────────────────────────────────────────────────

export const labelsApi = {
  list() {
    return request<{ labels: Label[] }>('/labels');
  },

  create(data: { title: string; hex_color?: string }) {
    return request<Label>('/labels', { method: 'PUT', body: JSON.stringify(data) });
  },

  descriptions() {
    return request<{ descriptions: LabelDescription[] }>('/labels/descriptions');
  },

  upsertDescription(labelId: number, data: { title: string; description: string }) {
    return request<LabelDescription>(`/labels/${labelId}/description`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  deleteDescription(labelId: number) {
    return request<{ success: boolean }>(`/labels/${labelId}/description`, { method: 'DELETE' });
  },

  stats() {
    return request<{ stats: LabelStats }>('/labels/stats');
  },

  update(labelId: number, data: { title?: string; hex_color?: string; description?: string }) {
    return request<Label>(`/labels/${labelId}`, { method: 'PUT', body: JSON.stringify(data) });
  },

  generateDescription(labelId: number) {
    return request<{ label_id: number; description: string }>(`/labels/${labelId}/generate-description`, { method: 'POST' });
  },

  delete(labelId: number) {
    return request<{ success: boolean }>(`/labels/${labelId}`, { method: 'DELETE' });
  },

  cleanup() {
    return request<{ deleted: number[]; count: number }>('/labels/cleanup', { method: 'POST' });
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
    return request<{ success: boolean; vikunja_task_id: number; new_project_created?: boolean; revision_id?: number }>(`/proposals/${id}/approve`, {
      method: 'POST',
    });
  },

  reject(id: string) {
    return request<{ success: boolean }>(`/proposals/${id}/reject`, { method: 'POST' });
  },

  approveAll(ids?: string[]) {
    return request<{ approved: number; errors: Array<{ id: string; title?: string; error: string }>; new_projects?: string[]; task_ids?: number[] }>(
      '/proposals/approve-all',
      { method: 'POST', body: JSON.stringify(ids ? { ids } : {}) },
    );
  },
};

// ── Models ──────────────────────────────────────────────────────────────────

export interface ModelOption {
  value: string;
  model_id: string;
  label: string;
  description: string;
  provider: string;
}

export const modelsApi = {
  list() {
    return request<ModelOption[]>('/models');
  },
};

// ── Chat ────────────────────────────────────────────────────────────────────

export const chatApi = {
  send(message: string, conversationId?: string, model?: string) {
    return request<{
      reply: string;
      proposals: TaskProposal[];
      actions: ChatAction[];
      pending_actions: ChatAction[];
      conversation_id: string;
    }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, conversation_id: conversationId, model }),
    });
  },

  listHistory() {
    return request<{ conversations: Array<{ id: string; snippet: string; created_at: string; message_count: number }> }>('/chat/history');
  },

  getConversation(conversationId: string) {
    return request<{
      conversation_id: string;
      messages: ChatMessage[];
      created_at: string;
      updated_at: string;
    }>(`/chat/${conversationId}`);
  },

  deleteConversation(conversationId: string) {
    return request<{ success: boolean }>(`/chat/${conversationId}`, { method: 'DELETE' });
  },

  executeAction(action: ChatAction) {
    return request<{ success: boolean; revision_id?: number }>('/chat/execute-action', {
      method: 'POST',
      body: JSON.stringify({
        type: action.type,
        task_id: action.task_id,
        changes: action.changes,
        project_id: action.project_id,
      }),
    });
  },
};

// ── Config ──────────────────────────────────────────────────────────────────

export interface AgentConfigResponse {
  default_project_id: number | null;
  ollama_model: string | null;
  gemini_model: string | null;
  gcal_calendar_id: string | null;
  system_prompt_override: string | null;
  base_prompt_override: string | null;
}

export const configApi = {
  get() {
    return request<AgentConfigResponse>('/config');
  },

  update(data: Partial<AgentConfigResponse>) {
    return request<AgentConfigResponse>('/config', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  getSystemPrompt() {
    return request<{ prompt: string }>('/config/system-prompt');
  },

  getTools() {
    return request<{ tools: Array<{ name: string; description: string; parameters: Record<string, unknown> }> }>('/config/tools');
  },
};

// ── Revisions ──────────────────────────────────────────────────────────────

export const revisionsApi = {
  list(limit = 50) {
    return request<{ revisions: Revision[] }>('/revisions', { params: { limit } });
  },

  get(id: number) {
    return request<Revision>(`/revisions/${id}`);
  },

  undo(id: number, force = false) {
    return request<Record<string, unknown>>(`/revisions/${id}/undo`, {
      method: 'POST',
      params: force ? { force: true } : undefined,
    });
  },

  redo(id: number) {
    return request<Record<string, unknown>>(`/revisions/${id}/redo`, {
      method: 'POST',
    });
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

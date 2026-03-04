/**
 * API client — fetch wrapper for all backend calls.
 * Handles auth cookies, JSON parsing, and SSE streaming.
 */

const BASE = '/api';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });

    if (res.status === 401) {
        // Try silent refresh first
        const refreshed = await tryRefresh();
        if (refreshed) {
            const retry = await fetch(`${BASE}${path}`, {
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options,
            });
            if (!retry.ok) throw new ApiError(retry.status, await retry.text());
            return retry.json();
        }
        throw new ApiError(401, 'Unauthorized');
    }

    if (!res.ok) {
        const body = await res.text();
        let detail = body;
        try {
            detail = JSON.parse(body)?.detail ?? body;
        } catch { }
        throw new ApiError(res.status, detail);
    }

    const text = await res.text();
    return text ? JSON.parse(text) : ({} as T);
}

async function tryRefresh(): Promise<boolean> {
    try {
        const res = await fetch(`${BASE}/auth/refresh`, {
            method: 'POST',
            credentials: 'include',
        });
        return res.ok;
    } catch {
        return false;
    }
}

export class ApiError extends Error {
    constructor(
        public status: number,
        public detail: string
    ) {
        super(detail);
        this.name = 'ApiError';
    }
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export function loginUrl(): string {
    return `${BASE}/auth/login`;
}

export async function getMe(): Promise<{ email: string; name: string; picture: string | null }> {
    return request('/auth/me');
}

export async function logout(): Promise<void> {
    await request('/auth/logout', { method: 'POST' });
}

// ── Projects ─────────────────────────────────────────────────────────────────
export async function getProjects(): Promise<{ id: number; title: string; description: string }[]> {
    const data = await request<{ projects: any[] }>('/projects');
    return data.projects;
}

export async function syncProjects(): Promise<number> {
    const data = await request<{ synced: number }>('/projects/sync', { method: 'POST' });
    return data.synced;
}

// ── Proposals ─────────────────────────────────────────────────────────────────
export async function getProposals(status?: string): Promise<any[]> {
    const qs = status ? `?status=${status}` : '';
    const data = await request<{ proposals: any[] }>(`/proposals${qs}`);
    return data.proposals;
}

export async function updateProposal(id: string, patch: Record<string, any>): Promise<any> {
    return request(`/proposals/${id}`, {
        method: 'PUT',
        body: JSON.stringify(patch),
    });
}

export async function approveProposal(id: string): Promise<any> {
    return request(`/proposals/${id}/approve`, { method: 'POST' });
}

export async function rejectProposal(id: string): Promise<void> {
    await request(`/proposals/${id}/reject`, { method: 'POST' });
}

export async function approveAll(): Promise<{ approved: number; errors: any[] }> {
    return request('/proposals/approve-all', { method: 'POST' });
}

// ── Ingest ───────────────────────────────────────────────────────────────────
export interface IngestOptions {
    text: string;
    source_type?: string;
    confidential?: boolean;
    project_hint?: string;
}

export async function ingest(opts: IngestOptions): Promise<any[]> {
    const data = await request<{ proposals: any[] }>('/ingest', {
        method: 'POST',
        body: JSON.stringify(opts),
    });
    return data.proposals;
}

/**
 * Stream proposals via SSE.
 * Calls onProposal for each streamed proposal, onDone when finished, onError on failure.
 */
export function ingestStream(
    opts: IngestOptions,
    onProposal: (proposal: any) => void,
    onDone: (count: number) => void,
    onError: (detail: string) => void
): () => void {
    const controller = new AbortController();

    (async () => {
        try {
            const res = await fetch(`${BASE}/ingest`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    Accept: 'text/event-stream',
                },
                body: JSON.stringify(opts),
                signal: controller.signal,
            });

            if (!res.ok) {
                onError(`HTTP ${res.status}`);
                return;
            }

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();
            if (!reader) return;

            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                const lines = buffer.split('\n');
                buffer = lines.pop() ?? '';

                let eventType = '';
                let eventData = '';

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        eventData = line.slice(6).trim();
                    } else if (line === '') {
                        if (eventType === 'proposal' && eventData) {
                            try {
                                onProposal(JSON.parse(eventData));
                            } catch { }
                        } else if (eventType === 'done' && eventData) {
                            try {
                                const d = JSON.parse(eventData);
                                onDone(d.count ?? 0);
                            } catch { }
                        } else if (eventType === 'error' && eventData) {
                            try {
                                onError(JSON.parse(eventData)?.detail ?? 'Unknown error');
                            } catch {
                                onError(eventData);
                            }
                        }
                        eventType = '';
                        eventData = '';
                    }
                }
            }
        } catch (e: any) {
            if (e?.name !== 'AbortError') {
                onError(e?.message ?? 'Stream error');
            }
        }
    })();

    return () => controller.abort();
}

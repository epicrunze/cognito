/// <reference types="@sveltejs/kit" />
/// <reference lib="webworker" />

const sw = self as unknown as ServiceWorkerGlobalScope;

// Activate updated workers immediately — this SW only handles push, no caching.
sw.addEventListener('install', () => {
  sw.skipWaiting();
});

sw.addEventListener('activate', (event) => {
  event.waitUntil(sw.clients.claim());
});

interface PushPayload {
  title: string;
  body: string;
  type: string;
  task_id: number | null;
}

sw.addEventListener('push', (event) => {
  let payload: PushPayload = { title: 'Cognito', body: '', type: 'nudge', task_id: null };
  try {
    if (event.data) payload = { ...payload, ...event.data.json() };
  } catch {
    if (event.data) payload.body = event.data.text();
  }
  event.waitUntil(
    sw.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/icons/icon-192.png',
      // Android renders the badge from the alpha channel only — must be
      // a monochrome white-on-transparent image, not the full-colour icon.
      badge: '/icons/badge-96.png',
      tag: payload.task_id ? `${payload.type}-${payload.task_id}` : payload.type,
      renotify: true,
      data: { task_id: payload.task_id, type: payload.type },
    } as NotificationOptions & { renotify?: boolean })
  );
});

sw.addEventListener('notificationclick', (event) => {
  event.notification.close();

  // Reminders carry a task → open it; summaries (digest/review/nudge) → Today page.
  const data = (event.notification.data ?? {}) as { task_id?: number | null };
  const taskId = data.task_id ?? null;
  const url = taskId ? `/?task=${taskId}` : '/briefing';

  event.waitUntil(
    sw.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((c) => 'focus' in c) as WindowClient | undefined;
      if (existing) {
        // Let the running SPA route client-side (no reload, keeps state).
        existing.postMessage({ type: 'notification-click', url, taskId });
        return existing.focus();
      }
      return sw.clients.openWindow(url);
    })
  );
});

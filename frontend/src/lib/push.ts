/**
 * Browser-side Web Push helpers.
 *
 * Flow: permission → service worker ready → pushManager.subscribe with the
 * backend's VAPID public key → POST the subscription to the backend.
 * iOS requires the PWA to be installed to the home screen (16.4+).
 */

import { notificationsApi } from '$lib/api';

export type PushSupport = 'supported' | 'unsupported' | 'needs-install';

export function getPushSupport(): PushSupport {
  if (!('serviceWorker' in navigator) || !('Notification' in window)) {
    // iOS Safari outside an installed PWA reports no Notification API
    const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
    return isIos ? 'needs-install' : 'unsupported';
  }
  if (!('PushManager' in window)) return 'unsupported';
  return 'supported';
}

export function getPermission(): NotificationPermission | null {
  return 'Notification' in window ? Notification.permission : null;
}

function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

/** Resolves to the SW registration or rejects after `timeoutMs`. */
async function swReady(timeoutMs = 5000): Promise<ServiceWorkerRegistration> {
  const timeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error('Service worker not ready — try reloading the page')), timeoutMs)
  );
  return Promise.race([navigator.serviceWorker.ready, timeout]);
}

export async function getExistingSubscription(): Promise<PushSubscription | null> {
  if (getPushSupport() !== 'supported') return null;
  const reg = await swReady();
  return reg.pushManager.getSubscription();
}

/** Request permission, subscribe the browser, and register with the backend. */
export async function enablePush(): Promise<void> {
  if (Notification.permission === 'denied') {
    throw new Error('Notifications are blocked in browser settings');
  }
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    throw new Error('Notification permission denied');
  }
  const { public_key } = await notificationsApi.getVapidPublicKey();
  if (!public_key) {
    throw new Error('Server has no VAPID key configured');
  }
  const reg = await swReady();
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(public_key),
  });
  const json = sub.toJSON();
  await notificationsApi.subscribe({
    endpoint: json.endpoint!,
    keys: { p256dh: json.keys!.p256dh, auth: json.keys!.auth },
  });
}

/** Unsubscribe this browser and deregister from the backend. */
export async function disablePush(): Promise<void> {
  const sub = await getExistingSubscription();
  if (!sub) return;
  const endpoint = sub.endpoint;
  await sub.unsubscribe();
  await notificationsApi.unsubscribe(endpoint);
}

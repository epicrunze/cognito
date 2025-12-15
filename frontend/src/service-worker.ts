/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

/**
 * Service Worker for Cognito PWA
 * 
 * Handles offline caching and background sync.
 */

import { build, files, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;

const CACHE_NAME = `cognito-cache-v${version}`;

// Files to cache on install
const CACHED_FILES = [
    ...build, // SvelteKit build files
    ...files  // Static files
];

/**
 * Install event - cache app shell
 */
sw.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(CACHED_FILES);
        }).then(() => {
            sw.skipWaiting();
        })
    );
});

/**
 * Activate event - clean up old caches
 */
sw.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        }).then(() => {
            sw.clients.claim();
        })
    );
});

/**
 * Fetch event - serve from cache, fallback to network
 */
sw.addEventListener('fetch', (event) => {
    const { request } = event;

    // Skip non-GET requests
    if (request.method !== 'GET') return;

    // Skip API requests (let them fail naturally for offline handling)
    if (request.url.includes('/api/')) return;

    event.respondWith(
        caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }

            return fetch(request).then((networkResponse) => {
                // Cache successful responses
                if (networkResponse.ok) {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, responseClone);
                    });
                }
                return networkResponse;
            }).catch(() => {
                // Return offline fallback if available
                return caches.match('/offline.html') || new Response('Offline', { status: 503 });
            });
        })
    );
});

/**
 * Background sync registration (for future enhancement)
 */
sw.addEventListener('sync', (event) => {
    if (event.tag === 'sync-data') {
        event.waitUntil(
            // Trigger sync logic (to be implemented)
            Promise.resolve()
        );
    }
});

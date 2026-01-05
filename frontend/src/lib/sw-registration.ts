/**
 * Service Worker Registration and Update Management
 * 
 * This module handles:
 * - Registering the service worker with proper cache bypass settings
 * - Detecting when updates are available
 * - Force-activating new service workers to ensure users get the latest version
 */

import { writable } from 'svelte/store';

// Store to track if an update is available and being applied
export const updateAvailable = writable(false);
export const updateApplying = writable(false);

let registration: ServiceWorkerRegistration | null = null;

/**
 * Register the service worker and set up update detection
 */
export async function registerServiceWorker(): Promise<void> {
    if (!('serviceWorker' in navigator)) {
        console.log('Service workers not supported');
        return;
    }

    try {
        // Register with updateViaCache: 'none' to ensure the browser always 
        // fetches the service worker file fresh from the network
        registration = await navigator.serviceWorker.register('/service-worker.js', {
            scope: '/',
            updateViaCache: 'none'
        });

        console.log('SW registered:', registration.scope);

        // Check for updates immediately
        await checkForUpdates();

        // Set up update detection
        registration.addEventListener('updatefound', () => {
            const newWorker = registration?.installing;
            if (newWorker) {
                handleNewWorker(newWorker);
            }
        });

        // Listen for the controlling service worker changing
        navigator.serviceWorker.addEventListener('controllerchange', () => {
            // The new service worker has taken control
            // Reload to ensure the app uses the new cached resources
            window.location.reload();
        });

    } catch (error) {
        console.error('SW registration failed:', error);
    }
}

/**
 * Manually check for service worker updates
 */
export async function checkForUpdates(): Promise<void> {
    if (!registration) return;

    try {
        await registration.update();
        console.log('SW update check completed');

        // Check if there's a waiting worker
        if (registration.waiting) {
            console.log('Update available - new SW waiting');
            updateAvailable.set(true);
            // Auto-apply the update
            applyUpdate();
        }
    } catch (error) {
        console.error('SW update check failed:', error);
    }
}

/**
 * Handle a new service worker being installed
 */
function handleNewWorker(worker: ServiceWorker): void {
    console.log('New SW installing');

    worker.addEventListener('statechange', () => {
        console.log('SW state changed:', worker.state);

        if (worker.state === 'installed') {
            // Check if there's an existing controller
            if (navigator.serviceWorker.controller) {
                // There's a previous version - this is an update
                console.log('New SW installed, waiting to activate');
                updateAvailable.set(true);
                // Auto-apply the update
                applyUpdate();
            } else {
                // First install - no need for update prompt
                console.log('SW installed for the first time');
            }
        }
    });
}

/**
 * Apply the pending update by telling the new SW to skip waiting
 */
export function applyUpdate(): void {
    if (!registration?.waiting) {
        console.log('No waiting SW to activate');
        return;
    }

    console.log('Applying update - telling SW to skip waiting');
    updateApplying.set(true);

    // Tell the waiting service worker to skip waiting and activate immediately
    registration.waiting.postMessage({ type: 'SKIP_WAITING' });
}

/**
 * Unregister all service workers (useful for debugging)
 */
export async function unregisterAll(): Promise<void> {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map(reg => reg.unregister()));
    console.log('All service workers unregistered');
}

/**
 * Clear all caches (useful for forcing a complete refresh)
 */
export async function clearAllCaches(): Promise<void> {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map(name => caches.delete(name)));
    console.log('All caches cleared');
}

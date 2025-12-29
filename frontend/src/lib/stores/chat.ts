/**
 * Chat store
 *
 * Manages chat state including messages, loading state, and offline queue.
 */

import { writable, derived, get } from 'svelte/store';
import type { Message } from '$lib/db';
import { sendMessage as sendMessageApi, type ChatResponse } from '$lib/api/chat';
import { isOnline } from '$lib/api/client';

// Current conversation messages
export const chatMessages = writable<Message[]>([]);

// Current conversation ID
export const currentConversationId = writable<string | null>(null);

// Loading state
export const chatLoading = writable<boolean>(false);

// Error state
export const chatError = writable<string | null>(null);

// Queued messages for offline support
export interface QueuedMessage {
    id: string;
    entry_id: string;
    message: string;
    timestamp: string;
}

export const offlineQueue = writable<QueuedMessage[]>([]);

// Derived store for queue count
export const offlineQueueCount = derived(offlineQueue, ($queue) => $queue.length);

// Has pending messages
export const hasPendingMessages = derived(offlineQueue, ($queue) => $queue.length > 0);

/**
 * Clear chat state
 */
export function clearChat(): void {
    chatMessages.set([]);
    currentConversationId.set(null);
    chatError.set(null);
}

/**
 * Initialize chat with existing messages
 */
export function initializeChat(messages: Message[], conversationId: string | null): void {
    chatMessages.set(messages);
    currentConversationId.set(conversationId);
    chatError.set(null);
}

/**
 * Add a message to the chat
 */
export function addMessage(message: Message): void {
    chatMessages.update((msgs) => [...msgs, message]);
}

/**
 * Send a message and get LLM response
 */
export async function sendMessage(entryId: string, message: string): Promise<ChatResponse | null> {
    chatError.set(null);

    // Add user message immediately
    const now = new Date().toISOString();
    const userMessage: Message = {
        role: 'user',
        content: message,
        timestamp: now
    };
    addMessage(userMessage);

    // Check if offline
    if (!isOnline()) {
        // Queue the message
        const queuedMessage: QueuedMessage = {
            id: crypto.randomUUID(),
            entry_id: entryId,
            message: message,
            timestamp: now
        };
        offlineQueue.update((q) => [...q, queuedMessage]);
        chatError.set('Message queued - will be sent when you are back online');
        return null;
    }

    chatLoading.set(true);

    try {
        const conversationId = get(currentConversationId);
        const response = await sendMessageApi({
            entry_id: entryId,
            conversation_id: conversationId || undefined,
            message: message
        });

        // Update conversation ID if new
        if (!conversationId) {
            currentConversationId.set(response.conversation_id);
        }

        // Add assistant message
        const assistantMessage: Message = {
            role: 'assistant',
            content: response.response,
            timestamp: new Date().toISOString()
        };
        addMessage(assistantMessage);

        return response;
    } catch (error: any) {
        const errorMessage = error?.message || 'Failed to send message';
        chatError.set(errorMessage);
        return null;
    } finally {
        chatLoading.set(false);
    }
}

/**
 * Process offline queue when back online
 */
export async function processOfflineQueue(entryId: string): Promise<void> {
    const queue = get(offlineQueue);
    if (queue.length === 0) return;

    const entryMessages = queue.filter((q) => q.entry_id === entryId);
    if (entryMessages.length === 0) return;

    for (const queuedMessage of entryMessages) {
        try {
            const conversationId = get(currentConversationId);
            const response = await sendMessageApi({
                entry_id: queuedMessage.entry_id,
                conversation_id: conversationId || undefined,
                message: queuedMessage.message
            });

            // Update conversation ID
            if (!conversationId) {
                currentConversationId.set(response.conversation_id);
            }

            // Add assistant response
            const assistantMessage: Message = {
                role: 'assistant',
                content: response.response,
                timestamp: new Date().toISOString()
            };
            addMessage(assistantMessage);

            // Remove from queue
            offlineQueue.update((q) => q.filter((m) => m.id !== queuedMessage.id));
        } catch (error) {
            console.error('Failed to process queued message:', error);
            // Keep in queue for retry
        }
    }
}

// Listen for online status changes
if (typeof window !== 'undefined') {
    window.addEventListener('online', () => {
        // Could trigger queue processing here if we had the entry ID
        console.log('Back online - queued messages can be sent');
    });
}

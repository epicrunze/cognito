/**
 * Chat store
 *
 * Manages chat state including messages, loading state, and unified offline support.
 * Offline messages are saved to the entry with pending_response flag for sync.
 */

import { writable, derived, get } from 'svelte/store';
import type { Message, Entry, Conversation } from '$lib/db';
import { db } from '$lib/db';
import { sendMessage as sendMessageApi, type ChatResponse } from '$lib/api/chat';
import { isOnline } from '$lib/api/client';
import { queueEntryChange } from '$lib/db/sync';
import { updatePendingCount } from '$lib/stores/sync';
import logger from '$lib/logger';

// Current conversation messages
export const chatMessages = writable<Message[]>([]);

// Current conversation ID
export const currentConversationId = writable<string | null>(null);

// Loading state
export const chatLoading = writable<boolean>(false);

// Error state
export const chatError = writable<string | null>(null);

// Derived store: has pending messages in current chat
export const hasPendingMessages = derived(chatMessages, ($messages) =>
    $messages.some((m) => m.pending_response)
);

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
 * Send a message and get LLM response.
 * 
 * When offline, saves the message to the entry with pending_response=true
 * and queues the entry for sync. The server will process pending messages
 * during sync and add LLM responses.
 */
export async function sendMessage(entryId: string, message: string): Promise<ChatResponse | null> {
    chatError.set(null);

    const now = new Date().toISOString();
    const userMessage: Message = {
        role: 'user',
        content: message,
        timestamp: now,
    };

    // Check if offline
    if (!isOnline()) {
        logger.info('Offline - saving message with pending_response flag');

        // Mark message as pending response
        const pendingMessage: Message = {
            ...userMessage,
            pending_response: true,
        };

        // Add to current chat display
        addMessage(pendingMessage);

        // Save to local entry
        await saveMessageToEntry(entryId, pendingMessage);

        chatError.set('Message saved - response will be generated when you are back online');
        return null;
    }

    // Online - add message and call API
    addMessage(userMessage);
    chatLoading.set(true);

    try {
        const conversationId = get(currentConversationId);
        const response = await sendMessageApi({
            entry_id: entryId,
            conversation_id: conversationId || undefined,
            message: message,
        });

        // Update conversation ID if new
        if (!conversationId) {
            currentConversationId.set(response.conversation_id);
        }

        // Add assistant message
        const assistantMessage: Message = {
            role: 'assistant',
            content: response.response,
            timestamp: new Date().toISOString(),
        };
        addMessage(assistantMessage);

        return response;
    } catch (error: any) {
        const errorMessage = error?.message || 'Failed to send message';
        chatError.set(errorMessage);
        logger.error('Failed to send message', { error: errorMessage });
        return null;
    } finally {
        chatLoading.set(false);
    }
}

/**
 * Save a message to the entry in IndexedDB and queue for sync.
 */
async function saveMessageToEntry(entryId: string, message: Message): Promise<void> {
    try {
        const entry = await db.entries.get(entryId);
        if (!entry) {
            logger.error('Entry not found for offline message', { entryId });
            return;
        }

        // Get or create current conversation
        const conversationId = get(currentConversationId);
        let conversations = [...entry.conversations];

        if (conversationId) {
            // Add to existing conversation
            const convIndex = conversations.findIndex((c) => c.id === conversationId);
            if (convIndex !== -1) {
                conversations[convIndex] = {
                    ...conversations[convIndex],
                    messages: [...conversations[convIndex].messages, message],
                };
            }
        } else {
            // Create new conversation
            const newConvId = crypto.randomUUID();
            const newConversation: Conversation = {
                id: newConvId,
                started_at: new Date().toISOString(),
                messages: [message],
                prompt_source: 'user',
                notification_id: null,
            };
            conversations.push(newConversation);
            currentConversationId.set(newConvId);
        }

        // Update entry
        const updatedEntry: Entry = {
            ...entry,
            conversations,
            last_interacted_at: new Date().toISOString(),
            interaction_count: entry.interaction_count + 1,
            updated_at: new Date().toISOString(),
        };

        await db.entries.put(updatedEntry);

        // Queue for sync
        await queueEntryChange('update', updatedEntry);
        await updatePendingCount();

        logger.debug('Saved offline message to entry', { entryId });
    } catch (error) {
        logger.error('Failed to save message to entry', { error: String(error) });
    }
}

// Listen for online status changes
if (typeof window !== 'undefined') {
    window.addEventListener('online', () => {
        logger.info('Back online - pending messages will be processed on next sync');
    });
}

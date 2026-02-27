/**
 * Chat API module
 * 
 * Handles chat/conversation messages with backend.
 */

import { api } from './client';
import type { Message } from '../db';

export interface ChatRequest {
    entry_id: string;
    message: string;
    conversation_id?: string;
}

export interface ChatResponse {
    response: string;
    conversation_id: string;
    messages: Message[];
}

/**
 * Send a chat message
 */
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    return await api.post<ChatResponse>('/chat', request);
}

/**
 * Get chat history for an entry
 */
export async function getChatHistory(entryId: string): Promise<{ messages: Message[] }> {
    return await api.get<{ messages: Message[] }>(`/chat/history/${entryId}`);
}

/**
 * Chat API client
 *
 * Handles communication with chat endpoints for conversational journaling.
 */

import { api } from './client';

export interface ChatRequest {
    entry_id: string;
    conversation_id?: string;
    message: string;
    use_local_model?: boolean;
}

export interface ChatResponse {
    response: string;
    conversation_id: string;
    entry_id: string;
}

export interface RefineResponse {
    refined_output: string;
    entry_id: string;
}

/**
 * Send a chat message and get LLM response.
 *
 * Creates a new conversation if conversation_id is not provided.
 */
export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
    return api.post<ChatResponse>('/chat', request);
}

/**
 * Generate refined output from all conversations in an entry.
 */
export async function refineEntry(
    entryId: string,
    useLocalModel: boolean = false
): Promise<RefineResponse> {
    return api.post<RefineResponse>('/chat/refine', {
        entry_id: entryId,
        use_local_model: useLocalModel
    });
}

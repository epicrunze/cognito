/**
 * Dexie.js Database Setup for Cognito
 * 
 * Offline-first IndexedDB database matching backend schema.
 * Follows spec Section 5.1 (Offline-First Principles).
 */

import Dexie, { type EntityTable } from 'dexie';

// Type definitions matching backend models
export interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: string; // ISO 8601
}

export interface Conversation {
    id: string; // UUID
    started_at: string; // ISO 8601
    messages: Message[];
    prompt_source: 'user' | 'notification' | 'continuation';
    notification_id: string | null;
}

export interface Entry {
    id: string; // UUID
    date: string; // YYYY-MM-DD
    conversations: Conversation[];
    refined_output: string;
    relevance_score: number;
    last_interacted_at: string; // ISO 8601
    interaction_count: number;
    status: 'active' | 'archived';
    version: number;
    created_at: string; // ISO 8601
    updated_at: string; // ISO 8601
}

export interface Goal {
    id: string; // UUID
    category: string;
    description: string;
    active: boolean;
    created_at: string; // ISO 8601
    updated_at: string; // ISO 8601
}

export interface PendingChange {
    id: string; // UUID
    type: 'create' | 'update' | 'delete';
    entity: 'entry' | 'goal';
    entity_id: string;
    data: any; // JSON data
    base_version?: number; // For entries
    timestamp: string; // ISO 8601
}

export interface Settings {
    id: string; // Single record with id='settings'
    lastSyncedAt: string | null; // ISO 8601
}

// Dexie database class
export class CognitoDB extends Dexie {
    entries!: EntityTable<Entry, 'id'>;
    goals!: EntityTable<Goal, 'id'>;
    pendingChanges!: EntityTable<PendingChange, 'id'>;
    settings!: EntityTable<Settings, 'id'>;

    constructor() {
        super('CognitoDB');

        this.version(1).stores({
            entries: 'id, date, status, last_interacted_at, relevance_score',
            goals: 'id, category, active',
            pendingChanges: 'id, timestamp, entity, entity_id',
            settings: 'id'
        });
    }
}

// Export singleton instance
export const db = new CognitoDB();

// Initialize settings if they don't exist
db.on('ready', async () => {
    const settings = await db.settings.get('settings');
    if (!settings) {
        await db.settings.add({
            id: 'settings',
            lastSyncedAt: null
        });
    }
});

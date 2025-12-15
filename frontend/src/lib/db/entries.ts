/**
 * Entry CRUD operations for IndexedDB
 */

import { db, type Entry, type Conversation } from './index';
import { queueChange } from './sync';

/**
 * Create a new entry locally
 */
export async function createEntry(entry: Omit<Entry, 'id' | 'created_at' | 'updated_at'>): Promise<Entry> {
const now = new Date().toISOString();
const newEntry: Entry = {
...entry,
id: crypto.randomUUID(),
created_at: now,
updated_at: now
};

await db.entries.add(newEntry);
await queueChange({
id: crypto.randomUUID(),
type: 'create',
entity: 'entry',
entity_id: newEntry.id,
data: newEntry,
base_version: newEntry.version,
timestamp: now
});

return newEntry;
}

/**
 * Get entry by ID
 */
export async function getEntry(id: string): Promise<Entry | undefined> {
return await db.entries.get(id);
}

/**
 * Get all entries with optional filtering
 */
export async function getAllEntries(filter?: {
status?: 'active' | 'archived';
after_date?: string;
before_date?: string;
}): Promise<Entry[]> {
let query = db.entries.toCollection();

if (filter?.status) {
query = db.entries.where('status').equals(filter.status);
}

let results = await query.toArray();

if (filter?.after_date) {
results = results.filter(e => e.date >= filter.after_date!);
}

if (filter?.before_date) {
results = results.filter(e => e.date <= filter.before_date!);
}

return results.sort((a, b) => b.date.localeCompare(a.date));
}

/**
 * Update an existing entry
 */
export async function updateEntry(
id: string,
data: Partial<Omit<Entry, 'id' | 'created_at'>>
): Promise<Entry | undefined> {
const existing = await db.entries.get(id);
if (!existing) return undefined;

const updated: Entry = {
...existing,
...data,
updated_at: new Date().toISOString()
};

await db.entries.put(updated);
await queueChange({
id: crypto.randomUUID(),
type: 'update',
entity: 'entry',
entity_id: id,
data: updated,
base_version: existing.version,
timestamp: updated.updated_at
});

return updated;
}

/**
 * Delete an entry (soft delete by marking as archived)
 */
export async function deleteEntry(id: string): Promise<boolean> {
return await updateEntry(id, { status: 'archived' }) !== undefined;
}

/**
 * Add a conversation to an entry
 */
export async function addConversation(entryId: string, conversation: Conversation): Promise<Entry | undefined> {
const entry = await getEntry(entryId);
if (!entry) return undefined;

return await updateEntry(entryId, {
conversations: [...entry.conversations, conversation],
last_interacted_at: new Date().toISOString(),
interaction_count: entry.interaction_count + 1
});
}

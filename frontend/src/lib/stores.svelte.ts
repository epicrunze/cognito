/**
 * Svelte 5 rune-based reactive stores for global app state.
 */

export type User = {
    email: string;
    name: string;
    picture: string | null;
};

export type Proposal = {
    id: string;
    source_id: string;
    title: string;
    description: string | null;
    project_name: string | null;
    project_id: number | null;
    priority: number;
    due_date: string | null;
    estimated_minutes: number | null;
    labels: string[];
    source_type: string;
    confidential: boolean;
    status: string;
    vikunja_task_id: number | null;
    created_at: string | null;
};

export type Project = {
    id: number;
    title: string;
    description: string;
};

// ── Reactive state using Svelte 5 $state runes (declared in components)
// These are exported as plain reactive objects that components can import.

// We use a simple class-based store pattern compatible with Svelte 5 runes.

class AppState {
    user = $state<User | null>(null);
    proposals = $state<Proposal[]>([]);
    projects = $state<Project[]>([]);
    isExtracting = $state(false);
    extractError = $state<string | null>(null);
    authChecked = $state(false);

    addProposal(p: Proposal) {
        this.proposals = [p, ...this.proposals];
    }

    updateProposal(id: string, patch: Partial<Proposal>) {
        this.proposals = this.proposals.map((p) => (p.id === id ? { ...p, ...patch } : p));
    }

    removeProposal(id: string) {
        this.proposals = this.proposals.filter((p) => p.id !== id);
    }

    get pendingProposals(): Proposal[] {
        return this.proposals.filter((p) => p.status === 'pending');
    }
}

export const appState = new AppState();

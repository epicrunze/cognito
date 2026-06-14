/**
 * Per-project workspace state: the one markdown notes doc (autosaved on idle)
 * and the AI status briefing (with stale + generating states). Backed by
 * /api/projects/{id}/notes and /api/projects/{id}/briefing.
 */
import { projectsApi } from '$lib/api';
import { addToast } from '$lib/stores/toast.svelte';

type SaveState = 'saved' | 'saving';

function relativeLabel(iso: string | null): string {
  if (!iso) return '';
  const then = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z').getTime();
  if (Number.isNaN(then)) return '';
  const diff = Math.max(0, Date.now() - then);
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  return `${d}d ago`;
}

const AUTOSAVE_MS = 800;

class ProjectWorkspaceStore {
  projectId = $state<number | null>(null);

  // Notes
  notes = $state('');
  notesUpdatedAt = $state<string | null>(null);
  saveState = $state<SaveState>('saved');

  // Briefing
  briefing = $state('');
  briefingGeneratedAt = $state<string | null>(null);
  briefingStale = $state(false);
  briefingGenerating = $state(false);

  private saveTimer: ReturnType<typeof setTimeout> | null = null;

  get savedLabel(): string {
    const rel = relativeLabel(this.notesUpdatedAt);
    return rel ? `saved · ${rel}` : 'saved';
  }

  get briefingLabel(): string {
    const rel = relativeLabel(this.briefingGeneratedAt);
    return rel ? `generated ${rel}` : '';
  }

  /** Load notes + briefing for a project (no-op if already loaded). */
  async load(projectId: number) {
    if (this.projectId === projectId) return;
    this.projectId = projectId;
    this.notes = '';
    this.briefing = '';
    this.briefingStale = false;
    try {
      const [notes, briefing] = await Promise.all([
        projectsApi.getNotes(projectId),
        projectsApi.getBriefing(projectId),
      ]);
      if (this.projectId !== projectId) return; // navigated away
      this.notes = notes.content;
      this.notesUpdatedAt = notes.updated_at;
      this.briefing = briefing.text;
      this.briefingGeneratedAt = briefing.generated_at;
      this.briefingStale = briefing.stale;
    } catch {
      // Quiet — the workspace simply shows empty states.
    }
  }

  /** Update notes locally and schedule an idle autosave. */
  setNotes(value: string) {
    this.notes = value;
    this.saveState = 'saving';
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(() => this.flush(), AUTOSAVE_MS);
  }

  /** Persist notes immediately (e.g. on close). */
  async flush() {
    if (this.saveTimer) {
      clearTimeout(this.saveTimer);
      this.saveTimer = null;
    }
    if (this.projectId == null) return;
    const id = this.projectId;
    try {
      const res = await projectsApi.putNotes(id, this.notes);
      if (this.projectId === id) {
        this.notesUpdatedAt = res.updated_at;
        this.saveState = 'saved';
      }
    } catch {
      addToast('Failed to save notes', 'error');
      this.saveState = 'saved';
    }
  }

  async regenerateBriefing() {
    if (this.projectId == null || this.briefingGenerating) return;
    const id = this.projectId;
    this.briefingGenerating = true;
    try {
      const res = await projectsApi.regenerateBriefing(id);
      if (this.projectId === id) {
        this.briefing = res.text;
        this.briefingGeneratedAt = res.generated_at;
        this.briefingStale = false;
      }
    } catch {
      addToast('Failed to generate briefing', 'error');
    } finally {
      if (this.projectId === id) this.briefingGenerating = false;
    }
  }
}

export const projectWorkspaceStore = new ProjectWorkspaceStore();

import { revisionsApi } from '$lib/api';
import { addToast } from '$lib/stores/toast.svelte';
import type { Revision } from '$lib/types';

function createRevisionsStore() {
  let recent = $state<Revision[]>([]);
  let redoStack = $state<Revision[]>([]);
  let loading = $state(false);

  const canUndo = $derived(recent.some((r) => !r.undone));
  const canRedo = $derived(redoStack.length > 0);

  return {
    get recent() { return recent; },
    get redoStack() { return redoStack; },
    get loading() { return loading; },
    get canUndo() { return canUndo; },
    get canRedo() { return canRedo; },

    async fetchRecent() {
      try {
        const res = await revisionsApi.list();
        recent = res.revisions;
      } catch {
        // silent
      }
    },

    async undo(onSuccess?: () => void) {
      const revision = recent.find((r) => !r.undone);
      if (!revision || loading) return;

      loading = true;
      try {
        const result = await revisionsApi.undo(revision.id);

        if (result.conflict) {
          addToast('Task was modified since this action. Use Force Undo from Settings > Revision History.', 'error');
          loading = false;
          return;
        }

        if (result.already_undone || result.success) {
          recent = recent.map((r) =>
            r.id === revision.id ? { ...r, undone: true, undone_at: new Date().toISOString() } : r,
          );
          redoStack = [revision, ...redoStack];
          addToast(`Undid ${_actionLabel(revision)}`, 'success');
          onSuccess?.();
        } else if (result.error) {
          addToast(String(result.error), 'error');
        }
      } catch (e) {
        addToast(e instanceof Error ? e.message : 'Undo failed', 'error');
      } finally {
        loading = false;
      }
    },

    async redo(onSuccess?: () => void) {
      const revision = redoStack[0];
      if (!revision || loading) return;

      loading = true;
      try {
        const result = await revisionsApi.redo(revision.id);

        if (result.success) {
          redoStack = redoStack.slice(1);
          recent = recent.map((r) =>
            r.id === revision.id ? { ...r, undone: false, undone_at: null } : r,
          );
          addToast(`Redid ${_actionLabel(revision)}`, 'success');
          onSuccess?.();
        } else if (result.error) {
          addToast(String(result.error), 'error');
        }
      } catch (e) {
        addToast(e instanceof Error ? e.message : 'Redo failed', 'error');
      } finally {
        loading = false;
      }
    },

    async undoById(id: number, force = false, onSuccess?: () => void) {
      loading = true;
      try {
        const result = await revisionsApi.undo(id, force);

        if (result.conflict && !force) {
          addToast('Task was modified since this action. Use Force Undo.', 'error');
          loading = false;
          return result;
        }

        if (result.already_undone || result.success) {
          recent = recent.map((r) =>
            r.id === id ? { ...r, undone: true, undone_at: new Date().toISOString() } : r,
          );
          const rev = recent.find((r) => r.id === id);
          if (rev) addToast(`Undid ${_actionLabel(rev)}`, 'success');
          onSuccess?.();
        } else if (result.error) {
          addToast(String(result.error), 'error');
        }
        return result;
      } catch (e) {
        addToast(e instanceof Error ? e.message : 'Undo failed', 'error');
      } finally {
        loading = false;
      }
    },

    async redoById(id: number, onSuccess?: () => void) {
      loading = true;
      try {
        const result = await revisionsApi.redo(id);

        if (result.success) {
          recent = recent.map((r) =>
            r.id === id ? { ...r, undone: false, undone_at: null } : r,
          );
          const rev = recent.find((r) => r.id === id);
          if (rev) addToast(`Redid ${_actionLabel(rev)}`, 'success');
          onSuccess?.();
        } else if (result.error) {
          addToast(String(result.error), 'error');
        }
        return result;
      } catch (e) {
        addToast(e instanceof Error ? e.message : 'Redo failed', 'error');
      } finally {
        loading = false;
      }
    },

    clearRedoStack() {
      redoStack = [];
    },
  };
}

function _actionLabel(rev: Revision): string {
  const title = (rev.before_state?.title ?? rev.after_state?.title ?? `task #${rev.task_id}`) as string;
  const actions: Record<string, string> = {
    create: 'creation of',
    update: 'update to',
    complete: 'completion of',
    move: 'move of',
    delete: 'deletion of',
    auto_tag: 'auto-tag on',
  };
  return `${actions[rev.action_type] ?? rev.action_type} "${title}"`;
}

export const revisionsStore = createRevisionsStore();

import { projectsApi } from '$lib/api';
import type { Project } from '$lib/types';
import { addToast } from '$lib/stores/toast.svelte';

function createProjectsStore() {
  let projects = $state<Project[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  return {
    get projects() {
      return projects;
    },
    get loading() {
      return loading;
    },
    get error() {
      return error;
    },

    async create(data: { title: string; description?: string; hex_color?: string }) {
      const project = await projectsApi.create(data);
      await this.fetchAll();
      return project;
    },

    async update(id: number, data: Partial<Pick<Project, 'title' | 'description' | 'hex_color' | 'is_archived' | 'position'>>) {
      const snapshot = projects.map(p => ({ ...p }));
      // Optimistic update
      projects = projects.map(p => p.id === id ? { ...p, ...data } : p);
      try {
        await projectsApi.update(id, data);
      } catch (e) {
        projects = snapshot;
        addToast(e instanceof Error ? e.message : 'Failed to update project', 'error');
        throw e;
      }
    },

    async delete(id: number) {
      const snapshot = [...projects];
      projects = projects.filter(p => p.id !== id);
      try {
        await projectsApi.delete(id);
      } catch (e) {
        projects = snapshot;
        addToast(e instanceof Error ? e.message : 'Failed to delete project', 'error');
        throw e;
      }
    },

    async archive(id: number) {
      const snapshot = [...projects];
      projects = projects.filter(p => p.id !== id);
      try {
        await projectsApi.update(id, { is_archived: true });
      } catch (e) {
        projects = snapshot;
        addToast(e instanceof Error ? e.message : 'Failed to archive project', 'error');
        throw e;
      }
    },

    async unarchive(id: number) {
      await this.update(id, { is_archived: false });
      await this.fetchAll();
    },

    async reorder(id: number, newIndex: number) {
      let sorted = [...projects].sort((a, b) => (a.position || 0) - (b.position || 0));

      // Normalize if all positions are equal (e.g., all 0)
      const allSame = sorted.every(p => (p.position || 0) === (sorted[0]?.position || 0));
      if (allSame) {
        sorted = sorted.map((p, i) => ({ ...p, position: i }));
      }

      const currentIdx = sorted.findIndex(p => p.id === id);
      if (currentIdx === -1 || currentIdx === newIndex) return;

      let newPosition: number;
      if (newIndex === 0) {
        newPosition = (sorted[0]?.position || 0) - 1;
      } else if (newIndex >= sorted.length - 1) {
        newPosition = (sorted[sorted.length - 1]?.position || 0) + 1;
      } else {
        const before = sorted[newIndex < currentIdx ? newIndex - 1 : newIndex];
        const after = sorted[newIndex < currentIdx ? newIndex : newIndex + 1];
        newPosition = ((before?.position || 0) + (after?.position || 0)) / 2;
      }

      // Optimistic: update position AND re-sort array
      const snapshot = projects.map(p => ({ ...p }));
      projects = projects.map(p => p.id === id ? { ...p, position: newPosition } : p)
        .sort((a, b) => (a.position || 0) - (b.position || 0));

      try {
        await projectsApi.update(id, { position: newPosition });
      } catch (e) {
        projects = snapshot;
        addToast(e instanceof Error ? e.message : 'Failed to reorder project', 'error');
      }
    },

    async fetchAll() {
      loading = true;
      error = null;
      try {
        const res = await projectsApi.list();
        const defaults = {
          description: '',
          hex_color: '',
          identifier: '',
          is_archived: false,
          is_favorite: false,
          parent_project_id: null as number | null,
          position: 0,
          views: [] as Project['views'],
        };
        projects = res.projects.map((p) => ({ ...defaults, ...p }));
      } catch (e) {
        error = e instanceof Error ? e.message : 'Failed to load projects';
      } finally {
        loading = false;
      }
    },
  };
}

export const projectsStore = createProjectsStore();

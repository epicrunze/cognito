import { projectsApi } from '$lib/api';
import type { Project } from '$lib/types';

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

    async fetchAll() {
      loading = true;
      error = null;
      try {
        const res = await projectsApi.list();
        // The backend returns { id, title, description } from cache — fill defaults
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

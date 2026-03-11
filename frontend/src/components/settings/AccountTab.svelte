<script lang="ts">
  import { authStore, projectsStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import Button from '$components/ui/Button.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';
  import type { Project } from '$lib/types';
  import { projectsApi } from '$lib/api';

  let archivedProjects = $state<Project[]>([]);
  let loadingArchived = $state(false);
  let celebrationSounds = $state(typeof localStorage !== 'undefined' && localStorage.getItem('cognito-celebration-sounds') === 'true');

  function toggleCelebrationSounds() {
    celebrationSounds = !celebrationSounds;
    localStorage.setItem('cognito-celebration-sounds', String(celebrationSounds));
  }

  async function fetchArchived() {
    loadingArchived = true;
    try {
      const res = await projectsApi.list({ include_archived: true });
      archivedProjects = res.projects.filter(p => p.is_archived);
    } catch {
      archivedProjects = [];
    } finally {
      loadingArchived = false;
    }
  }

  async function handleUnarchive(id: number) {
    try {
      await projectsStore.unarchive(id);
      addToast('Project restored', 'success');
      archivedProjects = archivedProjects.filter(p => p.id !== id);
    } catch {
      // store handles error
    }
  }

  async function handleDeleteArchived(id: number) {
    try {
      await projectsStore.delete(id);
      addToast('Project deleted', 'success');
      archivedProjects = archivedProjects.filter(p => p.id !== id);
    } catch {
      // store handles error
    }
  }

  onMount(() => {
    fetchArchived();
  });
</script>

<!-- Account -->
<div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; margin-bottom: 16px;">
  <div style="margin-bottom: 16px;">
    <span style="font-size: 13px; color: var(--text-tertiary);">Signed in as</span>
    <div style="font-size: 15px; color: var(--text-primary); margin-top: 4px;">{authStore.user?.email ?? ''}</div>
  </div>
  <Button variant="outline" size="sm" onclick={async () => { await authStore.logout(); goto('/login'); }}>
    Sign out
  </Button>
</div>

<!-- Preferences -->
<div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; margin-bottom: 16px;">
  <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 12px; display: block;">Preferences</span>
  <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 13px; color: var(--text-primary);">
    <input type="checkbox" checked={celebrationSounds} onchange={toggleCelebrationSounds} style="accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer;" />
    Celebration sounds
    <span style="color: var(--text-tertiary); font-size: 12px;">Play a chime when completing tasks</span>
  </label>
</div>

<!-- Archived Projects -->
<div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px;">
  <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 12px; display: block;">Archived Projects</span>

  {#if loadingArchived}
    <div style="display: flex; flex-direction: column; gap: 8px;">
      {#each [1, 2] as _ (_)}
        <div style="display: flex; align-items: center; gap: 10px; padding: 8px 10px;">
          <Skeleton width={8} height={8} radius={4} />
          <Skeleton width="60%" height={13} />
          <Skeleton width={60} height={28} radius={6} />
        </div>
      {/each}
    </div>
  {:else if archivedProjects.length === 0}
    <span style="font-size: 13px; color: var(--text-tertiary);">No archived projects.</span>
  {:else}
    <div style="display: flex; flex-direction: column; gap: 6px;">
      {#each archivedProjects as project (project.id)}
        <div style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; font-size: 13px;">
          <div style="width: 8px; height: 8px; border-radius: 50%; background: {project.hex_color || 'var(--text-tertiary)'}; flex-shrink: 0;"></div>
          <span style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary);">{project.title}</span>
          <Button variant="outline" size="sm" onclick={() => handleUnarchive(project.id)}>
            Restore
          </Button>
          <Button variant="outline" size="sm" onclick={() => handleDeleteArchived(project.id)}>
            Delete
          </Button>
        </div>
      {/each}
    </div>
  {/if}
</div>

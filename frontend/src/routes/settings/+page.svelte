<script lang="ts">
  import { authStore, tasksStore, projectsStore } from '$lib/stores.svelte';
  import { revisionsStore } from '$lib/stores/revisions.svelte';
  import { configApi, projectsApi } from '$lib/api';
  import { addToast } from '$lib/stores/toast.svelte';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import Button from '$components/ui/Button.svelte';
  import type { Project } from '$lib/types';

  let systemPrompt = $state('');
  let saved = $state(false);
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let savedTimer: ReturnType<typeof setTimeout> | undefined;
  let archivedProjects = $state<Project[]>([]);
  let loadingArchived = $state(false);

  const actionIcons: Record<string, string> = {
    create: '+',
    update: '~',
    complete: '\u2713',
    move: '\u2192',
    delete: '\u00d7',
    auto_tag: '#',
  };

  const sourceBadgeColors: Record<string, { bg: string; color: string }> = {
    chat: { bg: 'rgba(99, 140, 255, 0.15)', color: 'rgb(130, 165, 255)' },
    proposal: { bg: 'rgba(180, 130, 255, 0.15)', color: 'rgb(190, 150, 255)' },
    auto_tag: { bg: 'rgba(232, 119, 46, 0.15)', color: 'var(--accent)' },
  };

  function timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }

  function getRevisionTitle(rev: { before_state: Record<string, unknown> | null; after_state: Record<string, unknown> | null; task_id: number }): string {
    return (rev.before_state?.title ?? rev.after_state?.title ?? `Task #${rev.task_id}`) as string;
  }

  async function handleUndo(id: number) {
    await revisionsStore.undoById(id, false, () => {
      tasksStore.fetchAll();
    });
  }

  async function handleRedo(id: number) {
    await revisionsStore.redoById(id, () => {
      tasksStore.fetchAll();
    });
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

  onMount(async () => {
    try {
      const config = await configApi.get();
      systemPrompt = config.system_prompt_override ?? '';
    } catch {
      // ignore fetch errors on mount
    }
    revisionsStore.fetchRecent();
    fetchArchived();
  });

  function handleInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        await configApi.update({ system_prompt_override: systemPrompt || null });
        saved = true;
        clearTimeout(savedTimer);
        savedTimer = setTimeout(() => { saved = false; }, 2000);
      } catch {
        // save failed silently
      }
    }, 500);
  }
</script>

<div style="max-width: 600px; padding: 40px 24px;">
  <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 24px;">Settings</h2>

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

  <!-- Navigation -->
  <div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; margin-bottom: 16px;">
    <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 12px; display: block;">Manage</span>
    <a href="/settings/labels" style="display: flex; align-items: center; gap: 8px; padding: 8px 0; color: var(--text-primary); text-decoration: none; font-size: 14px; transition: color 150ms;">
      Labels
      <span style="color: var(--text-tertiary); font-size: 12px;">→</span>
    </a>
  </div>

  <!-- AI Behavior -->
  <div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; margin-bottom: 16px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
      <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">AI Behavior</span>
      {#if saved}
        <span style="font-size: 12px; color: var(--accent); transition: opacity 150ms;">Saved</span>
      {/if}
    </div>
    <textarea
      bind:value={systemPrompt}
      oninput={handleInput}
      placeholder="Custom instructions for task extraction, e.g.:&#10;&#8226; Always categorize tasks into specific projects&#10;&#8226; Prefer high priority for deadline-sensitive items"
      style="width: 100%; min-height: 100px; padding: 10px 12px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; color: var(--text-primary); font-size: 14px; font-family: inherit; line-height: 1.5; resize: vertical; outline: none; transition: border-color 150ms;"
    ></textarea>
    <span style="font-size: 12px; color: var(--text-tertiary); margin-top: 8px; display: block;">
      These instructions guide how the AI extracts and categorizes tasks from your input.
    </span>
  </div>

  <!-- Archived Projects -->
  <div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; margin-bottom: 16px;">
    <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 12px; display: block;">Archived Projects</span>

    {#if loadingArchived}
      <span style="font-size: 13px; color: var(--text-tertiary);">Loading...</span>
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

  <!-- Revision History -->
  <div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px; margin-top: 16px;">
    <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 12px; display: block;">Revision History</span>

    {#if revisionsStore.recent.length === 0}
      <span style="font-size: 13px; color: var(--text-tertiary);">No revisions yet.</span>
    {:else}
      <div style="display: flex; flex-direction: column; gap: 6px;">
        {#each revisionsStore.recent.slice(0, 50) as rev (rev.id)}
          {@const badge = sourceBadgeColors[rev.source] ?? sourceBadgeColors.chat}
          <div style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; font-size: 13px;">
            <!-- Time -->
            <span style="flex-shrink: 0; width: 60px; color: var(--text-tertiary); font-size: 12px;">{timeAgo(rev.created_at)}</span>

            <!-- Action icon + type -->
            <span style="flex-shrink: 0; width: 20px; text-align: center; color: var(--text-secondary); font-weight: 600;">{actionIcons[rev.action_type] ?? '?'}</span>

            <!-- Task title -->
            <span style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary);">{getRevisionTitle(rev)}</span>

            <!-- Source badge -->
            <span style="flex-shrink: 0; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 500; background: {badge.bg}; color: {badge.color};">{rev.source === 'auto_tag' ? 'auto-tag' : rev.source}</span>

            <!-- Status -->
            {#if rev.undone}
              <span style="flex-shrink: 0; width: 50px; text-align: center; font-size: 12px; color: var(--accent);">Undone</span>
            {:else}
              <span style="flex-shrink: 0; width: 50px; text-align: center; font-size: 12px; color: var(--text-secondary);">Active</span>
            {/if}

            <!-- Undo / Redo button -->
            <div style="flex-shrink: 0; width: 60px;">
              {#if rev.undone}
                <Button variant="outline" size="sm" onclick={() => handleRedo(rev.id)} disabled={revisionsStore.loading}>
                  Redo
                </Button>
              {:else}
                <Button variant="outline" size="sm" onclick={() => handleUndo(rev.id)} disabled={revisionsStore.loading}>
                  Undo
                </Button>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

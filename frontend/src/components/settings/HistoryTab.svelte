<script lang="ts">
  import { onMount } from 'svelte';
  import { tasksStore } from '$lib/stores.svelte';
  import { revisionsStore } from '$lib/stores/revisions.svelte';
  import Button from '$components/ui/Button.svelte';
  import Skeleton from '$components/ui/Skeleton.svelte';

  let fetching = $state(true);

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

  onMount(async () => {
    await revisionsStore.fetchRecent();
    fetching = false;
  });
</script>

<div style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 8px;">
  <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 12px; display: block;">Revision History</span>

  {#if fetching}
    <div style="display: flex; flex-direction: column; gap: 6px;">
      {#each [1, 2, 3, 4] as _ (_)}
        <div style="display: flex; align-items: center; gap: 10px; padding: 8px 10px;">
          <Skeleton width={50} height={12} />
          <Skeleton width={20} height={14} />
          <Skeleton width="50%" height={13} />
          <Skeleton width={50} height={18} radius={9} />
          <Skeleton width={40} height={12} />
          <Skeleton width={50} height={28} radius={6} />
        </div>
      {/each}
    </div>
  {:else if revisionsStore.recent.length === 0}
    <span style="font-size: 13px; color: var(--text-tertiary);">No revisions yet.</span>
  {:else}
    <div style="display: flex; flex-direction: column; gap: 6px;">
      {#each revisionsStore.recent.slice(0, 50) as rev (rev.id)}
        {@const badge = sourceBadgeColors[rev.source] ?? sourceBadgeColors.chat}
        <div style="display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: var(--bg-base); border: 1px solid var(--border-default); border-radius: 6px; font-size: 13px;">
          <span style="flex-shrink: 0; width: 60px; color: var(--text-tertiary); font-size: 12px;">{timeAgo(rev.created_at)}</span>
          <span style="flex-shrink: 0; width: 20px; text-align: center; color: var(--text-secondary); font-weight: 600;">{actionIcons[rev.action_type] ?? '?'}</span>
          <span style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary);">{getRevisionTitle(rev)}</span>
          <span style="flex-shrink: 0; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 500; background: {badge.bg}; color: {badge.color};">{rev.source === 'auto_tag' ? 'auto-tag' : rev.source}</span>
          {#if rev.undone}
            <span style="flex-shrink: 0; width: 50px; text-align: center; font-size: 12px; color: var(--accent);">Undone</span>
          {:else}
            <span style="flex-shrink: 0; width: 50px; text-align: center; font-size: 12px; color: var(--text-secondary);">Active</span>
          {/if}
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

<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { projectsStore, tasksStore } from '$lib/stores.svelte';
  import { projectsApi } from '$lib/api';
  import EmptyState from '$components/ui/EmptyState.svelte';

  // One-line AI summary per project (from the stored briefing, if any).
  let briefings = $state<Record<number, string>>({});

  const projects = $derived(projectsStore.projects.filter((p) => !p.is_archived));

  function counts(projectId: number) {
    const ts = tasksStore.tasks.filter((t) => t.project_id === projectId);
    return { open: ts.filter((t) => !t.done).length, done: ts.filter((t) => t.done).length };
  }

  onMount(async () => {
    if (tasksStore.tasks.length === 0) tasksStore.fetchAll();
    // Pull each project's existing briefing for an at-a-glance summary.
    const entries = await Promise.all(
      projectsStore.projects.map(async (p) => {
        try {
          const b = await projectsApi.getBriefing(p.id);
          return [p.id, b.text] as const;
        } catch {
          return [p.id, ''] as const;
        }
      })
    );
    briefings = Object.fromEntries(entries.filter(([, text]) => text));
  });
</script>

<div class="picker">
  {#if projects.length === 0}
    <EmptyState title="No projects yet" hint="Projects appear here as you organize your thoughts." />
  {:else}
    {#each projects as p (p.id)}
      {@const c = counts(p.id)}
      <button class="project-card" onclick={() => goto(`/project/${p.id}`)}>
        <div class="card-head">
          <span class="dot" style="background: {p.hex_color || 'var(--text-tertiary)'};"></span>
          <span class="name">{p.title}</span>
          <span class="counts">{c.open} open · {c.done} completed</span>
        </div>
        {#if briefings[p.id]}
          <div class="summary">
            <svg width="9" height="9" viewBox="0 0 10 10" style="flex-shrink: 0; margin-top: 4px;"><rect x="2.2" y="2.2" width="5.6" height="5.6" fill="none" stroke="var(--ai)" stroke-width="1.2" transform="rotate(45 5 5)"></rect></svg>
            <span>{briefings[p.id]}</span>
          </div>
        {/if}
      </button>
    {/each}
  {/if}
</div>

<style>
  .picker {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 20px;
    max-width: 720px;
    margin: 0 auto;
  }
  .project-card {
    text-align: left;
    width: 100%;
    background: var(--surface-card);
    border: 1px solid transparent;
    border-radius: var(--radius-card);
    box-shadow: var(--shadow-rest);
    padding: 16px 18px;
    cursor: pointer;
    transition: background var(--t-fast) var(--ease-out), box-shadow var(--t-fast) var(--ease-out), transform var(--t-normal) var(--ease-out);
  }
  .project-card:hover {
    background: var(--surface-card-hover);
    box-shadow: var(--shadow-lift);
    transform: translateY(-2px);
  }
  .card-head {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .name {
    font: var(--type-section);
    font-size: var(--text-lg);
    color: var(--text-primary);
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .counts {
    font: var(--type-data);
    color: var(--text-tertiary);
    flex-shrink: 0;
  }
  .summary {
    display: flex;
    gap: 7px;
    margin-top: 10px;
    font-family: var(--font-sans);
    font-size: 13px;
    line-height: var(--leading-normal);
    color: var(--text-secondary);
    text-wrap: pretty;
  }
</style>

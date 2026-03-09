<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import TaskList from '$components/features/TaskList.svelte';

  const projectId = $derived(Number($page.params.id));
</script>

<div style="display: flex; align-items: center; gap: 6px; padding: 10px 24px 0; flex-shrink: 0;">
  <button
    style="height: 28px; padding: 0 12px; font-size: 12.5px; font-weight: 500; border-radius: 6px; border: 1px solid var(--accent); background: var(--accent-subtle); color: var(--accent); cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
  >List</button>
  <button
    onclick={() => goto(`/project/${projectId}/kanban`)}
    style="height: 28px; padding: 0 12px; font-size: 12.5px; font-weight: 500; border-radius: 6px; border: 1px solid var(--border-default); background: transparent; color: var(--text-secondary); cursor: pointer; font-family: var(--font-sans); transition: all 150ms;"
  >Kanban</button>
</div>

<TaskList {projectId} />

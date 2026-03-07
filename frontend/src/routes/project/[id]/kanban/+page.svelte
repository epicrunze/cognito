<script lang="ts">
  import { page } from '$app/stores';

  const projectId = $derived(Number($page.params.id));
</script>

<div style="display: flex; align-items: center; justify-content: center; padding: 80px 24px;">
  <span style="font-size: 15px; color: var(--text-tertiary);">Kanban view for project {projectId} coming soon</span>
</div>

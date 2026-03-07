<script lang="ts">
  import { page } from '$app/stores';
  import TaskList from '$components/features/TaskList.svelte';

  const projectId = $derived(Number($page.params.id));
</script>

<TaskList {projectId} />

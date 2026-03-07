<script lang="ts">
  import type { Task } from '$lib/types';
  import TaskList from '$components/features/TaskList.svelte';

  function overdueFilter(t: Task): boolean {
    if (!t.due_date || t.done) return false;
    return new Date(t.due_date) < new Date();
  }
</script>

<TaskList filter={overdueFilter} />

<script lang="ts">
  import type { Task } from '$lib/types';
  import TaskList from '$components/features/TaskList.svelte';

  const sevenDays = 7 * 24 * 60 * 60 * 1000;

  function upcomingFilter(t: Task): boolean {
    if (!t.due_date || t.done) return false;
    const due = new Date(t.due_date).getTime();
    const now = Date.now();
    return due >= now && due <= now + sevenDays;
  }
</script>

<TaskList filter={upcomingFilter} />

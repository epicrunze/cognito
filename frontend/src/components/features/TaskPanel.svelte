<script lang="ts">
  import type { Task, TaskProposal } from '$lib/types';
  import SlideOver from '$components/ui/SlideOver.svelte';
  import TaskDetailContent from './TaskDetailContent.svelte';

  let {
    mode = 'create' as 'create' | 'edit' | 'proposal',
    open = false,
    onclose,
    defaultProjectId,
    task,
    proposal,
    onupdate,
  }: {
    mode?: 'create' | 'edit' | 'proposal';
    open: boolean;
    onclose?: () => void;
    defaultProjectId?: number;
    task?: Task;
    proposal?: TaskProposal;
    onupdate?: (p: TaskProposal) => void;
  } = $props();
</script>

<SlideOver {open} {onclose}>
  <div style="overflow-y: auto; max-height: 100vh;">
    <TaskDetailContent {mode} {task} {proposal} {defaultProjectId} {onclose} {onupdate} />
  </div>
</SlideOver>

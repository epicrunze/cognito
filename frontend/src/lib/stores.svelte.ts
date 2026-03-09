// Re-export all stores for convenience
export { authStore } from '$lib/stores/auth.svelte';
export { tasksStore } from '$lib/stores/tasks.svelte';
export { projectsStore } from '$lib/stores/projects.svelte';
export { proposalsStore } from '$lib/stores/proposals.svelte';
export { labelsStore } from '$lib/stores/labels.svelte';
export { updateTask, toggleDone, deleteTask } from '$lib/stores/taskMutations';

<script lang="ts">
  import { toasts, removeToast } from '$lib/stores/toast.svelte';
  import Toast from './Toast.svelte';
</script>

<div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000; display: flex; flex-direction: column; gap: 8px;">
  {#each toasts.value as toast (toast.id)}
    <Toast message={toast.message} variant={toast.variant} onclose={() => removeToast(toast.id)} />
  {/each}
</div>

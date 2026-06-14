<script lang="ts">
  import { toasts, removeToast } from '$lib/stores/toast.svelte';
  import Toast from './Toast.svelte';
</script>

<!-- Bottom-left: clear of the FAB + detail panel, which own the right edge. -->
<div style="position: fixed; bottom: 20px; left: 20px; z-index: 1000; display: flex; flex-direction: column; gap: 8px; align-items: flex-start;">
  {#each toasts.value as toast (toast.id)}
    <Toast
      message={toast.message}
      variant={toast.variant}
      ai={toast.ai}
      action={toast.action}
      onclose={() => removeToast(toast.id)}
    />
  {/each}
</div>

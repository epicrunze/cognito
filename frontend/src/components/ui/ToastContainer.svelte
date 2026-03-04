<script lang="ts">
  import { fly } from 'svelte/transition';
  import Toast from './Toast.svelte';
  import { toasts, removeToast } from '$lib/stores/toast.svelte';
</script>

<div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end">
  {#each toasts.value as toast (toast.id)}
    <div transition:fly={{ y: 20, duration: 150 }}>
      <Toast message={toast.message} variant={toast.variant} ondismiss={() => removeToast(toast.id)} />
    </div>
  {/each}
</div>

import { addToast } from '$lib/stores/toast.svelte';

export async function optimisticUpdate<T>(options: {
  apply: () => void;
  apiCall: () => Promise<T>;
  rollback: () => void;
  errorMessage?: string;
}): Promise<T | undefined> {
  const { apply, apiCall, rollback, errorMessage = 'Something went wrong' } = options;

  apply();

  try {
    return await apiCall();
  } catch (err) {
    rollback();
    const detail = err instanceof Error ? err.message : String(err);
    console.error(`[optimistic] ${errorMessage}:`, detail);
    addToast(`${errorMessage}: ${detail}`, 'error');
    return undefined;
  }
}

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
  } catch {
    rollback();
    addToast(errorMessage, 'error');
    return undefined;
  }
}

import { authApi, ApiError } from '$lib/api';

interface AuthUser {
  email: string;
  name: string;
  picture?: string;
}

function createAuthStore() {
  let user = $state<AuthUser | null>(null);
  let loading = $state(true);
  const authenticated = $derived(user !== null);

  async function check() {
    loading = true;
    try {
      user = await authApi.me();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        user = null;
      } else {
        user = null;
      }
    } finally {
      loading = false;
    }
  }

  async function logout() {
    try {
      await authApi.logout();
    } catch {
      // ignore errors
    }
    user = null;
  }

  return {
    get user() { return user; },
    get loading() { return loading; },
    get authenticated() { return authenticated; },
    check,
    logout,
  };
}

export const authStore = createAuthStore();

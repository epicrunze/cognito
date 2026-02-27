<!--
  AuthStatusBadge.svelte
  
  Shows current auth state indicator when using cached/stale credentials.
-->
<script lang="ts">
	import { authSource } from '$lib/stores/auth';
	import { isOnline } from '$lib/stores/sync';
</script>

{#if !$isOnline && $authSource === 'stale'}
	<span
		class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-warning/20 text-warning"
		title="Using cached credentials - some features may be limited"
	>
		⚠ Offline Mode
	</span>
{/if}

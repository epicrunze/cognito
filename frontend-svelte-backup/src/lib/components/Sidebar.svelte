<script lang="ts">
	import { page } from '$app/stores';
	import { NAV_ITEMS } from '$lib/theme';

	let isCollapsed = $state(true);
	let isHovering = $state(false);

	// Using $derived for Svelte 5 runes mode
	let currentPath = $derived($page.url.pathname);
	let showExpanded = $derived(!isCollapsed || isHovering);

	function isActive(href: string): boolean {
		if (href === '/') {
			return currentPath === '/';
		}
		return currentPath.startsWith(href);
	}

	function handleMouseEnter() {
		isHovering = true;
	}

	function handleMouseLeave() {
		isHovering = false;
	}
</script>

<aside
	class="sidebar hidden lg:flex flex-col {showExpanded ? 'expanded' : 'collapsed'}"
	onmouseenter={handleMouseEnter}
	onmouseleave={handleMouseLeave}
	role="navigation"
>
	<!-- Logo / Brand -->
	<div class="p-4 border-b border-surface-300 dark:border-surface-700">
		<a href="/" class="flex items-center gap-3">
			<span class="text-2xl">🧠</span>
			{#if showExpanded}
				<span class="text-lg font-bold text-primary-dark dark:text-primary-light">Cognito</span>
			{/if}
		</a>
	</div>

	<!-- Nav Items -->
	<nav class="flex-1 py-4">
		{#each NAV_ITEMS as item}
			<a
				href={item.href}
				class="flex items-center gap-3 px-4 py-3 mx-2 rounded-lg transition-colors
					{isActive(item.href)
					? 'bg-primary text-white'
					: 'text-text-secondary hover:bg-primary/10 hover:text-primary'}"
				title={isCollapsed && !isHovering ? item.label : undefined}
			>
				<span class="text-xl flex-shrink-0">{item.icon}</span>
				{#if showExpanded}
					<span class="font-medium">{item.label}</span>
				{/if}
			</a>
		{/each}
	</nav>

	<!-- Collapse Toggle -->
	<div class="p-4 border-t border-surface-300 dark:border-surface-700">
		<button
			onclick={() => (isCollapsed = !isCollapsed)}
			class="flex items-center gap-3 w-full px-4 py-2 rounded-lg text-text-secondary hover:bg-primary/10 transition-colors"
			title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
		>
			<span class="text-xl">{isCollapsed ? '→' : '←'}</span>
			{#if showExpanded}
				<span class="text-sm">{isCollapsed ? 'Expand' : 'Collapse'}</span>
			{/if}
		</button>
	</div>
</aside>

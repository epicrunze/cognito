<script lang="ts">
	import { page } from '$app/stores';
	import { NAV_ITEMS } from '$lib/theme';

	// Using $derived for Svelte 5 runes mode
	let currentPath = $derived($page.url.pathname);

	function isActive(href: string): boolean {
		if (href === '/') {
			return currentPath === '/';
		}
		return currentPath.startsWith(href);
	}
</script>

<nav class="bottom-nav flex justify-around items-center lg:hidden">
	{#each NAV_ITEMS as item}
		<a
			href={item.href}
			class="flex flex-col items-center gap-1 py-2 px-4 rounded-lg transition-colors
				{isActive(item.href)
				? 'text-primary bg-primary/10'
				: 'text-text-secondary hover:text-primary hover:bg-primary/5'}"
		>
			<span class="text-xl">{item.icon}</span>
			<span class="text-xs font-medium">{item.label}</span>
		</a>
	{/each}
</nav>

<script lang="ts">
  import ToastContainer from '../components/ui/ToastContainer.svelte';
  import Sidebar from '../components/features/Sidebar.svelte';
  import Button from '../components/ui/Button.svelte';
  import Input from '../components/ui/Input.svelte';
  import Kbd from '../components/ui/Kbd.svelte';
  import { shortcuts } from '$lib/shortcuts';
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();

  let searchQuery = $state('');
  let searchWrapper: HTMLDivElement | undefined = $state();

  shortcuts.register('/', () => {
    searchWrapper?.querySelector('input')?.focus();
  });
  shortcuts.register('n', () => {
    // placeholder — wired up in T-019
  });
  shortcuts.register('Escape', () => {
    // placeholder — close panel when panels exist
  });
</script>

<svelte:window onkeydown={shortcuts.handleKeydown} />

<div class="flex h-screen overflow-hidden bg-base">
  <Sidebar />

  <div class="flex-1 flex flex-col min-w-0">
    <!-- Header Bar -->
    <header class="h-[52px] bg-surface border-b border-default flex items-center justify-between px-4 shrink-0">
      <div bind:this={searchWrapper} class="relative w-80 max-w-full">
        <Input
          bind:value={searchQuery}
          placeholder="Search tasks..."
          class="pr-10"
        />
        <div class="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
          <Kbd>/</Kbd>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm">
          New
          <Kbd>N</Kbd>
        </Button>
        <Button variant="ghost" size="sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="color: var(--ai-accent);" aria-hidden="true">
            <path d="M12 2l1.5 4.6H18l-3.9 2.8 1.5 4.6L12 11.2l-3.6 2.8 1.5-4.6L6 6.6h4.5L12 2z" fill="var(--ai-accent)"/>
            <path d="M19 14l.8 2.4H22l-2 1.5.8 2.4L19 19l-1.8 1.3.8-2.4L16 16.4h2.2L19 14z" fill="var(--ai-accent)" opacity="0.7"/>
          </svg>
          AI
        </Button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto p-6">
      {@render children()}
    </main>
  </div>
</div>

<ToastContainer />

<script lang="ts">
  import { page } from '$app/stores';

  const smartFilters = [
    { label: 'All Tasks', href: '/', count: 24 },
    { label: 'Upcoming', href: '/upcoming', count: 8 },
    { label: 'Overdue', href: '/overdue', count: 3, overdue: true },
  ];

  const projects = [
    { label: 'PhD Research', color: '#6366F1', count: 12 },
    { label: 'Home Reno', color: '#F97316', count: 5 },
    { label: 'Side Project', color: '#22C55E', count: 9 },
    { label: 'Reading List', color: '#EAB308', count: 7 },
  ];
</script>

<nav class="w-sidebar bg-sidebar border-r border-default flex flex-col h-full p-4 shrink-0">
  <!-- Branding -->
  <div class="flex items-center gap-2 mb-5">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17 5.8 21.3l2.4-7.4L2 9.4h7.6L12 2z"
        fill="var(--accent)"
      />
    </svg>
    <span class="font-semibold text-primary text-base">Cognito</span>
  </div>

  <!-- Smart Filters -->
  <div class="mb-4">
    {#each smartFilters as filter}
      {@const isActive = $page.url.pathname === filter.href}
      <a
        href={filter.href}
        class="flex items-center justify-between gap-2 px-2 py-1.5 rounded-input text-sm font-medium duration-fast
          {isActive
          ? 'bg-accent-subtle text-accent'
          : 'text-secondary hover:bg-surface-hover hover:text-primary'}"
      >
        <div class="flex items-center gap-2">
          {#if filter.href === '/'}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>
              <line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/>
              <line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
            </svg>
          {:else if filter.href === '/upcoming'}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          {:else}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          {/if}
          {filter.label}
        </div>
        <span
          class="text-xs px-1.5 py-0.5 rounded-pill font-medium
            {filter.overdue
            ? 'bg-priority-urgent/10 text-overdue'
            : isActive
            ? 'bg-accent/10 text-accent'
            : 'bg-surface-hover text-tertiary'}"
        >
          {filter.count}
        </span>
      </a>
    {/each}
  </div>

  <!-- Projects Divider -->
  <div class="flex items-center gap-2 mb-2 px-2">
    <span class="text-xs font-medium text-tertiary uppercase tracking-wide">Projects</span>
    <hr class="flex-1 border-default" />
  </div>

  <!-- Projects List -->
  <div class="mb-4 flex-1">
    {#each projects as project}
      <div class="flex items-center justify-between gap-2 px-2 py-1.5 rounded-input text-sm text-secondary hover:bg-surface-hover hover:text-primary duration-fast cursor-pointer">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full shrink-0" style="background-color: {project.color};"></span>
          {project.label}
        </div>
        <span class="text-xs text-tertiary">{project.count}</span>
      </div>
    {/each}
  </div>

  <!-- Bottom Section -->
  <div class="mt-auto flex flex-col gap-0.5">
    <a
      href="/extract"
      class="flex items-center gap-2 px-2 py-1.5 rounded-input text-sm font-medium duration-fast text-ai-accent hover:bg-surface-hover"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 2l1.5 4.6H18l-3.9 2.8 1.5 4.6L12 11.2l-3.6 2.8 1.5-4.6L6 6.6h4.5L12 2z" fill="var(--ai-accent)"/>
        <path d="M19 14l.8 2.4H22l-2 1.5.8 2.4L19 19l-1.8 1.3.8-2.4L16 16.4h2.2L19 14z" fill="var(--ai-accent)" opacity="0.7"/>
        <path d="M6 14l.8 2.4H9l-2 1.5.8 2.4L6 19l-1.8 1.3.8-2.4L3 16.4h2.2L6 14z" fill="var(--ai-accent)" opacity="0.5"/>
      </svg>
      AI Extract
    </a>
    <a
      href="/settings"
      class="flex items-center gap-2 px-2 py-1.5 rounded-input text-sm text-secondary hover:bg-surface-hover hover:text-primary duration-fast"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
      </svg>
      Settings
    </a>

    <!-- User Info -->
    <div class="flex items-center gap-2 mt-2 pt-2 border-t border-default px-1">
      <div class="w-6 h-6 rounded-full bg-accent flex items-center justify-center text-on-accent text-xs font-semibold shrink-0">
        U
      </div>
      <span class="text-xs text-secondary truncate">user@example.com</span>
    </div>
  </div>
</nav>

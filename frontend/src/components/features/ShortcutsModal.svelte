<script lang="ts">
  import SlideOver from '$components/ui/SlideOver.svelte';
  import Kbd from '$components/ui/Kbd.svelte';

  let {
    open = false,
    onclose,
  }: {
    open: boolean;
    onclose?: () => void;
  } = $props();

  const sections = [
    {
      title: 'Navigation',
      shortcuts: [
        { key: 'J', label: 'Next task' },
        { key: 'K', label: 'Previous task' },
        { key: 'Enter', label: 'Open task' },
      ],
    },
    {
      title: 'Actions',
      shortcuts: [
        { key: 'X', label: 'Toggle done' },
        { key: 'E', label: 'Edit task' },
        { key: '1–5', label: 'Set priority' },
      ],
    },
    {
      title: 'Global',
      shortcuts: [
        { key: 'N', label: 'New task' },
        { key: '/', label: 'Focus search' },
        { key: 'Esc', label: 'Close / deselect' },
        { key: '?', label: 'This help' },
      ],
    },
  ];
</script>

<SlideOver {open} {onclose}>
  <div style="padding: 24px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
      <h2 style="font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0;">Keyboard Shortcuts</h2>
      <button
        onclick={onclose}
        style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 18px; padding: 4px 8px; line-height: 1;"
      >&times;</button>
    </div>

    {#each sections as section (section.title)}
      <div style="margin-bottom: 20px;">
        <h3 style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-tertiary); margin: 0 0 10px 0;">{section.title}</h3>
        {#each section.shortcuts as shortcut (shortcut.key)}
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border-subtle);">
            <span style="font-size: 14px; color: var(--text-secondary);">{shortcut.label}</span>
            <Kbd>{shortcut.key}</Kbd>
          </div>
        {/each}
      </div>
    {/each}
  </div>
</SlideOver>

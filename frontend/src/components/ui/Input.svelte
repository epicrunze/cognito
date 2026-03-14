<script lang="ts">
  let {
    placeholder = '',
    value = $bindable(''),
    height = 34,
    type = 'text' as 'text' | 'number',
    oninput,
    onkeydown,
    style = '',
    ref = $bindable<HTMLInputElement | undefined>(undefined),
  }: {
    placeholder?: string;
    value?: string;
    height?: number;
    type?: 'text' | 'number';
    oninput?: (e: Event) => void;
    onkeydown?: (e: KeyboardEvent) => void;
    style?: string;
    ref?: HTMLInputElement | undefined;
  } = $props();
  let focused = $state(false);
</script>

<input
  bind:this={ref}
  type={type}
  {placeholder}
  bind:value
  onfocus={() => focused = true}
  onblur={() => focused = false}
  {oninput}
  {onkeydown}
  style="height: {height}px; padding: 0 12px; font-size: 13.5px; font-weight: 400; color: var(--text-primary); background: var(--bg-elevated); border: 1px solid {focused ? 'var(--accent)' : 'var(--border-default)'}; border-radius: 8px; outline: none; box-shadow: {focused ? '0 0 0 2px rgba(232,119,46,0.25)' : 'none'}; transition: all var(--transition-fast) ease-out; min-width: 0; font-family: var(--font-sans); {style}"
/>

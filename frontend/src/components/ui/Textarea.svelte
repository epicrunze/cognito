<script lang="ts">
  let {
    placeholder = '',
    value = $bindable(''),
    rows = 3,
    onkeydown,
    oninput,
    onpaste,
  }: {
    placeholder?: string;
    value?: string;
    rows?: number;
    onkeydown?: (e: KeyboardEvent) => void;
    oninput?: (e: Event) => void;
    onpaste?: (e: ClipboardEvent) => void;
  } = $props();
  let focused = $state(false);
</script>

<textarea
  bind:value
  {placeholder}
  {rows}
  onfocus={() => focused = true}
  onblur={() => focused = false}
  {onkeydown}
  {oninput}
  {onpaste}
  style="padding: 10px 14px; font-size: 15px; font-weight: 400; color: var(--text-primary); background: var(--bg-elevated); border: 1px solid {focused ? 'var(--accent)' : 'var(--border-default)'}; border-radius: 8px; outline: none; box-shadow: {focused ? '0 0 0 2px rgba(232,119,46,0.25)' : 'none'}; transition: all var(--transition-fast) ease-out; width: 100%; resize: vertical; line-height: 1.55; font-family: var(--font-sans);"
></textarea>

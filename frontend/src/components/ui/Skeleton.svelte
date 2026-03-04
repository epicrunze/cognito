<script lang="ts">
  let {
    width = '100%',
    height = '1rem',
    rounded = 'rounded-input',
    ...restProps
  }: {
    width?: string;
    height?: string;
    rounded?: string;
    [key: string]: unknown;
  } = $props();
</script>

<div
  class="animate-pulse bg-surface-hover {rounded}"
  style="width: {width}; height: {height};"
  {...restProps}
></div>

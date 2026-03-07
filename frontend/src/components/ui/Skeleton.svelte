<script lang="ts">
  let { width = '100%', height = 14, radius = 6 }: { width?: string | number; height?: number; radius?: number } = $props();
</script>

<div
  style="width: {typeof width === 'number' ? `${width}px` : width}; height: {height}px; border-radius: {radius}px;"
  class="bg-elevated animate-pulse"
  style:animation="pulse 1.5s ease-in-out infinite"
></div>

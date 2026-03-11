<script lang="ts">
  import { PRESET_COLORS } from '$lib/constants';

  let { value, onchange }: { value: string; onchange: (hex: string) => void } = $props();

  let open = $state(false);
  let showCustom = $state(false);
  let pickerEl = $state<HTMLDivElement | null>(null);
  let hexInput = $state('');
  let hexValid = $state(true);

  // HSL state for custom picker
  let hue = $state(0);
  let saturation = $state(100);
  let lightness = $state(50);

  // Drag state
  let dragging = $state<'hue' | 'sl' | null>(null);
  let hueEl = $state<HTMLDivElement | null>(null);
  let slEl = $state<HTMLDivElement | null>(null);

  // --- HSL <-> Hex conversion utilities ---

  function hslToHex(h: number, s: number, l: number): string {
    s /= 100;
    l /= 100;
    const a = s * Math.min(l, 1 - l);
    const f = (n: number) => {
      const k = (n + h / 30) % 12;
      const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
      return Math.round(255 * color).toString(16).padStart(2, '0');
    };
    return `#${f(0)}${f(8)}${f(4)}`.toUpperCase();
  }

  function hexToHsl(hex: string): [number, number, number] {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    let h = 0;
    let s = 0;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
        case g: h = ((b - r) / d + 2) / 6; break;
        case b: h = ((r - g) / d + 4) / 6; break;
      }
    }
    return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
  }

  // Sync HSL state when value changes externally
  $effect(() => {
    if (dragging) return; // Don't fight with drag updates
    if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
      const [h, s, l] = hexToHsl(value);
      hue = h;
      saturation = s;
      lightness = l;
      hexInput = value.toUpperCase();
    }
  });

  const customHex = $derived(hslToHex(hue, saturation, lightness));

  function toggle() {
    open = !open;
    if (open) {
      showCustom = false;
      if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
        hexInput = value.toUpperCase();
      }
    }
  }

  function selectPreset(hex: string) {
    onchange(hex);
    open = false;
  }

  // --- Hue drag ---

  function updateHue(clientX: number) {
    if (!hueEl) return;
    const rect = hueEl.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    hue = Math.round((x / rect.width) * 360);
    hexInput = hslToHex(hue, saturation, lightness);
    hexValid = true;
    onchange(hexInput);
  }

  function handleHueDown(e: MouseEvent) {
    e.preventDefault();
    dragging = 'hue';
    updateHue(e.clientX);
  }

  // --- SL drag ---

  function updateSL(clientX: number, clientY: number) {
    if (!slEl) return;
    const rect = slEl.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    const y = Math.max(0, Math.min(clientY - rect.top, rect.height));
    saturation = Math.round((x / rect.width) * 100);
    lightness = Math.round((1 - y / rect.height) * 100);
    hexInput = hslToHex(hue, saturation, lightness);
    hexValid = true;
    onchange(hexInput);
  }

  function handleSLDown(e: MouseEvent) {
    e.preventDefault();
    dragging = 'sl';
    updateSL(e.clientX, e.clientY);
  }

  // --- Global mousemove/mouseup for drag ---

  $effect(() => {
    if (!dragging) return;

    function handleMove(e: MouseEvent) {
      e.preventDefault();
      if (dragging === 'hue') {
        updateHue(e.clientX);
      } else if (dragging === 'sl') {
        updateSL(e.clientX, e.clientY);
      }
    }

    function handleUp() {
      dragging = null;
    }

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);
    return () => {
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
    };
  });

  function handleHexInput(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    hexInput = val;
    if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
      hexValid = true;
      onchange(val);
    } else {
      hexValid = false;
    }
  }

  // Click-outside to close
  $effect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (pickerEl && !pickerEl.contains(e.target as Node)) {
        open = false;
      }
    }
    document.addEventListener('mousedown', handleClickOutside, true);
    return () => document.removeEventListener('mousedown', handleClickOutside, true);
  });
</script>

<div class="color-picker" bind:this={pickerEl}>
  <button
    class="trigger"
    style="background: {value || 'var(--text-tertiary)'};"
    onclick={toggle}
    aria-label="Pick color"
  ></button>

  {#if open}
    <div class="popup">
      <!-- Preset swatches: 4x2 grid -->
      <div class="preset-grid">
        {#each PRESET_COLORS as color (color.hex)}
          <button
            class="preset-swatch"
            class:selected={value === color.hex}
            style="background: {color.hex};"
            title={color.name}
            onclick={() => selectPreset(color.hex)}
          ></button>
        {/each}
      </div>

      <!-- Custom toggle -->
      <button class="custom-toggle" onclick={() => showCustom = !showCustom}>
        {showCustom ? 'Hide custom' : 'Custom...'}
      </button>

      {#if showCustom}
        <div class="custom-section">
          <!-- Hue strip -->
          <div
            bind:this={hueEl}
            class="hue-strip"
            role="slider"
            tabindex="0"
            aria-label="Hue"
            aria-valuemin={0}
            aria-valuemax={360}
            aria-valuenow={hue}
            onmousedown={handleHueDown}
          >
            <div class="hue-thumb" style="left: {(hue / 360) * 100}%;"></div>
          </div>

          <!-- Saturation/Lightness pad -->
          <div
            bind:this={slEl}
            class="sl-pad"
            role="slider"
            tabindex="0"
            aria-label="Saturation and Lightness"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={saturation}
            style="background: linear-gradient(to top, #000, transparent, #fff), linear-gradient(to right, #888, hsl({hue}, 100%, 50%));"
            onmousedown={handleSLDown}
          >
            <div
              class="sl-thumb"
              style="left: {saturation}%; top: {100 - lightness}%; background: {customHex};"
            ></div>
          </div>

          <!-- Hex input -->
          <div class="hex-row">
            <div class="hex-preview" style="background: {customHex};"></div>
            <input
              class="hex-input"
              class:invalid={!hexValid}
              type="text"
              value={hexInput}
              oninput={handleHexInput}
              spellcheck="false"
              maxlength={7}
              placeholder="#000000"
            />
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .color-picker {
    position: relative;
    display: inline-block;
  }

  .trigger {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid var(--border-default);
    cursor: pointer;
    padding: 0;
    transition: border-color 150ms, transform 150ms;
  }

  .trigger:hover {
    border-color: var(--text-secondary);
    transform: scale(1.1);
  }

  .popup {
    position: absolute;
    top: 28px;
    left: 0;
    z-index: 300;
    width: 200px;
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .preset-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    justify-items: center;
  }

  .preset-swatch {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    border: 2px solid transparent;
    cursor: pointer;
    padding: 0;
    transition: border-color 150ms, transform 150ms;
  }

  .preset-swatch:hover {
    transform: scale(1.15);
  }

  .preset-swatch.selected {
    border-color: var(--text-primary);
    box-shadow: 0 0 0 1px var(--bg-surface);
  }

  .custom-toggle {
    width: 100%;
    padding: 4px 8px;
    font-size: 11px;
    color: var(--text-tertiary);
    background: none;
    border: none;
    cursor: pointer;
    font-family: var(--font-sans);
    text-align: center;
    border-radius: 4px;
    transition: color 150ms, background 150ms;
  }

  .custom-toggle:hover {
    color: var(--text-secondary);
    background: var(--bg-surface-hover);
  }

  .custom-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* Hue strip */
  .hue-strip {
    position: relative;
    width: 100%;
    height: 14px;
    border-radius: 7px;
    background: linear-gradient(
      to right,
      hsl(0, 100%, 50%),
      hsl(60, 100%, 50%),
      hsl(120, 100%, 50%),
      hsl(180, 100%, 50%),
      hsl(240, 100%, 50%),
      hsl(300, 100%, 50%),
      hsl(360, 100%, 50%)
    );
    cursor: crosshair;
    user-select: none;
  }

  .hue-thumb {
    position: absolute;
    top: 50%;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid rgba(0, 0, 0, 0.3);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
    transform: translate(-50%, -50%);
    pointer-events: none;
    transition: box-shadow 150ms;
  }

  /* Saturation/Lightness pad */
  .sl-pad {
    position: relative;
    width: 100%;
    height: 120px;
    border-radius: 6px;
    cursor: crosshair;
    background-blend-mode: normal, overlay;
    user-select: none;
  }

  .sl-thumb {
    position: absolute;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid #fff;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.4);
    transform: translate(-50%, -50%);
    pointer-events: none;
  }

  /* Hex input row */
  .hex-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .hex-preview {
    width: 24px;
    height: 24px;
    border-radius: 4px;
    border: 1px solid var(--border-default);
    flex-shrink: 0;
  }

  .hex-input {
    flex: 1;
    padding: 5px 8px;
    font-size: 12px;
    font-family: var(--font-mono, monospace);
    color: var(--text-primary);
    background: var(--bg-base);
    border: 1px solid var(--border-default);
    border-radius: 4px;
    outline: none;
    transition: border-color 150ms;
  }

  .hex-input:focus {
    border-color: var(--accent);
  }

  .hex-input.invalid {
    border-color: #E85D5D;
  }
</style>

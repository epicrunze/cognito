import { onMount } from 'svelte';

let _isMobile = $state(false);
let _isTablet = $state(false);
let _isDesktop = $state(true);
let _sidebarOpen = $state(false);
let _initialized = $state(false);

function init() {
  if (_initialized || typeof window === 'undefined') return;
  _initialized = true;

  const mobileQuery = window.matchMedia('(max-width: 767px)');
  const tabletQuery = window.matchMedia('(min-width: 768px) and (max-width: 1023px)');
  const desktopQuery = window.matchMedia('(min-width: 1024px)');

  function update() {
    _isMobile = mobileQuery.matches;
    _isTablet = tabletQuery.matches;
    _isDesktop = desktopQuery.matches;

    // Auto-close sidebar overlay when resizing to desktop
    if (_isDesktop) _sidebarOpen = false;
  }

  update();

  mobileQuery.addEventListener('change', update);
  tabletQuery.addEventListener('change', update);
  desktopQuery.addEventListener('change', update);
}

// Auto-init on first import in browser
if (typeof window !== 'undefined') {
  init();
}

export const responsiveStore = {
  get isMobile() { return _isMobile; },
  get isTablet() { return _isTablet; },
  get isDesktop() { return _isDesktop; },
  get sidebarOpen() { return _sidebarOpen; },
  toggleSidebar() { _sidebarOpen = !_sidebarOpen; },
  openSidebar() { _sidebarOpen = true; },
  closeSidebar() { _sidebarOpen = false; },
};

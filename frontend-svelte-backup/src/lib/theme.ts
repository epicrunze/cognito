/**
 * Cognito Theme Configuration
 *
 * This file contains the Cognito brand color definitions and theme setup
 * for Skeleton UI integration.
 */

// Brand color hex values for reference
export const BRAND_COLORS = {
    primary: {
        dark: '#1B3C53',
        main: '#234C6A',
        light: '#456882'
    },
    background: '#E3E3E3',
    surface: '#FFFFFF',
    semantic: {
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',
        info: '#3b82f6'
    }
} as const;

// Navigation items configuration
export const NAV_ITEMS = [
    { href: '/', label: 'Journal', icon: '📓' },
    { href: '/goals', label: 'Goals', icon: '🎯' },
    { href: '/chat', label: 'Chat', icon: '💬' },
    { href: '/settings', label: 'Settings', icon: '⚙️' }
] as const;

// Drawer settings for bottom sheet chat
export const CHAT_DRAWER_SETTINGS = {
    position: 'bottom' as const,
    height: 'h-[85vh]',
    rounded: 'rounded-t-2xl',
    padding: 'p-0'
};

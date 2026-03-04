/** @type {import('tailwindcss').Config} */
export default {
    content: ['./src/**/*.{html,js,svelte,ts}'],
    theme: {
        extend: {
            fontFamily: {
                sans: ['IBM Plex Sans', 'system-ui', '-apple-system', 'sans-serif'],
                mono: ['IBM Plex Mono', 'Fira Code', 'monospace'],
            },
            fontSize: {
                xs: 'var(--text-xs)',
                sm: 'var(--text-sm)',
                base: 'var(--text-base)',
                md: 'var(--text-md)',
                lg: 'var(--text-lg)',
                xl: 'var(--text-xl)',
            },
            colors: {
                accent: 'var(--accent)',
                'accent-hover': 'var(--accent-hover)',
                'accent-subtle': 'var(--accent-subtle)',
                'priority-urgent': 'var(--priority-urgent)',
                'priority-high': 'var(--priority-high)',
                'priority-medium': 'var(--priority-medium)',
                'priority-low': 'var(--priority-low)',
                'priority-none': 'var(--priority-none)',
                done: 'var(--done)',
                overdue: 'var(--overdue)',
                'ai-accent': 'var(--ai-accent)',
            },
            textColor: {
                primary: 'var(--text-primary)',
                secondary: 'var(--text-secondary)',
                tertiary: 'var(--text-tertiary)',
                'on-accent': 'var(--text-on-accent)',
            },
            backgroundColor: {
                base: 'var(--bg-base)',
                surface: 'var(--bg-surface)',
                'surface-hover': 'var(--bg-surface-hover)',
                sidebar: 'var(--bg-sidebar)',
                overlay: 'var(--bg-overlay)',
            },
            borderColor: {
                default: 'var(--border-default)',
                strong: 'var(--border-strong)',
            },
            boxShadow: {
                sm: 'var(--shadow-sm)',
                md: 'var(--shadow-md)',
                lg: 'var(--shadow-lg)',
                'slide-over': 'var(--shadow-slide-over)',
            },
            width: {
                sidebar: '240px',
                'detail-panel': '480px',
            },
            borderRadius: {
                container: '6px',
                input: '4px',
                pill: '9999px',
            },
            transitionDuration: {
                fast: 'var(--transition-fast)',
                normal: 'var(--transition-normal)',
                slow: 'var(--transition-slow)',
            },
        },
    },
    plugins: [],
};

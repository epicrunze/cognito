/** @type {import('tailwindcss').Config} */
export default {
    content: ['./src/**/*.{html,js,svelte,ts}'],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            },
            colors: {
                brand: {
                    50: '#f0f4ff',
                    100: '#e0e9ff',
                    200: '#c2d3fe',
                    300: '#93b4fd',
                    400: '#628bf8',
                    500: '#3d64f3',
                    600: '#2b47e7',
                    700: '#2135c9',
                    800: '#1f2ea2',
                    900: '#1d2b80',
                    950: '#141c57',
                },
                surface: {
                    50: '#f8f9fc',
                    100: '#f0f2f8',
                    200: '#dfe3ef',
                    800: '#1e2235',
                    900: '#141728',
                    950: '#0d0f1c',
                },
            },
        },
    },
    plugins: [],
};

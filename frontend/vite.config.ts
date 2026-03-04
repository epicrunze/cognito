import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
    plugins: [sveltekit()],
    server: {
        proxy: {
            '/api': {
                target: process.env.PUBLIC_API_URL || 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
});

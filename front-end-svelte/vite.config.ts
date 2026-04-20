import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	ssr: {
		noExternal: ['@tanstack/svelte-query'],
	},
	resolve: {
		conditions: ['svelte', 'browser', 'import']
	},
	server: {
		port: 8080
	}
});

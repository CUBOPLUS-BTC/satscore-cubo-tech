<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '$lib/components/ui/sonner';
	import { i18n } from '$lib/i18n/index.svelte';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<ModeWatcher defaultMode="dark" />
<Toaster />

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>{i18n.t.app.name} — {i18n.t.app.tagline}</title>
	<meta name="description" content={i18n.t.app.description} />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<meta property="og:site_name" content={i18n.t.app.name} />
	<meta property="og:type" content="website" />
</svelte:head>

{@render children()}

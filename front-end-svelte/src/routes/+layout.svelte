<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '$lib/components/ui/sonner';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<ModeWatcher defaultMode="dark" />
<Toaster />

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Magma — Bitcoin Financial Intelligence</title>
	<meta name="description" content="Track your sats, analyze your wealth, and understand your financial footprint in the Bitcoin ecosystem." />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<meta property="og:site_name" content="Magma" />
	<meta property="og:type" content="website" />
</svelte:head>

{@render children()}

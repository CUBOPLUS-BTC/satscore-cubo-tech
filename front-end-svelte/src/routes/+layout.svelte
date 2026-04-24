<script lang="ts">
	import '../app.css';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '$lib/components/ui/sonner';
	import { i18n } from '$lib/i18n/index.svelte';
	import favicon from '$lib/assets/favicon.svg';
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { queryClient } from '$lib/api/query-client';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>{i18n.t.app.name} — {i18n.t.app.tagline}</title>
	<meta name="description" content={i18n.t.app.description} />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<meta property="og:site_name" content={i18n.t.app.name} />
	<meta property="og:type" content="website" />
</svelte:head>

<ModeWatcher defaultMode="light" track={false} />
<Toaster />
<QueryClientProvider client={queryClient}>
	{@render children()}
</QueryClientProvider>

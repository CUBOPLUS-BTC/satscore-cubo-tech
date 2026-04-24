<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
	import WalletGuide from '$lib/components/wallet-guide.svelte';
	import { Button } from '$lib/components/ui/button';
	import { animateIn } from '$lib/motion';
	import Geo from '$lib/components/geo.svelte';

	let filter = $state<'all' | 'lightning' | 'liquid'>('all');
</script>

<svelte:head>
	<title>{i18n.t.wallets.title} {i18n.t.app.titleSuffix}</title>
</svelte:head>

<div class="space-y-8">
	<section use:animateIn={{ y: [24, 0], duration: 0.5 }}>
		<div class="flex items-center gap-3 mb-1">
			<Geo state="studying" class="w-12 h-12 shrink-0" />
			<div>
				<h1 class="font-heading text-2xl font-bold tracking-tight">{i18n.t.wallets.title}</h1>
				<p class="text-sm text-muted-foreground mt-0.5">{i18n.t.wallets.subtitle}</p>
			</div>
		</div>
	</section>

	<section use:animateIn={{ y: [12, 0], delay: 0.1 }}>
		<div class="flex gap-2">
			<Button
				size="sm"
				variant={filter === 'all' ? 'default' : 'outline'}
				onclick={() => filter = 'all'}
			>
				{i18n.t.wallets.filterAll}
			</Button>
			<Button
				size="sm"
				variant={filter === 'lightning' ? 'default' : 'outline'}
				onclick={() => filter = 'lightning'}
			>
				Lightning
			</Button>
			<Button
				size="sm"
				variant={filter === 'liquid' ? 'default' : 'outline'}
				onclick={() => filter = 'liquid'}
			>
				Liquid
			</Button>
		</div>
	</section>

	<section use:animateIn={{ y: [16, 0], delay: 0.2 }}>
		<WalletGuide {filter} />
	</section>
</div>

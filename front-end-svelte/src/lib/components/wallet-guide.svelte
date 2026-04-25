<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
	import ShieldCheck from 'phosphor-svelte/lib/ShieldCheck';
	import Warning from 'phosphor-svelte/lib/Warning';
	import Lightning from 'phosphor-svelte/lib/Lightning';
	import Cube from 'phosphor-svelte/lib/Cube';
	import Drop from 'phosphor-svelte/lib/Drop';
	import ArrowSquareOut from 'phosphor-svelte/lib/ArrowSquareOut';
	import { staggerChildren } from '$lib/motion';

	type WalletType = 'lightning' | 'onchain' | 'liquid';

	interface WalletInfo {
		name: string;
		logoUrl: string;
		url: string;
		custody: 'self' | 'custodial';
		types: WalletType[];
		kyc: boolean;
		lnurlAuth?: boolean;
		platforms: string[];
		headline: string;
		howItWorks: string;
		bestFor: string;
		tradeoffs: string;
		fee: string;
	}

	let { filter = 'all' }: { filter?: 'all' | 'lightning' | 'liquid' } = $props();

	let wallets = $derived(i18n.t.wallets.list as unknown as WalletInfo[]);
	let filtered = $derived(
		filter === 'all'
			? wallets
			: wallets.filter(w => {
				if (filter === 'lightning') return w.types.includes('lightning');
				if (filter === 'liquid') return w.types.includes('liquid');
				return true;
			})
	);

	const typeIcon = { lightning: Lightning, onchain: Cube, liquid: Drop } as const;
	const typeLabel = { lightning: 'Lightning', onchain: 'On-chain', liquid: 'Liquid' } as const;
</script>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6" use:staggerChildren={{ y: 16, staggerDelay: 0.06 }}>
	{#each filtered as w (w.name)}
		<a
			href={w.url}
			target="_blank"
			rel="noopener noreferrer"
			class="group block rounded-2xl border border-border p-6 transition-all duration-200 hover:border-primary/30 hover:bg-muted/40"
		>
			<!-- Header: logo + name + custody -->
			<div class="flex items-start gap-4 mb-4">
				<img
					src={w.logoUrl}
					alt={w.name}
					class="size-12 rounded-xl object-contain bg-muted/50 p-1 shrink-0"
				/>
				<div class="flex-1 min-w-0">
					<div class="flex items-center gap-2 flex-wrap">
						<h3 class="font-heading text-base font-bold">{w.name}</h3>
						{#if w.custody === 'self'}
							<span class="inline-flex items-center gap-1 text-[11px] font-semibold text-green-600 dark:text-green-400">
								<ShieldCheck size={13} weight="fill" />
								{i18n.t.wallets.selfCustody}
							</span>
						{:else}
							<span class="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-600 dark:text-amber-400">
								<Warning size={13} weight="fill" />
								{i18n.t.wallets.custodial}
							</span>
						{/if}
						{#if w.lnurlAuth}
							<span class="inline-flex items-center gap-1 text-[11px] font-semibold text-primary">
								<Lightning size={13} weight="fill" />
								Login Magma
							</span>
						{/if}
					</div>
					<p class="text-sm text-muted-foreground mt-1 leading-snug">{w.headline}</p>
				</div>
			</div>

			<!-- Network types -->
			<div class="flex items-center gap-3 mb-4">
				{#each w.types as type}
					{@const Icon = typeIcon[type]}
					<span class="inline-flex items-center gap-1 text-xs text-muted-foreground">
						<Icon size={13} weight={type === 'lightning' ? 'fill' : 'regular'} />
						{typeLabel[type]}
					</span>
				{/each}
				{#if w.kyc}
					<span class="text-xs text-amber-600 dark:text-amber-400 font-medium">KYC</span>
				{/if}
				<span class="ml-auto text-xs text-muted-foreground">{w.platforms.join(' / ')}</span>
			</div>

			<!-- How it works -->
			<p class="text-xs text-muted-foreground leading-relaxed mb-3">{w.howItWorks}</p>

			<!-- Best for -->
			<div class="rounded-xl bg-muted/50 p-3 mb-4">
				<span class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">{i18n.t.wallets.bestFor}</span>
				<p class="text-xs text-foreground/80 mt-1 leading-relaxed">{w.bestFor}</p>
			</div>

			<!-- Footer: fee + tradeoffs + visit -->
			<div class="flex items-center justify-between gap-3">
				<div class="text-xs text-muted-foreground">
					{i18n.t.wallets.fees}: <span class="font-medium text-foreground">{w.fee}</span>
				</div>
				<span class="inline-flex items-center gap-1.5 text-xs font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity">
					{i18n.t.wallets.visit}
					<ArrowSquareOut size={12} />
				</span>
			</div>

			{#if w.tradeoffs}
				<p class="text-[11px] text-muted-foreground/60 mt-2 leading-relaxed">{w.tradeoffs}</p>
			{/if}
		</a>
	{/each}
</div>

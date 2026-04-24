<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
	import { api } from '$lib/api/client';
	import { endpoints } from '$lib/api/endpoints';
	import { createQuery } from '@tanstack/svelte-query';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Separator } from '$lib/components/ui/separator';
	import { animateIn, staggerChildren, inViewStagger } from '$lib/motion';
	import Drop from 'phosphor-svelte/lib/Drop';
	import ShieldCheck from 'phosphor-svelte/lib/ShieldCheck';
	import Lightning from 'phosphor-svelte/lib/Lightning';
	import Cube from 'phosphor-svelte/lib/Cube';
	import Wallet from 'phosphor-svelte/lib/Wallet';
	import ArrowRight from 'phosphor-svelte/lib/ArrowRight';
	import CheckCircle from 'phosphor-svelte/lib/CheckCircle';
	import Geo from '$lib/components/geo.svelte';
	import WalletGuide from '$lib/components/wallet-guide.svelte';
	import type {
		LiquidOverview,
		LiquidAssets,
		LiquidCompare,
		LiquidPegInfo,
		LiquidRecommendation,
		LiquidLayer,
		LiquidOption,
		LiquidUrgency,
		LiquidPrivacyLevel,
	} from '$lib/models/liquid';

	const overviewQuery = createQuery(() => ({
		queryKey: ['liquid-overview'],
		queryFn: () => api.get<LiquidOverview>(endpoints.liquid.overview),
		refetchInterval: 120_000,
	}));

	const assetsQuery = createQuery(() => ({
		queryKey: ['liquid-assets'],
		queryFn: () => api.get<LiquidAssets>(endpoints.liquid.assets),
		refetchInterval: 300_000,
	}));

	const compareQuery = createQuery(() => ({
		queryKey: ['liquid-compare'],
		queryFn: () => api.get<LiquidCompare>(endpoints.liquid.compare),
		staleTime: 60_000,
	}));

	const pegQuery = createQuery(() => ({
		queryKey: ['liquid-peg'],
		queryFn: () => api.get<LiquidPegInfo>(endpoints.liquid.pegInfo),
		staleTime: 300_000,
	}));

	let overview = $derived(overviewQuery.data ?? null);
	let assets = $derived(assetsQuery.data ?? null);
	let comparison = $derived(compareQuery.data ?? null);
	let pegInfo = $derived(pegQuery.data ?? null);

	// Recommendation form
	let recAmount = $state(200);
	let recUrgency = $state<LiquidUrgency>('medium');
	let recPrivacy = $state<LiquidPrivacyLevel>('normal');
	let recommendation = $state<LiquidRecommendation | null>(null);
	let recLoading = $state(false);

	async function getRecommendation() {
		recLoading = true;
		try {
			recommendation = await api.post<LiquidRecommendation>(endpoints.liquid.recommend, {
				amount_usd: recAmount,
				urgency: recUrgency,
				privacy: recPrivacy,
			});
		} catch {
			recommendation = null;
		} finally {
			recLoading = false;
		}
	}

	function formatSeconds(s: number): string {
		if (s < 60) return `${s} ${i18n.t.liquid.seconds}`;
		return `${Math.round(s / 60)} ${i18n.t.liquid.minutes}`;
	}

	const layerColors: Record<string, string> = {
		on_chain: 'text-amber-500',
		lightning: 'text-yellow-400',
		liquid: 'text-cyan-500',
	};

	const layerLabels: Record<string, string> = {
		on_chain: 'Bitcoin On-chain',
		lightning: 'Lightning Network',
		liquid: 'Liquid Network',
	};
</script>

<svelte:head>
	<title>{i18n.t.liquid.title} {i18n.t.app.titleSuffix}</title>
</svelte:head>

<div class="space-y-10">
	<section use:animateIn={{ y: [24, 0], duration: 0.5 }}>
		<div class="flex items-center gap-3 mb-2">
			<Geo state="alert" class="w-14 h-14 shrink-0" />
			<div>
				<h1 class="font-heading text-2xl font-bold">{i18n.t.liquid.title}</h1>
				<p class="text-sm text-muted-foreground">{i18n.t.liquid.subtitle}</p>
			</div>
		</div>
	</section>

	<!-- Network Overview -->
	<section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" use:staggerChildren={{ y: 16, staggerDelay: 0.06 }}>
		{#if overview}
			<Card>
				<CardContent class="pt-5 space-y-1">
					<span class="text-xs text-muted-foreground uppercase tracking-wider">{i18n.t.liquid.blockHeight}</span>
					<p class="text-2xl font-bold tabular-nums">#{overview.block_height.toLocaleString()}</p>
				</CardContent>
			</Card>
			<Card>
				<CardContent class="pt-5 space-y-1">
					<span class="text-xs text-muted-foreground uppercase tracking-wider">{i18n.t.liquid.blockTime}</span>
					<p class="text-2xl font-bold">~1 min</p>
				</CardContent>
			</Card>
			<Card>
				<CardContent class="pt-5 space-y-1">
					<span class="text-xs text-muted-foreground uppercase tracking-wider">{i18n.t.liquid.avgTxPerBlock}</span>
					<p class="text-2xl font-bold tabular-nums">{overview.recent_blocks.avg_tx_per_block}</p>
				</CardContent>
			</Card>
			<Card>
				<CardContent class="pt-5 space-y-1">
					<span class="text-xs text-muted-foreground uppercase tracking-wider">{i18n.t.liquid.typicalFee}</span>
					<p class="text-2xl font-bold tabular-nums text-green-500">{overview.typical_tx_fee_sats} <span class="text-sm font-normal text-muted-foreground">sats</span></p>
				</CardContent>
			</Card>
		{:else}
			{#each Array(4) as _, i (i)}
				<Card><CardContent class="pt-5"><Skeleton class="h-12 w-full" /></CardContent></Card>
			{/each}
		{/if}
	</section>

	<!-- Features -->
	{#if overview}
		<section use:animateIn={{ y: [16, 0], delay: 0.1 }}>
			<h2 class="font-heading text-lg font-semibold mb-3">{i18n.t.liquid.features}</h2>
			<div class="flex flex-wrap gap-2">
				{#each overview.features as feature (feature)}
					<Badge variant="secondary" class="text-xs">{feature}</Badge>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Assets -->
	{#if assets}
		<section use:inViewStagger={{ y: 16, staggerDelay: 0.08 }}>
			<h2 class="font-heading text-lg font-semibold mb-4">{i18n.t.liquid.assets}</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<Card>
					<CardContent class="pt-5 space-y-3">
						<div class="flex items-center gap-2">
							<div class="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center">
								<span class="text-amber-500 font-bold text-sm">L</span>
							</div>
							<div>
								<h3 class="font-semibold text-sm">{i18n.t.liquid.lbtc}</h3>
								<span class="text-xs text-muted-foreground">{assets.l_btc.ticker}</span>
							</div>
							{#if assets.l_btc.available}
								<Badge variant="default" class="ml-auto text-[10px]">Active</Badge>
							{/if}
						</div>
						<p class="text-xs text-muted-foreground">1:1 peg with Bitcoin mainchain. Same value, faster transfers.</p>
					</CardContent>
				</Card>
				<Card>
					<CardContent class="pt-5 space-y-3">
						<div class="flex items-center gap-2">
							<div class="w-8 h-8 rounded-full bg-green-500/10 flex items-center justify-center">
								<span class="text-green-500 font-bold text-sm">$</span>
							</div>
							<div>
								<h3 class="font-semibold text-sm">{i18n.t.liquid.usdt}</h3>
								<span class="text-xs text-muted-foreground">{assets.usdt.ticker}</span>
							</div>
							{#if assets.usdt.available}
								<Badge variant="default" class="ml-auto text-[10px]">Active</Badge>
							{/if}
						</div>
						<p class="text-xs text-muted-foreground">Dollar stability without leaving the Bitcoin ecosystem.</p>
					</CardContent>
				</Card>
			</div>
		</section>
	{/if}

	<!-- Layer Comparison -->
	{#if comparison}
		<section use:inViewStagger={{ y: 16, staggerDelay: 0.06 }}>
			<h2 class="font-heading text-lg font-semibold mb-1">{i18n.t.liquid.compare}</h2>
			<p class="text-sm text-muted-foreground mb-4">{i18n.t.liquid.compareSubtitle}</p>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<!-- On-chain -->
				<Card>
					<CardContent class="pt-5 space-y-3">
						<div class="flex items-center gap-2">
							<Cube size={20} class="text-amber-500" />
							<h3 class="font-semibold text-sm">{i18n.t.liquid.onChain}</h3>
						</div>
						<div class="space-y-2 text-xs">
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.fee}</span>
								<span class="font-medium">{comparison.on_chain.fee_fastest_sats.toLocaleString()} sats</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.speed}</span>
								<span class="font-medium">{formatSeconds(comparison.on_chain.settlement_seconds)}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.privacy}</span>
								<span class="font-medium">{comparison.on_chain.privacy}</span>
							</div>
						</div>
						<Separator />
						<div>
							<span class="text-[10px] uppercase text-muted-foreground tracking-wider">{i18n.t.liquid.bestFor}</span>
							<ul class="mt-1 space-y-0.5">
								{#each comparison.on_chain.best_for as use (use)}
									<li class="text-xs text-muted-foreground flex items-start gap-1.5">
										<ArrowRight size={10} class="mt-0.5 shrink-0 text-amber-500" />
										{use}
									</li>
								{/each}
							</ul>
						</div>
					</CardContent>
				</Card>

				<!-- Lightning -->
				<Card>
					<CardContent class="pt-5 space-y-3">
						<div class="flex items-center gap-2">
							<Lightning size={20} class="text-yellow-400" />
							<h3 class="font-semibold text-sm">{i18n.t.liquid.lightning}</h3>
						</div>
						<div class="space-y-2 text-xs">
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.fee}</span>
								<span class="font-medium">{comparison.lightning.fee_typical_sats} sat + ppm</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.speed}</span>
								<span class="font-medium">{formatSeconds(comparison.lightning.settlement_seconds)}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.privacy}</span>
								<span class="font-medium">{comparison.lightning.privacy}</span>
							</div>
						</div>
						<Separator />
						<div>
							<span class="text-[10px] uppercase text-muted-foreground tracking-wider">{i18n.t.liquid.bestFor}</span>
							<ul class="mt-1 space-y-0.5">
								{#each comparison.lightning.best_for as use (use)}
									<li class="text-xs text-muted-foreground flex items-start gap-1.5">
										<ArrowRight size={10} class="mt-0.5 shrink-0 text-yellow-400" />
										{use}
									</li>
								{/each}
							</ul>
						</div>
					</CardContent>
				</Card>

				<!-- Liquid -->
				<Card class="ring-1 ring-cyan-500/30">
					<CardContent class="pt-5 space-y-3">
						<div class="flex items-center gap-2">
							<Drop size={20} class="text-cyan-500" weight="fill" />
							<h3 class="font-semibold text-sm">{i18n.t.liquid.liquidLabel}</h3>
							<Badge variant="default" class="ml-auto text-[10px]">NEW</Badge>
						</div>
						<div class="space-y-2 text-xs">
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.fee}</span>
								<span class="font-medium text-green-500">{comparison.liquid.fee_typical_sats} sats</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.speed}</span>
								<span class="font-medium">{formatSeconds(comparison.liquid.settlement_seconds)}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.privacy}</span>
								<span class="font-medium text-cyan-500">{comparison.liquid.privacy}</span>
							</div>
						</div>
						<Separator />
						<div>
							<span class="text-[10px] uppercase text-muted-foreground tracking-wider">{i18n.t.liquid.bestFor}</span>
							<ul class="mt-1 space-y-0.5">
								{#each comparison.liquid.best_for as use (use)}
									<li class="text-xs text-muted-foreground flex items-start gap-1.5">
										<ArrowRight size={10} class="mt-0.5 shrink-0 text-cyan-500" />
										{use}
									</li>
								{/each}
							</ul>
						</div>
					</CardContent>
				</Card>
			</div>
		</section>
	{/if}

	<!-- Smart Recommendation -->
	<section use:animateIn={{ y: [16, 0], delay: 0.15 }}>
		<h2 class="font-heading text-lg font-semibold mb-1">{i18n.t.liquid.recommend}</h2>
		<p class="text-sm text-muted-foreground mb-4">{i18n.t.liquid.recommendSubtitle}</p>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<Card>
				<CardContent class="pt-5 space-y-4">
					<div class="space-y-2">
						<label class="text-sm font-medium" for="rec-amount">{i18n.t.liquid.amount}</label>
						<Input id="rec-amount" type="number" bind:value={recAmount} min="1" step="1" class="tabular-nums" />
					</div>
					<fieldset class="space-y-2">
						<legend class="text-sm font-medium">{i18n.t.liquid.urgency}</legend>
						<div class="flex gap-2 flex-wrap">
							{#each ['low', 'medium', 'high', 'instant'] as u (u)}
								<Button
									size="sm"
									variant={recUrgency === u ? 'default' : 'outline'}
									onclick={() => (recUrgency = u as LiquidUrgency)}
								>
									{i18n.t.liquid[u as keyof typeof i18n.t.liquid]}
								</Button>
							{/each}
						</div>
					</fieldset>
					<fieldset class="space-y-2">
						<legend class="text-sm font-medium">{i18n.t.liquid.privacyLevel}</legend>
						<div class="flex gap-2 flex-wrap">
							{#each ['normal', 'high', 'confidential'] as p (p)}
								<Button
									size="sm"
									variant={recPrivacy === p ? 'default' : 'outline'}
									onclick={() => (recPrivacy = p as LiquidPrivacyLevel)}
								>
									{i18n.t.liquid[p as keyof typeof i18n.t.liquid]}
								</Button>
							{/each}
						</div>
					</fieldset>
					<Button class="w-full" onclick={getRecommendation} disabled={recLoading}>
						{recLoading ? '...' : i18n.t.liquid.getRecommendation}
					</Button>
				</CardContent>
			</Card>

			{#if recommendation}
				<Card class="ring-1 ring-cyan-500/20">
					<CardContent class="pt-5 space-y-4">
						<div class="flex items-center gap-2">
							<CheckCircle size={22} class={layerColors[recommendation.recommended_layer] || 'text-cyan-500'} weight="fill" />
							<div>
								<span class="text-xs text-muted-foreground uppercase tracking-wider">{i18n.t.liquid.recommendedLayer}</span>
								<h3 class="font-heading text-lg font-bold {layerColors[recommendation.recommended_layer] || ''}">
									{layerLabels[recommendation.recommended_layer] || recommendation.recommended_layer}
								</h3>
							</div>
						</div>
						<p class="text-sm text-muted-foreground">{recommendation.reason}</p>
						<Separator />
						<div class="grid grid-cols-2 gap-3 text-sm">
							<div>
								<span class="text-xs text-muted-foreground">{i18n.t.liquid.estimatedFee}</span>
								<p class="font-semibold text-green-500">${recommendation.estimated_fee_usd}</p>
							</div>
							<div>
								<span class="text-xs text-muted-foreground">{i18n.t.liquid.speed}</span>
								<p class="font-semibold">{formatSeconds(recommendation.estimated_confirm_seconds)}</p>
							</div>
						</div>
						<Separator />
						<div>
							<span class="text-xs text-muted-foreground uppercase tracking-wider">{i18n.t.liquid.alternatives}</span>
							<div class="mt-2 space-y-1.5">
								{#each Object.entries(recommendation.all_options) as [key, opt] (key)}
									{@const o = opt as LiquidOption}
									<div class="flex justify-between text-xs">
										<span class={layerColors[key] ?? ''}>{layerLabels[key] ?? key}</span>
										<span class="text-muted-foreground">${o.fee_usd} / {formatSeconds(o.confirm_seconds)}</span>
									</div>
								{/each}
							</div>
						</div>
					</CardContent>
				</Card>
			{:else}
				<Card class="flex items-center justify-center">
					<CardContent class="pt-5 text-center text-muted-foreground">
						<ShieldCheck size={40} class="mx-auto mb-3 text-cyan-500/40" />
						<p class="text-sm">{i18n.t.liquid.recommendSubtitle}</p>
					</CardContent>
				</Card>
			{/if}
		</div>
	</section>

	<!-- Peg-in/Peg-out & Wallets -->
	{#if pegInfo}
		<section class="grid grid-cols-1 md:grid-cols-2 gap-6" use:inViewStagger={{ y: 16, staggerDelay: 0.08 }}>
			<!-- Peg Info -->
			<Card>
				<CardContent class="pt-5 space-y-4">
					<h2 class="font-heading text-base font-semibold">{i18n.t.liquid.pegInfo}</h2>

					<div class="space-y-3">
						<h3 class="text-sm font-medium text-amber-500">{i18n.t.liquid.pegInTitle}</h3>
						<div class="space-y-1.5 text-xs">
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.confirmations}</span>
								<span class="font-medium">{pegInfo.peg_in.confirmations_required}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.estimatedTime}</span>
								<span class="font-medium">{pegInfo.peg_in.estimated_time}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.minAmount}</span>
								<span class="font-medium">{pegInfo.peg_in.minimum_amount_btc} BTC</span>
							</div>
						</div>
					</div>

					<Separator />

					<div class="space-y-3">
						<h3 class="text-sm font-medium text-cyan-500">{i18n.t.liquid.pegOutTitle}</h3>
						<div class="space-y-1.5 text-xs">
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.confirmations}</span>
								<span class="font-medium">{pegInfo.peg_out.confirmations_required}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.estimatedTime}</span>
								<span class="font-medium">{pegInfo.peg_out.estimated_time}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-muted-foreground">{i18n.t.liquid.fee}</span>
								<span class="font-medium">{pegInfo.peg_out.fee}</span>
							</div>
						</div>
					</div>

					<Separator />

					<div class="space-y-2">
						<h3 class="text-sm font-medium text-green-500">{i18n.t.liquid.swapServices}</h3>
						{#each Object.entries(pegInfo.alternatives) as [key, svc] (key)}
							<div class="p-2 rounded-lg bg-muted/50 text-xs space-y-0.5">
								<span class="font-medium">{svc.description}</span>
								<div class="flex gap-2 text-muted-foreground">
									<span>{i18n.t.liquid.speed}: {svc.speed}</span>
									{#if svc.fee}<span>|</span><span>{i18n.t.liquid.fee}: {svc.fee}</span>{/if}
								</div>
							</div>
						{/each}
					</div>
				</CardContent>
			</Card>

			<!-- Wallets -->
			<Card>
				<CardContent class="pt-5 space-y-4">
					<div class="flex items-center gap-2">
						<Wallet size={20} class="text-cyan-500" />
						<h2 class="font-heading text-base font-semibold">{i18n.t.liquid.wallets}</h2>
					</div>

					<div class="space-y-3">
						{#each pegInfo.wallets as wallet (wallet.name)}
							<div class="p-4 rounded-xl border border-border space-y-2.5 hover:bg-muted/50 transition-colors">
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<div class="flex items-center gap-2 flex-wrap">
											<h3 class="text-sm font-semibold">{wallet.name}</h3>
											<Badge variant={wallet.custody === 'self' ? 'default' : 'secondary'} class="text-[10px]">
												{wallet.custody === 'self' ? (i18n.locale === 'es' ? 'Autocustodia' : 'Self-custody') : 'Custodial'}
											</Badge>
										</div>
										<span class="text-[10px] text-muted-foreground">{wallet.by}</span>
									</div>
									<div class="flex gap-1 shrink-0">
										{#each wallet.platforms as platform (platform)}
											<Badge variant="outline" class="text-[10px]">{platform}</Badge>
										{/each}
									</div>
								</div>
								{#if wallet.description}
									<p class="text-xs text-muted-foreground leading-relaxed">{wallet.description}</p>
								{/if}
								<div class="flex flex-wrap gap-1">
									{#each wallet.features as feature (feature)}
										<Badge variant="secondary" class="text-[10px]">{feature}</Badge>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</CardContent>
			</Card>
		</section>
	{/if}

	<!-- Wallet Intelligence -->
	<section use:animateIn={{ y: [16, 0], delay: 0.2 }}>
		<h2 class="font-heading text-lg font-semibold mb-1">{i18n.t.wallets.title}</h2>
		<p class="text-sm text-muted-foreground mb-4">{i18n.t.wallets.subtitle}</p>
		<WalletGuide filter="liquid" />
	</section>
</div>

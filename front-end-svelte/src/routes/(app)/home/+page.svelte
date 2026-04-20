<script lang="ts">
	import type { VerifiedPrice } from '$lib/models/price';
	import type { NetworkStatus } from '$lib/models/network';
	import { formatUSD } from '$lib/utils/formatters';
	import { i18n } from '$lib/i18n/index.svelte';
	import { resolve } from '$app/paths';
	import { api } from '$lib/api/client';
	import { endpoints } from '$lib/api/endpoints';
	import { createQuery } from '@tanstack/svelte-query';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import PaperPlaneTilt from 'phosphor-svelte/lib/PaperPlaneTilt';
	import PiggyBank from 'phosphor-svelte/lib/PiggyBank';
	import CurrencyBtc from 'phosphor-svelte/lib/CurrencyBtc';
	import Cube from 'phosphor-svelte/lib/Cube';
	import ArrowRight from 'phosphor-svelte/lib/ArrowRight';
	import ArrowsLeftRight from 'phosphor-svelte/lib/ArrowsLeftRight';
	import Geo from '$lib/components/geo.svelte';
	import AnimatedNumber from '$lib/components/animated-number.svelte';
	import { animateIn, staggerChildren, inViewStagger, springHover, pressScale } from '$lib/motion';
	import { browser } from '$app/environment';
	import { Button } from '$lib/components/ui/button';
	import AlertBanner from '$lib/components/alert-banner.svelte';
	import type { AlertStatus } from '$lib/models/alert';
	import { goto } from '$app/navigation';

	const priceQuery = createQuery(() => ({
		queryKey: ['price'],
		queryFn: () => api.get<VerifiedPrice>(endpoints.price),
		refetchInterval: 60_000,
	}));

	const networkQuery = createQuery(() => ({
		queryKey: ['network'],
		queryFn: () => api.get<NetworkStatus>(endpoints.network.status),
		refetchInterval: 60_000,
	}));

	const alertStatusQuery = createQuery(() => ({
		queryKey: ['alert-status'],
		queryFn: () => api.get<AlertStatus>(endpoints.alerts.status),
		refetchInterval: 30_000,
		retry: 1,
	}));

	let price = $derived(priceQuery.data ?? null);
	let network = $derived(networkQuery.data ?? null);
	let alertStatus = $derived(alertStatusQuery.data ?? null);

	let calcUsd = $state(100);
	let calcBtc = $derived(
		price && price.price_usd > 0
			? (calcUsd / price.price_usd)
			: 0
	);

	let onboarded = $state(browser ? !!localStorage.getItem('magma_onboarded') : true);

	function dismissOnboarding() {
		localStorage.setItem('magma_onboarded', 'true');
		onboarded = true;
	}

	const tools = $derived([
		{
			icon: PaperPlaneTilt,
			title: () => i18n.t.home.tools.remittance.title,
			description: () => i18n.t.home.tools.remittance.description,
			href: '/remittance',
			color: 'text-blue-500',
		},
		{
			icon: PiggyBank,
			title: () => i18n.t.home.tools.pension.title,
			description: () => i18n.t.home.tools.pension.description,
			href: '/pension',
			color: 'text-emerald-500',
		},
		{
			icon: CurrencyBtc,
			title: () => i18n.t.home.tools.savings.title,
			description: () => i18n.t.home.tools.savings.description,
			href: '/savings',
			color: 'text-amber-500',
		},
	]);
</script>

<svelte:head>
	<title>{i18n.t.nav.home} {i18n.t.app.titleSuffix}</title>
</svelte:head>

<div class="space-y-10">
	{#if !onboarded}
		<div use:animateIn={{ y: [-20, 0], duration: 0.4 }}>
			<Card>
				<CardContent class="pt-6 space-y-3">
					<div class="flex items-center gap-3">
						<Geo state="success" class="w-10 h-10 shrink-0" />
						<div>
							<h2 class="font-heading text-base font-semibold">{i18n.t.home.dontTrust}</h2>
							<p class="text-sm text-muted-foreground">{i18n.t.home.welcomeDescription}</p>
						</div>
					</div>
					<div class="flex gap-2 mt-3">
						<Button size="sm" onclick={() => goto(resolve('/remittance'))}>{i18n.t.home.tools.remittance.title}</Button>
						<Button size="sm" variant="ghost" onclick={dismissOnboarding}>{i18n.t.common.close}</Button>
					</div>
				</CardContent>
			</Card>
		</div>
	{/if}

	<section use:animateIn={{ y: [24, 0], duration: 0.6 }}>
		{#if price}
			<div class="flex items-start gap-5">
				<Geo state="idle" class="w-20 h-20 shrink-0 hidden sm:block" />
				<div class="space-y-2">
					<span class="text-sm font-medium text-muted-foreground uppercase tracking-wider">BTC/USD</span>
					<div>
						<span class="font-heading text-5xl sm:text-6xl font-bold text-foreground tabular-nums tracking-tight">
							<AnimatedNumber
								value={price.price_usd}
								format={formatUSD}
								duration={1200}
							/>
						</span>
					</div>
					<div class="flex gap-2 pt-1">
						<Badge variant="secondary" class="text-xs font-normal">
							{i18n.t.home.sources.replace('{count}', String(price.sources_count))}
						</Badge>
						<Badge variant="default" class="text-xs font-normal">{i18n.t.home.verified}</Badge>
					</div>
				</div>
			</div>
		{:else}
			<div class="space-y-3">
				<Skeleton class="h-4 w-16" />
				<Skeleton class="h-14 w-64" />
				<Skeleton class="h-5 w-32" />
			</div>
		{/if}
	</section>

	<div use:animateIn={{ y: [16, 0], delay: 0.15 }}>
		<AlertBanner status={alertStatus} />
	</div>

	<section class="grid grid-cols-1 md:grid-cols-2 gap-5" use:staggerChildren={{ y: 24, staggerDelay: 0.08, delay: 0.2 }}>
		<Card>
			<CardContent class="pt-6 space-y-4">
				<div class="flex items-center gap-2 text-sm font-medium text-muted-foreground">
					<ArrowsLeftRight size={18} class="text-amber-500" />
					{i18n.t.home.calculator}
				</div>
				<div class="space-y-3">
					<div class="flex items-center gap-2">
						<Input
							type="number"
							bind:value={calcUsd}
							min="0"
							step="1"
							class="tabular-nums"
						/>
						<span class="text-sm font-medium text-muted-foreground shrink-0">USD</span>
					</div>
					<div class="text-2xl font-bold text-amber-500 tabular-nums">
						= <AnimatedNumber
							value={calcBtc}
							format={(v) => v.toFixed(8)}
							duration={400}
						/> BTC
					</div>
				</div>
			</CardContent>
		</Card>

		<Card>
			<CardContent class="pt-6 space-y-4">
				<div class="flex items-center gap-2 text-sm font-medium text-muted-foreground">
					<Cube size={18} class="text-blue-500" />
					{i18n.t.home.networkStatus}
				</div>
				{#if network}
					<div class="space-y-3">
						<div class="flex justify-between items-center">
							<span class="text-sm text-muted-foreground">{i18n.t.home.blockHeight}</span>
							<span class="text-sm font-semibold tabular-nums">
								#<AnimatedNumber value={network.block_height} duration={1000} />
							</span>
						</div>
						<div class="flex justify-between items-center">
							<span class="text-sm text-muted-foreground">{i18n.t.home.fastFee}</span>
							<span class="text-sm font-semibold tabular-nums">{network.fees.fastestFee} <span class="text-muted-foreground font-normal">sat/vB</span></span>
						</div>
						<div class="flex justify-between items-center">
							<span class="text-sm text-muted-foreground">{i18n.t.home.economyFee}</span>
							<span class="text-sm font-semibold tabular-nums text-green-600 dark:text-green-500">{network.fees.economyFee} <span class="text-muted-foreground font-normal">sat/vB</span></span>
						</div>
						<div class="flex justify-between items-center">
							<span class="text-sm text-muted-foreground">{i18n.t.home.mempoolTxs}</span>
							<span class="text-sm font-semibold tabular-nums">{network.mempool_size.count.toLocaleString()}</span>
						</div>
					</div>
				{:else}
					<div class="space-y-3">
						<Skeleton class="h-5 w-full" />
						<Skeleton class="h-5 w-full" />
						<Skeleton class="h-5 w-full" />
					</div>
				{/if}
			</CardContent>
		</Card>
	</section>

	<section use:inViewStagger={{ y: 20, staggerDelay: 0.09 }}>
		<h2 class="font-heading text-lg font-semibold mb-5">{i18n.t.home.toolsTitle}</h2>
		<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
			{#each tools as tool (tool.href)}
				<a
					href={resolve(tool.href as '/remittance' | '/pension' | '/savings')}
					class="group block h-full"
					use:springHover={{ scale: 1.02 }}
					use:pressScale
				>
					<Card class="p-6 h-full transition-colors duration-200 hover:bg-muted">
						<div class="space-y-4">
							<div class="flex items-center justify-between">
								<tool.icon size={28} class={tool.color} weight="regular" />
								<ArrowRight size={18} class="text-muted-foreground transition-transform duration-200 group-hover:translate-x-1 group-hover:text-primary" weight="bold" />
							</div>
							<div class="space-y-1.5">
								<h3 class="font-heading text-base font-semibold text-foreground">{tool.title()}</h3>
								<p class="text-sm text-muted-foreground leading-relaxed">{tool.description()}</p>
							</div>
						</div>
					</Card>
				</a>
			{/each}
		</div>
	</section>
</div>

<script lang="ts">
	import type { PensionProjection } from '$lib/models/pension';
	import { api } from '$lib/api/client';
	import { endpoints } from '$lib/api/endpoints';
	import { i18n } from '$lib/i18n/index.svelte';
	import { formatUSD } from '$lib/utils/formatters';
	import { createQuery } from '@tanstack/svelte-query';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import PiggyBank from 'phosphor-svelte/lib/PiggyBank';
	import CurrencyBtc from 'phosphor-svelte/lib/CurrencyBtc';
	import TrendUp from 'phosphor-svelte/lib/TrendUp';
	import Geo from '$lib/components/geo.svelte';
	import SavingsChart from '$lib/components/savings-chart.svelte';
	import GrowthChart from '$lib/components/GrowthChart.svelte';
	import PriceBar from '$lib/components/PriceBar.svelte';
	import AnimatedNumber from '$lib/components/animated-number.svelte';
	import { animateIn, staggerChildren, pressScale } from '$lib/motion';
	import { priceStore } from '$lib/stores/price.svelte';

	const HORIZONS = [10, 15, 25] as const;

	let monthlySaving = $state(10);

	// Single API call with 25 years — we extract 10yr and 15yr data from it
	let queryInput = $state<{ monthly_saving_usd: number; years: number } | null>(null);

	const pensionQuery = createQuery(() => ({
		queryKey: ['pension-projection', queryInput] as const,
		queryFn: () => api.post<PensionProjection>(endpoints.pension.projection, queryInput!),
		enabled: queryInput !== null,
	}));

	function handleCalculate() {
		queryInput = { monthly_saving_usd: monthlySaving, years: 25 };
	}

	let fullResult = $derived(pensionQuery.data ?? null);
	let isLoading = $derived(pensionQuery.isFetching);
	let error = $derived(pensionQuery.error?.message ?? null);

	// Extract snapshot at each horizon from the 25-year breakdown
	interface HorizonSnapshot {
		years: number;
		totalInvested: number;
		btcAccumulated: number;
		currentValue: number;
		piggyBank: number;
	}

	// Live price for scenario charts
	let livePrice = $derived($priceStore.price);

	$effect(() => {
		priceStore.startAutoRefresh();
		return () => priceStore.stopAutoRefresh();
	});

	// Scenario projections (friend's component integration)
	let scenarioData = $derived.by(() => {
		if (!fullResult || livePrice <= 0) return null;
		const years = 25;
		const totalInvested = monthlySaving * 12 * years;
		const totalBtc = fullResult.total_btc_accumulated;

		const scenarios = [
			{ name: 'Pesimista', btcPrice: 150_000, color: 'border-red-400 hover:shadow-[0_0_30px_rgba(239,68,68,0.4)]' },
			{ name: 'Base', btcPrice: 500_000, color: 'border-amber-500 hover:shadow-[0_0_30px_rgba(234,179,8,0.4)]' },
			{ name: 'Optimista', btcPrice: 1_000_000, color: 'border-green-500 hover:shadow-[0_0_30px_rgba(34,197,94,0.4)]' },
		];

		return scenarios.map(s => {
			const portfolioValue = totalBtc * s.btcPrice;
			const gain = portfolioValue - totalInvested;
			const gainPct = totalInvested > 0 ? (gain / totalInvested) * 100 : 0;
			const multiplier = totalInvested > 0 ? portfolioValue / totalInvested : 0;
			return { ...s, portfolioValue, gain, gainPct, multiplier, totalBtc, totalInvested };
		});
	});

	let snapshots = $derived.by(() => {
		if (!fullResult) return [];
		const breakdown = fullResult.monthly_breakdown;
		if (!breakdown || breakdown.length === 0) return [];

		return HORIZONS.map((yr): HorizonSnapshot => {
			const monthIdx = yr * 12 - 1; // 0-indexed
			const entry = breakdown[Math.min(monthIdx, breakdown.length - 1)];
			return {
				years: yr,
				totalInvested: entry?.invested ?? monthlySaving * yr * 12,
				btcAccumulated: entry?.btc_total ?? 0,
				currentValue: entry?.value_usd ?? 0,
				piggyBank: monthlySaving * yr * 12,
			};
		});
	});
</script>

<svelte:head>
	<title>{i18n.t.pension.title} {i18n.t.app.titleSuffix}</title>
</svelte:head>

<div class="space-y-8" use:staggerChildren={{ y: 20, staggerDelay: 0.08 }}>
	<div>
		<h1 class="font-heading text-2xl font-bold tracking-tight">{i18n.t.pension.title}</h1>
		<p class="text-sm text-muted-foreground mt-1">{i18n.t.pension.subtitle}</p>
	</div>

	<!-- Live BTC Price Bar -->
	<PriceBar />

	<Card>
		<CardHeader>
			<CardTitle class="font-heading flex items-center gap-2">
				<PiggyBank size={20} class="text-emerald-500" />
				{i18n.t.pension.formTitle}
			</CardTitle>
		</CardHeader>
		<CardContent class="space-y-6">
			<div class="max-w-sm space-y-2">
				<label for="monthly" class="text-sm font-semibold">{i18n.t.pension.monthlySaving}</label>
				<Input
					id="monthly"
					type="number"
					bind:value={monthlySaving}
					min="1"
					step="1"
					placeholder="10"
				/>
				<p class="text-xs text-muted-foreground">{i18n.t.pension.minimumHint}</p>
			</div>

			<div use:pressScale>
				<Button onclick={handleCalculate} disabled={isLoading} class="w-full md:w-auto">
					{isLoading ? i18n.t.common.loading : i18n.t.pension.calculate}
				</Button>
			</div>
		</CardContent>
	</Card>
</div>

{#if error}
	<div class="mt-6" use:animateIn={{ y: [10, 0], duration: 0.3 }}>
		<Card class="border-destructive">
			<CardContent class="pt-4">
				<p class="text-sm text-destructive">{error}</p>
			</CardContent>
		</Card>
	</div>
{/if}

{#if isLoading}
	<div class="mt-6 space-y-6" use:animateIn={{ opacity: [0, 1], duration: 0.2 }}>
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			{#each Array(3) as _}
				<Card>
					<CardContent class="pt-6 space-y-3">
						<Skeleton class="h-4 w-20" />
						<Skeleton class="h-10 w-32" />
						<Skeleton class="h-4 w-full" />
						<Skeleton class="h-10 w-32" />
					</CardContent>
				</Card>
			{/each}
		</div>
	</div>
{:else if !fullResult && !error}
	<div class="mt-6 rounded-2xl border border-dashed border-border bg-muted p-8 text-center space-y-3" use:animateIn={{ y: [12, 0], delay: 0.2 }}>
		<Geo state="waiting" class="w-24 h-24 mx-auto" />
		<p class="text-muted-foreground text-sm">{i18n.t.pension.emptyState}</p>
	</div>
{/if}

{#if fullResult && snapshots.length > 0}
	<div class="mt-8 space-y-8" use:animateIn={{ y: [30, 0], duration: 0.6 }}>

		<div class="flex items-center gap-3">
			<Geo state="success" class="w-16 h-16 shrink-0" />
			<div>
				<p class="text-sm font-medium text-foreground">{i18n.t.pension.resultsReady}</p>
				<Badge variant="secondary" class="text-xs font-normal mt-1">
					{i18n.t.pension.basedOnHistorical}
				</Badge>
			</div>
		</div>

		<!-- 3 horizons side by side -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4" use:staggerChildren={{ y: 20, staggerDelay: 0.12 }}>
			{#each snapshots as snap, idx}
				{@const multiplier = snap.piggyBank > 0 ? (snap.currentValue / snap.piggyBank) : 0}
				{@const isLast = idx === snapshots.length - 1}
				<Card class={isLast ? 'border-primary' : ''}>
					<CardHeader class="pb-3">
						<CardTitle class="font-heading text-lg flex items-center justify-between">
							{snap.years} {i18n.t.pension.years}
							{#if isLast}
								<Badge variant="default" class="text-xs">{i18n.t.remittance.recommended}</Badge>
							{/if}
						</CardTitle>
					</CardHeader>
					<CardContent class="space-y-4">
						<!-- Piggy bank -->
						<div class="space-y-1">
							<span class="text-xs text-muted-foreground">{i18n.t.pension.piggyBankSaved}</span>
							<div class="text-lg font-bold tabular-nums text-muted-foreground">
								<AnimatedNumber value={snap.piggyBank} format={formatUSD} />
							</div>
						</div>

						<!-- Bitcoin -->
						<div class="space-y-1">
							<span class="text-xs text-muted-foreground flex items-center gap-1">
								<CurrencyBtc size={12} class="text-amber-500" />
								{i18n.t.pension.piggyBankBtc}
							</span>
							<div class="text-2xl font-bold tabular-nums text-emerald-500">
								<AnimatedNumber value={snap.currentValue} format={formatUSD} duration={1000} />
							</div>
						</div>

						<!-- BTC accumulated -->
						<div class="text-xs text-muted-foreground tabular-nums">
							<AnimatedNumber value={snap.btcAccumulated} format={(v) => `${v.toFixed(6)} BTC`} />
						</div>

						<!-- Multiplier -->
						{#if multiplier > 1}
							<div class="pt-2 border-t border-border">
								<Badge variant={isLast ? 'default' : 'secondary'} class="text-sm font-bold">
									{multiplier.toFixed(1)}x
								</Badge>
								<span class="text-xs text-muted-foreground ml-2">{i18n.t.pension.piggyBankCaption}</span>
							</div>
						{/if}
					</CardContent>
				</Card>
			{/each}
		</div>

		<!-- Price context -->
		<div use:animateIn={{ y: [16, 0], delay: 0.3 }}>
			<Card>
				<CardContent class="pt-6">
					<div class="grid grid-cols-2 gap-4">
						<div class="space-y-1">
							<span class="text-sm text-muted-foreground">{i18n.t.pension.avgBuyPrice}</span>
							<div class="text-lg font-semibold tabular-nums">
								<AnimatedNumber value={fullResult.avg_buy_price} format={formatUSD} />
							</div>
						</div>
						<div class="space-y-1">
							<span class="text-sm text-muted-foreground">{i18n.t.pension.currentPrice}</span>
							<div class="text-lg font-semibold tabular-nums">
								<AnimatedNumber value={fullResult.current_btc_price} format={formatUSD} />
							</div>
						</div>
					</div>
				</CardContent>
			</Card>
		</div>

		<!-- Chart (full 25-year projection) -->
		{#if fullResult.monthly_data.length > 0}
			<div use:animateIn={{ y: [20, 0], delay: 0.4 }}>
				<SavingsChart data={fullResult.monthly_data} />
			</div>
		{/if}

		<!-- Scenario Analysis (friend's component) -->
		{#if scenarioData && livePrice > 0}
			<div use:animateIn={{ y: [20, 0], delay: 0.5 }}>
				<Card>
					<CardHeader>
						<CardTitle class="font-heading text-base">
							{i18n.locale === 'es' ? '¿Y si el precio de Bitcoin sube?' : 'What if Bitcoin price goes up?'}
						</CardTitle>
						<p class="text-xs text-muted-foreground">
							{i18n.locale === 'es'
								? 'Tres escenarios de precio para tu ahorro de 25 años'
								: 'Three price scenarios for your 25-year savings'}
						</p>
					</CardHeader>
					<CardContent>
						<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
							{#each scenarioData as scenario}
								<div class="p-4 border-2 rounded-xl space-y-3 transition-all duration-300 hover:scale-[1.02] {scenario.color}">
									<div class="flex items-center justify-between">
										<h3 class="text-base font-semibold">{scenario.name}</h3>
										<Badge variant="secondary" class="text-xs">
											BTC @ ${(scenario.btcPrice / 1000).toFixed(0)}K
										</Badge>
									</div>
									<div class="space-y-2 text-sm">
										<div class="flex justify-between">
											<span class="text-muted-foreground">{i18n.locale === 'es' ? 'Valor del portafolio' : 'Portfolio value'}</span>
											<span class="font-bold text-lg tabular-nums">
												<AnimatedNumber value={scenario.portfolioValue} format={formatUSD} />
											</span>
										</div>
										<div class="flex justify-between">
											<span class="text-muted-foreground">{i18n.locale === 'es' ? 'Ganancia' : 'Gain'}</span>
											<span class="font-medium text-green-500 tabular-nums">
												+<AnimatedNumber value={scenario.gain} format={formatUSD} /> ({scenario.gainPct.toFixed(0)}%)
											</span>
										</div>
										<div class="flex justify-between">
											<span class="text-muted-foreground">{i18n.locale === 'es' ? 'Multiplicador' : 'Multiplier'}</span>
											<span class="font-bold">{scenario.multiplier.toFixed(1)}x</span>
										</div>
									</div>
									<div class="pt-2 border-t border-border text-xs text-muted-foreground tabular-nums">
										{scenario.totalBtc.toFixed(6)} BTC × ${(scenario.btcPrice).toLocaleString()}
									</div>
								</div>
							{/each}
						</div>
					</CardContent>
				</Card>
			</div>

			<!-- Growth Chart with 3 scenarios -->
			<div use:animateIn={{ y: [20, 0], delay: 0.6 }}>
				<Card>
					<CardHeader class="pb-2">
						<CardTitle class="font-heading text-base">
							{i18n.locale === 'es' ? 'Proyección por escenario' : 'Scenario Projection'}
						</CardTitle>
					</CardHeader>
					<CardContent class="pt-0">
						<GrowthChart
							years={25}
							goalValue={monthlySaving * 12 * 25}
							{livePrice}
							btcOwned={0}
							monthlyDCA={monthlySaving}
						/>
					</CardContent>
				</Card>
			</div>
		{/if}

		<p class="text-xs text-muted-foreground text-center pt-4">{i18n.t.pension.disclaimer}</p>
	</div>
{/if}

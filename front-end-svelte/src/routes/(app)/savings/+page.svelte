<script lang="ts">
	import type { ProjectionResult, SavingsProgress } from '$lib/models/savings';
	import { api } from '$lib/api/client';
	import { endpoints } from '$lib/api/endpoints';
	import { auth } from '$lib/stores/auth.svelte';
	import { i18n } from '$lib/i18n/index.svelte';
	import { formatUSD } from '$lib/utils/formatters';
	import { createQuery, createMutation, keepPreviousData, useQueryClient } from '@tanstack/svelte-query';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Badge } from '$lib/components/ui/badge';
	import CurrencyBtc from 'phosphor-svelte/lib/CurrencyBtc';
	import Geo from '$lib/components/geo.svelte';
	import SavingsChart from '$lib/components/savings-chart.svelte';
	import AnimatedNumber from '$lib/components/animated-number.svelte';
	import { animateIn, staggerChildren, pressScale } from '$lib/motion';
	import PdfExportButton from '$lib/components/pdf-export-button.svelte';
	import { exportSavingsPdf } from '$lib/utils/export-pdf';
	import Wallet from 'phosphor-svelte/lib/Wallet';
	import ArrowRight from 'phosphor-svelte/lib/ArrowRight';
	import { resolve } from '$app/paths';

	let savingsChartRef = $state<HTMLElement | null>(null);

	async function handleExportPdf() {
		if (!projection) return;
		await exportSavingsPdf({
			monthlyAmount,
			years,
			scenarios: projection.scenarios,
			traditionalValue: projection.traditional_value,
			chartEl: savingsChartRef,
		});
	}

	const client = useQueryClient();

	let monthlyAmount = $state(10);
	let years = $state(10);
	let depositAmount = $state(10);
	let goalMonthly = $state(10);
	let goalYears = $state(10);
	let error = $state<string | null>(null);

	// --- Projection (on-demand, not auto) ---
	let projectionInput = $state<{ monthly_usd: number; years: number } | null>(null);

	const projectionQuery = createQuery(() => ({
		queryKey: ['savings-projection', projectionInput] as const,
		queryFn: () => api.post<ProjectionResult>(endpoints.savings.project, projectionInput!),
		enabled: projectionInput !== null,
		placeholderData: keepPreviousData,
	}));

	function runProjection() {
		error = null;
		projectionInput = { monthly_usd: monthlyAmount, years };
	}

	let projection = $derived(projectionQuery.data ?? null);
	let isProjecting = $derived(projectionQuery.isFetching);

	// --- Progress (auto-fetch when authenticated) ---
	const progressQuery = createQuery(() => ({
		queryKey: ['savings-progress'],
		queryFn: () => api.get<SavingsProgress>(endpoints.savings.progress),
		enabled: auth.isAuthenticated,
		staleTime: 30_000,
	}));

	let progress = $derived(progressQuery.data ?? null);

	// --- Create goal mutation ---
	const goalMutation = createMutation(() => ({
		mutationFn: (data: { monthly_target_usd: number; target_years: number }) =>
			api.post(endpoints.savings.goal, data),
		onSuccess: () => { client.invalidateQueries({ queryKey: ['savings-progress'] }); },
		onError: (e: Error) => { error = e.message || 'Failed to create goal'; },
	}));

	function createGoal() {
		goalMutation.mutate({ monthly_target_usd: goalMonthly, target_years: goalYears });
	}

	// --- Record deposit mutation ---
	const depositMutation = createMutation(() => ({
		mutationFn: (data: { amount_usd: number }) =>
			api.post(endpoints.savings.deposit, data),
		onSuccess: () => { client.invalidateQueries({ queryKey: ['savings-progress'] }); },
		onError: (e: Error) => { error = e.message || 'Failed to record deposit'; },
	}));

	function recordDeposit() {
		error = null;
		depositMutation.mutate({ amount_usd: depositAmount });
	}

	let isSaving = $derived(depositMutation.isPending);
</script>

<svelte:head>
	<title>{i18n.t.savings.title} {i18n.t.app.titleSuffix}</title>
</svelte:head>

<div class="space-y-6">
	<div use:animateIn={{ y: [20, 0], duration: 0.5 }}>
		<h1 class="font-heading text-2xl font-bold tracking-tight">{i18n.t.savings.title}</h1>
	</div>

	<div use:animateIn={{ y: [20, 0], delay: 0.08 }}>
		<Card>
			<CardHeader>
				<CardTitle class="font-heading">{i18n.t.savings.projectionTitle}</CardTitle>
			</CardHeader>
			<CardContent class="space-y-6">
				<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
					<div class="space-y-1.5">
						<Label class="text-sm font-semibold text-muted-foreground">{i18n.t.savings.monthlyAmount}</Label>
						<Input type="number" bind:value={monthlyAmount} min="1" step="1" />
					</div>
					<div class="space-y-1.5">
						<Label class="text-sm font-semibold text-muted-foreground">{i18n.t.savings.years}</Label>
						<Input type="number" bind:value={years} min="1" max="50" step="1" />
					</div>
					<div class="flex items-end">
						<div use:pressScale class="w-full">
							<Button onclick={runProjection} disabled={isProjecting} class="w-full">
								{isProjecting ? i18n.t.common.loading : i18n.t.savings.calculate}
							</Button>
						</div>
					</div>
				</div>

				{#if !projection && !isProjecting}
					<div class="rounded-2xl border border-dashed border-border bg-muted p-8 text-center space-y-3" use:animateIn={{ y: [12, 0], delay: 0.2 }}>
						<Geo state="stacking" class="w-24 h-24 mx-auto" />
						<p class="text-muted-foreground text-sm">{i18n.t.savings.subtitle}</p>
						<p class="text-xs text-muted-foreground">${monthlyAmount}/mo &middot; {years} {i18n.t.savings.years.toLowerCase()}</p>
					</div>
				{/if}

				{#if projection}
					<div class="space-y-6" use:animateIn={{ y: [24, 0], duration: 0.5 }}>
						<div class="grid grid-cols-1 sm:grid-cols-3 gap-3" use:staggerChildren={{ y: 16, staggerDelay: 0.08 }}>
							{#each projection.scenarios as scenario}
								<div class="rounded-2xl p-5 transition-colors duration-200 {scenario.name === 'moderate' ? 'bg-muted border border-primary' : 'bg-muted'}">
									<div class="space-y-2">
										<div class="flex items-center gap-2">
											<Badge variant={scenario.name === 'moderate' ? 'default' : 'secondary'} class="text-xs">
												{scenario.name === 'conservative' ? i18n.t.savings.conservative :
												 scenario.name === 'moderate' ? i18n.t.savings.moderate :
												 i18n.t.savings.optimistic}
											</Badge>
											<span class="text-xs text-muted-foreground">{scenario.annual_return_pct}% {i18n.t.savings.annual}</span>
										</div>
										<p class="font-heading text-2xl font-bold tabular-nums">
											<AnimatedNumber value={scenario.projected_value} format={formatUSD} duration={800} />
										</p>
										<p class="text-xs text-muted-foreground">
											{scenario.multiplier}x {i18n.t.savings.multiplier}
										</p>
									</div>
								</div>
							{/each}
						</div>

						<div class="flex items-center gap-4 p-4 rounded-2xl bg-muted" use:animateIn={{ opacity: [0, 1], delay: 0.3 }}>
							<div>
								<p class="text-xs text-muted-foreground">{i18n.t.savings.traditionalSavings}</p>
								<p class="font-heading text-lg font-semibold tabular-nums">
									<AnimatedNumber value={projection.traditional_value} format={formatUSD} />
								</p>
							</div>
							<span class="text-muted-foreground text-sm">vs</span>
							<div>
								<p class="text-xs text-muted-foreground">Bitcoin DCA ({i18n.t.savings.moderate})</p>
								<p class="font-heading text-lg font-semibold text-emerald-500 tabular-nums">
									<AnimatedNumber
										value={projection.scenarios.find(s => s.name === 'moderate')?.projected_value ?? 0}
										format={formatUSD}
									/>
								</p>
							</div>
						</div>

						{#if projection.monthly_data.length > 0}
							<div use:animateIn={{ y: [16, 0], delay: 0.4 }} bind:this={savingsChartRef}>
								<SavingsChart data={projection.monthly_data} />
							</div>
						{/if}

						<div class="flex items-center justify-between pt-2 gap-3">
							<a
								href={resolve('/wallets')}
								class="group flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
							>
								<Wallet size={14} class="text-cyan-500 shrink-0" />
								<span>{i18n.t.wallets.tipSavings}</span>
								<ArrowRight size={12} class="opacity-0 group-hover:opacity-100 transition-opacity" />
							</a>
							<PdfExportButton onclick={handleExportPdf} label="Exportar proyección" />
						</div>
					</div>
				{/if}
			</CardContent>
		</Card>
	</div>

	{#if auth.isAuthenticated}
		{#if progress?.has_goal}
			<div use:animateIn={{ y: [20, 0], delay: 0.15 }}>
				<Card>
					<CardHeader>
						<CardTitle class="font-heading">{i18n.t.savings.progressTitle}</CardTitle>
					</CardHeader>
					<CardContent class="space-y-6">
						<div class="grid grid-cols-2 sm:grid-cols-4 gap-4" use:staggerChildren={{ y: 12, staggerDelay: 0.06 }}>
							<div class="space-y-1">
								<p class="text-xs text-muted-foreground">{i18n.t.savings.totalInvested}</p>
								<p class="font-heading text-xl font-bold tabular-nums">
									<AnimatedNumber value={progress.total_invested_usd} format={formatUSD} />
								</p>
							</div>
							<div class="space-y-1">
								<p class="text-xs text-muted-foreground">{i18n.t.savings.currentValue}</p>
								<p class="font-heading text-xl font-bold text-emerald-500 tabular-nums">
									<AnimatedNumber value={progress.current_value_usd} format={formatUSD} />
								</p>
							</div>
							<div class="space-y-1">
								<p class="text-xs text-muted-foreground">ROI</p>
								<p class="font-heading text-xl font-bold tabular-nums {progress.roi_percent >= 0 ? 'text-green-600 dark:text-green-500' : 'text-red-600 dark:text-red-500'}">
									{progress.roi_percent >= 0 ? '+' : ''}<AnimatedNumber value={progress.roi_percent} format={(v) => `${v.toFixed(1)}%`} />
								</p>
							</div>
							<div class="space-y-1">
								<p class="text-xs text-muted-foreground">{i18n.t.savings.streak}</p>
								<p class="font-heading text-xl font-bold tabular-nums">
									<AnimatedNumber value={progress.streak_months} format={(v) => `${Math.round(v)}`} /> {i18n.t.savings.months}
								</p>
							</div>
						</div>

						<div class="space-y-2">
							<h3 class="text-sm font-medium">{i18n.t.savings.milestones}</h3>
							<div class="flex flex-wrap gap-2">
								{#each progress.milestones as milestone}
									<Badge variant={milestone.reached ? 'default' : 'outline'} class="{milestone.reached ? 'bg-green-600' : ''} transition-all duration-300">
										{milestone.reached ? '✓' : '○'} {milestone.name}
									</Badge>
								{/each}
							</div>
						</div>

						<div class="flex gap-3 items-end p-4 rounded-2xl border border-dashed border-border">
							<div class="space-y-1.5 flex-1">
								<Label class="text-sm font-semibold text-muted-foreground">{i18n.t.savings.depositAmount}</Label>
								<Input type="number" bind:value={depositAmount} min="1" step="1" />
							</div>
							<div use:pressScale>
								<Button onclick={recordDeposit} disabled={isSaving}>
									{isSaving ? i18n.t.common.loading : i18n.t.savings.recordDeposit}
								</Button>
							</div>
						</div>

						{#if progress.recent_deposits.length > 0}
							<div class="space-y-2">
								<h3 class="text-sm font-medium">{i18n.t.savings.recentDeposits}</h3>
								<div use:staggerChildren={{ y: 8, staggerDelay: 0.05 }}>
									{#each progress.recent_deposits as deposit}
										<div class="flex justify-between items-center py-2.5 border-b border-border/50 text-sm">
											<span class="font-medium tabular-nums">{formatUSD(deposit.amount_usd)}</span>
											<span class="text-muted-foreground tabular-nums">{deposit.btc_amount.toFixed(8)} BTC</span>
											<span class="text-muted-foreground text-xs">
												{new Date(deposit.created_at * 1000).toLocaleDateString()}
											</span>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</CardContent>
				</Card>
			</div>
		{:else}
			<div use:animateIn={{ y: [20, 0], delay: 0.15 }}>
				<Card>
					<CardHeader>
						<CardTitle class="font-heading">{i18n.t.savings.setupGoal}</CardTitle>
					</CardHeader>
					<CardContent>
						<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
							<div class="space-y-1.5">
								<Label class="text-sm font-semibold text-muted-foreground">{i18n.t.savings.monthlyTarget}</Label>
								<Input type="number" bind:value={goalMonthly} min="1" step="1" />
							</div>
							<div class="space-y-1.5">
								<Label class="text-sm font-semibold text-muted-foreground">{i18n.t.savings.targetYears}</Label>
								<Input type="number" bind:value={goalYears} min="1" max="50" step="1" />
							</div>
							<div class="flex items-end">
								<div use:pressScale class="w-full">
									<Button onclick={createGoal} class="w-full">{i18n.t.savings.createGoal}</Button>
								</div>
							</div>
						</div>
					</CardContent>
				</Card>
			</div>
		{/if}
	{/if}

	{#if error || projectionQuery.error}
		<div use:animateIn={{ y: [10, 0], duration: 0.3 }}>
			<p class="text-sm text-destructive">{error || projectionQuery.error?.message}</p>
		</div>
	{/if}
</div>

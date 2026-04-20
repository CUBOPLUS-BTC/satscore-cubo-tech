<script lang="ts">
	import type { RemittanceResult } from '$lib/models/remittance';
	import { api } from '$lib/api/client';
	import { endpoints } from '$lib/api/endpoints';
	import { i18n } from '$lib/i18n/index.svelte';
	import { createQuery } from '@tanstack/svelte-query';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Select from '$lib/components/ui/select';
	import ChannelCard from '$lib/components/channel-card.svelte';
	import SavingsCard from '$lib/components/savings-card.svelte';
	import AnimatedNumber from '$lib/components/animated-number.svelte';
	import { animateIn, staggerChildren, pressScale } from '$lib/motion';
	import Clock from 'phosphor-svelte/lib/Clock';
	import Geo from '$lib/components/geo.svelte';

	let amountUsd = $state(200);
	let frequency = $state<string>('monthly');

	let queryInput = $state<{ amount_usd: number; frequency: string } | null>(null);

	const compareQuery = createQuery(() => ({
		queryKey: ['remittance-compare', queryInput] as const,
		queryFn: () => api.post<RemittanceResult>(endpoints.remittance.compare, queryInput!),
		enabled: queryInput !== null,
	}));

	function handleCompare() {
		queryInput = { amount_usd: amountUsd, frequency };
	}

	let result = $derived(compareQuery.data ?? null);
	let isLoading = $derived(compareQuery.isFetching);
	let error = $derived(compareQuery.error?.message ?? null);
</script>

<svelte:head>
	<title>{i18n.t.remittance.title} {i18n.t.app.titleSuffix}</title>
	<meta name="description" content={i18n.t.remittance.subtitle} />
</svelte:head>

<div class="space-y-8" use:staggerChildren={{ y: 20, staggerDelay: 0.08 }}>
	<div>
		<h1 class="font-heading text-2xl font-bold tracking-tight">{i18n.t.remittance.title}</h1>
		<p class="text-sm text-muted-foreground mt-1">{i18n.t.remittance.corridor}</p>
	</div>

	<Card>
		<CardHeader>
			<CardTitle class="font-heading">{i18n.t.remittance.compareOptions}</CardTitle>
		</CardHeader>
		<CardContent class="space-y-6">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="space-y-2">
					<label for="amount" class="text-sm font-semibold">{i18n.t.remittance.amount}</label>
					<Input
						id="amount"
						type="number"
						bind:value={amountUsd}
						min="1"
						step="1"
						placeholder="Enter amount"
					/>
				</div>

				<div class="space-y-2">
					<label for="frequency" class="text-sm font-semibold">{i18n.t.remittance.frequency}</label>
					<Select.Root type="single" bind:value={frequency}>
						<Select.Trigger id="frequency">
							{i18n.t.remittance.frequencies[frequency as keyof typeof i18n.t.remittance.frequencies] ?? frequency}
						</Select.Trigger>
						<Select.Content>
							<Select.Item value="monthly">{i18n.t.remittance.frequencies.monthly}</Select.Item>
							<Select.Item value="biweekly">{i18n.t.remittance.frequencies.biweekly}</Select.Item>
							<Select.Item value="weekly">{i18n.t.remittance.frequencies.weekly}</Select.Item>
						</Select.Content>
					</Select.Root>
				</div>
			</div>

			<div use:pressScale>
				<Button onclick={handleCompare} disabled={isLoading} class="w-full md:w-auto">
					{isLoading ? i18n.t.remittance.comparing : i18n.t.remittance.compare}
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
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<Card>
				<CardContent class="pt-6 space-y-4">
					<Skeleton class="h-4 w-32" />
					<Skeleton class="h-8 w-24" />
					<Skeleton class="h-4 w-full" />
				</CardContent>
			</Card>
			<Card>
				<CardContent class="pt-6 space-y-4">
					<Skeleton class="h-4 w-32" />
					<Skeleton class="h-8 w-24" />
					<Skeleton class="h-4 w-full" />
				</CardContent>
			</Card>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			{#each Array(3) as _}
				<Card>
					<CardContent class="pt-6 space-y-3">
						<Skeleton class="h-5 w-20" />
						<Skeleton class="h-6 w-16" />
						<Skeleton class="h-4 w-full" />
					</CardContent>
				</Card>
			{/each}
		</div>
	</div>
{:else if !result && !error}
	<div class="mt-6 rounded-2xl border border-dashed border-border bg-muted p-8 text-center space-y-3" use:animateIn={{ y: [12, 0], delay: 0.3 }}>
		<Geo state="waiting" class="w-24 h-24 mx-auto" />
		<p class="text-muted-foreground text-sm">{i18n.t.remittance.subtitle}</p>
	</div>
{/if}

{#if result}
	<div class="mt-8 space-y-6" use:animateIn={{ y: [30, 0], duration: 0.6 }}>
		<!-- Impact message hero -->
		{#if result.savings_vs_worst > 0}
			<div class="rounded-2xl border-2 border-primary bg-primary/5 p-6 text-center space-y-2">
				<Geo state="success" class="w-16 h-16 mx-auto" />
				<p class="text-sm text-muted-foreground">{i18n.t.remittance.impactMessage}</p>
				<p class="font-heading text-4xl font-bold text-primary tabular-nums">
					<AnimatedNumber value={result.savings_vs_worst} format={(v) => `$${v.toFixed(2)}`} duration={1000} />
				</p>
				<p class="text-sm text-muted-foreground">
					{i18n.t.remittance.impactMore} <span class="font-semibold text-foreground">{result.worst_channel_name}</span> {i18n.t.remittance.impactPerTransfer}
				</p>
			</div>
		{/if}

		{#if i18n.t.remittance.legalTender}
			<p class="text-sm text-muted-foreground bg-muted/50 rounded-xl p-4">{i18n.t.remittance.legalTender}</p>
		{/if}

		<SavingsCard annualSavings={result.annual_savings} bestChannel={result.best_channel} />

		<div class="grid grid-cols-1 md:grid-cols-2 gap-4" use:staggerChildren={{ y: 20, staggerDelay: 0.1 }}>
			{#if result.best_time}
				<Card>
					<CardHeader>
						<CardTitle class="flex items-center gap-2 text-sm font-medium text-muted-foreground">
							<Clock size={18} weight="regular" />
							{i18n.t.remittance.bestTime}
						</CardTitle>
					</CardHeader>
					<CardContent class="space-y-3">
						<div class="text-2xl font-bold text-foreground">
							{result.best_time.best_time}
						</div>
						<div class="flex justify-between items-center">
							<span class="text-sm text-muted-foreground">{i18n.t.remittance.currentFee}</span>
							<span class="text-sm font-medium tabular-nums">{result.best_time.current_fee_sat_vb} sat/vB</span>
						</div>
						<div class="flex justify-between items-center">
							<span class="text-sm text-muted-foreground">{i18n.t.remittance.lowFee}</span>
							<span class="text-sm font-medium tabular-nums text-green-600 dark:text-green-500">{result.best_time.estimated_low_fee_sat_vb} sat/vB</span>
						</div>
						<div class="flex justify-between items-center">
							<span class="text-sm text-muted-foreground">{i18n.t.remittance.savings}</span>
							<Badge variant="secondary">
								<AnimatedNumber value={result.best_time.savings_percent} format={(v) => `${v.toFixed(0)}%`} />
							</Badge>
						</div>
					</CardContent>
				</Card>
			{/if}
		</div>

		<div>
			<h2 class="font-heading text-lg font-semibold mb-4">{i18n.t.remittance.availableChannels}</h2>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4" use:staggerChildren={{ y: 16, staggerDelay: 0.08 }}>
				{#each result.channels as channel (channel.name)}
					<ChannelCard {channel} />
				{/each}
			</div>
		</div>

		<!-- Deep links to wallets -->
		<div use:animateIn={{ y: [16, 0], delay: 0.5 }}>
			<Card>
				<CardHeader>
					<CardTitle class="font-heading text-base">{i18n.t.remittance.walletsTitle}</CardTitle>
					<p class="text-xs text-muted-foreground">{i18n.t.remittance.walletsSubtitle}</p>
				</CardHeader>
				<CardContent>
					<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
						{#each [
							{ name: 'Blink', url: 'https://www.blink.sv/', color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 hover:bg-blue-500/20' },
							{ name: 'Strike', url: 'https://strike.me/', color: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 hover:bg-purple-500/20' },
							{ name: 'Phoenix', url: 'https://phoenix.acinq.co/', color: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 hover:bg-orange-500/20' },
							{ name: 'WoS', url: 'https://www.walletofsatoshi.com/', color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20' },
						] as wallet}
							<a
								href={wallet.url}
								target="_blank"
								rel="noopener noreferrer"
								class="flex items-center justify-center gap-2 rounded-xl border border-border px-4 py-3 text-sm font-medium transition-colors {wallet.color}"
							>
								{i18n.t.remittance.sendWith} {wallet.name}
							</a>
						{/each}
					</div>
				</CardContent>
			</Card>
		</div>
	</div>
{/if}

<script lang="ts">
	import type { RemittanceResult } from '$lib/models/remittance';
	import { api } from '$lib/api/client';
	import { endpoints } from '$lib/api/endpoints';
	import { Card } from '$lib/components/ui/card';
	import { CardHeader } from '$lib/components/ui/card';
	import { CardTitle } from '$lib/components/ui/card';
	import { CardContent } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Select } from 'bits-ui';
	import ChannelCard from '$lib/components/channel-card.svelte';
	import SavingsCard from '$lib/components/savings-card.svelte';
	import Clock from 'phosphor-svelte/lib/Clock';
	import ArrowsLeftRight from 'phosphor-svelte/lib/ArrowsLeftRight';

	let amountUsd = $state(200);
	let frequency = $state<string>('monthly');
	let result = $state<RemittanceResult | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	async function handleCompare() {
		isLoading = true;
		error = null;
		result = null;

		try {
			result = await api.post<RemittanceResult>(endpoints.remittance.compare, {
				amount_usd: amountUsd,
				frequency: frequency as 'monthly' | 'biweekly' | 'weekly'
			});
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to compare remittance options';
		} finally {
			isLoading = false;
		}
	}

	function getFrequencyLabel(value: string): string {
		const labels: Record<string, string> = {
			monthly: 'Monthly',
			biweekly: 'Biweekly',
			weekly: 'Weekly'
		};
		return labels[value] || value;
	}
</script>

<svelte:head>
	<title>Remittance — Magma</title>
	<meta name="description" content="Compare cross-border transfer channels and find the best option for your Bitcoin payments." />
</svelte:head>

<div class="space-y-8">
	<div class="space-y-2">
		<h1 class="text-3xl font-bold tracking-tight">Remittance</h1>
		<p class="text-muted-foreground">
			Compare transfer channels and find the best option for your cross-border payments.
		</p>
	</div>

	<Card>
		<CardHeader>
			<CardTitle class="flex items-center gap-2">
				<ArrowsLeftRight size={20} />
				Compare Options
			</CardTitle>
		</CardHeader>
		<CardContent class="space-y-6">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="space-y-2">
					<label for="amount" class="text-sm font-medium">Amount (USD)</label>
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
					<label for="frequency" class="text-sm font-medium">Frequency</label>
					<Select.Root type="single" bind:value={frequency}>
						<Select.Trigger id="frequency">
							{getFrequencyLabel(frequency)}
						</Select.Trigger>
						<Select.Content>
							<Select.Item value="monthly">Monthly</Select.Item>
							<Select.Item value="biweekly">Biweekly</Select.Item>
							<Select.Item value="weekly">Weekly</Select.Item>
						</Select.Content>
					</Select.Root>
				</div>
			</div>

			<Button onclick={handleCompare} disabled={isLoading} class="w-full md:w-auto">
				{isLoading ? 'Comparing...' : 'Compare Channels'}
			</Button>
		</CardContent>
	</Card>

	{#if error}
		<Card class="border-destructive">
			<CardContent class="pt-4">
				<p class="text-sm text-destructive">{error}</p>
			</CardContent>
		</Card>
	{/if}

	{#if isLoading}
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			{#each [1, 2, 3] as _, i (i)}
				<Card>
					<CardHeader>
						<Skeleton class="h-5 w-24" />
						<Skeleton class="h-4 w-16" />
					</CardHeader>
					<CardContent class="space-y-3">
						<Skeleton class="h-6 w-28" />
						<Skeleton class="h-4 w-20" />
					</CardContent>
				</Card>
			{/each}
		</div>
	{/if}

	{#if result}
		<div class="space-y-6">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<SavingsCard annualSavings={result.annual_savings} bestChannel={result.best_channel} />

				{#if result.best_time}
					<Card class="bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800">
						<CardHeader>
							<CardTitle class="flex items-center gap-2 text-blue-700 dark:text-blue-400">
								<Clock size={20} />
								Best Time to Send
							</CardTitle>
						</CardHeader>
						<CardContent class="space-y-3">
							<div class="text-2xl font-bold text-blue-600 dark:text-blue-500">
								{result.best_time.best_time}
							</div>
							<div class="flex justify-between items-center">
								<span class="text-sm text-muted-foreground">Current Fee</span>
								<span class="font-medium">{result.best_time.current_fee_sat_vb} sat/vB</span>
							</div>
							<div class="flex justify-between items-center">
								<span class="text-sm text-muted-foreground">Low Fee</span>
								<span class="font-medium text-green-600">{result.best_time.estimated_low_fee_sat_vb} sat/vB</span>
							</div>
							<div class="flex justify-between items-center">
								<span class="text-sm text-muted-foreground">Savings</span>
								<Badge variant="secondary" class="bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
									{result.best_time.savings_percent}%
								</Badge>
							</div>
						</CardContent>
					</Card>
				{/if}
			</div>

			<div>
				<h2 class="text-lg font-semibold mb-4">Available Channels</h2>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					{#each result.channels as channel (channel.name)}
						<ChannelCard {channel} />
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>

<script lang="ts">
	import type { ScoreResult } from '$lib/models/score';
	import { api } from '$lib/api/client';
	import { endpoints } from '$lib/api/endpoints';
	import { isValidBtcAddress } from '$lib/utils/validators';
	import { Card } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Alert, AlertTitle, AlertDescription } from '$lib/components/ui/alert';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ScoreGauge from '$lib/components/score-gauge.svelte';
	import BreakdownBar from '$lib/components/breakdown-bar.svelte';

	let address = $state('');
	let result = $state<ScoreResult | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	const breakdownItems = [
		{ key: 'consistency', label: 'Consistency' },
		{ key: 'relative_volume', label: 'Relative Volume' },
		{ key: 'diversification', label: 'Diversification' },
		{ key: 'savings_pattern', label: 'Savings Pattern' },
		{ key: 'payment_history', label: 'Payment History' },
		{ key: 'lightning_activity', label: 'Lightning Activity' }
	] as const;

	async function handleSubmit() {
		if (!address.trim()) {
			error = 'Please enter a Bitcoin address';
			return;
		}

		if (!isValidBtcAddress(address.trim())) {
			error = 'Invalid Bitcoin address format';
			return;
		}

		isLoading = true;
		error = null;
		result = null;

		try {
			result = await api.get<ScoreResult>(endpoints.score(address.trim()));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to fetch score';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Bitcoin Score — Magma</title>
	<meta name="description" content="Evaluate a Bitcoin address financial health score with breakdown analysis." />
</svelte:head>

<div class="container mx-auto max-w-4xl px-4 py-12 space-y-8">
	<div class="space-y-2">
		<h1 class="text-4xl font-bold tracking-tight">Bitcoin Score</h1>
		<p class="text-muted-foreground">
			Enter a Bitcoin address to evaluate its financial health score
		</p>
	</div>

	<Card class="p-6">
		<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="flex gap-3" aria-label="Bitcoin address score lookup">
			<Input
				bind:value={address}
				placeholder="bc1q..."
				class="flex-1"
				disabled={isLoading}
			/>
			<Button type="submit" disabled={isLoading}>
				{isLoading ? 'Loading...' : 'Get Score'}
			</Button>
		</form>
	</Card>

	{#if error}
		<Alert variant="destructive">
			<AlertTitle>Error</AlertTitle>
			<AlertDescription>{error}</AlertDescription>
		</Alert>
	{/if}

	{#if isLoading}
		<Card class="p-8">
			<div class="flex flex-col items-center gap-8">
				<Skeleton class="h-48 w-48 rounded-none" />
				<div class="w-full space-y-3">
					<Skeleton class="h-4 w-full rounded-none" />
					<Skeleton class="h-4 w-full rounded-none" />
					<Skeleton class="h-4 w-full rounded-none" />
					<Skeleton class="h-4 w-full rounded-none" />
					<Skeleton class="h-4 w-full rounded-none" />
					<Skeleton class="h-4 w-full rounded-none" />
				</div>
			</div>
		</Card>
	{/if}

	{#if result}
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<Card class="p-8">
				<div class="flex flex-col items-center gap-6">
					<h2 class="text-lg font-semibold">Overall Score</h2>
					<ScoreGauge score={result.total_score} rank={result.rank} />
					<div class="text-center">
						<p class="text-sm text-muted-foreground">Address</p>
						<p class="text-xs font-mono break-all">{result.address}</p>
					</div>
				</div>
			</Card>

			<Card class="p-8">
				<div class="space-y-6">
					<h2 class="text-lg font-semibold">Score Breakdown</h2>
					<div class="space-y-4">
						{#each breakdownItems as item (item.key)}
							<BreakdownBar
								label={item.label}
								score={result.breakdown[item.key]}
								maxScore={100}
							/>
						{/each}
					</div>
				</div>
			</Card>
		</div>

		{#if result.recommendations.length > 0}
			<Card class="p-6">
				<div class="space-y-4">
					<h2 class="text-lg font-semibold">Recommendations</h2>
					<ul class="space-y-2">
						{#each result.recommendations as recommendation, i (i)}
							<li class="flex items-start gap-2">
								<span class="h-1.5 w-1.5 mt-2 rounded-full bg-primary"></span>
								<span class="text-sm">{recommendation}</span>
							</li>
						{/each}
					</ul>
				</div>
			</Card>
		{/if}
	{/if}
</div>

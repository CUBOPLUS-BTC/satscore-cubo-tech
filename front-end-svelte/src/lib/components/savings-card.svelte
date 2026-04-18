<script lang="ts">
	import { formatUSD } from '$lib/utils/formatters';
	import { i18n } from '$lib/i18n/index.svelte';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';

	let {
		annualSavings,
		bestChannel
	}: {
		annualSavings: number;
		bestChannel: string;
	} = $props();

	let monthlySavings = $derived(annualSavings / 12);
</script>

<Card>
	<CardHeader>
		<CardTitle class="text-sm font-medium text-muted-foreground">{i18n.t.remittance.potentialAnnualSavings}</CardTitle>
	</CardHeader>

	<CardContent class="space-y-3">
		<div class="text-3xl font-bold text-foreground tabular-nums">
			{formatUSD(annualSavings)}
		</div>

		<div class="space-y-1">
			<p class="text-sm text-muted-foreground">
				{i18n.t.remittance.vsWorstChannel} <span class="font-medium text-foreground">{bestChannel}</span>
			</p>
			<p class="text-sm font-medium text-green-600 dark:text-green-500">
				+{formatUSD(monthlySavings)}/month
			</p>
		</div>
	</CardContent>
</Card>

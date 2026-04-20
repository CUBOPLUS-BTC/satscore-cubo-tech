<script lang="ts">
	import type { ChannelComparison } from '$lib/models/remittance';
	import { formatUSD } from '$lib/utils/formatters';
	import { i18n } from '$lib/i18n/index.svelte';
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';

	let { channel }: { channel: ChannelComparison } = $props();
</script>

<Card
	class="relative {channel.is_recommended
		? 'border-primary'
		: ''}"
>
	<CardHeader>
		<div class="flex items-center justify-between">
			<CardTitle class="text-base">{channel.name}</CardTitle>
			{#if channel.is_recommended}
				<Badge variant="default" class="text-xs">{i18n.t.remittance.recommended}</Badge>
			{/if}
		</div>
		<CardDescription class="flex items-center gap-2">
			<span>{i18n.t.remittance.fee}:</span>
			<span class="font-medium text-foreground tabular-nums">{channel.fee_percent}%</span>
			{#if channel.is_live}
				<span class="inline-flex items-center gap-1 text-[10px] text-green-600 dark:text-green-500">
					<span class="size-1.5 rounded-full bg-green-500 animate-pulse"></span>
					{i18n.t.remittance.live}
				</span>
			{:else}
				<span class="text-[10px] text-muted-foreground">{i18n.t.remittance.reference}</span>
			{/if}
		</CardDescription>
	</CardHeader>

	<CardContent class="space-y-3">
		<div class="flex justify-between items-center">
			<span class="text-sm text-muted-foreground">{i18n.t.remittance.amountReceived}</span>
			<span class="text-lg font-semibold text-green-600 dark:text-green-500 tabular-nums">
				{formatUSD(channel.amount_received)}
			</span>
		</div>

		<div class="flex justify-between items-center">
			<span class="text-sm text-muted-foreground">{i18n.t.remittance.estimatedTime}</span>
			<span class="text-sm font-medium">{channel.estimated_time}</span>
		</div>
	</CardContent>
</Card>

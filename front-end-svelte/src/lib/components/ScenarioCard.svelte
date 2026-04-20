<script lang="ts">
  import { Card } from '$lib/components/ui/card';
  import { Badge } from '$lib/components/ui/badge';

  interface Props {
    name: string;
    scenarioPrice: number;
    finalValue: number;
    btcNeeded: number;
    shortfall: number;
    totalInvested: number;
    gain: number;
    gainPct: number;
    multiplier: number;
    goalReached: boolean;
    priceColor: string;
  }

  let {
    name,
    scenarioPrice,
    finalValue,
    btcNeeded,
    shortfall,
    totalInvested,
    gain,
    gainPct,
    multiplier,
    goalReached,
    priceColor
  }: Props = $props();

  function formatUSD(value: number): string {
    return value.toLocaleString('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
  }

  function formatBTC(value: number): string {
    return value.toFixed(8);
  }
</script>

<Card class="p-6 space-y-4">
  <div class="flex items-center justify-between">
    <h3 class="text-lg font-semibold">{name}</h3>
    <Badge variant={goalReached ? 'default' : 'destructive'}>
      {goalReached ? 'Meta alcanzada' : 'Faltante'}
    </Badge>
  </div>

  <div class="space-y-2">
    <div class="flex justify-between text-sm">
      <span class="text-muted-foreground">Precio BTC</span>
      <span class="font-medium" style="color: {priceColor}">
        {formatUSD(scenarioPrice)}
      </span>
    </div>

    <div class="flex justify-between text-sm">
      <span class="text-muted-foreground">Valor final</span>
      <span class="font-bold text-xl">{formatUSD(finalValue)}</span>
    </div>

    <div class="flex justify-between text-sm">
      <span class="text-muted-foreground">BTC necesario</span>
      <span class="font-mono">{formatBTC(btcNeeded)} BTC</span>
    </div>

    {#if shortfall > 0}
      <div class="flex justify-between text-sm">
        <span class="text-muted-foreground">Faltante</span>
        <span class="text-red-500 font-medium">{formatUSD(shortfall)}</span>
      </div>
    {/if}

    <div class="h-px bg-border my-2"></div>

    <div class="flex justify-between text-sm">
      <span class="text-muted-foreground">Total invertido</span>
      <span>{formatUSD(totalInvested)}</span>
    </div>

    <div class="flex justify-between text-sm">
      <span class="text-muted-foreground">Ganancia</span>
      <span class="text-green-500 font-medium">{formatUSD(gain)}</span>
    </div>

    <div class="flex justify-between text-sm">
      <span class="text-muted-foreground">Ganancia %</span>
      <span class="text-green-500 font-medium">{gainPct.toFixed(1)}%</span>
    </div>

    <div class="flex justify-between text-sm">
      <span class="text-muted-foreground">Multiplicador</span>
      <span class="font-bold">{multiplier.toFixed(2)}x</span>
    </div>
  </div>
</Card>

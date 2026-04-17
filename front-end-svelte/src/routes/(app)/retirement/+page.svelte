<script lang="ts">
  import { onMount } from 'svelte';
  import { priceStore } from '$lib/stores/price.svelte';
  import PriceBar from '$lib/components/PriceBar.svelte';
  import ScenarioCard from '$lib/components/ScenarioCard.svelte';
  import GrowthChart from '$lib/components/GrowthChart.svelte';
  import { Card } from '$lib/components/ui/card';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Button } from '$lib/components/ui/button';

  let btcNow = $state(0.5);
  let yearsUntilRetirement = $state(10);
  let retirementGoal = $state(1000000);
  let monthlyDCA = $state(500);

  let bearishPrice = $state(150000);
  let basePrice = $state(500000);
  let bullishPrice = $state(1000000);

  let livePrice = $derived($priceStore.price);
  let change24h = $derived($priceStore.change24h);

  interface Scenario {
    name: string;
    price: number;
    color: string;
    finalValue: number;
    btcNeeded: number;
    shortfall: number;
    totalInvested: number;
    gain: number;
    gainPct: number;
    multiplier: number;
    goalReached: boolean;
  }

  let scenarios = $derived.by(() => {
    if (!livePrice) return [];

    const priceData = [
      { name: 'Bearish', price: bearishPrice, color: '#ef4444' },
      { name: 'Base', price: basePrice, color: '#f59e0b' },
      { name: 'Bullish', price: bullishPrice, color: '#22c55e' }
    ];

    const totalInvested = monthlyDCA * yearsUntilRetirement * 12;
    const currentValue = btcNow * livePrice;

    return priceData.map(s => {
      const dcaBtcPerMonth = monthlyDCA / livePrice;
      const totalBTC = btcNow + dcaBtcPerMonth * yearsUntilRetirement * 12;
      const finalValue = totalBTC * s.price;
      const btcNeeded = retirementGoal / s.price;
      const shortfall = Math.max(0, btcNeeded - totalBTC);
      const gain = finalValue - currentValue - totalInvested;
      const gainPct = (currentValue + totalInvested) > 0 ? (gain / (currentValue + totalInvested)) * 100 : 0;
      const multiplier = (currentValue + totalInvested) > 0 ? finalValue / (currentValue + totalInvested) : 0;

      return {
        name: s.name,
        price: s.price,
        color: s.color,
        finalValue,
        btcNeeded,
        shortfall,
        totalInvested,
        gain,
        gainPct,
        multiplier,
        goalReached: finalValue >= retirementGoal
      } as Scenario;
    });
  });

  let chartDatasets = $derived.by(() => {
    if (!livePrice || !yearsUntilRetirement) return [];

    const priceData = [
      { name: 'Bearish', price: bearishPrice, color: 'rgb(239, 68, 68)' },
      { name: 'Base', price: basePrice, color: 'rgb(245, 158, 11)' },
      { name: 'Bullish', price: bullishPrice, color: 'rgb(34, 197, 94)' }
    ];

    return priceData.map(s => {
      const dcaBtcPerMonth = monthlyDCA / livePrice;
      const data: number[] = [];

      for (let year = 0; year <= yearsUntilRetirement; year++) {
        const btcAtYear = btcNow + dcaBtcPerMonth * year * 12;
        const interpolatedPrice = livePrice + ((s.price - livePrice) / yearsUntilRetirement) * year;
        data.push(btcAtYear * interpolatedPrice);
      }

      return {
        label: s.name,
        data,
        color: s.color
      };
    });
  });

  onMount(() => {
    priceStore.startAutoRefresh();
    return () => priceStore.stopAutoRefresh();
  });

  function formatUSD(value: number): string {
    return value.toLocaleString('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
  }
</script>

<div class="container mx-auto max-w-7xl px-4 py-8 space-y-8">
  <div class="flex items-center justify-between">
    <h1 class="text-4xl font-bold">Bitcoin Retirement Calculator</h1>
  </div>

  <Card class="p-6">
    <PriceBar />
  </Card>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
    <Card class="p-6 space-y-6">
      <h2 class="text-xl font-semibold">Your Inputs</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="space-y-2">
          <Label for="btcNow">BTC Owned Today</Label>
          <Input id="btcNow" type="number" step="0.001" bind:value={btcNow} min="0" />
        </div>

        <div class="space-y-2">
          <Label for="years">Years Until Retirement</Label>
          <Input id="years" type="number" bind:value={yearsUntilRetirement} min="1" max="50" />
        </div>

        <div class="space-y-2">
          <Label for="goal">Retirement Goal (USD)</Label>
          <Input id="goal" type="number" bind:value={retirementGoal} min="0" step="10000" />
        </div>

        <div class="space-y-2">
          <Label for="dca">Monthly DCA (USD)</Label>
          <Input id="dca" type="number" bind:value={monthlyDCA} min="0" />
        </div>
      </div>

      <div class="h-px bg-border"></div>

      <div class="space-y-4">
        <h3 class="font-medium">BTC Price at Retirement</h3>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="space-y-2">
            <Label for="bearish" class="text-red-500">Bearish</Label>
            <Input id="bearish" type="number" bind:value={bearishPrice} />
          </div>

          <div class="space-y-2">
            <Label for="base" class="text-amber-500">Base</Label>
            <Input id="base" type="number" bind:value={basePrice} />
          </div>

          <div class="space-y-2">
            <Label for="bullish" class="text-green-500">Bullish</Label>
            <Input id="bullish" type="number" bind:value={bullishPrice} />
          </div>
        </div>
      </div>
    </Card>

    <Card class="p-6 space-y-4">
      <h2 class="text-xl font-semibold">Summary</h2>

      <div class="grid grid-cols-2 gap-4 text-center">
        <div class="p-4 bg-muted rounded-lg">
          <div class="text-2xl font-bold">{formatUSD(livePrice)}</div>
          <div class="text-sm text-muted-foreground">Current BTC Price</div>
        </div>
        <div class="p-4 bg-muted rounded-lg">
          <div class="text-2xl font-bold">{formatUSD(retirementGoal)}</div>
          <div class="text-sm text-muted-foreground">Your Goal</div>
        </div>
        <div class="p-4 bg-muted rounded-lg">
          <div class="text-2xl font-bold">{((change24h >= 0 ? '+' : '') + change24h.toFixed(2))}%</div>
          <div class="text-sm text-muted-foreground">24h Change</div>
        </div>
        <div class="p-4 bg-muted rounded-lg">
          <div class="text-2xl font-bold">{yearsUntilRetirement}</div>
          <div class="text-sm text-muted-foreground">Years to Retire</div>
        </div>
      </div>
    </Card>
  </div>

  {#if livePrice > 0}
    <Card class="p-6">
      <h2 class="text-xl font-semibold mb-4">Projected Growth</h2>
      <GrowthChart
        years={yearsUntilRetirement}
        chartDatasets={chartDatasets}
        goalValue={retirementGoal}
        {livePrice}
      />
    </Card>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      {#each scenarios as scenario}
        <ScenarioCard
          name={scenario.name}
          scenarioPrice={scenario.price}
          finalValue={scenario.finalValue}
          btcNeeded={scenario.btcNeeded}
          shortfall={scenario.shortfall}
          totalInvested={scenario.totalInvested}
          gain={scenario.gain}
          gainPct={scenario.gainPct}
          multiplier={scenario.multiplier}
          goalReached={scenario.goalReached}
          priceColor={scenario.color}
        />
      {/each}
    </div>
  {:else}
    <Card class="p-12 text-center">
      <div class="text-lg text-muted-foreground">Loading price data...</div>
    </Card>
  {/if}
</div>

<script lang="ts">
  import type { SimulationResult, DayAnalysis } from '$lib/models/simulation';
  import { api } from '$lib/api/client';
  import { endpoints } from '$lib/api/endpoints';
  import { Card } from '$lib/components/ui/card';
  import { Input } from '$lib/components/ui/input';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import {
    Table,
    TableBody,
    TableCaption,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
  } from '$lib/components/ui/table';
  import RiskChart from '$lib/components/risk-chart.svelte';

  let amountUsd = $state(100);
  let daysHistory = $state(30);
  let result = $state<SimulationResult | null>(null);
  let isLoading = $state(false);
  let error = $state<string | null>(null);

  async function handleSimulate() {
    isLoading = true;
    error = null;
    result = null;

    try {
      result = await api.post<SimulationResult>(endpoints.simulate.volatility, {
        amount_usd: amountUsd,
        days_history: daysHistory
      });
    } catch (e) {
      error = e instanceof Error ? e.message : 'Simulation failed';
    } finally {
      isLoading = false;
    }
  }

  function getRiskBadgeVariant(risk: string): 'default' | 'secondary' | 'destructive' | 'outline' {
    switch (risk.toLowerCase()) {
      case 'low':
        return 'default';
      case 'medium':
        return 'secondary';
      case 'high':
        return 'destructive';
      default:
        return 'outline';
    }
  }
</script>

<svelte:head>
  <title>Volatility Simulator — Magma</title>
  <meta name="description" content="Model future Bitcoin scenarios and optimize your financial decisions with volatility analysis." />
</svelte:head>

<div class="space-y-6">
  <div class="space-y-2">
    <h1 class="text-3xl font-bold tracking-tight">Volatility Simulator</h1>
    <p class="text-muted-foreground">
      Model future scenarios and optimize your financial decisions
    </p>
  </div>

  <Card class="p-6">
    <div class="flex flex-col gap-4 md:flex-row md:items-end">
      <div class="flex-1 space-y-2">
        <label for="amount" class="text-sm font-medium">Amount (USD)</label>
        <Input
          id="amount"
          type="number"
          bind:value={amountUsd}
          min="1"
          step="1"
        />
      </div>
      <div class="flex-1 space-y-2">
        <label for="days" class="text-sm font-medium">Days History</label>
        <Input
          id="days"
          type="number"
          bind:value={daysHistory}
          min="1"
          max="365"
          step="1"
        />
      </div>
      <Button onclick={handleSimulate} disabled={isLoading}>
        {isLoading ? 'Simulating...' : 'Simulate'}
      </Button>
    </div>
  </Card>

  {#if error}
    <Card class="p-6 border-destructive">
      <p class="text-sm text-destructive">{error}</p>
    </Card>
  {/if}

  {#if isLoading}
    <div class="space-y-4">
      <Skeleton class="h-32 w-full" />
      <Skeleton class="h-20 w-full" />
      <Skeleton class="h-80 w-full" />
    </div>
  {:else if result}
    <Card class="p-6">
      <div class="space-y-4">
        <div class="flex items-center justify-between gap-4">
          <p class="text-lg font-medium">{result.recommendation}</p>
          <Badge variant={getRiskBadgeVariant(result.risk_level)}>
            {result.risk_level}
          </Badge>
        </div>

        <div class="flex flex-wrap gap-4">
          <div class="flex-1 min-w-[140px] rounded-lg bg-muted p-4 text-center">
            <p class="text-sm text-muted-foreground">Optimal Day</p>
            <p class="text-2xl font-bold">{result.optimal_day}</p>
          </div>
          <div class="flex-1 min-w-[140px] rounded-lg bg-muted p-4 text-center">
            <p class="text-sm text-muted-foreground">Expected Return</p>
            <p class="text-2xl font-bold">{result.expected_return.toFixed(2)}%</p>
          </div>
          <div class="flex-1 min-w-[140px] rounded-lg bg-muted p-4 text-center">
            <p class="text-sm text-muted-foreground">Risk Level</p>
            <p class="text-2xl font-bold capitalize">{result.risk_level}</p>
          </div>
        </div>
      </div>
    </Card>

    <Card class="p-6">
      <h2 class="text-lg font-semibold mb-4">Risk Analysis</h2>
      <RiskChart data={result.daily_analysis} />
    </Card>

    <Card class="p-6">
      <h2 class="text-lg font-semibold mb-4">Daily Analysis</h2>
      <div class="overflow-x-auto">
        <Table>
          <TableCaption>Historical analysis for the past {daysHistory} days</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Day</TableHead>
              <TableHead>Avg Return</TableHead>
              <TableHead>Std Dev</TableHead>
              <TableHead>Best Case</TableHead>
              <TableHead>Worst Case</TableHead>
              <TableHead>Risk Zone</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {#each result.daily_analysis as row (row.wait_days)}
              <TableRow>
                <TableCell>{row.wait_days}</TableCell>
                <TableCell>{row.avg_return.toFixed(2)}%</TableCell>
                <TableCell>{row.std_dev.toFixed(2)}</TableCell>
                <TableCell class="text-green-600">+{row.best_case.toFixed(2)}%</TableCell>
                <TableCell class="text-red-600">{row.worst_case.toFixed(2)}%</TableCell>
                <TableCell>
                  <Badge variant={row.risk_zone === 'low' ? 'default' : row.risk_zone === 'medium' ? 'secondary' : 'destructive'}>
                    {row.risk_zone}
                  </Badge>
                </TableCell>
              </TableRow>
            {/each}
          </TableBody>
        </Table>
      </div>
    </Card>
  {/if}
</div>

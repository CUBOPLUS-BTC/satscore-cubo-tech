<script lang="ts">
  import type { ProjectionResult, SavingsProgress } from '$lib/models/savings';
  import { api } from '$lib/api/client';
  import { endpoints } from '$lib/api/endpoints';
  import { auth } from '$lib/stores/auth.svelte';
  import { i18n } from '$lib/i18n/index.svelte';
  import { formatUSD } from '$lib/utils/formatters';
  import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Badge } from '$lib/components/ui/badge';
  import CurrencyBtc from 'phosphor-svelte/lib/CurrencyBtc';

  let monthlyAmount = $state(10);
  let years = $state(10);
  let projection = $state<ProjectionResult | null>(null);
  let progress = $state<SavingsProgress | null>(null);
  let isProjecting = $state(false);
  let isSaving = $state(false);
  let depositAmount = $state(10);
  let goalMonthly = $state(10);
  let goalYears = $state(10);
  let error = $state<string | null>(null);

  async function runProjection() {
    isProjecting = true;
    error = null;
    try {
      projection = await api.post<ProjectionResult>(endpoints.savings.project, {
        monthly_usd: monthlyAmount,
        years,
      });
    } catch (e) {
      error = e instanceof Error ? e.message : 'Projection failed';
    } finally {
      isProjecting = false;
    }
  }

  async function loadProgress() {
    if (!auth.isAuthenticated) return;
    try {
      progress = await api.get<SavingsProgress>(endpoints.savings.progress);
    } catch {
    }
  }

  async function createGoal() {
    try {
      await api.post(endpoints.savings.goal, {
        monthly_target_usd: goalMonthly,
        target_years: goalYears,
      });
      await loadProgress();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to create goal';
    }
  }

  async function recordDeposit() {
    isSaving = true;
    try {
      await api.post(endpoints.savings.deposit, { amount_usd: depositAmount });
      await loadProgress();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to record deposit';
    } finally {
      isSaving = false;
    }
  }

  $effect(() => {
    if (auth.isAuthenticated) loadProgress();
  });
</script>

<svelte:head>
  <title>{i18n.t.nav.savings} {i18n.t.app.titleSuffix}</title>
</svelte:head>

<div class="space-y-6">
  <h1 class="font-heading text-2xl font-bold tracking-tight">{i18n.t.savings.title}</h1>

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
          <Button onclick={runProjection} disabled={isProjecting} class="w-full">
            {isProjecting ? i18n.t.common.loading : i18n.t.savings.calculate}
          </Button>
        </div>
      </div>

      {#if !projection && !isProjecting}
        <div class="rounded-2xl border border-dashed border-border bg-muted/30 p-8 text-center space-y-3">
          <CurrencyBtc size={36} class="mx-auto text-muted-foreground/40" weight="regular" />
          <p class="text-muted-foreground text-sm">{i18n.t.savings.subtitle}</p>
          <p class="text-xs text-muted-foreground/70">${monthlyAmount}/mo &middot; {years} {i18n.t.savings.years.toLowerCase()}</p>
        </div>
      {/if}

      {#if projection}
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {#each projection.scenarios as scenario}
            <div class="rounded-2xl p-4 {scenario.name === 'moderate' ? 'bg-primary/10 ring-1 ring-primary/20' : 'bg-muted/60'}">
              <div class="space-y-2">
                <div class="flex items-center gap-2">
                  <Badge variant={scenario.name === 'moderate' ? 'default' : 'secondary'} class="text-xs">
                    {scenario.name === 'conservative' ? i18n.t.savings.conservative :
                     scenario.name === 'moderate' ? i18n.t.savings.moderate :
                     i18n.t.savings.optimistic}
                  </Badge>
                  <span class="text-xs text-muted-foreground">{scenario.annual_return_pct}% {i18n.t.savings.annual}</span>
                </div>
                <p class="font-heading text-2xl font-bold tabular-nums">{formatUSD(scenario.projected_value)}</p>
                <p class="text-xs text-muted-foreground">
                  {scenario.multiplier}x {i18n.t.savings.multiplier}
                </p>
              </div>
            </div>
          {/each}
        </div>

        <div class="flex items-center gap-4 p-4 rounded-2xl bg-muted/40">
          <div>
            <p class="text-xs text-muted-foreground">{i18n.t.savings.traditionalSavings}</p>
            <p class="font-heading text-lg font-semibold tabular-nums">{formatUSD(projection.traditional_value)}</p>
          </div>
          <span class="text-muted-foreground text-sm">vs</span>
          <div>
            <p class="text-xs text-muted-foreground">Bitcoin DCA ({i18n.t.savings.moderate})</p>
            <p class="font-heading text-lg font-semibold text-primary tabular-nums">
              {formatUSD(projection.scenarios.find(s => s.name === 'moderate')?.projected_value ?? 0)}
            </p>
          </div>
        </div>
      {/if}
    </CardContent>
  </Card>

  {#if auth.isAuthenticated}
    {#if progress?.has_goal}
      <Card>
        <CardHeader>
          <CardTitle class="font-heading">{i18n.t.savings.progressTitle}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-6">
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div class="space-y-1">
              <p class="text-xs text-muted-foreground">{i18n.t.savings.totalInvested}</p>
              <p class="font-heading text-xl font-bold tabular-nums">{formatUSD(progress.total_invested_usd)}</p>
            </div>
            <div class="space-y-1">
              <p class="text-xs text-muted-foreground">{i18n.t.savings.currentValue}</p>
              <p class="font-heading text-xl font-bold text-primary tabular-nums">{formatUSD(progress.current_value_usd)}</p>
            </div>
            <div class="space-y-1">
              <p class="text-xs text-muted-foreground">ROI</p>
              <p class="font-heading text-xl font-bold tabular-nums {progress.roi_percent >= 0 ? 'text-green-600 dark:text-green-500' : 'text-red-600 dark:text-red-500'}">
                {progress.roi_percent >= 0 ? '+' : ''}{progress.roi_percent}%
              </p>
            </div>
            <div class="space-y-1">
              <p class="text-xs text-muted-foreground">{i18n.t.savings.streak}</p>
              <p class="font-heading text-xl font-bold tabular-nums">{progress.streak_months} {i18n.t.savings.months}</p>
            </div>
          </div>

          <div class="space-y-2">
            <h3 class="text-sm font-medium">{i18n.t.savings.milestones}</h3>
            <div class="flex flex-wrap gap-2">
              {#each progress.milestones as milestone}
                <Badge variant={milestone.reached ? 'default' : 'outline'} class={milestone.reached ? 'bg-green-600' : ''}>
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
            <Button onclick={recordDeposit} disabled={isSaving}>
              {isSaving ? i18n.t.common.loading : i18n.t.savings.recordDeposit}
            </Button>
          </div>

          {#if progress.recent_deposits.length > 0}
            <div class="space-y-2">
              <h3 class="text-sm font-medium">{i18n.t.savings.recentDeposits}</h3>
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
          {/if}
        </CardContent>
      </Card>
    {:else}
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
              <Button onclick={createGoal} class="w-full">{i18n.t.savings.createGoal}</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    {/if}
  {/if}

  {#if error}
    <p class="text-sm text-destructive">{error}</p>
  {/if}
</div>

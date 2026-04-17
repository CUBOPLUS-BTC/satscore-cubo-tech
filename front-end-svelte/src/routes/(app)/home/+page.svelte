<script lang="ts">
  import type { VerifiedPrice } from '$lib/models/price';
  import { formatUSD } from '$lib/utils/formatters';
  import { i18n } from '$lib/i18n/index.svelte';
  import { resolve } from '$app/paths';
  import { Card } from '$lib/components/ui/card';
  import { Badge } from '$lib/components/ui/badge';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import Gauge from 'phosphor-svelte/lib/Gauge';
  import Waveform from 'phosphor-svelte/lib/Waveform';
  import PaperPlaneTilt from 'phosphor-svelte/lib/PaperPlaneTilt';

  let { data }: { data: { price: VerifiedPrice | null } } = $props();

  const tools = [
    {
      icon: Gauge,
      title: 'Score',
      description: 'Evaluate your financial health with our comprehensive scoring system',
      href: '/score'
    },
    {
      icon: Waveform,
      title: 'Simulator',
      description: 'Model future scenarios and optimize your financial decisions',
      href: '/simulator'
    },
    {
      icon: PaperPlaneTilt,
      title: 'Remittance',
      description: 'Send money across borders with competitive rates and fast delivery',
      href: '/remittance'
    }
  ];
</script>

<svelte:head>
  <title>Home — Magma</title>
</svelte:head>

<div class="container mx-auto max-w-6xl px-4 py-12 space-y-12">
  <section class="space-y-4">
    {#if data.price}
      <div class="flex items-baseline gap-4">
        <h1 class="text-6xl font-bold tracking-tight">BTC/USD</h1>
        <span class="text-5xl font-semibold text-foreground">
          {formatUSD(data.price.price_usd)}
        </span>
        <Badge variant="secondary" class="text-sm">
          {data.price.sources_count} Sources
        </Badge>
        <Badge variant="default" class="bg-green-600">Verified</Badge>
      </div>
    {:else}
      <div class="flex items-baseline gap-4">
        <Skeleton class="h-12 w-32" />
        <Skeleton class="h-12 w-48" />
        <Skeleton class="h-6 w-24" />
        <Skeleton class="h-6 w-20" />
      </div>
    {/if}
  </section>

  <section class="grid grid-cols-1 md:grid-cols-3 gap-6">
    {#each tools as tool (tool.href)}
      <a href={resolve(tool.href as '/score' | '/simulator' | '/remittance')} class="block">
        <Card class="p-6 h-full transition-colors hover:bg-muted/50 cursor-pointer">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-3">
              <tool.icon class="h-8 w-8 text-primary" weight="duotone" />
              <h2 class="text-xl font-semibold">{tool.title}</h2>
            </div>
            <p class="text-muted-foreground">{tool.description}</p>
          </div>
        </Card>
      </a>
    {/each}
  </section>

  <Card class="p-8">
    <div class="space-y-6">
      <div class="flex items-center gap-3">
        <h2 class="text-2xl font-bold">Welcome to Magma</h2>
        <Badge variant="outline" class="border-primary text-primary">
          Don't trust, verify
        </Badge>
      </div>
      <p class="text-lg text-muted-foreground">
        Magma empowers you with transparent, verified financial data. Make informed decisions
        with confidence using our suite of powerful tools.
      </p>
      <ul class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <li class="flex items-center gap-2">
          <span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
          Verified price data from multiple sources
        </li>
        <li class="flex items-center gap-2">
          <span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
          Real-time financial scoring
        </li>
        <li class="flex items-center gap-2">
          <span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
          Advanced simulation capabilities
        </li>
        <li class="flex items-center gap-2">
          <span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
          Cross-border remittance services
        </li>
      </ul>
    </div>
  </Card>
</div>

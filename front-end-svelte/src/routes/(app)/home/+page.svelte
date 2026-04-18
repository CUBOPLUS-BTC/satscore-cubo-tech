<script lang="ts">
  import type { VerifiedPrice } from '$lib/models/price';
  import { formatUSD } from '$lib/utils/formatters';
  import { i18n } from '$lib/i18n/index.svelte';
  import { resolve } from '$app/paths';
  import { Badge } from '$lib/components/ui/badge';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Card } from '$lib/components/ui/card';
  import PaperPlaneTilt from 'phosphor-svelte/lib/PaperPlaneTilt';
  import Vault from 'phosphor-svelte/lib/Vault';
  import Lightning from 'phosphor-svelte/lib/Lightning';
  import CurrencyBtc from 'phosphor-svelte/lib/CurrencyBtc';
  import ArrowRight from 'phosphor-svelte/lib/ArrowRight';
  import { alertStore } from '$lib/stores/alerts.svelte';
  import AlertBanner from '$lib/components/alert-banner.svelte';
  import { onDestroy } from 'svelte';

  let { data }: { data: { price: VerifiedPrice | null } } = $props();

  const tools = $derived([
    {
      icon: Lightning,
      title: () => i18n.t.home.tools.remittance.title,
      description: () => i18n.t.home.tools.remittance.description,
      href: '/remittance',
    },
    {
      icon: CurrencyBtc,
      title: () => i18n.t.home.tools.savings.title,
      description: () => i18n.t.home.tools.savings.description,
      href: '/savings',
    },
  ]);

  $effect(() => {
    alertStore.startPolling();
  });

  onDestroy(() => {
    alertStore.stopPolling();
  });
</script>

<svelte:head>
  <title>{i18n.t.nav.home} {i18n.t.app.titleSuffix}</title>
</svelte:head>

<div class="space-y-8">
  <section class="pt-2">
    {#if data.price}
      <div class="space-y-1">
        <span class="text-sm font-medium text-muted-foreground uppercase tracking-wider">BTC/USD</span>
        <div class="flex items-baseline gap-3">
          <span class="font-heading text-5xl sm:text-6xl font-bold text-foreground tabular-nums tracking-tight">
            {formatUSD(data.price.price_usd)}
          </span>
        </div>
        <div class="flex gap-2 pt-1">
          <Badge variant="secondary" class="text-xs font-normal">
            {i18n.t.home.sources.replace('{count}', String(data.price.sources_count))}
          </Badge>
          <Badge variant="default" class="text-xs font-normal">{i18n.t.home.verified}</Badge>
        </div>
      </div>
    {:else}
      <div class="space-y-2">
        <Skeleton class="h-4 w-16" />
        <Skeleton class="h-14 w-64" />
        <Skeleton class="h-5 w-32" />
      </div>
    {/if}
  </section>

  <AlertBanner status={alertStore.status} />

  <section class="grid grid-cols-1 sm:grid-cols-2 gap-4">
    {#each tools as tool (tool.href)}
      <a
        href={resolve(tool.href as '/remittance' | '/savings')}
        class="group block"
      >
        <Card class="p-5 h-full transition-all hover:border-primary/30 hover:shadow-md active:scale-[0.98]">
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <tool.icon size={24} class="text-primary" weight="regular" />
              <ArrowRight size={18} class="text-muted-foreground/40 transition-transform group-hover:translate-x-0.5 group-hover:text-primary" weight="bold" />
            </div>
            <div class="space-y-1">
              <h3 class="font-heading text-base font-semibold text-foreground">{tool.title()}</h3>
              <p class="text-sm text-muted-foreground leading-relaxed">{tool.description()}</p>
            </div>
          </div>
        </Card>
      </a>
    {/each}
  </section>
</div>

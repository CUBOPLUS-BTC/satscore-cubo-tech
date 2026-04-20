<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { browser } from '$app/environment';
  import { auth } from '$lib/stores/auth.svelte';
  import { i18n } from '$lib/i18n/index.svelte';
  import { api } from '$lib/api/client';
  import { endpoints } from '$lib/api/endpoints';
  import { createQuery } from '@tanstack/svelte-query';
  import { formatUSD } from '$lib/utils/formatters';
  import type { VerifiedPrice } from '$lib/models/price';
  import type { NetworkStatus } from '$lib/models/network';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import { Input } from '$lib/components/ui/input';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import Mountains from 'phosphor-svelte/lib/Mountains';
  import Globe from 'phosphor-svelte/lib/Globe';
  import ArrowRight from 'phosphor-svelte/lib/ArrowRight';
  import Lightning from 'phosphor-svelte/lib/Lightning';
  import PaperPlaneTilt from 'phosphor-svelte/lib/PaperPlaneTilt';
  import CurrencyBtc from 'phosphor-svelte/lib/CurrencyBtc';
  import PiggyBank from 'phosphor-svelte/lib/PiggyBank';
  import Cube from 'phosphor-svelte/lib/Cube';
  import AnimatedNumber from '$lib/components/animated-number.svelte';
  import Marquee from '$lib/components/magic/marquee.svelte';

  let searchParams = $derived(browser ? new URLSearchParams(window.location.search) : null);
  let isPreview = $derived(searchParams?.has('preview') ?? false);

  $effect(() => {
    if (browser && auth.isAuthenticated && !isPreview) {
      goto(resolve('/home'), { replaceState: true });
    }
  });

  const priceQuery = createQuery(() => ({
    queryKey: ['price'],
    queryFn: () => api.get<VerifiedPrice>(endpoints.price),
    refetchInterval: 60_000,
  }));

  const networkQuery = createQuery(() => ({
    queryKey: ['network'],
    queryFn: () => api.get<NetworkStatus>(endpoints.network.status),
    refetchInterval: 60_000,
  }));

  let price = $derived(priceQuery.data ?? null);
  let network = $derived(networkQuery.data ?? null);
  const t = $derived(i18n.t.landing);

  // Interactive comparison
  let sendAmount = $state(200);
  let traditionalFee = $derived(sendAmount * 0.062);
  let lightningFee = $derived(Math.max(sendAmount * 0.0003, 0.01));
  let saved = $derived(traditionalFee - lightningFee);
  let annualSaved = $derived(saved * 12);

  // Savings example: $10/month for 4 years at ~average BTC growth
  let dcaMonthly = 10;
  let dcaYears = 4;
  let dcaInvested = $derived(dcaMonthly * 12 * dcaYears);
  let dcaCurrentValue = $derived(dcaInvested * 2.8); // conservative historical multiplier

  const wallets = ['Blink', 'Strike', 'Phoenix', 'Wallet of Satoshi', 'Muun', 'Zeus', 'Breez'];
</script>

<svelte:head>
  <title>Magma — {i18n.t.app.tagline}</title>
  <meta name="description" content={i18n.t.app.description} />
</svelte:head>

<div class="min-h-screen bg-background text-foreground">

  <!-- HEADER -->
  <header class="border-b border-border">
    <div class="mx-auto max-w-5xl flex items-center justify-between px-5 py-3">
      <a href="/" class="flex items-center gap-2">
        <Mountains class="size-6 text-primary" weight="bold" />
        <span class="font-heading text-base font-semibold tracking-tight">{i18n.t.app.name}</span>
      </a>
      <div class="flex items-center gap-3">
        <button
          onclick={() => i18n.setLocale(i18n.locale === 'en' ? 'es' : 'en')}
          class="text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          <Globe size={16} />
        </button>
        <Button variant="ghost" size="sm" onclick={() => goto(resolve('/login'))}>
          {t.login}
        </Button>
      </div>
    </div>
  </header>

  <main class="mx-auto max-w-5xl px-5">

    <!-- HERO -->
    <section class="py-14 lg:py-20 grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-14 items-center">
      <div class="space-y-4">
        <h1 class="font-heading text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight leading-[1.1]">
          {t.hero}
        </h1>
        <p class="text-base text-muted-foreground leading-relaxed max-w-md">
          {t.subtitle}
        </p>
        <div class="flex items-center gap-4 pt-2">
          <Button size="lg" onclick={() => goto(resolve('/login'))}>
            {t.cta}
            <ArrowRight size={16} class="ml-1.5" />
          </Button>
        </div>
        <!-- Stats inline -->
        <div class="flex gap-8 pt-4">
          <div>
            <span class="font-heading text-2xl font-bold">{t.stats.remittanceVolume}</span>
            <p class="text-[11px] text-muted-foreground">{t.stats.remittanceLabel}</p>
          </div>
          <div>
            <span class="font-heading text-2xl font-bold text-red-500">{t.stats.avgFee}</span>
            <p class="text-[11px] text-muted-foreground">{t.stats.avgFeeLabel}</p>
          </div>
          <div>
            <span class="font-heading text-2xl font-bold text-green-500">{t.stats.lightningFee}</span>
            <p class="text-[11px] text-muted-foreground">{t.stats.lightningFeeLabel}</p>
          </div>
        </div>
      </div>

      <!-- Phone mockup -->
      <div class="flex justify-center lg:justify-end">
        <div class="w-[280px] sm:w-[300px]">
          <div class="rounded-[2.5rem] border-[6px] border-foreground/10 bg-card shadow-2xl overflow-hidden">
            <div class="flex justify-center pt-2 pb-3 bg-card">
              <div class="w-20 h-5 rounded-full bg-foreground/10"></div>
            </div>
            <div class="px-5 pb-6 space-y-5">
              <div>
                <span class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">BTC/USD</span>
                {#if price}
                  <div class="font-heading text-3xl font-bold tabular-nums tracking-tight mt-0.5">
                    <AnimatedNumber value={price.price_usd} format={formatUSD} duration={1200} />
                  </div>
                  <div class="flex gap-1.5 mt-1.5">
                    <Badge variant="secondary" class="text-[9px] py-0 h-4 font-normal">
                      {i18n.t.home.sources.replace('{count}', String(price.sources_count))}
                    </Badge>
                    <Badge variant="default" class="text-[9px] py-0 h-4 font-normal">{i18n.t.home.verified}</Badge>
                  </div>
                {:else}
                  <Skeleton class="h-8 w-36 mt-1" />
                  <div class="flex gap-1.5 mt-1.5"><Skeleton class="h-4 w-14" /><Skeleton class="h-4 w-12" /></div>
                {/if}
              </div>
              <div class="space-y-2">
                <div class="flex items-center gap-2.5 rounded-lg border border-border p-2.5">
                  <PaperPlaneTilt size={16} class="text-blue-500 shrink-0" weight="regular" />
                  <div>
                    <p class="text-[11px] font-semibold leading-none">{i18n.t.home.tools.remittance.title}</p>
                    <p class="text-[9px] text-muted-foreground mt-0.5 leading-tight">{i18n.t.home.tools.remittance.description.slice(0, 45)}…</p>
                  </div>
                </div>
                <div class="flex items-center gap-2.5 rounded-lg border border-border p-2.5">
                  <CurrencyBtc size={16} class="text-amber-500 shrink-0" weight="regular" />
                  <div>
                    <p class="text-[11px] font-semibold leading-none">{i18n.t.home.tools.savings.title}</p>
                    <p class="text-[9px] text-muted-foreground mt-0.5 leading-tight">{i18n.t.home.tools.savings.description.slice(0, 45)}…</p>
                  </div>
                </div>
                <div class="flex items-center gap-2.5 rounded-lg border border-border p-2.5">
                  <PiggyBank size={16} class="text-emerald-500 shrink-0" weight="regular" />
                  <div>
                    <p class="text-[11px] font-semibold leading-none">{i18n.t.home.tools.pension.title}</p>
                    <p class="text-[9px] text-muted-foreground mt-0.5 leading-tight">{i18n.t.home.tools.pension.description.slice(0, 45)}…</p>
                  </div>
                </div>
              </div>
              <div class="flex justify-around pt-2 border-t border-border">
                {#each [
                  { icon: Cube, label: i18n.t.nav.home },
                  { icon: PaperPlaneTilt, label: i18n.t.nav.remittance },
                  { icon: CurrencyBtc, label: i18n.t.nav.savings },
                  { icon: PiggyBank, label: i18n.t.nav.pension },
                ] as tab}
                  <div class="flex flex-col items-center gap-0.5">
                    <tab.icon size={14} class={tab.label === i18n.t.nav.home ? 'text-primary' : 'text-muted-foreground'} weight={tab.label === i18n.t.nav.home ? 'fill' : 'regular'} />
                    <span class="text-[8px] {tab.label === i18n.t.nav.home ? 'text-primary font-medium' : 'text-muted-foreground'}">{tab.label}</span>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- INTERACTIVE COMPARISON -->
    <section class="pb-14 border-t border-border pt-10">
      <h2 class="font-heading text-xl font-semibold mb-1">{t.comparison.title}</h2>
      <p class="text-sm text-muted-foreground mb-5">{t.comparison.subtitle}</p>

      <div class="flex items-center gap-2 mb-5">
        <span class="text-2xl font-bold text-muted-foreground/50">$</span>
        <Input
          type="number"
          bind:value={sendAmount}
          min={1}
          max={10000}
          step={10}
          class="w-28 tabular-nums text-xl font-bold h-12"
        />
      </div>

      <div class="overflow-hidden rounded-xl border border-border">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border bg-muted/50">
              <th class="text-left font-medium text-muted-foreground px-4 py-2.5"></th>
              <th class="text-right font-medium text-muted-foreground px-4 py-2.5">{t.comparison.traditional}</th>
              <th class="text-right font-medium px-4 py-2.5">
                <span class="inline-flex items-center gap-1 text-foreground">
                  <Lightning size={14} weight="fill" class="text-primary" />
                  {t.comparison.lightning}
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-border">
              <td class="px-4 py-3 text-muted-foreground">{t.comparison.fee}</td>
              <td class="px-4 py-3 text-right tabular-nums text-red-500 font-medium">${traditionalFee.toFixed(2)}</td>
              <td class="px-4 py-3 text-right tabular-nums text-green-500 font-medium">${lightningFee.toFixed(2)}</td>
            </tr>
            <tr class="border-b border-border">
              <td class="px-4 py-3 text-muted-foreground">{t.comparison.received}</td>
              <td class="px-4 py-3 text-right tabular-nums">${(sendAmount - traditionalFee).toFixed(2)}</td>
              <td class="px-4 py-3 text-right tabular-nums font-semibold">${(sendAmount - lightningFee).toFixed(2)}</td>
            </tr>
            <tr>
              <td class="px-4 py-3 text-muted-foreground">{t.comparison.time}</td>
              <td class="px-4 py-3 text-right text-muted-foreground">{t.comparison.traditionalTime}</td>
              <td class="px-4 py-3 text-right font-medium">{t.comparison.lightningTime}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex flex-wrap gap-x-8 gap-y-2 mt-4">
        <p class="text-sm">
          <span class="font-semibold text-primary tabular-nums">${saved.toFixed(2)}</span>
          <span class="text-muted-foreground"> {t.comparison.savedLabel}</span>
        </p>
        <p class="text-sm">
          <span class="font-semibold text-foreground tabular-nums">${annualSaved.toFixed(0)}</span>
          <span class="text-muted-foreground"> / {i18n.t.savings.annual}</span>
        </p>
      </div>
    </section>

    <!-- WHAT YOU CAN DO — two-column with second phone -->
    <section class="pb-14 border-t border-border pt-10">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-14 items-center">

        <!-- DCA phone mockup -->
        <div class="flex justify-center lg:justify-start order-2 lg:order-1">
          <div class="w-[260px] sm:w-[280px]">
            <div class="rounded-[2.5rem] border-[6px] border-foreground/10 bg-card shadow-2xl overflow-hidden">
              <div class="flex justify-center pt-2 pb-3 bg-card">
                <div class="w-20 h-5 rounded-full bg-foreground/10"></div>
              </div>
              <div class="px-5 pb-6 space-y-4">
                <div>
                  <span class="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{i18n.t.savings.projectionTitle}</span>
                  <p class="text-[11px] text-muted-foreground mt-1">${dcaMonthly}/mo × {dcaYears} {i18n.t.savings.years.toLowerCase()}</p>
                </div>
                <!-- Mini projection results -->
                <div class="space-y-3">
                  <div class="flex justify-between items-center">
                    <span class="text-[11px] text-muted-foreground">{i18n.t.savings.totalInvested}</span>
                    <span class="text-[13px] font-semibold tabular-nums">${dcaInvested.toLocaleString()}</span>
                  </div>
                  <div class="h-px bg-border"></div>
                  <div class="flex justify-between items-center">
                    <span class="text-[11px] text-muted-foreground">{i18n.t.savings.currentValue}</span>
                    <span class="text-[13px] font-bold tabular-nums text-green-500">${dcaCurrentValue.toLocaleString()}</span>
                  </div>
                  <div class="h-px bg-border"></div>
                  <div class="flex justify-between items-center">
                    <span class="text-[11px] text-muted-foreground">{i18n.t.savings.multiplier}</span>
                    <span class="text-[13px] font-bold tabular-nums">2.8×</span>
                  </div>
                </div>
                <!-- Mini bar chart mockup -->
                <div class="flex items-end gap-1 h-16 pt-2">
                  {#each [15, 25, 20, 35, 30, 45, 40, 55, 50, 65, 60, 75, 70, 80, 85, 100] as h, idx}
                    <div
                      class="flex-1 rounded-sm {idx > 11 ? 'bg-primary' : 'bg-primary/30'}"
                      style="height: {h}%"
                    ></div>
                  {/each}
                </div>
                <p class="text-[9px] text-muted-foreground">{i18n.t.pension.basedOnHistorical}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Content -->
        <div class="space-y-6 order-1 lg:order-2">
          <div>
            <h2 class="font-heading text-xl font-semibold">{t.modules.savings.title}</h2>
            <p class="text-sm text-muted-foreground leading-relaxed mt-2">{t.modules.savings.desc}</p>
          </div>
          <div>
            <h2 class="font-heading text-xl font-semibold">{t.modules.pension.title}</h2>
            <p class="text-sm text-muted-foreground leading-relaxed mt-2">{t.modules.pension.desc}</p>
          </div>
          <div>
            <h2 class="font-heading text-xl font-semibold">{t.modules.alerts.title}</h2>
            <p class="text-sm text-muted-foreground leading-relaxed mt-2">{t.modules.alerts.desc}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- LIVE NETWORK -->
    <section class="pb-14 border-t border-border pt-10">
      <h2 class="font-heading text-base font-semibold text-muted-foreground mb-4">{i18n.t.home.networkStatus}</h2>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-6">
        <div>
          <span class="text-xs text-muted-foreground">{i18n.t.home.blockHeight}</span>
          {#if network}
            <p class="font-heading text-xl font-bold tabular-nums mt-0.5">#{network.block_height.toLocaleString()}</p>
          {:else}
            <Skeleton class="h-7 w-28 mt-0.5" />
          {/if}
        </div>
        <div>
          <span class="text-xs text-muted-foreground">{i18n.t.home.fastFee}</span>
          {#if network}
            <p class="font-heading text-xl font-bold tabular-nums mt-0.5">{network.fees.fastestFee} <span class="text-sm font-normal text-muted-foreground">sats</span></p>
          {:else}
            <Skeleton class="h-7 w-20 mt-0.5" />
          {/if}
        </div>
        <div>
          <span class="text-xs text-muted-foreground">{i18n.t.home.economyFee}</span>
          {#if network}
            <p class="font-heading text-xl font-bold tabular-nums text-green-500 mt-0.5">{network.fees.economyFee} <span class="text-sm font-normal text-muted-foreground">sats</span></p>
          {:else}
            <Skeleton class="h-7 w-20 mt-0.5" />
          {/if}
        </div>
        <div>
          <span class="text-xs text-muted-foreground">{i18n.t.home.mempoolTxs}</span>
          {#if network}
            <p class="font-heading text-xl font-bold tabular-nums mt-0.5">{network.mempool_size.count.toLocaleString()}</p>
          {:else}
            <Skeleton class="h-7 w-24 mt-0.5" />
          {/if}
        </div>
      </div>
    </section>

    <!-- TRUST — compact -->
    <section class="pb-10 border-t border-border pt-8">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-4">
        {#each [
          { title: t.trust.noAccount, desc: t.trust.noAccountDesc },
          { title: t.trust.noCustody, desc: t.trust.noCustodyDesc },
          { title: t.trust.openProtocol, desc: t.trust.openProtocolDesc },
          { title: t.trust.legalTender, desc: t.trust.legalTenderDesc },
        ] as item}
          <div>
            <h3 class="text-sm font-semibold">{item.title}</h3>
            <p class="text-xs text-muted-foreground leading-relaxed mt-1">{item.desc}</p>
          </div>
        {/each}
      </div>
    </section>

    <!-- WALLETS -->
    <section class="pb-8 border-t border-border pt-6">
      <Marquee pauseOnHover class="[--duration:25s] [--gap:2rem]">
        {#each wallets as wallet}
          <span class="text-sm font-medium text-muted-foreground/60 whitespace-nowrap">{wallet}</span>
        {/each}
      </Marquee>
    </section>

    <!-- CTA -->
    <section class="pb-20 lg:pb-24 border-t border-border pt-12 text-center">
      <h2 class="font-heading text-2xl sm:text-3xl font-bold tracking-tight">{t.finalCta.title}</h2>
      <p class="text-sm text-muted-foreground mt-2 max-w-md mx-auto">{t.finalCta.subtitle}</p>
      <div class="mt-5">
        <Button size="lg" onclick={() => goto(resolve('/login'))}>
          {t.cta}
          <ArrowRight size={16} class="ml-1.5" />
        </Button>
      </div>
    </section>

  </main>

  <!-- FOOTER -->
  <footer class="border-t border-border">
    <div class="mx-auto max-w-5xl px-5 py-6 flex items-center justify-between">
      <div class="flex items-center gap-2 text-xs text-muted-foreground">
        <Mountains class="size-3.5" weight="bold" />
        <span>{t.footer}</span>
      </div>
      <span class="text-xs text-muted-foreground">© {new Date().getFullYear()}</span>
    </div>
  </footer>
</div>

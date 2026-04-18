<script lang="ts">
  import { Card } from '$lib/components/ui/card';
  import SectionLabel from './SectionLabel.svelte';
  import HeroNumber from './HeroNumber.svelte';

  let {
    label,
    value,
    sub = '',
    accent = false,
  }: {
    label: string;
    value: string;
    sub?: string;
    accent?: boolean;
  } = $props();
</script>

<Card class="rounded-[20px] border border-border bg-card p-6">
  <div class="mb-2"><SectionLabel>{label}</SectionLabel></div>
  <HeroNumber size="md">
    <span class={accent ? 'text-primary' : ''}>{value}</span>
  </HeroNumber>
  {#if sub}
    <div class="text-xs text-muted-foreground mt-1.5">{sub}</div>
  {/if}
</Card>

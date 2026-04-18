<script lang="ts">
  import type { AlertStatus } from '$lib/models/alert';
  import { Card } from '$lib/components/ui/card';
  import { Badge } from '$lib/components/ui/badge';
  import Lightning from 'phosphor-svelte/lib/Lightning';
  import Pulse from 'phosphor-svelte/lib/Pulse';
  import Info from 'phosphor-svelte/lib/Info';

  let { status }: { status: AlertStatus | null } = $props();

  let badgeVariant = $derived(
    status?.recommendation === 'on-chain' ? 'default' as const :
    status?.recommendation === 'lightning' ? 'secondary' as const :
    'outline' as const
  );
</script>

{#if status}
  <Card class="p-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          {#if status.recommendation === 'on-chain'}
            <Pulse class="size-5 text-green-600 dark:text-green-500" weight="bold" />
          {:else if status.recommendation === 'lightning'}
            <Lightning class="size-5 text-yellow-600 dark:text-yellow-500" weight="bold" />
          {:else}
            <Info class="size-5 text-muted-foreground" weight="regular" />
          {/if}
          <span class="text-sm font-medium">{status.message}</span>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Badge variant={badgeVariant}>
          {status.half_hour_fee} sat/vB
        </Badge>
        <span class="text-xs text-muted-foreground">
          BTC {status.price?.price_usd ? `$${status.price.price_usd.toLocaleString()}` : '...'}
        </span>
      </div>
    </div>
  </Card>
{/if}

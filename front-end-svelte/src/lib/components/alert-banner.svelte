<script lang="ts">
  import type { AlertStatus } from '$lib/models/alert';
  import { Card } from '$lib/components/ui/card';
  import { Badge } from '$lib/components/ui/badge';
  import Geo from '$lib/components/geo.svelte';

  let { status }: { status: AlertStatus | null } = $props();

  let badgeVariant = $derived(
    status?.recommendation === 'on-chain' ? 'default' as const :
    status?.recommendation === 'lightning' ? 'secondary' as const :
    'outline' as const
  );

  let geoState = $derived.by(() => {
    if (!status) return 'idle' as const;
    if (status.half_hour_fee <= 3) return 'stacking' as const;
    if (status.half_hour_fee >= 20) return 'nervous' as const;
    return 'idle' as const;
  });
</script>

{#if status}
  <Card class="p-4">
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <Geo state={geoState} class="w-9 h-9 shrink-0" />
        <span class="text-sm font-medium">{status.message}</span>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <Badge variant={badgeVariant}>
          {status.half_hour_fee} sat/vB
        </Badge>
        <span class="text-xs text-muted-foreground hidden sm:inline">
          BTC {status.price?.price_usd ? `$${status.price.price_usd.toLocaleString()}` : '...'}
        </span>
      </div>
    </div>
  </Card>
{/if}

<script lang="ts">
  import { priceStore } from '$lib/stores/price.svelte';
  import { Card } from '$lib/components/ui/card';
  import { Button } from '$lib/components/ui/button';

  let isLoading = $state(false);

  async function handleRefresh() {
    isLoading = true;
    await priceStore.refresh();
    isLoading = false;
  }

  function formatTime(date: Date) {
    return date.toLocaleTimeString();
  }
</script>

<div class="flex items-center gap-4 py-4">
  <div class="flex items-baseline gap-2">
    <span class="text-sm text-muted-foreground">BTC/USD</span>
    <span class="text-3xl font-bold tabular-nums">
      ${$priceStore.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
    </span>
  </div>

  <div class="flex items-center gap-2">
    <span class="text-sm font-medium {$priceStore.change24h >= 0 ? 'text-green-500' : 'text-red-500'}">
      {$priceStore.change24h >= 0 ? '+' : ''}{$priceStore.change24h.toFixed(2)}%
    </span>
  </div>

  <div class="flex-1"></div>

  <div class="flex items-center gap-3">
    <span class="text-xs text-muted-foreground">
      Updated: {formatTime($priceStore.lastUpdated)}
    </span>
    <Button variant="outline" size="sm" onclick={handleRefresh} disabled={isLoading}>
      {isLoading ? 'Refreshing...' : 'Refresh'}
    </Button>
  </div>
</div>

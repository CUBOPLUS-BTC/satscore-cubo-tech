import { writable, derived } from 'svelte/store';

interface PriceData {
  price: number;
  change24h: number;
  lastUpdated: Date;
}

function createPriceStore() {
  const { subscribe, set, update } = writable<PriceData>({
    price: 0,
    change24h: 0,
    lastUpdated: new Date()
  });

  let intervalId: ReturnType<typeof setInterval> | null = null;

  async function fetchPrice() {
    try {
      const response = await fetch('/api/price');
      const data = await response.json();
      set({
        price: data.price_usd ?? data.price ?? 0,
        change24h: data.change_24h ?? 0,
        lastUpdated: new Date()
      });
    } catch (error) {
      console.error('Failed to fetch BTC price:', error);
    }
  }

  return {
    subscribe,
    refresh: fetchPrice,
    startAutoRefresh: () => {
      fetchPrice();
      if (intervalId) clearInterval(intervalId);
      intervalId = setInterval(fetchPrice, 60000);
    },
    stopAutoRefresh: () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    }
  };
}

export const priceStore = createPriceStore();

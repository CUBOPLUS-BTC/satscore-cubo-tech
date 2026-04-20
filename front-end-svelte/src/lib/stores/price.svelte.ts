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
      const response = await fetch(
        'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true'
      );
      const data = await response.json();
      set({
        price: data.bitcoin.usd,
        change24h: data.bitcoin.usd_24h_change || 0,
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

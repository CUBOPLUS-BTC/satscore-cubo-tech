import { browser } from '$app/environment';
import type { Alert, AlertStatus } from '$lib/models/alert';
import { endpoints } from '$lib/api/endpoints';

function createAlerts() {
  let alerts = $state<Alert[]>([]);
  let status = $state<AlertStatus | null>(null);
  let lastFetch = $state(0);
  let _statusInterval: ReturnType<typeof setInterval> | null = null;
  let _alertInterval: ReturnType<typeof setInterval> | null = null;

  return {
    get alerts() { return alerts; },
    get status() { return status; },
    get count() { return alerts.length; },

    async fetchStatus(): Promise<void> {
      try {
        const res = await fetch(endpoints.alerts.status);
        if (res.ok) status = await res.json();
      } catch { /* silent */ }
    },

    async fetchAlerts(): Promise<void> {
      try {
        const res = await fetch(endpoints.alerts.list(lastFetch));
        if (res.ok) {
          const data = await res.json();
          if (data.alerts?.length > 0) {
            alerts = [...data.alerts, ...alerts].slice(0, 50);
            lastFetch = Math.max(...data.alerts.map((a: Alert) => a.created_at));
          }
        }
      } catch { /* silent */ }
    },

    startPolling(): void {
      if (!browser) return;
      if (_statusInterval || _alertInterval) return;
      this.fetchStatus();
      this.fetchAlerts();
      _statusInterval = setInterval(() => this.fetchStatus(), 30_000);
      _alertInterval = setInterval(() => this.fetchAlerts(), 60_000);
    },

    stopPolling(): void {
      if (_statusInterval) { clearInterval(_statusInterval); _statusInterval = null; }
      if (_alertInterval) { clearInterval(_alertInterval); _alertInterval = null; }
    },

    clear(): void {
      alerts = [];
    },
  };
}

export const alertStore = createAlerts();

import { browser } from '$app/environment';
import { endpoints } from '$lib/api/endpoints';

const TOKEN_KEY = 'magma_token';
const PUBKEY_KEY = 'magma_pubkey';

function createAuth() {
  const storedToken = browser ? localStorage.getItem(TOKEN_KEY) : null;
  const storedPubkey = browser ? localStorage.getItem(PUBKEY_KEY) : null;

  let token = $state<string | null>(storedToken);
  let publicKey = $state<string | null>(storedPubkey);
  let isLoading = $state(false);
  let error = $state<string | null>(null);
  let lnurlData = $state<{ k1: string; lnurl: string } | null>(null);
  let _pollInterval: ReturnType<typeof setInterval> | null = null;

  return {
    get isAuthenticated() { return !!token; },
    get publicKey() { return publicKey; },
    get isLoading() { return isLoading; },
    get error() { return error; },
    get lnurlData() { return lnurlData; },

    clearError() { error = null; },

    async startLogin(): Promise<string> {
      isLoading = true;
      error = null;
      lnurlData = null;

      try {
        const res = await fetch(endpoints.auth.lnurl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!res.ok) throw new Error('Failed to create LNURL challenge');
        const data = await res.json();

        lnurlData = { k1: data.k1, lnurl: data.lnurl };
        return data.k1;
      } catch (e) {
        error = e instanceof Error ? e.message : 'Login failed';
        throw e;
      } finally {
        isLoading = false;
      }
    },

    startPolling(k1: string, onSuccess: () => void): void {
      this.stopPolling();
      _pollInterval = setInterval(async () => {
        try {
          const res = await fetch(endpoints.auth.lnurlStatus(k1));
          if (!res.ok) return;
          const data = await res.json();

          if (data.status === 'ok' && data.token && data.pubkey) {
            token = data.token;
            publicKey = data.pubkey;
            if (browser) {
              localStorage.setItem(TOKEN_KEY, data.token);
              localStorage.setItem(PUBKEY_KEY, data.pubkey);
            }
            this.stopPolling();
            lnurlData = null;
            onSuccess();
          } else if (data.status === 'expired' || data.status === 'error') {
            error = 'Session expired. Try again.';
            this.stopPolling();
            lnurlData = null;
          }
        } catch {
          // network error, will retry
        }
      }, 2000);
    },

    async loginWithNostr(): Promise<void> {
      isLoading = true;
      error = null;

      try {
        const nostr = (window as any).nostr;
        if (!nostr) throw new Error('No Nostr extension found. Install nos2x or Alby.');

        const pubkeyHex: string = await nostr.getPublicKey();

        const challengeRes = await fetch(endpoints.auth.challenge, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pubkey: pubkeyHex }),
        });
        if (!challengeRes.ok) throw new Error('Failed to get challenge');
        const { challenge } = await challengeRes.json();

        const event = await nostr.signEvent({
          kind: 27235,
          created_at: Math.floor(Date.now() / 1000),
          tags: [['u', window.location.origin], ['method', 'GET']],
          content: challenge,
        });

        const verifyRes = await fetch(endpoints.auth.verify, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ signed_event: event, challenge }),
        });
        if (!verifyRes.ok) throw new Error('Signature verification failed');
        const data = await verifyRes.json();

        token = data.token;
        publicKey = data.pubkey;
        if (browser) {
          localStorage.setItem(TOKEN_KEY, data.token);
          localStorage.setItem(PUBKEY_KEY, data.pubkey);
        }
      } catch (e) {
        error = e instanceof Error ? e.message : 'Nostr login failed';
        throw e;
      } finally {
        isLoading = false;
      }
    },

    async devLogin(): Promise<void> {
      isLoading = true;
      error = null;

      try {
        const res = await fetch(endpoints.auth.devLogin, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        if (!res.ok) throw new Error('Dev login disabled');
        const data = await res.json();

        token = data.token;
        publicKey = data.pubkey;
        if (browser) {
          localStorage.setItem(TOKEN_KEY, data.token);
          localStorage.setItem(PUBKEY_KEY, data.pubkey);
        }
      } catch (e) {
        error = e instanceof Error ? e.message : 'Dev login failed';
        throw e;
      } finally {
        isLoading = false;
      }
    },

    stopPolling(): void {
      if (_pollInterval) {
        clearInterval(_pollInterval);
        _pollInterval = null;
      }
    },

    logout() {
      this.stopPolling();
      token = null;
      publicKey = null;
      lnurlData = null;
      if (browser) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(PUBKEY_KEY);
      }
    },

    getAuthHeader(): string | null {
      if (!token) return null;
      return `Bearer ${token}`;
    },
  };
}

export const auth = createAuth();
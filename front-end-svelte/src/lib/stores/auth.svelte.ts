import { browser } from '$app/environment';
import { nip19, getPublicKey, finalizeEvent, generateSecretKey } from 'nostr-tools';
import { endpoints } from '$lib/api/endpoints';

const KEY_STORAGE = 'magma_nsec';

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

function decodePrivateKey(input: string): Uint8Array {
  const trimmed = input.trim();
  if (trimmed.startsWith('nsec1')) {
    const decoded = nip19.decode(trimmed);
    if (decoded.type !== 'nsec') throw new Error('Invalid nsec key');
    return decoded.data as Uint8Array;
  }
  if (/^[0-9a-f]{64}$/i.test(trimmed)) {
    return hexToBytes(trimmed);
  }
  throw new Error('Invalid key format. Use nsec1... or 64-char hex.');
}

function createAuth() {
  const stored = browser ? localStorage.getItem(KEY_STORAGE) : null;

  let secretKey = $state<Uint8Array | null>(stored ? hexToBytes(stored) : null);
  let publicKey = $state<string | null>(stored ? getPublicKey(hexToBytes(stored)) : null);
  let isLoading = $state(false);
  let error = $state<string | null>(null);

  return {
    get isAuthenticated() { return !!secretKey; },
    get publicKey() { return publicKey; },
    get isLoading() { return isLoading; },
    get error() { return error; },

    clearError() { error = null; },

    async login(nsecOrHex: string) {
      isLoading = true;
      error = null;

      try {
        const sk = decodePrivateKey(nsecOrHex);
        const pk = getPublicKey(sk);

        const challengeRes = await fetch(endpoints.auth.challenge, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pubkey: pk }),
        });

        if (!challengeRes.ok) throw new Error('Failed to get challenge');
        const { challenge } = await challengeRes.json();

        const event = finalizeEvent({
          kind: 27235,
          created_at: Math.floor(Date.now() / 1000),
          tags: [
            ['u', endpoints.auth.verify],
            ['method', 'POST'],
            ['challenge', challenge],
          ],
          content: '',
        }, sk);

        const verifyRes = await fetch(endpoints.auth.verify, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ signed_event: event, challenge }),
        });

        if (!verifyRes.ok) throw new Error('Authentication failed');

        const skHex = Array.from(sk).map(b => b.toString(16).padStart(2, '0')).join('');
        secretKey = sk;
        publicKey = pk;
        if (browser) localStorage.setItem(KEY_STORAGE, skHex);

      } catch (e) {
        error = e instanceof Error ? e.message : 'Authentication failed';
        throw e;
      } finally {
        isLoading = false;
      }
    },

    generateKeys() {
      const sk = generateSecretKey();
      const pk = getPublicKey(sk);
      const nsec = nip19.nsecEncode(sk);
      const npub = nip19.npubEncode(pk);
      return { nsec, npub };
    },

    logout() {
      secretKey = null;
      publicKey = null;
      if (browser) localStorage.removeItem(KEY_STORAGE);
    },

    getAuthHeader(): string | null {
      if (!secretKey || !publicKey) return null;
      const sk = secretKey;
      const event = finalizeEvent({
        kind: 27235,
        created_at: Math.floor(Date.now() / 1000),
        tags: [['u', endpoints.auth.me], ['method', 'GET']],
        content: '',
      }, sk);
      return `Nostr ${btoa(JSON.stringify(event))}`;
    },
  };
}

export const auth = createAuth();

<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { auth } from '$lib/stores/auth.svelte';
  import { i18n } from '$lib/i18n/index.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card } from '$lib/components/ui/card';
  import Mountains from 'phosphor-svelte/lib/Mountains';
  import QRCode from 'qrcode';
  import { onDestroy } from 'svelte';

  let qrDataUrl = $state('');
  let showQR = $state(false);
  let hasNostrExtension = $state(false);
  let isDev = $state(false);

  $effect(() => {
    hasNostrExtension = !!(window as any).nostr;
    isDev = window.location.hostname === 'localhost';
  });

  async function handleLnurl() {
    try {
      const k1 = await auth.startLogin();

      if (auth.lnurlData) {
        qrDataUrl = await QRCode.toDataURL(auth.lnurlData.lnurl, {
          width: 300,
          margin: 2,
          color: { dark: '#000000', light: '#ffffff' },
        });
        showQR = true;

        auth.startPolling(k1, () => {
          goto(resolve('/home'));
        });
      }
    } catch {
    }
  }

  async function handleNostr() {
    try {
      await auth.loginWithNostr();
      goto(resolve('/home'));
    } catch {
    }
  }

  async function handleDevLogin() {
    try {
      await auth.devLogin();
      goto(resolve('/home'));
    } catch {
    }
  }

  function handleCancel() {
    auth.stopPolling();
    showQR = false;
    qrDataUrl = '';
    auth.clearError();
  }

  onDestroy(() => {
    auth.stopPolling();
  });
</script>

<svelte:head>
  <title>{i18n.t.login.connect} {i18n.t.app.titleSuffix}</title>
  <meta name="description" content={i18n.t.app.description} />
</svelte:head>

<div class="flex min-h-screen bg-background">
  <div class="hidden lg:flex lg:w-1/2 lg:flex-col lg:justify-center lg:p-12 border-r border-border">
    <div class="space-y-8 max-w-md mx-auto">
      <div class="flex items-center gap-3">
        <Mountains class="size-10 text-primary" weight="bold" />
        <span class="font-heading text-4xl font-bold text-foreground tracking-tight">{i18n.t.app.name}</span>
      </div>
      <div class="space-y-3">
        <h1 class="font-heading text-3xl font-semibold text-foreground tracking-tight">
          {i18n.t.app.tagline}
        </h1>
        <p class="text-muted-foreground text-sm leading-relaxed">
          {i18n.t.app.description}
        </p>
      </div>
    </div>
  </div>

  <div class="flex flex-1 items-center justify-center p-6 lg:p-12">
    <div class="w-full max-w-sm space-y-6">
      <div class="lg:hidden flex items-center gap-3 justify-center mb-4">
        <Mountains class="size-8 text-primary" weight="bold" />
        <span class="font-heading text-2xl font-bold text-foreground tracking-tight">{i18n.t.app.name}</span>
      </div>

      <Card class="border-border bg-card">
        <div class="p-6 space-y-5">
          {#if !showQR}
            <div class="space-y-1.5 text-center">
              <h2 class="font-heading text-xl font-semibold tracking-tight text-card-foreground">
                {i18n.t.login.connect}
              </h2>
              <p class="text-muted-foreground text-sm">{i18n.t.login.scanWithWallet}</p>
            </div>

            <div class="space-y-3">
              <Button
                onclick={handleLnurl}
                disabled={auth.isLoading}
                size="lg"
                class="w-full font-medium text-base"
              >
                <svg class="size-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M13 3L4 14h7l-2 7 9-11h-7l2-7z"/>
                </svg>
                {i18n.t.login.loginWithLightning}
              </Button>

              {#if hasNostrExtension}
                <Button
                  variant="outline"
                  onclick={handleNostr}
                  disabled={auth.isLoading}
                  size="lg"
                  class="w-full font-medium"
                >
                  <svg class="size-5 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M8 12l2 2 4-4"/>
                  </svg>
                  {i18n.t.login.loginWithNostr}
                </Button>
              {/if}

              {#if isDev}
                <Button
                  variant="secondary"
                  onclick={handleDevLogin}
                  disabled={auth.isLoading}
                  class="w-full h-10 text-sm rounded-xl"
                >
                  Dev Login
                </Button>
              {/if}
            </div>

            {#if auth.isLoading}
              <div class="flex items-center justify-center gap-2">
                <span class="animate-spin size-4 border-2 border-primary border-t-transparent rounded-full"></span>
                <span class="text-sm text-muted-foreground">{i18n.t.common.loading}</span>
              </div>
            {/if}

            {#if auth.error}
              <p class="text-sm text-destructive text-center">{auth.error}</p>
            {/if}
          {:else}
            <div class="space-y-1.5 text-center">
              <h2 class="font-heading text-xl font-semibold tracking-tight text-card-foreground">
                {i18n.t.login.scanQR}
              </h2>
              <p class="text-muted-foreground text-sm">{i18n.t.login.waitingForWallet}</p>
            </div>

            <div class="flex justify-center">
              {#if qrDataUrl}
                <img src={qrDataUrl} alt="LNURL-auth QR" class="rounded-xl" width="240" height="240" />
              {/if}
            </div>

            <div class="flex items-center justify-center gap-2">
              <span class="animate-pulse size-2 rounded-full bg-primary"></span>
              <span class="text-sm text-muted-foreground">{i18n.t.login.waitingForWallet}</span>
            </div>

            {#if auth.error}
              <p class="text-xs text-destructive text-center">{auth.error}</p>
            {/if}

            <Button
              variant="outline"
              onclick={handleCancel}
              size="sm"
              class="w-full"
            >
              {i18n.t.common.cancel}
            </Button>
          {/if}
        </div>
      </Card>

      <div class="flex items-center justify-center gap-2 text-muted-foreground">
        <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        <span class="text-sm">{i18n.t.login.keysNeverLeave}</span>
      </div>
    </div>
  </div>
</div>
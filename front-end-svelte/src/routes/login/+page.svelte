<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { auth } from '$lib/stores/auth.svelte';
  import { i18n } from '$lib/i18n/index.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card } from '$lib/components/ui/card';
  import Mountains from 'phosphor-svelte/lib/Mountains';
  import Geo from '$lib/components/geo.svelte';
  import Globe from 'phosphor-svelte/lib/Globe';
  import QRCode from 'qrcode';
  import { onDestroy } from 'svelte';

  type View = 'main' | 'phone' | 'phone-code' | 'qr' | 'nostr-help' | 'keys';

  let view = $state<View>('main');
  let qrDataUrl = $state('');
  let generatedKeys = $state<{ nsec: string; npub: string } | null>(null);
  let keysCopied = $state(false);

  // Phone auth state
  let phoneNumber = $state('');
  let phoneCode = $state('');
  let phoneFull = $state('');
  let devCode = $state<string | null>(null);

  function formatPhoneInput(raw: string): string {
    const digits = raw.replace(/\D/g, '').slice(0, 8);
    if (digits.length > 4) {
      return digits.slice(0, 4) + '-' + digits.slice(4);
    }
    return digits;
  }

  function handlePhoneInput(e: Event) {
    const input = e.target as HTMLInputElement;
    phoneNumber = formatPhoneInput(input.value);
    input.value = phoneNumber;
  }

  function handleCodeInput(e: Event) {
    const input = e.target as HTMLInputElement;
    phoneCode = input.value.replace(/\D/g, '').slice(0, 6);
    input.value = phoneCode;
  }

  async function handlePhoneSend() {
    const digits = phoneNumber.replace(/\D/g, '');
    if (digits.length !== 8 || !/^[267]/.test(digits)) {
      auth.clearError();
      return;
    }
    phoneFull = `+503${digits}`;
    try {
      devCode = await auth.sendPhoneCode(phoneFull);
      view = 'phone-code';
      phoneCode = '';
    } catch {
    }
  }

  async function handlePhoneVerify() {
    if (phoneCode.length !== 6) return;
    try {
      await auth.verifyPhoneCode(phoneFull, phoneCode);
      goto(resolve('/home'));
    } catch {
    }
  }

  async function handlePhoneResend() {
    try {
      devCode = await auth.sendPhoneCode(phoneFull);
      phoneCode = '';
    } catch {
    }
  }

  function useDevCode() {
    if (devCode) phoneCode = devCode;
  }

  async function handleLnurl() {
    try {
      const k1 = await auth.startLogin();

      if (auth.lnurlData) {
        qrDataUrl = await QRCode.toDataURL(auth.lnurlData.lnurl, {
          width: 300,
          margin: 2,
          color: { dark: '#000000', light: '#ffffff' },
        });
        view = 'qr';

        auth.startPolling(k1, () => {
          goto(resolve('/home'));
        });
      }
    } catch {
    }
  }

  async function handleNostr() {
    if (!(window as any).nostr) {
      view = 'nostr-help';
      return;
    }
    try {
      await auth.loginWithNostr();
      goto(resolve('/home'));
    } catch {
    }
  }

  async function handleCreateAccount() {
    try {
      generatedKeys = await auth.loginWithGeneratedKey();
      view = 'keys';
    } catch (e) {
      console.error('Create account failed:', e);
    }
  }

  async function copyNsec() {
    if (!generatedKeys) return;
    await navigator.clipboard.writeText(generatedKeys.nsec);
    keysCopied = true;
  }

  function handleCancel() {
    auth.stopPolling();
    view = 'main';
    qrDataUrl = '';
    generatedKeys = null;
    keysCopied = false;
    phoneNumber = '';
    phoneCode = '';
    phoneFull = '';
    devCode = null;
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

<div class="relative flex min-h-screen bg-background">
  <!-- Language toggle -->
  <button
    onclick={() => i18n.setLocale(i18n.locale === 'en' ? 'es' : 'en')}
    class="absolute top-4 right-4 z-10 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
  >
    <Globe size={16} />
    {i18n.locale === 'en' ? 'ES' : 'EN'}
  </button>
  <div class="hidden lg:flex lg:w-1/2 lg:flex-col lg:items-center lg:justify-center lg:p-12 border-r border-border">
    <div class="space-y-6 max-w-sm mx-auto text-center">
      <Geo state="calculating" class="w-40 h-40 mx-auto" />
      <div class="flex items-center gap-3 justify-center">
        <Mountains class="size-8 text-primary" weight="bold" />
        <span class="font-heading text-3xl font-bold text-foreground tracking-tight">{i18n.t.app.name}</span>
      </div>
      <p class="text-muted-foreground text-sm leading-relaxed">
        {i18n.t.app.tagline}
      </p>
    </div>
  </div>

  <div class="flex flex-1 items-center justify-center p-6 lg:p-12">
    <div class="w-full max-w-sm space-y-6">
      <div class="lg:hidden flex items-center gap-3 justify-center mb-4">
        <Mountains class="size-8 text-primary" weight="bold" />
        <span class="font-heading text-2xl font-bold text-foreground tracking-tight">{i18n.t.app.name}</span>
      </div>

      <Card class="border-border bg-card shadow-sm">
        <div class="p-7 space-y-6">
          {#if view === 'main'}
            <div class="space-y-2">
              <h2 class="font-heading text-2xl font-semibold tracking-tight text-card-foreground">
                {i18n.t.login.welcomeBack}
              </h2>
              <p class="text-muted-foreground text-sm leading-relaxed">{i18n.t.login.chooseMethod}</p>
            </div>

            <div class="space-y-2.5">
              <button
                onclick={() => { auth.clearError(); view = 'phone'; }}
                disabled={auth.isLoading}
                class="group w-full flex items-center gap-4 rounded-xl border border-border bg-background hover:bg-secondary/50 hover:border-primary/40 active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none px-4 py-3.5 transition-all"
              >
                <span class="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                  <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
                    <line x1="12" y1="18" x2="12.01" y2="18"/>
                  </svg>
                </span>
                <span class="flex-1 text-left">
                  <span class="block font-medium text-sm text-foreground">{i18n.t.login.loginWithPhone}</span>
                  <span class="block text-xs text-muted-foreground mt-0.5">{i18n.t.login.loginPhoneDesc}</span>
                </span>
                <svg class="size-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 transition-all" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </button>

              <button
                onclick={handleLnurl}
                disabled={auth.isLoading}
                class="group w-full flex items-center gap-4 rounded-xl border border-border bg-background hover:bg-secondary/50 hover:border-primary/40 active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none px-4 py-3.5 transition-all"
              >
                <span class="flex size-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 shrink-0">
                  <svg class="size-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M13 3L4 14h7l-2 7 9-11h-7l2-7z"/>
                  </svg>
                </span>
                <span class="flex-1 text-left">
                  <span class="block font-medium text-sm text-foreground">{i18n.t.login.loginWithLightning}</span>
                  <span class="block text-xs text-muted-foreground mt-0.5">{i18n.t.login.loginLightningDesc}</span>
                </span>
                <svg class="size-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 transition-all" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </button>

              <button
                onclick={handleNostr}
                disabled={auth.isLoading}
                class="group w-full flex items-center gap-4 rounded-xl border border-border bg-background hover:bg-secondary/50 hover:border-primary/40 active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none px-4 py-3.5 transition-all"
              >
                <span class="flex size-10 items-center justify-center rounded-lg bg-violet-500/10 text-violet-600 dark:text-violet-400 shrink-0">
                  <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2a10 10 0 1 0 10 10"/>
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M12 9V2M12 22v-7M5 12H2M22 12h-7"/>
                  </svg>
                </span>
                <span class="flex-1 text-left">
                  <span class="block font-medium text-sm text-foreground">{i18n.t.login.loginWithNostr}</span>
                  <span class="block text-xs text-muted-foreground mt-0.5">{i18n.t.login.loginNostrDesc}</span>
                </span>
                <svg class="size-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 transition-all" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </button>
            </div>

            {#if auth.isLoading}
              <div class="flex items-center justify-center gap-2 pt-1">
                <span class="animate-spin size-4 border-2 border-primary border-t-transparent rounded-full"></span>
                <span class="text-sm text-muted-foreground">{i18n.t.common.loading}</span>
              </div>
            {/if}

            {#if auth.error}
              <p class="text-sm text-destructive text-center">{auth.error}</p>
            {/if}

          {:else if view === 'phone'}
            <div class="space-y-1.5 text-center">
              <h2 class="font-heading text-xl font-semibold tracking-tight text-card-foreground">
                {i18n.t.login.phoneTitle}
              </h2>
              <p class="text-muted-foreground text-sm">{i18n.t.login.phoneSubtitle}</p>
            </div>

            <div class="space-y-4">
              <div class="flex items-center gap-2">
                <div class="flex items-center gap-1.5 rounded-xl border border-border bg-muted px-3 py-2.5 text-sm font-medium text-muted-foreground shrink-0">
                  <span class="text-base">🇸🇻</span>
                  <span>+503</span>
                </div>
                <input
                  type="tel"
                  value={phoneNumber}
                  oninput={handlePhoneInput}
                  placeholder={i18n.t.login.phonePlaceholder}
                  class="flex-1 rounded-xl border border-border bg-background px-3 py-2.5 text-base font-mono tracking-wider placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
                  autocomplete="tel-local"
                  inputmode="numeric"
                />
              </div>

              <Button
                onclick={handlePhoneSend}
                disabled={auth.isLoading || phoneNumber.replace(/\D/g, '').length !== 8}
                size="lg"
                class="w-full font-medium text-base"
              >
                {#if auth.isLoading}
                  <span class="animate-spin size-4 border-2 border-current border-t-transparent rounded-full mr-2"></span>
                {/if}
                {i18n.t.login.phoneSend}
              </Button>

              {#if auth.error}
                <p class="text-sm text-destructive text-center">{auth.error}</p>
              {/if}

              <Button
                variant="ghost"
                onclick={handleCancel}
                size="sm"
                class="w-full"
              >
                {i18n.t.login.nostrBack}
              </Button>
            </div>

          {:else if view === 'phone-code'}
            <div class="space-y-1.5 text-center">
              <h2 class="font-heading text-xl font-semibold tracking-tight text-card-foreground">
                {i18n.t.login.phoneCodeTitle}
              </h2>
              <p class="text-muted-foreground text-sm">
                {i18n.t.login.phoneCodeSubtitle}
                <span class="font-medium text-foreground"> +503 {phoneNumber}</span>
              </p>
            </div>

            <div class="space-y-4">
              {#if devCode}
                <button
                  type="button"
                  onclick={useDevCode}
                  class="w-full flex items-center gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-left hover:bg-amber-500/15 transition-colors"
                >
                  <span class="flex size-8 items-center justify-center rounded-lg bg-amber-500/20 text-amber-700 dark:text-amber-400 shrink-0">
                    <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                      <path d="M2 17l10 5 10-5"/>
                      <path d="M2 12l10 5 10-5"/>
                    </svg>
                  </span>
                  <span class="flex-1 min-w-0">
                    <span class="block text-[10px] font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wider">Dev mode · tocá para usar</span>
                    <span class="block font-mono text-lg font-semibold text-foreground tracking-[0.3em]">{devCode}</span>
                  </span>
                </button>
              {/if}

              <input
                type="text"
                value={phoneCode}
                oninput={handleCodeInput}
                placeholder={i18n.t.login.phoneCodePlaceholder}
                maxlength="6"
                class="w-full rounded-xl border border-border bg-background px-4 py-3 text-center text-2xl font-mono tracking-[0.5em] placeholder:text-muted-foreground placeholder:tracking-[0.5em] focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors"
                autocomplete="one-time-code"
                inputmode="numeric"
              />

              <Button
                onclick={handlePhoneVerify}
                disabled={auth.isLoading || phoneCode.length !== 6}
                size="lg"
                class="w-full font-medium text-base"
              >
                {#if auth.isLoading}
                  <span class="animate-spin size-4 border-2 border-current border-t-transparent rounded-full mr-2"></span>
                {/if}
                {i18n.t.login.phoneVerify}
              </Button>

              {#if auth.error}
                <p class="text-sm text-destructive text-center">{auth.error}</p>
              {/if}

              <button
                onclick={handlePhoneResend}
                disabled={auth.isLoading}
                class="w-full text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
              >
                {i18n.t.login.phoneResend}
              </button>

              <Button
                variant="ghost"
                onclick={handleCancel}
                size="sm"
                class="w-full"
              >
                {i18n.t.login.nostrBack}
              </Button>
            </div>

          {:else if view === 'nostr-help'}
            <div class="space-y-1.5 text-center">
              <h2 class="font-heading text-xl font-semibold tracking-tight text-card-foreground">
                Nostr
              </h2>
              <p class="text-muted-foreground text-sm">{i18n.t.login.nostrNeeded}</p>
            </div>

            <div class="space-y-3">
              <Button
                onclick={handleCreateAccount}
                disabled={auth.isLoading}
                size="lg"
                class="w-full font-medium text-base"
              >
                <svg class="size-5 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <line x1="19" y1="8" x2="19" y2="14"/>
                  <line x1="16" y1="11" x2="22" y2="11"/>
                </svg>
                {i18n.t.login.nostrCreateAccount}
              </Button>

              <div class="relative">
                <div class="absolute inset-0 flex items-center">
                  <span class="w-full border-t border-border"></span>
                </div>
                <div class="relative flex justify-center text-xs">
                  <span class="bg-card px-2 text-muted-foreground">{i18n.t.login.nostrGetExtension}</span>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-2">
                <a
                  href="https://getalby.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center justify-center gap-1.5 rounded-xl border border-border bg-secondary px-3 py-2 text-xs font-medium text-secondary-foreground hover:bg-secondary/80 transition-colors"
                >
                  Alby
                </a>
                <a
                  href="https://chromewebstore.google.com/detail/nos2x/kpgefcfmnafjgpblomihpgcdmpdobcaa"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center justify-center gap-1.5 rounded-xl border border-border bg-secondary px-3 py-2 text-xs font-medium text-secondary-foreground hover:bg-secondary/80 transition-colors"
                >
                  nos2x
                </a>
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

              <Button
                variant="ghost"
                onclick={handleCancel}
                size="sm"
                class="w-full"
              >
                {i18n.t.login.nostrBack}
              </Button>
            </div>

          {:else if view === 'keys'}
            <div class="space-y-1.5 text-center">
              <Geo state="success" class="w-16 h-16 mx-auto" />
              <h2 class="font-heading text-xl font-semibold tracking-tight text-card-foreground">
                {i18n.t.login.nostrAccountCreated}
              </h2>
              <p class="text-muted-foreground text-sm">{i18n.t.login.nostrSaveWarning}</p>
            </div>

            {#if generatedKeys}
              <div class="space-y-3">
                <div class="space-y-1.5">
                  <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{i18n.t.login.nostrPrivateKey}</span>
                  <div class="relative">
                    <code class="block w-full rounded-xl bg-destructive/10 border border-destructive/20 p-3 text-xs break-all font-mono text-destructive select-all">
                      {generatedKeys.nsec}
                    </code>
                  </div>
                </div>

                <div class="space-y-1.5">
                  <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{i18n.t.login.nostrPublicKey}</span>
                  <code class="block w-full rounded-xl bg-muted p-3 text-xs break-all font-mono text-muted-foreground select-all">
                    {generatedKeys.npub}
                  </code>
                </div>

                <p class="text-xs text-destructive/80">{i18n.t.login.nostrBackupWarning}</p>

                <Button
                  variant="outline"
                  onclick={copyNsec}
                  class="w-full"
                >
                  {keysCopied ? i18n.t.login.nostrCopied : i18n.t.login.nostrCopyKey}
                </Button>

                <Button
                  onclick={() => goto(resolve('/home'))}
                  class="w-full"
                >
                  {i18n.t.login.nostrContinue}
                </Button>
              </div>
            {/if}

          {:else if view === 'qr'}
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

            {#if auth.lnurlData}
              <a
                href="lightning:{auth.lnurlData.lnurl}"
                class="inline-flex items-center justify-center gap-2 w-full rounded-xl border border-border bg-secondary px-4 py-2.5 text-sm font-medium text-secondary-foreground hover:bg-secondary/80 transition-colors"
              >
                <svg class="size-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M13 3L4 14h7l-2 7 9-11h-7l2-7z"/>
                </svg>
                {i18n.t.login.openInWallet}
              </a>
              <p class="text-xs text-muted-foreground text-center">{i18n.t.login.walletCompatibility}</p>
            {/if}

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

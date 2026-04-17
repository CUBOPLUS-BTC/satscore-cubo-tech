<script lang="ts">
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth.svelte';
  import { browser } from '$app/environment';
  import { i18n } from '$lib/i18n/index.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Separator } from '$lib/components/ui/separator';
  import { toggleMode } from 'mode-watcher';
  import Flame from 'phosphor-svelte/lib/Flame';
  import Gauge from 'phosphor-svelte/lib/Gauge';
  import Waveform from 'phosphor-svelte/lib/Waveform';
  import PaperPlaneTilt from 'phosphor-svelte/lib/PaperPlaneTilt';
  import Door from 'phosphor-svelte/lib/Door';
  import Moon from 'phosphor-svelte/lib/Moon';
  import Sun from 'phosphor-svelte/lib/Sun';

  let { children } = $props();

  // TEMPORARILY DISABLED - auth requires api.eclalune.com
  // if (browser && !auth.isAuthenticated) {
  //   goto('/login', { replaceState: true });
  // }

  const navItems = [
    { href: '/home', icon: Flame, label: i18n.t.nav.home },
    { href: '/score', icon: Gauge, label: i18n.t.nav.score },
    { href: '/simulator', icon: Waveform, label: i18n.t.nav.simulator },
    { href: '/remittance', icon: PaperPlaneTilt, label: 'Pensiones' },
  ];

  let currentPath = $derived(page.url.pathname);

  function handleLogout() {
    auth.logout();
    goto('/login');
  }
</script>

<div class="flex h-screen">
  <aside class="hidden lg:flex w-60 flex-col border-r border-sidebar-border bg-sidebar p-4">
    <div class="mb-8 px-2">
      <h1 class="font-heading text-xl font-bold text-sidebar-foreground">Magma</h1>
      <p class="text-xs text-sidebar-foreground/60">Bitcoin Financial Intelligence</p>
    </div>

    <nav class="flex flex-1 flex-col gap-1">
      {#each navItems as item}
        <a
          href={item.href}
          class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors
            {currentPath === item.href
              ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
              : 'text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'}"
        >
          <item.icon size={20} weight={currentPath === item.href ? 'fill' : 'regular'} />
          {item.label}
        </a>
      {/each}
    </nav>

    <Separator class="my-2" />

    <div class="flex flex-col gap-1">
      <Button variant="ghost" size="sm" class="justify-start gap-3" onclick={toggleMode}>
        <Sun size={18} class="dark:hidden" />
        <Moon size={18} class="hidden dark:block" />
        Theme
      </Button>
      <Button variant="ghost" size="sm" class="justify-start gap-3 text-destructive" onclick={handleLogout}>
        <Door size={18} />
        {i18n.t.nav.logout}
      </Button>
    </div>
  </aside>

  <main class="flex-1 overflow-y-auto pb-20 lg:pb-0">
    <div class="mx-auto max-w-5xl p-4 lg:p-6">
      {@render children()}
    </div>
  </main>
</div>

<nav class="fixed inset-x-0 bottom-0 z-50 flex items-center justify-around border-t border-border bg-background p-2 lg:hidden">
  {#each navItems as item}
    <a
      href={item.href}
      class="flex flex-col items-center gap-0.5 px-3 py-1 text-xs transition-colors
        {currentPath === item.href
          ? 'text-primary font-medium'
          : 'text-muted-foreground'}"
    >
      <item.icon size={22} weight={currentPath === item.href ? 'fill' : 'regular'} />
      {item.label}
    </a>
  {/each}
</nav>

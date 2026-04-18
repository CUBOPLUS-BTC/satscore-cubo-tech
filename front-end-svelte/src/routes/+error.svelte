<script lang="ts">
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { i18n } from '$lib/i18n/index.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card } from '$lib/components/ui/card';
  import WarningCircle from 'phosphor-svelte/lib/WarningCircle';
</script>

<div class="flex min-h-screen items-center justify-center p-6 bg-muted/30">
  <Card class="w-full max-w-md p-8 text-center space-y-6">
    <div class="flex justify-center">
      <WarningCircle size={64} weight="duotone" class="text-destructive" />
    </div>

    <div class="space-y-2">
      <h1 class="text-4xl font-bold tracking-tight">
        {page.status}
      </h1>
      <p class="text-muted-foreground">
        {page.error?.message ?? i18n.t.error.somethingWentWrong}
      </p>
    </div>

    <div class="flex gap-3 justify-center">
      <Button variant="outline" onclick={() => history.back()}>
        {i18n.t.error.goBack}
      </Button>
      <Button onclick={() => goto(resolve('/home'))}>
        {i18n.t.error.home}
      </Button>
    </div>
  </Card>
</div>

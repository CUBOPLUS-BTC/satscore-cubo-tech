<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { browser } from '$app/environment';
  import { auth } from '$lib/stores/auth.svelte';

  if (browser) {
    goto(resolve(auth.isAuthenticated ? '/home' : '/login'), { replaceState: true });
  }
</script>

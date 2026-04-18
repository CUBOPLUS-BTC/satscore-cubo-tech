<script lang="ts">
  import type { Snippet } from 'svelte';
  let { children }: { children: Snippet } = $props();
</script>

<span class="text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
  {@render children()}
</span>

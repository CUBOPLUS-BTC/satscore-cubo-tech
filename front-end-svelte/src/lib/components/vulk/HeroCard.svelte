<script lang="ts">
  import { Card } from '$lib/components/ui/card';
  import type { Snippet } from 'svelte';
  let {
    children,
    class: className = '',
  }: { children: Snippet; class?: string } = $props();
</script>

<Card class="rounded-[28px] border border-border bg-card p-10 relative overflow-hidden {className}">
  {@render children()}
</Card>

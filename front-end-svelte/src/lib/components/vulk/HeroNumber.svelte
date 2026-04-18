<script lang="ts">
  import type { Snippet } from 'svelte';
  let {
    children,
    size = 'lg',
  }: { children: Snippet; size?: 'md' | 'lg' | 'xl' } = $props();

  const sizes = {
    md: 'text-[28px]',
    lg: 'text-[36px]',
    xl: 'text-[48px]',
  } as const;
</script>

<span class="font-bold leading-none tabular-nums text-foreground {sizes[size]}">
  {@render children()}
</span>

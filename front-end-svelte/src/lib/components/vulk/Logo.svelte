<script lang="ts">
  let { size = 28 }: { size?: number } = $props();
</script>

<div class="flex items-center gap-2">
  <svg width={size} height={size} viewBox="0 0 28 28" fill="none">
    <path d="M 4 23 L 14 5 L 24 23 Z" style="fill: var(--primary)" />
    <circle cx="14" cy="16" r="3" fill="white" />
    <circle cx="14" cy="15.5" r="1.5" style="fill: var(--foreground)" />
  </svg>
  <span class="text-xl font-bold tracking-tight text-foreground">
    Vulk
  </span>
</div>

<script lang="ts">
  type Props = {
    size?: number;
    animated?: boolean;
    mood?: 'happy' | 'chill' | 'proud';
    class?: string;
  };
  let {
    size = 96,
    animated = true,
    mood = 'happy',
    class: className = '',
  }: Props = $props();

  let filterId = $derived(`vulki-glow-${size}`);
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 100 100"
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
  aria-label="Vulki"
  role="img"
  class={className}
>
  <ellipse
    cx="50" cy="22" rx="16" ry="7"
    style="fill: var(--primary)"
    opacity="0.5"
    filter="url(#{filterId})"
    class={animated ? 'vulki-pulse' : ''}
  />

  <path
    d="M 20 82 Q 20 78 22 75 L 40 38 Q 44 30 50 30 Q 56 30 60 38 L 78 75 Q 80 78 80 82 Q 80 88 74 88 L 26 88 Q 20 88 20 82 Z"
    style="fill: var(--primary)"
  />
  <path
    d="M 32 82 Q 32 79 34 76 L 44 52 Q 47 46 50 46 Q 53 46 56 52 L 66 76 Q 68 79 68 82 Q 68 86 64 86 L 36 86 Q 32 86 32 82 Z"
    style="fill: var(--primary-soft)"
    opacity="0.6"
  />

  {#if mood === 'chill'}
    <line x1="39" y1="58" x2="45" y2="58" stroke="white" stroke-width="2.5" stroke-linecap="round" />
    <line x1="55" y1="58" x2="61" y2="58" stroke="white" stroke-width="2.5" stroke-linecap="round" />
  {:else}
    <circle cx="42" cy="57" r="4" fill="white" />
    <circle cx="58" cy="57" r="4" fill="white" />
    <circle cx="43" cy="56.5" r="2" fill="#1F1611" />
    <circle cx="59" cy="56.5" r="2" fill="#1F1611" />
    <circle cx="44" cy="55.5" r="0.8" fill="white" />
    <circle cx="60" cy="55.5" r="0.8" fill="white" />
  {/if}

  {#if mood === 'proud'}
    <path d="M 45 65 Q 50 70 55 65" stroke="white" stroke-width="2" stroke-linecap="round" fill="none" />
  {:else if mood === 'chill'}
    <line x1="46" y1="65" x2="54" y2="65" stroke="white" stroke-width="2" stroke-linecap="round" />
  {:else}
    <path d="M 43 64 Q 50 72 57 64" stroke="white" stroke-width="2" stroke-linecap="round" fill="none" />
  {/if}

  <ellipse cx="50" cy="30" rx="8" ry="3" style="fill: var(--ember)" opacity="0.7" />
  <circle cx="44" cy="26" r="3" style="fill: var(--primary)" opacity="0.8">
    {#if animated}
      <animate attributeName="cy" values="26;23;26" dur="2s" repeatCount="indefinite" />
      <animate attributeName="opacity" values="0.8;0.4;0.8" dur="2s" repeatCount="indefinite" />
    {/if}
  </circle>
  <circle cx="56" cy="24" r="2.5" style="fill: var(--ember)" opacity="0.6">
    {#if animated}
      <animate attributeName="cy" values="24;21;24" dur="2.5s" repeatCount="indefinite" />
      <animate attributeName="opacity" values="0.6;0.3;0.6" dur="2.5s" repeatCount="indefinite" />
    {/if}
  </circle>
  <circle cx="50" cy="23" r="2" style="fill: var(--primary-foreground)" opacity="0.5">
    {#if animated}
      <animate attributeName="cy" values="23;19;23" dur="1.8s" repeatCount="indefinite" />
      <animate attributeName="opacity" values="0.5;0.2;0.5" dur="1.8s" repeatCount="indefinite" />
    {/if}
  </circle>

  <defs>
    <filter id={filterId} x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" />
    </filter>
  </defs>
</svg>

<style>
  @keyframes vulki-pulse {
    0%, 100% { opacity: 0.4; transform: scale(1); }
    50%      { opacity: 0.7; transform: scale(1.1); }
  }
  .vulki-pulse {
    animation: vulki-pulse 3s ease-in-out infinite;
    transform-origin: 50px 22px;
  }
</style>

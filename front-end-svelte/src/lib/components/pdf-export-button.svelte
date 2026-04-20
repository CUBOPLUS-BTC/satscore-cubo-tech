<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  import FilePdf from 'phosphor-svelte/lib/FilePdf';

  interface Props {
    onclick: () => Promise<void>;
    label?: string;
    class?: string;
  }

  let { onclick, label = 'Exportar PDF', class: cls = '' }: Props = $props();

  let exporting = $state(false);

  async function handleClick() {
    exporting = true;
    try {
      await onclick();
    } finally {
      exporting = false;
    }
  }
</script>

<Button
  variant="outline"
  size="sm"
  disabled={exporting}
  onclick={handleClick}
  class="gap-2 {cls}"
>
  <FilePdf size={16} weight={exporting ? 'regular' : 'bold'} />
  {exporting ? 'Generando...' : label}
</Button>

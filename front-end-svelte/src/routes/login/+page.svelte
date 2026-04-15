<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { nip19, generateSecretKey, getPublicKey } from 'nostr-tools';
	import { Button } from '$lib/components/ui/button';
	import { Card } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import Lock from 'phosphor-svelte/lib/Lock';
	import Lightning from 'phosphor-svelte/lib/Lightning';
	import Copy from 'phosphor-svelte/lib/Copy';
	import Check from 'phosphor-svelte/lib/Check';
	import Eye from 'phosphor-svelte/lib/Eye';
	import EyeSlash from 'phosphor-svelte/lib/EyeSlash';

	let key = $state('');
	let showKey = $state(false);
	let showGenDialog = $state(false);
	let savedConfirmed = $state(false);
	let generatedKeys = $state<{ nsec: string; npub: string } | null>(null);
	let copiedNsec = $state(false);
	let copiedNpub = $state(false);

	async function handleConnect() {
		if (!key.trim()) return;
		try {
			await auth.login(key.trim());
			goto('/home');
		} catch {
			// error shown via auth.error
		}
	}

	function handleGenerate() {
		const sk = generateSecretKey();
		const pk = getPublicKey(sk);
		generatedKeys = {
			nsec: nip19.nsecEncode(sk),
			npub: nip19.npubEncode(pk),
		};
		showGenDialog = true;
		savedConfirmed = false;
	}

	async function copyToClipboard(text: string, which: 'nsec' | 'npub') {
		await navigator.clipboard.writeText(text);
		if (which === 'nsec') { copiedNsec = true; setTimeout(() => copiedNsec = false, 2000); }
		else { copiedNpub = true; setTimeout(() => copiedNpub = false, 2000); }
	}

	function useGeneratedKey() {
		if (generatedKeys) key = generatedKeys.nsec;
		showGenDialog = false;
	}
</script>

<div class="flex min-h-screen bg-muted/30">
	<!-- Left branding panel (desktop) -->
	<div class="hidden lg:flex lg:w-1/2 lg:flex-col lg:justify-center lg:p-12 bg-primary">
		<div class="space-y-8 max-w-md mx-auto">
			<div class="flex items-center gap-3">
				<div class="flex size-12 items-center justify-center rounded-sm bg-primary-foreground">
					<Lightning class="size-7 text-primary" weight="fill" />
				</div>
				<span class="font-heading text-4xl font-bold text-primary-foreground tracking-tight">Magma</span>
			</div>
			<div class="space-y-2">
				<h1 class="font-heading text-3xl font-semibold text-primary-foreground tracking-tight">
					Bitcoin Financial Intelligence
				</h1>
				<p class="text-primary-foreground/80 text-sm leading-relaxed">
					Track your sats, analyze your wealth, and understand your financial footprint in the Bitcoin ecosystem.
				</p>
			</div>
		</div>
	</div>

	<!-- Right form panel -->
	<div class="flex flex-1 items-center justify-center p-6 lg:p-12">
		<div class="w-full max-w-md space-y-6">

			<!-- Mobile logo -->
			<div class="lg:hidden flex items-center gap-3 justify-center mb-2">
				<div class="flex size-10 items-center justify-center rounded-sm bg-primary">
					<Lightning class="size-6 text-primary-foreground" weight="fill" />
				</div>
				<span class="font-heading text-2xl font-bold text-primary tracking-tight">Magma</span>
			</div>

			<Card class="border-border/50 bg-card shadow-sm ring-1 ring-border/50">
				<div class="p-6 space-y-5">
					<div class="space-y-1 text-center">
						<h2 class="font-heading text-xl font-semibold tracking-tight text-card-foreground">Connect Your Key</h2>
						<p class="text-muted-foreground text-xs">Enter your Nostr private key to get started</p>
					</div>

					<div class="space-y-4">
						<div class="space-y-2">
							<Label for="key" class="text-muted-foreground text-xs">Private Key</Label>
							<div class="relative">
								<Input
									id="key"
									type={showKey ? 'text' : 'password'}
									placeholder="nsec1... or 64-char hex"
									bind:value={key}
									class="h-10 pr-10 border-input bg-background text-xs font-mono placeholder:text-muted-foreground placeholder:font-sans {auth.error ? 'border-destructive' : ''}"
									onkeydown={(e) => e.key === 'Enter' && handleConnect()}
								/>
								<button
									type="button"
									onclick={() => showKey = !showKey}
									class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
								>
									{#if showKey}
										<EyeSlash size={16} />
									{:else}
										<Eye size={16} />
									{/if}
								</button>
							</div>
							{#if auth.error}
								<p class="text-xs text-destructive">{auth.error}</p>
							{/if}
						</div>

						<Button
							onclick={handleConnect}
							disabled={!key.trim() || auth.isLoading}
							class="w-full h-10 font-medium"
						>
							{#if auth.isLoading}
								<span class="animate-spin mr-2 size-4 border-2 border-current border-t-transparent rounded-full inline-block"></span>
								Connecting...
							{:else}
								Connect
							{/if}
						</Button>
					</div>

					<div class="relative">
						<div class="absolute inset-0 flex items-center">
							<span class="w-full border-t border-border"></span>
						</div>
						<div class="relative flex justify-center text-xs">
							<span class="bg-card px-2 text-muted-foreground">or</span>
						</div>
					</div>

					<Button
						variant="outline"
						onclick={handleGenerate}
						class="w-full h-9 text-xs"
					>
						Generate New Keys
					</Button>
				</div>
			</Card>

			<div class="flex items-center justify-center gap-2 text-muted-foreground">
				<Lock class="size-3.5" />
				<span class="text-xs">Your keys never leave your device</span>
			</div>
		</div>
	</div>
</div>

<!-- Generate Keys Dialog -->
{#if showGenDialog && generatedKeys}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
		<div class="bg-card border border-border rounded-xl shadow-xl w-full max-w-md space-y-5 p-6">
			<div class="space-y-1">
				<h3 class="font-heading text-lg font-semibold">Your New Keys</h3>
				<p class="text-xs text-destructive font-medium">⚠ Save your private key now. It cannot be recovered.</p>
			</div>

			<!-- nsec -->
			<div class="space-y-1.5">
				<Label class="text-xs text-muted-foreground">Private Key (nsec) — keep this secret</Label>
				<div class="flex gap-2">
					<Input
						type="password"
						value={generatedKeys.nsec}
						readonly
						class="font-mono text-xs bg-muted h-9"
					/>
					<Button
						variant="outline"
						size="sm"
						class="shrink-0 h-9 w-9 p-0"
						onclick={() => copyToClipboard(generatedKeys!.nsec, 'nsec')}
					>
						{#if copiedNsec}
							<Check size={14} class="text-green-500" />
						{:else}
							<Copy size={14} />
						{/if}
					</Button>
				</div>
			</div>

			<!-- npub -->
			<div class="space-y-1.5">
				<Label class="text-xs text-muted-foreground">Public Key (npub) — share freely</Label>
				<div class="flex gap-2">
					<Input
						value={generatedKeys.npub}
						readonly
						class="font-mono text-xs bg-muted h-9"
					/>
					<Button
						variant="outline"
						size="sm"
						class="shrink-0 h-9 w-9 p-0"
						onclick={() => copyToClipboard(generatedKeys!.npub, 'npub')}
					>
						{#if copiedNpub}
							<Check size={14} class="text-green-500" />
						{:else}
							<Copy size={14} />
						{/if}
					</Button>
				</div>
			</div>

			<label class="flex items-center gap-2 text-xs cursor-pointer">
				<input type="checkbox" bind:checked={savedConfirmed} class="rounded border-border" />
				<span class="text-muted-foreground">I have saved my private key in a safe place</span>
			</label>

			<div class="flex gap-2">
				<Button
					variant="outline"
					class="flex-1 h-9 text-xs"
					onclick={() => showGenDialog = false}
				>
					Cancel
				</Button>
				<Button
					class="flex-1 h-9 text-xs"
					disabled={!savedConfirmed}
					onclick={useGeneratedKey}
				>
					Use this key
				</Button>
			</div>
		</div>
	</div>
{/if}

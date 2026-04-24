<script lang="ts">
	import type { AchievementsResponse } from '$lib/models/achievements';
	import { auth } from '$lib/stores/auth.svelte';
	import { i18n } from '$lib/i18n/index.svelte';
	import { api } from '$lib/api/client';
	import { endpoints } from '$lib/api/endpoints';
	import { createQuery } from '@tanstack/svelte-query';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Progress } from '$lib/components/ui/progress';
	import { Avatar, AvatarFallback } from '$lib/components/ui/avatar';
	import Trophy from 'phosphor-svelte/lib/Trophy';
	import Medal from 'phosphor-svelte/lib/Medal';
	import Copy from 'phosphor-svelte/lib/Copy';
	import Check from 'phosphor-svelte/lib/Check';
	import User from 'phosphor-svelte/lib/User';
	import Globe from 'phosphor-svelte/lib/Globe';
	import Door from 'phosphor-svelte/lib/Door';
	import AnimatedNumber from '$lib/components/animated-number.svelte';
	import { animateIn, staggerChildren } from '$lib/motion';

	const achievementsQuery = createQuery(() => ({
		queryKey: ['achievements'],
		queryFn: () => api.get<AchievementsResponse>(endpoints.achievements),
		staleTime: 60_000,
	}));

	let achievements = $derived(achievementsQuery.data ?? null);

	let copied = $state(false);

	function copyPubkey() {
		if (!auth.publicKey) return;
		navigator.clipboard.writeText(auth.publicKey);
		copied = true;
		setTimeout(() => { copied = false; }, 2000);
	}

	let shortPubkey = $derived(
		auth.publicKey
			? `${auth.publicKey.slice(0, 8)}...${auth.publicKey.slice(-8)}`
			: ''
	);

	let initials = $derived(
		auth.publicKey
			? auth.publicKey.slice(0, 2).toUpperCase()
			: '?'
	);

	function handleLogout() {
		auth.logout();
		goto(resolve('/login'));
	}

	let progressPercent = $derived(
		achievements?.next_level_xp
			? Math.min((achievements.total_xp / achievements.next_level_xp) * 100, 100)
			: 100
	);
</script>

<svelte:head>
	<title>{i18n.t.profile.title} {i18n.t.app.titleSuffix}</title>
</svelte:head>

<div class="space-y-6">
	<div use:animateIn={{ y: [20, 0], duration: 0.5 }}>
		<h1 class="font-heading text-2xl font-bold tracking-tight">{i18n.t.profile.title}</h1>
	</div>

	<!-- Identity -->
	<div use:animateIn={{ y: [20, 0], delay: 0.06 }}>
		<Card>
			<CardContent class="pt-6">
				<div class="flex items-center gap-4">
					<Avatar size="lg" class="size-14 bg-primary text-primary-foreground">
						<AvatarFallback class="bg-primary text-primary-foreground"><User size={28} /></AvatarFallback>
					</Avatar>
					<div class="min-w-0 flex-1">
						<p class="text-sm font-semibold text-foreground">{i18n.t.profile.pubkey}</p>
						<div class="flex items-center gap-2 mt-1">
							<code class="text-xs text-muted-foreground font-mono truncate">{shortPubkey}</code>
							<Button variant="ghost" size="xs" onclick={copyPubkey} class="shrink-0">
								{#if copied}
									<Check size={14} class="text-green-500" />
								{:else}
									<Copy size={14} />
								{/if}
							</Button>
						</div>
					</div>
				</div>
			</CardContent>
		</Card>
	</div>

	<!-- Level & XP -->
	{#if achievements}
		<div use:animateIn={{ y: [20, 0], delay: 0.12 }}>
			<Card>
				<CardHeader>
					<CardTitle class="font-heading flex items-center justify-between">
						<span>{i18n.t.profile.yourLevel.replace('{level}', String(achievements.level))}</span>
						<Badge variant="secondary">
							<AnimatedNumber value={achievements.total_xp} duration={600} /> XP
						</Badge>
					</CardTitle>
				</CardHeader>
				<CardContent class="space-y-4">
					<Progress value={progressPercent} max={100} />
					{#if achievements.next_level_xp}
						<p class="text-xs text-muted-foreground">
							{i18n.t.profile.nextLevel
								.replace('{xp}', String(achievements.next_level_xp - achievements.total_xp))}
						</p>
					{/if}
				</CardContent>
			</Card>
		</div>
	{/if}

	<!-- Achievements Grid -->
	<div use:animateIn={{ y: [20, 0], delay: 0.18 }}>
		<Card>
			<CardHeader>
				<CardTitle class="font-heading flex items-center justify-between">
					<span>{i18n.t.achievements.title}</span>
					{#if achievements}
						<span class="text-sm font-normal text-muted-foreground">
							{i18n.t.profile.earnedCount
								.replace('{earned}', String(achievements.earned_count))
								.replace('{total}', String(achievements.total_count))}
						</span>
					{/if}
				</CardTitle>
			</CardHeader>
			<CardContent>
				{#if achievements}
					<div class="grid grid-cols-2 sm:grid-cols-3 gap-3" use:staggerChildren={{ y: 12, staggerDelay: 0.04 }}>
						{#each achievements.achievements as achievement (achievement.id)}
							<div
								class="rounded-xl border p-4 text-center transition-colors duration-200 {achievement.earned ? 'border-primary bg-muted' : 'border-border opacity-40'}"
							>
								<div class="flex justify-center mb-2">
									{#if achievement.earned}
										<Trophy size={24} class="text-primary" weight="fill" />
									{:else}
										<Medal size={24} class="text-muted-foreground" weight="regular" />
									{/if}
								</div>
								<p class="text-sm font-medium text-foreground">{achievement.name}</p>
								<p class="text-xs text-muted-foreground mt-1">{achievement.desc}</p>
								<p class="text-xs text-muted-foreground mt-0.5">{achievement.xp} {i18n.t.achievements.xp}</p>
							</div>
						{/each}
					</div>
				{:else}
					<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
						{#each Array(6) as _}
							<div class="rounded-xl border border-border p-4 text-center animate-pulse">
								<div class="size-6 rounded-full bg-muted mx-auto mb-2"></div>
								<div class="h-4 w-20 bg-muted rounded mx-auto mb-1"></div>
								<div class="h-3 w-12 bg-muted rounded mx-auto"></div>
							</div>
						{/each}
					</div>
				{/if}
			</CardContent>
		</Card>
	</div>

	<!-- Settings -->
	<div use:animateIn={{ y: [20, 0], delay: 0.24 }}>
		<Card>
			<CardHeader>
				<CardTitle class="font-heading">{i18n.t.profile.settings}</CardTitle>
			</CardHeader>
			<CardContent class="space-y-1">
				<button
					onclick={() => i18n.setLocale(i18n.locale === 'en' ? 'es' : 'en')}
					class="flex items-center justify-between w-full rounded-xl px-3 py-3 text-sm hover:bg-muted transition-colors"
				>
					<span class="flex items-center gap-3">
						<Globe size={18} />
						{i18n.t.profile.language}
					</span>
					<span class="text-muted-foreground text-xs">
						{i18n.locale === 'en' ? 'English' : 'Espa\u00f1ol'}
					</span>
				</button>

				<button
					onclick={handleLogout}
					class="flex items-center gap-3 w-full rounded-xl px-3 py-3 text-sm text-red-500 hover:bg-destructive/10 transition-colors"
				>
					<Door size={18} />
					{i18n.t.nav.logout}
				</button>
			</CardContent>
		</Card>
	</div>
</div>

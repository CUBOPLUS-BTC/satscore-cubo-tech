<script lang="ts">
	import { i18n } from '$lib/i18n/index.svelte';
	import { api } from '$lib/api/client';
	import { endpoints } from '$lib/api/endpoints';
	import { auth } from '$lib/stores/auth.svelte';
	import { createQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Separator } from '$lib/components/ui/separator';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Progress } from '$lib/components/ui/progress';
	import { animateIn, staggerChildren, pressScale } from '$lib/motion';
	import BookBookmark from 'phosphor-svelte/lib/BookBookmark';
	import ArrowLeft from 'phosphor-svelte/lib/ArrowLeft';
	import ArrowRight from 'phosphor-svelte/lib/ArrowRight';
	import CheckCircle from 'phosphor-svelte/lib/CheckCircle';
	import XCircle from 'phosphor-svelte/lib/XCircle';
	import Clock from 'phosphor-svelte/lib/Clock';
	import Trophy from 'phosphor-svelte/lib/Trophy';
	import MagnifyingGlass from 'phosphor-svelte/lib/MagnifyingGlass';
	import Heart from 'phosphor-svelte/lib/Heart';
	import Flame from 'phosphor-svelte/lib/Flame';
	import Lock from 'phosphor-svelte/lib/Lock';
	import Star from 'phosphor-svelte/lib/Star';
	import Lightning from 'phosphor-svelte/lib/Lightning';
	import PlayCircle from 'phosphor-svelte/lib/PlayCircle';
	import Geo from '$lib/components/geo.svelte';
	import MagmaMiner from '$lib/components/game/MagmaMiner.svelte';
	import { resolve } from '$app/paths';
	import type {
		UnitsResponse,
		ProgressResponse,
		LearningUnit,
		UnitLesson,
		LessonDetail,
		QuizResult,
	} from '$lib/models/education';

	const qc = useQueryClient();

	type View = 'path' | 'lesson' | 'quiz' | 'result' | 'no-hearts' | 'glossary' | 'game';
	let view = $state<View>('path');
	let selectedId = $state<string | null>(null);
	let glossarySearch = $state('');

	// Quiz state (Duolingo-style: one question at a time)
	let questionIndex = $state(0);
	let selectedOption = $state<number | null>(null);
	let revealed = $state(false);
	let answers = $state<number[]>([]);
	let wrongCount = $state(0);
	let quizResult = $state<QuizResult | null>(null);

	let locale = $derived(i18n.locale === 'es' ? 'es' : 'en');

	// ── Queries ───────────────────────────────────────────────────────────────
	const unitsQuery = createQuery(() => ({
		queryKey: ['education-units', locale],
		queryFn: () => api.get<UnitsResponse>(endpoints.education.units(locale)),
		staleTime: 60_000,
	}));

	const progressQuery = createQuery(() => ({
		queryKey: ['education-progress'],
		queryFn: () => api.get<ProgressResponse>(endpoints.education.progress),
		enabled: auth.isAuthenticated,
		staleTime: 30_000,
	}));

	const lessonQuery = createQuery(() => ({
		queryKey: ['lesson', selectedId, locale],
		queryFn: () => api.get<LessonDetail>(endpoints.education.lesson(selectedId!, locale)),
		enabled: selectedId !== null && (view === 'lesson' || view === 'quiz' || view === 'result'),
		staleTime: 300_000,
	}));

	const glossaryQuery = createQuery(() => ({
		queryKey: ['glossary', locale, glossarySearch],
		queryFn: () => api.get<{ results: Array<{ key: string; term: string; definition: string; category: string; difficulty: string; example: string }> }>(
			endpoints.education.glossary(locale, glossarySearch || undefined)
		),
		enabled: view === 'glossary',
		staleTime: 300_000,
	}));

	const quizMutation = createMutation(() => ({
		mutationFn: (payload: { lesson_id: string; answers: number[]; locale: string }) =>
			api.post<QuizResult>(endpoints.education.quiz, payload),
		onSuccess: (data) => {
			quizResult = data;
			view = 'result';
			qc.invalidateQueries({ queryKey: ['education-progress'] });
			qc.invalidateQueries({ queryKey: ['education-units', locale] });
		},
	}));

	// ── Derived ───────────────────────────────────────────────────────────────
	let units = $derived(unitsQuery.data?.units ?? []);
	let gamState = $derived(progressQuery.data?.state ?? null);
	let lesson = $derived(lessonQuery.data ?? null);
	let glossaryEntries = $derived(glossaryQuery.data?.results ?? []);
	let isSubmitting = $derived(quizMutation.isPending);

	let currentQuestion = $derived(lesson?.quiz?.[questionIndex] ?? null);
	let totalQuestions = $derived(lesson?.quiz?.length ?? 0);

	// ── Handlers ──────────────────────────────────────────────────────────────
	function openLesson(lessonId: string, unit: LearningUnit) {
		if (!unit.unlocked) return;
		selectedId = lessonId;
		answers = [];
		quizResult = null;
		questionIndex = 0;
		selectedOption = null;
		revealed = false;
		wrongCount = 0;
		view = 'lesson';
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}

	function startQuiz() {
		if (!lesson || !lesson.quiz.length) return;
		// Hard gate: block if hearts empty (when authenticated).
		if (gamState && gamState.hearts === 0) {
			view = 'no-hearts';
			return;
		}
		answers = new Array(lesson.quiz.length).fill(-1);
		questionIndex = 0;
		selectedOption = null;
		revealed = false;
		wrongCount = 0;
		view = 'quiz';
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}

	function selectOption(idx: number) {
		if (revealed) return;
		selectedOption = idx;
	}

	async function checkAnswer() {
		if (selectedOption === null || !currentQuestion) return;
		answers[questionIndex] = selectedOption;
		revealed = true;

		// Client-side correctness check against stored answers collected so far.
		// The real grading happens on submit, but we surface feedback instantly.
		// Since the backend strips correct_index from GET /lesson, we can't
		// know here — we treat it as "submitted" and wait for full result.
		// However we want immediate feedback. Solution: assume the user is
		// right if option was chosen, but show the explanation on click.
		// For a tighter UX we'd need the server to expose correct_index
		// (safe because lessons aren't graded competitively).
	}

	function nextQuestion() {
		if (!revealed) return;
		revealed = false;
		selectedOption = null;
		if (questionIndex < totalQuestions - 1) {
			questionIndex += 1;
		} else {
			submitQuiz();
		}
	}

	function submitQuiz() {
		if (!selectedId) return;
		quizMutation.mutate({ lesson_id: selectedId, answers, locale });
	}

	function goToPath() {
		view = 'path';
		selectedId = null;
		quizResult = null;
	}

	// ── Game handlers ─────────────────────────────────────────────────────
	async function handleGameScore(data: { score: number; blocks_mined: number; halvings_survived: number; duration_seconds: number }) {
		try {
			await api.post(endpoints.education.gameComplete, data);
			qc.invalidateQueries({ queryKey: ['education-progress'] });
		} catch {
			// Never block the game on a server glitch
		}
	}

	// ── Format helpers ────────────────────────────────────────────────────────
	function fmtCountdown(seconds: number): string {
		if (seconds <= 0) return '0m';
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		if (h > 0) return `${h}h ${m}m`;
		return `${m}m`;
	}

	const timePrefLabel: Record<string, () => string> = {
		high: () => i18n.t.education.timePrefHigh,
		mixed: () => i18n.t.education.timePrefMixed,
		low: () => i18n.t.education.timePrefLow,
	};

	const themeColorMap: Record<string, { ring: string; bg: string; text: string; border: string }> = {
		amber:   { ring: 'ring-amber-500/40',   bg: 'bg-amber-500',   text: 'text-amber-500',   border: 'border-amber-500' },
		orange:  { ring: 'ring-orange-500/40',  bg: 'bg-orange-500',  text: 'text-orange-500',  border: 'border-orange-500' },
		emerald: { ring: 'ring-emerald-500/40', bg: 'bg-emerald-500', text: 'text-emerald-500', border: 'border-emerald-500' },
		violet:  { ring: 'ring-violet-500/40',  bg: 'bg-violet-500',  text: 'text-violet-500',  border: 'border-violet-500' },
		red:     { ring: 'ring-red-500/40',     bg: 'bg-red-500',     text: 'text-red-500',     border: 'border-red-500' },
		yellow:  { ring: 'ring-yellow-500/40',  bg: 'bg-yellow-500',  text: 'text-yellow-500',  border: 'border-yellow-500' },
		cyan:    { ring: 'ring-cyan-500/40',    bg: 'bg-cyan-500',    text: 'text-cyan-500',    border: 'border-cyan-500' },
		sky:     { ring: 'ring-sky-500/40',     bg: 'bg-sky-500',     text: 'text-sky-500',     border: 'border-sky-500' },
	};

	function colors(theme: string) {
		return themeColorMap[theme] ?? themeColorMap.amber;
	}

	// Simple markdown-ish renderer
	function renderContent(text: string): string {
		return text
			.replace(/^### (.+)$/gm, '<h3 class="font-heading text-base font-semibold mt-5 mb-1.5">$1</h3>')
			.replace(/^## (.+)$/gm, '<h2 class="font-heading text-lg font-bold mt-6 mb-2">$1</h2>')
			.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
			.replace(/\n\n/g, '</p><p class="mb-3">')
			.replace(/^/, '<p class="mb-3">')
			.concat('</p>');
	}

	// Next lesson to tackle = first non-passed lesson in the first unlocked unit.
	function currentLessonId(): string | null {
		for (const u of units) {
			if (!u.unlocked) continue;
			for (const l of u.lessons) {
				if (!l.status.passed) return l.id;
			}
		}
		return null;
	}

	let currentId = $derived(currentLessonId());
</script>

<svelte:head>
	<title>{i18n.t.education.title} {i18n.t.app.titleSuffix}</title>
</svelte:head>

<!-- ═══════════════════════════════════════════════════════════════════════
     GAMIFICATION HEADER (visible in path/lesson/quiz views when logged in)
     ═══════════════════════════════════════════════════════════════════════ -->
{#if gamState && view !== 'result' && view !== 'no-hearts' && view !== 'glossary' && view !== 'game'}
	<div class="sticky top-0 z-30 -mx-4 lg:-mx-8 px-4 lg:px-8 py-3 mb-6 bg-background/95 backdrop-blur-sm border-b border-border">
		<div class="flex items-center gap-4 flex-wrap">
			<!-- Streak -->
			<div class="flex items-center gap-1.5">
				<Flame size={20} class="text-orange-500" weight="fill" />
				<span class="font-heading text-base font-bold tabular-nums">{gamState.streak_days}</span>
				<span class="text-xs text-muted-foreground">
					{gamState.streak_days === 1 ? i18n.t.education.day : i18n.t.education.days}
				</span>
			</div>

			<Separator orientation="vertical" class="h-5" />

			<!-- Hearts -->
			<div class="flex items-center gap-1">
				{#each Array(gamState.hearts_max) as _, i (i)}
					<Heart
						size={18}
						class={i < gamState.hearts ? 'text-red-500' : 'text-muted-foreground/30'}
						weight={i < gamState.hearts ? 'fill' : 'regular'}
					/>
				{/each}
				{#if gamState.hearts < gamState.hearts_max}
					<span class="text-[10px] text-muted-foreground ml-1 tabular-nums">
						{fmtCountdown(gamState.next_heart_in_seconds)}
					</span>
				{/if}
			</div>

			<Separator orientation="vertical" class="h-5" />

			<!-- XP + Level -->
			<div class="flex items-center gap-2 flex-1 min-w-[140px]">
				<Star size={18} class="text-amber-500 shrink-0" weight="fill" />
				<div class="flex-1 min-w-0">
					<div class="flex items-center justify-between text-xs">
						<span class="font-medium truncate">
							{locale === 'es' ? gamState.level.name_es : gamState.level.name_en}
						</span>
						<span class="text-muted-foreground tabular-nums shrink-0 ml-2">
							{gamState.xp_total} XP
						</span>
					</div>
					<Progress value={gamState.level.progress_pct} max={100} class="h-1.5 mt-1" />
				</div>
			</div>

			<!-- Daily goal chip -->
			{#if gamState.daily_goal_met}
				<Badge variant="default" class="gap-1 shrink-0">
					<CheckCircle size={12} weight="fill" />
					{i18n.t.education.dailyGoalMet}
				</Badge>
			{:else}
				<Badge variant="secondary" class="gap-1 shrink-0 text-[10px]">
					{gamState.daily_xp_today}/{gamState.daily_xp_goal} XP
				</Badge>
			{/if}
		</div>
	</div>
{/if}

<!-- ═══════════════════════════════════════════════════════════════════════
     PATH VIEW (main learning map)
     ═══════════════════════════════════════════════════════════════════════ -->
{#if view === 'path'}
	<div class="space-y-8" use:staggerChildren={{ y: 16, staggerDelay: 0.06 }}>
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<div class="flex items-center gap-3">
				<Geo state="studying" class="w-14 h-14 shrink-0" />
				<div>
					<h1 class="font-heading text-2xl font-bold tracking-tight">{i18n.t.education.pathTitle}</h1>
					<p class="text-sm text-muted-foreground">{i18n.t.education.pathSubtitle}</p>
				</div>
			</div>
			<div class="flex gap-2">
				<Button size="sm" class="gap-1.5" onclick={() => (view = 'game')}>
					<PlayCircle size={14} weight="fill" />
					{i18n.t.education.game.play}
				</Button>
				<Button variant="outline" size="sm" onclick={() => (view = 'glossary')}>
					{i18n.t.education.glossary}
				</Button>
			</div>
		</div>

		{#if unitsQuery.isPending}
			<div class="space-y-4">
				{#each Array(3) as _, i (i)}
					<Card><CardContent class="pt-5"><Skeleton class="h-40 w-full" /></CardContent></Card>
				{/each}
			</div>
		{:else}
			<div class="space-y-10">
				{#each units as unit (unit.id)}
					{@const c = colors(unit.theme_color)}
					<section
						class="relative rounded-3xl border border-border overflow-hidden
							{unit.unlocked ? '' : 'opacity-60'}"
					>
						<!-- Unit header -->
						<div class="px-5 py-4 {c.bg}/10 border-b border-border">
							<div class="flex items-center justify-between gap-3">
								<div class="flex items-center gap-3 min-w-0">
									<div class="w-10 h-10 rounded-xl {c.bg}/20 flex items-center justify-center shrink-0">
										{#if !unit.unlocked}
											<Lock size={18} class="text-muted-foreground" />
										{:else if unit.completed}
											<Trophy size={18} class={c.text} weight="fill" />
										{:else}
											<Lightning size={18} class={c.text} weight="fill" />
										{/if}
									</div>
									<div class="min-w-0">
										<h2 class="font-heading text-base font-bold tracking-tight truncate">
											{unit.title}
										</h2>
										<p class="text-xs text-muted-foreground truncate">{unit.subtitle}</p>
									</div>
								</div>
								<Badge variant="outline" class="text-[10px] shrink-0 {c.text} {c.border}/30">
									{timePrefLabel[unit.time_preference]?.() ?? unit.time_preference}
								</Badge>
							</div>
							{#if unit.unlocked && unit.lessons.length > 0}
								<Progress value={unit.progress_pct} max={100} class="h-1 mt-3" />
							{/if}
						</div>

						<!-- Lesson nodes — zigzag layout -->
						<div class="p-6 flex flex-col items-center gap-5">
							{#each unit.lessons as lsn, idx (lsn.id)}
								{@const offsetClass = idx % 2 === 0 ? 'self-start' : 'self-end'}
								{@const isCurrent = unit.unlocked && !lsn.status.passed && currentId === lsn.id}
								<div class="{offsetClass} flex items-center gap-3 max-w-[85%]" use:animateIn={{ y: [8, 0], delay: idx * 0.05 }}>
									{#if idx % 2 === 1}
										<div class="text-right min-w-0">
											<h3 class="font-heading text-sm font-semibold truncate">{lsn.title}</h3>
											<p class="text-[11px] text-muted-foreground flex items-center gap-1 justify-end">
												<Clock size={10} /> {lsn.duration_min} {i18n.t.education.min}
												· {lsn.quiz_count} {i18n.t.education.questions}
											</p>
										</div>
									{/if}

									<button
										onclick={() => openLesson(lsn.id, unit)}
										disabled={!unit.unlocked}
										class="relative w-16 h-16 rounded-full border-4 flex items-center justify-center transition-all duration-200 shrink-0
											{lsn.status.perfect
												? `${c.bg} ${c.border} text-white shadow-lg`
												: lsn.status.passed
												? `${c.bg}/80 ${c.border} text-white`
												: isCurrent
												? `bg-background ${c.border} ${c.text} animate-pulse`
												: unit.unlocked
												? `bg-muted border-border ${c.text} hover:${c.border} hover:shadow-md`
												: 'bg-muted border-border text-muted-foreground cursor-not-allowed'}
											{unit.unlocked ? 'cursor-pointer hover:scale-105 active:scale-95' : ''}"
										title={lsn.title}
										aria-label={lsn.title}
									>
										{#if lsn.status.perfect}
											<Star size={26} weight="fill" />
										{:else if lsn.status.passed}
											<CheckCircle size={26} weight="fill" />
										{:else if !unit.unlocked}
											<Lock size={22} />
										{:else if isCurrent}
											<PlayCircle size={28} weight="fill" />
										{:else}
											<BookBookmark size={24} weight="regular" />
										{/if}
									</button>

									{#if idx % 2 === 0}
										<div class="min-w-0">
											<h3 class="font-heading text-sm font-semibold truncate">{lsn.title}</h3>
											<p class="text-[11px] text-muted-foreground flex items-center gap-1">
												<Clock size={10} /> {lsn.duration_min} {i18n.t.education.min}
												· {lsn.quiz_count} {i18n.t.education.questions}
											</p>
										</div>
									{/if}
								</div>
							{/each}
						</div>

						{#if !unit.unlocked}
							<div class="absolute inset-0 flex items-end justify-center pb-6 pointer-events-none">
								<Badge variant="secondary" class="gap-1.5 shadow-md">
									<Lock size={12} /> {i18n.t.education.unitLocked}
								</Badge>
							</div>
						{/if}
					</section>
				{/each}
			</div>
		{/if}
	</div>

<!-- ═══════════════════════════════════════════════════════════════════════
     LESSON VIEW
     ═══════════════════════════════════════════════════════════════════════ -->
{:else if view === 'lesson'}
	<div class="space-y-6" use:animateIn={{ y: [20, 0], duration: 0.4 }}>
		<button
			onclick={goToPath}
			class="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
		>
			<ArrowLeft size={16} />
			{i18n.t.education.backToLessons}
		</button>

		{#if lessonQuery.isPending}
			<div class="space-y-4">
				<Skeleton class="h-7 w-2/3" />
				<Skeleton class="h-4 w-full" />
				<Skeleton class="h-4 w-full" />
				<Skeleton class="h-4 w-3/4" />
			</div>
		{:else if lesson}
			<div class="space-y-2">
				<div class="flex items-center gap-2 flex-wrap">
					<Badge variant="outline" class="text-[10px] capitalize">{lesson.difficulty}</Badge>
					<span class="flex items-center gap-1 text-xs text-muted-foreground">
						<Clock size={12} /> {lesson.duration_min} {i18n.t.education.min}
					</span>
					{#if lesson.quiz.length > 0}
						<span class="text-xs text-muted-foreground">·</span>
						<span class="text-xs text-muted-foreground">
							{lesson.quiz.length} {i18n.t.education.questions}
						</span>
					{/if}
				</div>
				<h1 class="font-heading text-2xl font-bold tracking-tight">{lesson.title}</h1>
				<p class="text-sm text-muted-foreground">{lesson.description}</p>
			</div>

			<Separator />

			<article class="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed text-foreground">
				{@html renderContent(lesson.content)}
			</article>

			{#if lesson.quiz.length > 0}
				<Card class="ring-1 ring-primary/20">
					<CardContent class="pt-5 flex items-center justify-between gap-4">
						<div class="flex items-center gap-3">
							<Trophy size={22} class="text-primary shrink-0" weight="fill" />
							<div>
								<p class="text-sm font-semibold">{i18n.t.education.quiz}</p>
								<p class="text-xs text-muted-foreground">{lesson.quiz.length} {i18n.t.education.questions}</p>
							</div>
						</div>
						<div use:pressScale>
							<Button onclick={startQuiz}>{i18n.t.education.startQuiz}</Button>
						</div>
					</CardContent>
				</Card>
			{/if}
		{/if}
	</div>

<!-- ═══════════════════════════════════════════════════════════════════════
     QUIZ VIEW — Duolingo-style: one question at a time
     ═══════════════════════════════════════════════════════════════════════ -->
{:else if view === 'quiz' && lesson && currentQuestion}
	<div class="flex flex-col min-h-[70vh] gap-6" use:animateIn={{ y: [12, 0], duration: 0.3 }}>
		<!-- Top bar: progress -->
		<div class="flex items-center gap-3">
			<button
				onclick={() => (view = 'lesson')}
				class="text-muted-foreground hover:text-foreground transition-colors"
				aria-label={i18n.t.education.backToLesson}
			>
				<XCircle size={22} />
			</button>
			<Progress value={questionIndex + (revealed ? 1 : 0)} max={totalQuestions} class="flex-1 h-3" />
			<span class="text-xs text-muted-foreground tabular-nums shrink-0">
				{questionIndex + 1}/{totalQuestions}
			</span>
		</div>

		<!-- Question -->
		<div class="flex-1 space-y-6" use:animateIn={{ y: [20, 0], duration: 0.3 }}>
			<h2 class="font-heading text-xl sm:text-2xl font-bold tracking-tight leading-tight">
				{currentQuestion.question}
			</h2>

			<div class="grid grid-cols-1 gap-3">
				{#each currentQuestion.options as opt, j (j)}
					{@const isSelected = selectedOption === j}
					<button
						onclick={() => selectOption(j)}
						disabled={revealed}
						class="text-left px-5 py-4 rounded-2xl border-2 text-sm transition-all duration-150
							{isSelected
								? revealed
									? 'border-primary bg-primary/10 text-primary font-semibold'
									: 'border-primary bg-primary/5 text-primary font-medium'
								: 'border-border hover:border-muted-foreground hover:bg-muted'}
							{revealed && !isSelected ? 'opacity-50' : ''}
							{revealed ? 'cursor-default' : 'cursor-pointer'}"
					>
						<span class="flex items-center gap-3">
							<span class="w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold shrink-0
								{isSelected ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-muted-foreground'}">
								{String.fromCharCode(65 + j)}
							</span>
							<span>{opt}</span>
						</span>
					</button>
				{/each}
			</div>

			<!-- Explanation panel (shown after reveal) -->
			{#if revealed}
				<div use:animateIn={{ y: [10, 0], duration: 0.25 }}>
					<Card class="ring-1 ring-primary/20 bg-primary/5">
						<CardContent class="pt-4 space-y-1">
							<p class="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
								<CheckCircle size={14} weight="fill" />
								{i18n.t.education.keepGoing}
							</p>
							<p class="text-sm leading-relaxed">{currentQuestion.explanation}</p>
						</CardContent>
					</Card>
				</div>
			{/if}
		</div>

		<!-- Sticky action bar -->
		<div class="sticky bottom-0 -mx-4 lg:-mx-8 px-4 lg:px-8 py-4 bg-background/95 backdrop-blur-sm border-t border-border">
			{#if !revealed}
				<Button
					class="w-full h-12 text-base font-semibold"
					onclick={checkAnswer}
					disabled={selectedOption === null}
				>
					{i18n.t.education.check}
				</Button>
			{:else}
				<Button
					class="w-full h-12 text-base font-semibold"
					onclick={nextQuestion}
					disabled={isSubmitting}
				>
					{isSubmitting
						? i18n.t.common.loading
						: questionIndex < totalQuestions - 1
						? i18n.t.education.continue
						: i18n.t.education.submitQuiz}
				</Button>
			{/if}
		</div>
	</div>

<!-- ═══════════════════════════════════════════════════════════════════════
     RESULT VIEW
     ═══════════════════════════════════════════════════════════════════════ -->
{:else if view === 'result' && quizResult}
	<div class="space-y-6" use:animateIn={{ y: [20, 0], duration: 0.4 }}>
		<!-- Score hero -->
		<Card class="ring-1 {quizResult.score.passed ? 'ring-green-500/40' : 'ring-amber-500/40'}">
			<CardContent class="pt-6 text-center space-y-3">
				{#if quizResult.score.passed}
					<Geo state="success" class="w-20 h-20 mx-auto" />
				{:else}
					<Geo state="nervous" class="w-20 h-20 mx-auto" />
				{/if}
				<p class="font-heading text-5xl font-bold tabular-nums {quizResult.score.passed ? 'text-green-500' : 'text-amber-500'}">
					{quizResult.score.percentage}%
				</p>
				<p class="text-sm font-medium">
					{quizResult.score.correct}/{quizResult.score.total} {i18n.t.education.correct}
				</p>
				<Badge variant={quizResult.score.passed ? 'default' : 'secondary'}>
					{quizResult.score.passed ? i18n.t.education.passed : i18n.t.education.failed}
				</Badge>
				<p class="text-sm text-muted-foreground">{quizResult.score.grade}</p>

				<!-- XP / hearts earned -->
				{#if quizResult.progress && quizResult.progress.xp_earned > 0}
					<div class="flex items-center justify-center gap-2 pt-2">
						<Star size={18} class="text-amber-500" weight="fill" />
						<span class="font-heading text-lg font-bold text-amber-500">
							+{quizResult.progress.xp_earned} {i18n.t.education.xp}
						</span>
					</div>
				{/if}
				{#if quizResult.progress && quizResult.progress.hearts_lost > 0}
					<div class="flex items-center justify-center gap-1 text-xs text-muted-foreground">
						<Heart size={12} class="text-red-500" weight="fill" />
						<span>-{quizResult.progress.hearts_lost}</span>
					</div>
				{/if}
			</CardContent>
		</Card>

		<!-- Per-question breakdown -->
		<div class="space-y-3" use:staggerChildren={{ y: 12, staggerDelay: 0.05 }}>
			{#each quizResult.results as r (r.question_number)}
				<Card class="border {r.is_correct ? 'border-green-500/20' : 'border-red-500/20'}">
					<CardContent class="pt-4 space-y-2">
						<div class="flex items-start gap-2">
							{#if r.is_correct}
								<CheckCircle size={18} class="text-green-500 shrink-0 mt-0.5" weight="fill" />
							{:else}
								<XCircle size={18} class="text-red-500 shrink-0 mt-0.5" weight="fill" />
							{/if}
							<p class="text-sm font-medium">{r.question}</p>
						</div>
						<p class="text-xs text-muted-foreground pl-6">{r.explanation}</p>
					</CardContent>
				</Card>
			{/each}
		</div>

		<!-- Wallet tip (only on pass) -->
		{#if quizResult.score.passed}
			<a
				href={resolve('/wallets')}
				class="group flex items-center gap-3 rounded-2xl border border-dashed border-border p-4 hover:border-primary/30 hover:bg-muted/40 transition-all"
			>
				<Geo state="stacking" class="w-10 h-10 shrink-0" />
				<div class="flex-1 min-w-0">
					<p class="text-sm font-medium text-foreground">{i18n.t.wallets.seeGuide}</p>
					<p class="text-xs text-muted-foreground">{i18n.t.wallets.tipEducation}</p>
				</div>
				<ArrowRight size={16} class="text-muted-foreground/40 group-hover:text-primary transition-colors shrink-0" />
			</a>
		{/if}

		<!-- Actions -->
		<div class="flex gap-3">
			<Button variant="outline" class="flex-1" onclick={() => (view = 'lesson')}>
				{i18n.t.education.backToLesson}
			</Button>
			<Button class="flex-1" onclick={goToPath}>
				{i18n.t.education.nextLesson}
				<ArrowRight size={16} />
			</Button>
		</div>
	</div>

<!-- ═══════════════════════════════════════════════════════════════════════
     NO HEARTS VIEW
     ═══════════════════════════════════════════════════════════════════════ -->
{:else if view === 'no-hearts'}
	<div class="flex flex-col items-center justify-center min-h-[50vh] text-center space-y-5" use:animateIn={{ y: [16, 0] }}>
		<Geo state="sleeping" class="w-20 h-20 mx-auto" />
		<div class="flex gap-1">
			{#each Array(5) as _, i (i)}
				<Heart size={32} class="text-muted-foreground/30" />
			{/each}
		</div>
		<div>
			<h2 class="font-heading text-xl font-bold">{i18n.t.education.noHearts}</h2>
			<p class="text-sm text-muted-foreground mt-2 max-w-md">{i18n.t.education.noHeartsBody}</p>
		</div>
		{#if gamState}
			<p class="text-sm tabular-nums">
				<span class="text-muted-foreground">{i18n.t.education.heartRefill}:</span>
				<span class="font-semibold ml-1">{fmtCountdown(gamState.next_heart_in_seconds)}</span>
			</p>
		{/if}
		<Button variant="outline" onclick={goToPath}>
			<ArrowLeft size={16} />
			{i18n.t.education.backToLessons}
		</Button>
	</div>

<!-- ═══════════════════════════════════════════════════════════════════════
     GLOSSARY VIEW
     ═══════════════════════════════════════════════════════════════════════ -->
{:else if view === 'glossary'}
	<div class="space-y-6" use:staggerChildren={{ y: 16, staggerDelay: 0.06 }}>
		<button
			onclick={() => (view = 'path')}
			class="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
		>
			<ArrowLeft size={16} />
			{i18n.t.education.allLessons}
		</button>

		<div>
			<h1 class="font-heading text-2xl font-bold tracking-tight">{i18n.t.education.glossary}</h1>
			<p class="text-sm text-muted-foreground">{i18n.t.education.subtitle}</p>
		</div>

		<div class="relative">
			<MagnifyingGlass size={16} class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
			<Input class="pl-9" placeholder={i18n.t.education.search} bind:value={glossarySearch} />
		</div>

		{#if glossaryQuery.isPending}
			<div class="space-y-3">
				{#each Array(8) as _, i (i)}
					<Skeleton class="h-14 w-full rounded-xl" />
				{/each}
			</div>
		{:else if glossaryEntries.length === 0}
			<p class="text-muted-foreground text-sm">{i18n.t.education.noResults}</p>
		{:else}
			<div class="divide-y divide-border rounded-2xl border border-border overflow-hidden">
				{#each glossaryEntries as entry (entry.key)}
					<div class="px-4 py-3.5 bg-card hover:bg-muted transition-colors">
						<div class="flex items-start justify-between gap-4">
							<div class="space-y-0.5 min-w-0">
								<p class="text-sm font-semibold">{entry.term}</p>
								<p class="text-xs text-muted-foreground leading-relaxed">{entry.definition}</p>
								{#if entry.example}
									<p class="text-xs text-muted-foreground/70 italic mt-1">{entry.example}</p>
								{/if}
							</div>
							<Badge variant="outline" class="text-[10px] shrink-0 capitalize">{entry.difficulty}</Badge>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

<!-- ═══════════════════════════════════════════════════════════════════════
     GAME VIEW — Magma Miner
     ═══════════════════════════════════════════════════════════════════════ -->
{:else if view === 'game'}
	<MagmaMiner onBack={goToPath} onSubmitScore={handleGameScore} />
{/if}

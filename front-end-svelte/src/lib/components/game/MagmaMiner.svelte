<script lang="ts">
	import { onDestroy } from 'svelte';
	import { i18n } from '$lib/i18n/index.svelte';
	import { MagmaFlappyEngine, type GameState, type GeoPosition } from '$lib/game/engine';
	import { pickQuestion, type QuizQuestion } from '$lib/game/questions';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { animateIn, pressScale } from '$lib/motion';
	import Geo from '$lib/components/geo.svelte';
	import ArrowLeft from 'phosphor-svelte/lib/ArrowLeft';
	import confetti from 'canvas-confetti';

	interface Props {
		onBack: () => void;
		onSubmitScore: (data: { score: number; blocks_mined: number; halvings_survived: number; duration_seconds: number }) => void;
	}

	let { onBack, onSubmitScore }: Props = $props();

	const t = $derived(i18n.t.education.game);
	let locale = $derived(i18n.locale === 'es' ? 'es' : 'en') as 'en' | 'es';

	let canvasEl: HTMLCanvasElement;
	let engine: MagmaFlappyEngine | null = null;
	let gameState = $state<GameState>({ status: 'idle', score: 0, highScore: 0, distance: 0 });
	let geoPos = $state<GeoPosition>({ x: 0, y: 0, angle: 0, vy: 0 });
	let startTime = $state(0);

	// Geo SVG size in px (matches the viewBox scaling)
	const GEO_PX = 44;

	// Map game status + velocity to Geo animation state
	let geoState = $derived<'idle' | 'mining' | 'success' | 'nervous' | 'alert'>(
		gameState.status === 'dead' ? 'nervous' :
		gameState.status === 'idle' ? 'idle' :
		geoPos.vy < -3 ? 'success' :   // flapping up = happy
		geoPos.vy > 4 ? 'alert' :       // falling fast = worried
		'mining'                          // normal flight = mining
	);

	// Quiz state
	let showQuiz = $state(false);
	let currentQuiz = $state<QuizQuestion | null>(null);
	let selectedAnswer = $state<number | null>(null);
	let answerRevealed = $state(false);
	let answerCorrect = $state(false);
	let revivesUsed = $state(0);
	let usedQuestions = $state(new Set<number>());
	const MAX_REVIVES = 3;

	// ── Engine setup ──────────────────────────────────────────────────

	function initEngine() {
		if (!canvasEl || engine) return;
		engine = new MagmaFlappyEngine(canvasEl);

		engine.onStateChange = (s) => {
			gameState = { ...s };
		};

		engine.onGeoMove = (pos) => {
			geoPos = pos;
		};

		engine.onDie = (s) => {
			gameState = { ...s };

			if (revivesUsed < MAX_REVIVES) {
				// Show quiz to revive
				const pick = pickQuestion(usedQuestions);
				if (pick) {
					usedQuestions.add(pick.index);
					currentQuiz = pick.question;
					selectedAnswer = null;
					answerRevealed = false;
					answerCorrect = false;
					showQuiz = true;
					return;
				}
			}

			// No more revives or questions — game over
			finalGameOver();
		};

		engine.startIdle();

		const onResize = () => engine?.resize();
		window.addEventListener('resize', onResize);

		const onKey = (e: KeyboardEvent) => {
			if (e.code === 'Space' || e.code === 'ArrowUp') {
				e.preventDefault();
				if (showQuiz) return;
				if (gameState.status === 'idle' || gameState.status === 'running') {
					if (gameState.status === 'idle') startTime = Date.now();
					engine?.flap();
				}
			}
		};
		window.addEventListener('keydown', onKey);

		return () => {
			window.removeEventListener('resize', onResize);
			window.removeEventListener('keydown', onKey);
		};
	}

	$effect(() => {
		if (canvasEl) {
			const cleanup = initEngine();
			return cleanup;
		}
	});

	onDestroy(() => {
		engine?.destroy();
		engine = null;
	});

	// ── Handlers ──────────────────────────────────────────────────────

	function handleTap() {
		if (showQuiz) return;
		if (gameState.status === 'idle') startTime = Date.now();
		engine?.flap();
	}

	function selectQuizAnswer(idx: number) {
		if (answerRevealed) return;
		selectedAnswer = idx;
	}

	function confirmAnswer() {
		if (selectedAnswer === null || !currentQuiz) return;
		answerRevealed = true;
		answerCorrect = selectedAnswer === currentQuiz.correct;
	}

	function afterAnswer() {
		showQuiz = false;

		if (answerCorrect) {
			revivesUsed += 1;
			engine?.revive();
		} else {
			finalGameOver();
		}
	}

	function finalGameOver() {
		const duration = startTime > 0 ? Math.floor((Date.now() - startTime) / 1000) : 0;
		onSubmitScore({
			score: gameState.score,
			blocks_mined: gameState.score,
			halvings_survived: revivesUsed,
			duration_seconds: duration,
		});

		if (gameState.score >= gameState.highScore && gameState.score > 5) {
			confetti({
				particleCount: 60,
				spread: 70,
				origin: { y: 0.5 },
				colors: ['#f97316', '#f59e0b', '#eab308'],
			});
		}
	}

	function restart() {
		showQuiz = false;
		currentQuiz = null;
		revivesUsed = 0;
		usedQuestions = new Set();
		startTime = Date.now();
		engine?.start();
	}
</script>

<div class="space-y-3">
	<!-- Back button -->
	<button
		onclick={onBack}
		class="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
	>
		<ArrowLeft size={16} />
		{i18n.t.education.backToLessons}
	</button>

	<!-- Game container -->
	<div class="relative w-full rounded-2xl overflow-hidden border border-border shadow-lg select-none touch-none">
		<canvas
			bind:this={canvasEl}
			onpointerdown={handleTap}
			class="w-full block cursor-pointer"
			style="touch-action: none;"
		></canvas>

		<!-- Geo character (real SVG, positioned over canvas) -->
		{#if gameState.status === 'running' || gameState.status === 'dead'}
			<div
				class="absolute pointer-events-none"
				style="left: {geoPos.x - GEO_PX / 2}px; top: {geoPos.y - GEO_PX / 2}px; width: {GEO_PX}px; height: {GEO_PX}px; transform: rotate({geoPos.angle}deg); will-change: transform;"
			>
				<Geo state={geoState} class="w-full h-full" />
			</div>
		{/if}

		<!-- Idle overlay — tap to start -->
		{#if gameState.status === 'idle'}
			<div class="absolute inset-0 flex flex-col items-center justify-center bg-white/40 backdrop-blur-[2px]">
				<div class="text-center space-y-3" use:animateIn={{ y: [20, 0], duration: 0.5 }}>
					<Geo state="idle" class="w-20 h-20 mx-auto" />
					<h2 class="font-heading text-2xl font-bold text-foreground drop-shadow-sm">{t.title}</h2>
					<p class="text-sm text-muted-foreground">{t.tapToStart}</p>
				</div>
			</div>
		{/if}

		<!-- Quiz overlay — answer to revive -->
		{#if showQuiz && currentQuiz}
			<div class="absolute inset-0 flex items-center justify-center bg-white/60 backdrop-blur-sm p-4">
				<Card class="w-full max-w-sm ring-1 ring-orange-500/30 shadow-2xl">
					<CardContent class="pt-5 space-y-4">
						<div class="text-center space-y-2" use:animateIn={{ y: [16, 0], duration: 0.35 }}>
							{#if !answerRevealed}
								<Geo state="nervous" class="w-16 h-16 mx-auto" />
								<p class="text-xs text-muted-foreground">{t.quizRevive} ({MAX_REVIVES - revivesUsed} {t.livesLeft})</p>
							{:else if answerCorrect}
								<Geo state="success" class="w-16 h-16 mx-auto" />
								<p class="text-xs text-green-500 font-semibold">{t.correct}</p>
							{:else}
								<Geo state="nervous" class="w-16 h-16 mx-auto" />
								<p class="text-xs text-red-500 font-semibold">{t.wrong}</p>
							{/if}

							<h3 class="font-heading text-base font-bold leading-tight">
								{currentQuiz.question[locale]}
							</h3>
						</div>

						<div class="space-y-2">
							{#each currentQuiz.options[locale] as opt, j (j)}
								{@const isSelected = selectedAnswer === j}
								{@const isCorrect = j === currentQuiz.correct}
								<button
									onclick={() => selectQuizAnswer(j)}
									disabled={answerRevealed}
									class="w-full text-left px-4 py-3 rounded-xl border-2 text-sm transition-all duration-150
										{answerRevealed && isCorrect
											? 'border-green-500 bg-green-500/10 text-green-700 dark:text-green-400 font-semibold'
											: answerRevealed && isSelected && !isCorrect
											? 'border-red-500 bg-red-500/10 text-red-700 dark:text-red-400'
											: isSelected
											? 'border-orange-500 bg-orange-500/10 font-medium'
											: 'border-border hover:border-muted-foreground'}
										{answerRevealed && !isCorrect && !isSelected ? 'opacity-40' : ''}"
								>
									<span class="flex items-center gap-2.5">
										<span class="w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-bold shrink-0
											{answerRevealed && isCorrect
												? 'border-green-500 bg-green-500 text-white'
												: isSelected
												? 'border-orange-500 bg-orange-500 text-white'
												: 'border-border text-muted-foreground'}">
											{String.fromCharCode(65 + j)}
										</span>
										{opt}
									</span>
								</button>
							{/each}
						</div>

						{#if !answerRevealed}
							<div use:pressScale>
								<Button
									class="w-full h-11 font-semibold"
									disabled={selectedAnswer === null}
									onclick={confirmAnswer}
								>
									{t.checkAnswer}
								</Button>
							</div>
						{:else}
							<div use:pressScale>
								<Button
									class="w-full h-11 font-semibold {answerCorrect ? 'bg-green-600 hover:bg-green-700' : ''}"
									onclick={afterAnswer}
								>
									{answerCorrect ? t.revive : t.gameOverBtn}
								</Button>
							</div>
						{/if}
					</CardContent>
				</Card>
			</div>
		{/if}

		<!-- Game over overlay (no more revives) -->
		{#if gameState.status === 'dead' && !showQuiz}
			<div class="absolute inset-0 flex items-center justify-center bg-white/50 backdrop-blur-[2px] p-4">
				<div class="text-center space-y-4" use:animateIn={{ y: [20, 0], duration: 0.4 }}>
					<Geo state={gameState.score > 10 ? 'stacking' : 'nervous'} class="w-20 h-20 mx-auto" />
					<h2 class="font-heading text-3xl font-bold text-foreground">{gameState.score}</h2>
					<p class="text-sm text-muted-foreground">{t.best}: {gameState.highScore}</p>
					<div use:pressScale>
						<Button
							class="bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 h-11 px-8 font-semibold"
							onclick={restart}
						>
							{t.playAgain}
						</Button>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Bottom info -->
	<div class="flex items-center justify-between text-xs text-muted-foreground px-1">
		<span>{t.controls}</span>
		<span class="tabular-nums">{t.best}: <span class="font-bold text-amber-500">{gameState.highScore}</span></span>
	</div>
</div>

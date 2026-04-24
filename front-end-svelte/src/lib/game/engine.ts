/**
 * Magma Miner — Flappy Bird engine.
 * Geo flies through volcanic rock columns. Collect ₿ coins.
 * Canvas handles: background, pipes, coins, particles, Geo character.
 */

export interface GameState {
	status: 'idle' | 'running' | 'dead';
	score: number;
	highScore: number;
	distance: number;
}

export interface GeoPosition {
	x: number;
	y: number;
	angle: number;
	vy: number;
}

interface Pipe {
	x: number;
	gapY: number;
	gapH: number;
	width: number;
	passed: boolean;
	hasCoin: boolean;
	coinCollected: boolean;
}

interface Particle {
	x: number;
	y: number;
	vx: number;
	vy: number;
	life: number;
	maxLife: number;
	size: number;
	color: string;
}

// ── Constants ─────────────────────────────────────────────────────────

const GRAVITY = 0.45;
const FLAP_FORCE = -7.5;
const GEO_SIZE = 36;
const PIPE_WIDTH = 56;
const PIPE_GAP = 135;
const PIPE_SPACING = 200;
const SCROLL_SPEED = 2.5;
const COIN_RADIUS = 12;

// Colors — light/warm palette matching Magma app
const SKY_TOP = '#fef3c7';   // warm cream
const SKY_BOT = '#ffedd5';   // soft peach
const MOUNTAIN_1 = '#fed7aa'; // light orange
const MOUNTAIN_2 = '#fdba74'; // warm tangerine
const LAVA_COLOR = '#ea580c';
const PIPE_COLOR = '#d6d3d1'; // stone-300
const PIPE_HIGHLIGHT = '#e7e5e4'; // stone-200
const PIPE_DARK = '#a8a29e';  // stone-400
const COIN_COLOR = '#f59e0b';
const COIN_INNER = '#fbbf24';
const SCORE_COLOR = '#78350f'; // amber-900 for readable score on light bg

export class MagmaFlappyEngine {
	private canvas: HTMLCanvasElement;
	private ctx: CanvasRenderingContext2D;
	private w = 0;
	private h = 0;
	private dpr = 1;

	// Player
	private geoX = 0;
	private geoY = 0;
	private geoVy = 0;
	private geoAngle = 0;

	// World
	private pipes: Pipe[] = [];
	private particles: Particle[] = [];
	private scrollOffset = 0;
	private lavaOffset = 0;

	// State
	private state: GameState = { status: 'idle', score: 0, highScore: 0, distance: 0 };
	private rafId = 0;
	private lastTime = 0;

	// Mountain parallax points (generated once)
	private mountains1: number[] = [];
	private mountains2: number[] = [];

	// Callbacks
	onStateChange: ((s: GameState) => void) | null = null;
	onDie: ((s: GameState) => void) | null = null;
	onGeoMove: ((pos: GeoPosition) => void) | null = null;

	constructor(canvas: HTMLCanvasElement) {
		this.canvas = canvas;
		this.ctx = canvas.getContext('2d')!;
		this.resize();
		this.generateMountains();
	}

	// ── Public API ──────────────────────────────────────────────────────

	resize() {
		const rect = this.canvas.parentElement!.getBoundingClientRect();
		this.dpr = Math.min(window.devicePixelRatio || 1, 2);
		this.w = rect.width;
		this.h = Math.min(rect.width * 1.4, 520);
		this.canvas.width = this.w * this.dpr;
		this.canvas.height = this.h * this.dpr;
		this.canvas.style.width = `${this.w}px`;
		this.canvas.style.height = `${this.h}px`;
		this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
		this.geoX = this.w * 0.25;
	}

	startIdle() {
		this.state = { status: 'idle', score: 0, highScore: this.state.highScore, distance: 0 };
		this.geoY = this.h * 0.45;
		this.geoVy = 0;
		this.pipes = [];
		this.particles = [];
		this.scrollOffset = 0;
		this.lastTime = performance.now();
		this.emit();
		this.loop();
	}

	start() {
		this.state = { status: 'running', score: 0, highScore: this.state.highScore, distance: 0 };
		this.geoY = this.h * 0.4;
		this.geoVy = 0;
		this.geoAngle = 0;
		this.pipes = [];
		this.particles = [];
		this.scrollOffset = 0;
		this.spawnInitialPipes();
		this.lastTime = performance.now();
		this.emit();
		this.loop();
	}

	flap() {
		if (this.state.status === 'idle') {
			this.start();
		}
		if (this.state.status === 'running') {
			this.geoVy = FLAP_FORCE;
		}
	}

	revive() {
		// Resume from death position, shift Geo to safe spot
		this.state.status = 'running';
		this.geoY = this.h * 0.4;
		this.geoVy = 0;
		this.geoAngle = 0;
		// Remove the pipe that killed us
		if (this.pipes.length > 0) {
			this.pipes.shift();
		}
		this.lastTime = performance.now();
		this.emit();
		this.loop();
	}

	destroy() {
		cancelAnimationFrame(this.rafId);
	}

	getState(): GameState {
		return { ...this.state };
	}

	getGeoPos(): GeoPosition {
		return { x: this.geoX, y: this.geoY, angle: this.geoAngle, vy: this.geoVy };
	}

	getCanvasHeight(): number {
		return this.h;
	}

	setHighScore(hs: number) {
		this.state.highScore = hs;
	}

	// ── Game Loop ───────────────────────────────────────────────────────

	private loop = () => {
		const now = performance.now();
		const dt = Math.min((now - this.lastTime) / 16.667, 2); // normalize to ~60fps
		this.lastTime = now;

		this.update(dt);
		this.draw();
		this.onGeoMove?.(this.getGeoPos());

		if (this.state.status !== 'dead') {
			this.rafId = requestAnimationFrame(this.loop);
		}
	};

	private update(dt: number) {
		if (this.state.status === 'idle') {
			// Gentle float
			this.geoY = this.h * 0.45 + Math.sin(performance.now() / 600) * 12;
			this.scrollOffset += SCROLL_SPEED * 0.3 * dt;
			this.lavaOffset += 0.5 * dt;
			return;
		}

		// Running
		this.geoVy += GRAVITY * dt;
		this.geoY += this.geoVy * dt;
		this.geoAngle = Math.max(-25, Math.min(70, this.geoVy * 4));
		this.scrollOffset += SCROLL_SPEED * dt;
		this.lavaOffset += 0.8 * dt;
		this.state.distance += SCROLL_SPEED * dt;

		// Move pipes
		for (const p of this.pipes) {
			p.x -= SCROLL_SPEED * dt;
			// Score
			if (!p.passed && p.x + p.width < this.geoX) {
				p.passed = true;
				this.state.score += 1;
				this.emit();
			}
		}

		// Remove off-screen pipes, spawn new ones
		if (this.pipes.length > 0 && this.pipes[0].x + PIPE_WIDTH < -10) {
			this.pipes.shift();
		}
		if (this.pipes.length > 0) {
			const last = this.pipes[this.pipes.length - 1];
			if (last.x < this.w - PIPE_SPACING) {
				this.spawnPipe(this.w + 40);
			}
		}

		// Collision detection
		const geoL = this.geoX - GEO_SIZE / 2 + 4;
		const geoR = this.geoX + GEO_SIZE / 2 - 4;
		const geoT = this.geoY - GEO_SIZE / 2 + 4;
		const geoB = this.geoY + GEO_SIZE / 2 - 4;

		// Floor / ceiling
		if (geoB > this.h - 40 || geoT < 0) {
			this.die();
			return;
		}

		// Pipes
		for (const p of this.pipes) {
			if (geoR > p.x && geoL < p.x + p.width) {
				if (geoT < p.gapY || geoB > p.gapY + p.gapH) {
					this.die();
					return;
				}
			}

			// Coin collection
			if (p.hasCoin && !p.coinCollected) {
				const cx = p.x + p.width / 2;
				const cy = p.gapY + p.gapH / 2;
				const dx = this.geoX - cx;
				const dy = this.geoY - cy;
				if (Math.sqrt(dx * dx + dy * dy) < COIN_RADIUS + GEO_SIZE / 2 - 4) {
					p.coinCollected = true;
					this.state.score += 2;
					this.spawnCoinParticles(cx, cy);
					this.emit();
				}
			}
		}

		// Update particles
		this.particles = this.particles.filter(p => {
			p.x += p.vx * dt;
			p.y += p.vy * dt;
			p.vy += 0.15 * dt;
			p.life -= dt;
			return p.life > 0;
		});
	}

	private die() {
		this.state.status = 'dead';
		if (this.state.score > this.state.highScore) {
			this.state.highScore = this.state.score;
		}
		this.spawnDeathParticles();
		this.emit();
		this.onDie?.(this.getState());
		// One final draw
		this.draw();
	}

	// ── Pipe spawning ───────────────────────────────────────────────────

	private spawnInitialPipes() {
		for (let i = 0; i < 4; i++) {
			this.spawnPipe(this.w + 100 + i * PIPE_SPACING);
		}
	}

	private spawnPipe(x: number) {
		const minGapY = 60;
		const maxGapY = this.h - 40 - PIPE_GAP - 20;
		const gapY = minGapY + Math.random() * (maxGapY - minGapY);
		this.pipes.push({
			x,
			gapY,
			gapH: PIPE_GAP,
			width: PIPE_WIDTH,
			passed: false,
			hasCoin: Math.random() < 0.6,
			coinCollected: false,
		});
	}

	// ── Drawing ─────────────────────────────────────────────────────────

	private draw() {
		const { ctx, w, h } = this;
		ctx.clearRect(0, 0, w, h);

		this.drawSky();
		this.drawMountains();
		this.drawPipes();
		this.drawCoins();
		this.drawLava();
		this.drawParticles();
		this.drawScore();
	}

	private drawSky() {
		const { ctx, w, h } = this;
		const g = ctx.createLinearGradient(0, 0, 0, h);
		g.addColorStop(0, SKY_TOP);
		g.addColorStop(1, SKY_BOT);
		ctx.fillStyle = g;
		ctx.fillRect(0, 0, w, h);

		// Soft clouds instead of stars
		ctx.fillStyle = 'rgba(255,255,255,0.5)';
		const so = this.scrollOffset;
		const seed = 42;
		for (let i = 0; i < 6; i++) {
			const cx = (((seed * (i + 1) * 7) % 1000) / 1000 * w * 1.5 - so * 0.2 * (0.5 + i * 0.1)) % (w + 100) - 50;
			const cy = 30 + ((seed * (i + 1) * 13) % 1000) / 1000 * h * 0.25;
			const cw = 40 + (i % 3) * 25;
			const ch = 12 + (i % 2) * 6;
			ctx.beginPath();
			ctx.ellipse(cx, cy, cw, ch, 0, 0, Math.PI * 2);
			ctx.fill();
			ctx.beginPath();
			ctx.ellipse(cx - cw * 0.4, cy + 3, cw * 0.6, ch * 0.8, 0, 0, Math.PI * 2);
			ctx.fill();
			ctx.beginPath();
			ctx.ellipse(cx + cw * 0.35, cy + 2, cw * 0.5, ch * 0.7, 0, 0, Math.PI * 2);
			ctx.fill();
		}
	}

	private generateMountains() {
		// Generate mountain height profiles
		this.mountains1 = [];
		this.mountains2 = [];
		for (let i = 0; i < 20; i++) {
			this.mountains1.push(0.55 + Math.random() * 0.15);
			this.mountains2.push(0.62 + Math.random() * 0.12);
		}
	}

	private drawMountains() {
		const { ctx, w, h } = this;
		const so = this.scrollOffset;

		// Layer 1 — far mountains
		ctx.fillStyle = MOUNTAIN_1;
		ctx.beginPath();
		ctx.moveTo(0, h);
		const segW1 = w / 6;
		for (let i = 0; i <= 8; i++) {
			const x = i * segW1 - (so * 0.15) % segW1;
			const mi = ((i + Math.floor(so * 0.15 / segW1)) % this.mountains1.length + this.mountains1.length) % this.mountains1.length;
			const y = h * this.mountains1[mi];
			ctx.lineTo(x, y);
		}
		ctx.lineTo(w + 10, h);
		ctx.fill();

		// Layer 2 — near mountains
		ctx.fillStyle = MOUNTAIN_2;
		ctx.beginPath();
		ctx.moveTo(0, h);
		const segW2 = w / 5;
		for (let i = 0; i <= 7; i++) {
			const x = i * segW2 - (so * 0.3) % segW2;
			const mi = ((i + Math.floor(so * 0.3 / segW2)) % this.mountains2.length + this.mountains2.length) % this.mountains2.length;
			const y = h * this.mountains2[mi];
			ctx.lineTo(x, y);
		}
		ctx.lineTo(w + 10, h);
		ctx.fill();
	}

	private drawPipes() {
		const { ctx, h } = this;

		for (const p of this.pipes) {
			// Top pipe
			this.drawRock(p.x, 0, p.width, p.gapY);
			// Bottom pipe
			this.drawRock(p.x, p.gapY + p.gapH, p.width, h - (p.gapY + p.gapH) - 40);
		}
	}

	private drawRock(x: number, y: number, w: number, h: number) {
		if (h <= 0) return;
		const { ctx } = this;
		const r = 8; // corner radius

		// Clean pipe body
		ctx.fillStyle = PIPE_COLOR;
		ctx.beginPath();
		ctx.roundRect(x, y, w, h, r);
		ctx.fill();

		// Subtle highlight on left edge
		ctx.fillStyle = PIPE_HIGHLIGHT;
		ctx.beginPath();
		ctx.roundRect(x, y, w * 0.35, h, [r, 0, 0, r]);
		ctx.fill();

		// Border
		ctx.strokeStyle = PIPE_DARK;
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		ctx.roundRect(x, y, w, h, r);
		ctx.stroke();

		// Lip at the gap opening (wider cap)
		const lipH = 10;
		const lipW = w + 12;
		const lipX = x - 6;
		const lipY = y === 0 ? y + h - lipH : y;
		ctx.fillStyle = PIPE_COLOR;
		ctx.beginPath();
		ctx.roundRect(lipX, lipY, lipW, lipH, 4);
		ctx.fill();
		ctx.strokeStyle = PIPE_DARK;
		ctx.lineWidth = 1.5;
		ctx.beginPath();
		ctx.roundRect(lipX, lipY, lipW, lipH, 4);
		ctx.stroke();
	}

	private drawCoins() {
		const { ctx } = this;

		for (const p of this.pipes) {
			if (!p.hasCoin || p.coinCollected) continue;
			const cx = p.x + p.width / 2;
			const cy = p.gapY + p.gapH / 2;
			const pulse = 1 + Math.sin(performance.now() / 300) * 0.08;

			// Glow
			ctx.save();
			ctx.shadowColor = COIN_COLOR;
			ctx.shadowBlur = 12;

			// Outer circle
			ctx.fillStyle = COIN_COLOR;
			ctx.beginPath();
			ctx.arc(cx, cy, COIN_RADIUS * pulse, 0, Math.PI * 2);
			ctx.fill();

			// Inner circle
			ctx.fillStyle = COIN_INNER;
			ctx.beginPath();
			ctx.arc(cx, cy, (COIN_RADIUS - 3) * pulse, 0, Math.PI * 2);
			ctx.fill();

			// ₿ symbol
			ctx.shadowBlur = 0;
			ctx.fillStyle = '#92400e';
			ctx.font = `bold ${Math.round(14 * pulse)}px sans-serif`;
			ctx.textAlign = 'center';
			ctx.textBaseline = 'middle';
			ctx.fillText('₿', cx, cy + 1);
			ctx.restore();
		}
	}

	private drawLava() {
		const { ctx, w, h } = this;
		const lavaH = 40;
		const lavaY = h - lavaH;

		// Lava glow
		const glow = ctx.createLinearGradient(0, lavaY - 15, 0, lavaY);
		glow.addColorStop(0, 'rgba(234, 88, 12, 0)');
		glow.addColorStop(1, 'rgba(234, 88, 12, 0.3)');
		ctx.fillStyle = glow;
		ctx.fillRect(0, lavaY - 15, w, 15);

		// Lava surface (wavy)
		ctx.fillStyle = LAVA_COLOR;
		ctx.beginPath();
		ctx.moveTo(0, h);
		for (let x = 0; x <= w; x += 8) {
			const wave = Math.sin((x + this.lavaOffset * 40) / 30) * 4;
			ctx.lineTo(x, lavaY + wave);
		}
		ctx.lineTo(w, h);
		ctx.fill();

		// Bright top
		ctx.fillStyle = '#fb923c';
		ctx.beginPath();
		for (let x = 0; x <= w; x += 8) {
			const wave = Math.sin((x + this.lavaOffset * 40) / 30) * 4;
			ctx.lineTo(x, lavaY + wave);
		}
		for (let x = w; x >= 0; x -= 8) {
			const wave = Math.sin((x + this.lavaOffset * 40) / 30) * 4;
			ctx.lineTo(x, lavaY + wave + 4);
		}
		ctx.fill();
	}

	private drawScore() {
		if (this.state.status !== 'running') return;
		const { ctx, w } = this;

		ctx.save();
		ctx.fillStyle = SCORE_COLOR;
		ctx.strokeStyle = 'rgba(255,255,255,0.6)';
		ctx.lineWidth = 3;
		ctx.font = 'bold 36px "Space Grotesk Variable", sans-serif';
		ctx.textAlign = 'center';
		ctx.textBaseline = 'top';
		ctx.strokeText(String(this.state.score), w / 2, 20);
		ctx.fillText(String(this.state.score), w / 2, 20);
		ctx.restore();
	}

	private drawParticles() {
		const { ctx } = this;
		for (const p of this.particles) {
			const alpha = Math.max(0, p.life / p.maxLife);
			ctx.globalAlpha = alpha;
			ctx.fillStyle = p.color;
			ctx.beginPath();
			ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
			ctx.fill();
		}
		ctx.globalAlpha = 1;
	}

	// ── Particles ───────────────────────────────────────────────────────

	private spawnDeathParticles() {
		for (let i = 0; i < 20; i++) {
			this.particles.push({
				x: this.geoX,
				y: this.geoY,
				vx: (Math.random() - 0.5) * 6,
				vy: (Math.random() - 0.5) * 6,
				life: 30 + Math.random() * 20,
				maxLife: 50,
				size: 2 + Math.random() * 4,
				color: ['#e5e7eb', '#9ca3af', '#e36520', '#fbbf24'][Math.floor(Math.random() * 4)],
			});
		}
	}

	private spawnCoinParticles(cx: number, cy: number) {
		for (let i = 0; i < 8; i++) {
			this.particles.push({
				x: cx,
				y: cy,
				vx: (Math.random() - 0.5) * 4,
				vy: (Math.random() - 0.5) * 4 - 2,
				life: 20 + Math.random() * 15,
				maxLife: 35,
				size: 2 + Math.random() * 3,
				color: COIN_COLOR,
			});
		}
	}

	// ── Helpers ──────────────────────────────────────────────────────────

	private emit() {
		this.onStateChange?.(this.getState());
	}
}

<script lang="ts">
	import { priceStore } from '$lib/stores/price.svelte';
	import { Card } from '$lib/components/ui/card';
	import { CardHeader } from '$lib/components/ui/card';
	import { CardTitle } from '$lib/components/ui/card';
	import { CardContent } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Button } from '$lib/components/ui/button';
	import GrowthChart from '$lib/components/GrowthChart.svelte';
	import ComparisonChart from '$lib/components/ComparisonChart.svelte';
	import * as Dialog from '$lib/components/ui/dialog';

	let btcOwned = $state(0.0);
	let yearsToRetirement = $state<number | ''>('');
	let retirementGoal = $state<number | ''>('');
	let monthlyDCA = $state<number | ''>('');

	let hasCalculated = $state(false);
	let showComparison = $state(false);
	let comparisonChartRef: ComparisonChart;

	let errors = $state({
		years: '',
		goal: '',
		dca: ''
	});

	function toNumber(val: number | ''): number {
		return val === '' ? 0 : val;
	}

	function isValidNumber(val: number | ''): val is number {
		return val !== '';
	}

	function handleComparisonOpenChange(open: boolean) {
		showComparison = open;
		if (open && comparisonChartRef) {
			setTimeout(() => comparisonChartRef?.renderChart(), 50);
		} else if (!open && comparisonChartRef) {
			comparisonChartRef?.destroyChart();
		}
	}

	let livePrice = $derived($priceStore.price);
	let btcValueUSD = $derived(btcOwned > 0 ? btcOwned * livePrice : 0);

	interface ScenarioResult {
		name: string;
		annualRate: number;
		btcAtPrice: number;
		portfolioValue: number;
		btcNeeded: number;
		btcFaltante: number;
		covered: string;
		goalPercent: number;
		totalGain: number;
		gainPercent: number;
		multiplier: number;
		dcaBtcAccumulated: number;
	}

	let scenarios = $derived.by(() => {
		if (!livePrice || !hasCalculated || toNumber(yearsToRetirement) < 1) return [];

		const y = toNumber(yearsToRetirement);
		const g = toNumber(retirementGoal);
		const d = toNumber(monthlyDCA);

		const rateOptions = [
			{ name: 'Pesimista', annualRate: 0.04, btcPrice: 150000 },
			{ name: 'Base', annualRate: 0.07, btcPrice: 500000 },
			{ name: 'Optimista', annualRate: 0.10, btcPrice: 1000000 }
		];

		const months = y * 12;
		const dcaBtcPerMonth = d / livePrice;
		const dcaBtcAccumulated = dcaBtcPerMonth * months;
		const totalBtc = btcOwned + dcaBtcAccumulated;
		const totalInvested = d * months;

		return rateOptions.map(rate => {
			const portfolioValue = totalBtc * rate.btcPrice;
			const btcNeeded = g / rate.btcPrice;
			const btcFaltante = Math.max(0, btcNeeded - totalBtc);
			const covered = btcFaltante === 0 ? 'Sí' : 'No';
			const currentValue = btcOwned * livePrice;
			const totalGain = portfolioValue - currentValue - totalInvested;
			const gainPercent = (currentValue + totalInvested) > 0 
				? (totalGain / (currentValue + totalInvested)) * 100 
				: 0;
			const multiplier = (currentValue + totalInvested) > 0 
				? portfolioValue / (currentValue + totalInvested) 
				: 0;
			const goalPercent = g > 0 
				? (portfolioValue / g) * 100 
				: 0;

			return {
				name: rate.name,
				annualRate: rate.annualRate,
				btcAtPrice: rate.btcPrice,
				portfolioValue,
				btcNeeded,
				btcFaltante,
				covered,
				goalPercent,
				totalGain,
				gainPercent,
				multiplier,
				dcaBtcAccumulated
			} as ScenarioResult;
		});
	});

	function handleCalculate() {
		errors = { years: '', goal: '', dca: '' };
		
		if (toNumber(yearsToRetirement) < 1) {
			errors.years = 'Ingresa años válidos (mínimo 1)';
		}
		if (toNumber(retirementGoal) < 1) {
			errors.goal = 'Ingresa una meta de retiro';
		}
		if (toNumber(monthlyDCA) < 1) {
			errors.dca = 'Ingresa un monto mensual a invertir';
		}
		
		if (errors.years || errors.goal || errors.dca) {
			return;
		}
		
		hasCalculated = true;
	}

	function formatUSD(value: number): string {
		if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
		if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
		return `$${value.toFixed(0)}`;
	}

	function formatUSDFull(value: number): string {
		if (value === 0) return '$0';
		return value.toLocaleString('en-US', {
			style: 'currency',
			currency: 'USD',
			minimumFractionDigits: 0,
			maximumFractionDigits: 2
		});
	}

	function formatBTC(value: number): string {
		return value.toFixed(4);
	}

	let comparisonValues = $derived.by(() => {
		if (!livePrice || toNumber(yearsToRetirement) < 1) return null;

		const y = toNumber(yearsToRetirement);
		const g = toNumber(retirementGoal);
		const d = toNumber(monthlyDCA);

		const pBase = 500000;
		const interpolatedPriceBase = livePrice + (pBase - livePrice);

		const youDCA = btcOwned + (d / livePrice) * 12 * y;
		const youDCAValue = youDCA * interpolatedPriceBase;

		const noInvest = btcOwned * interpolatedPriceBase;

		const doubleDCA = btcOwned + ((d * 2) / livePrice) * 12 * y;
		const doubleDCAValue = doubleDCA * interpolatedPriceBase;

		const inflationValue = g * Math.pow(1.03, y);

		return {
			youDCA: youDCAValue,
			noInvest: noInvest,
			doubleDCA: doubleDCAValue,
			inflation: inflationValue,
			meta: g
		};
	});

	$effect(() => {
		priceStore.startAutoRefresh();
		return () => priceStore.stopAutoRefresh();
	});

	function handleRipple(e: MouseEvent) {
		const button = e.currentTarget as HTMLElement;
		const rect = button.getBoundingClientRect();
		const x = e.clientX - rect.left;
		const y = e.clientY - rect.top;

		const ripple = document.createElement('span');
		ripple.className = 'ripple';
		ripple.style.left = `${x}px`;
		ripple.style.top = `${y}px`;
		button.appendChild(ripple);

		const ringWave = document.createElement('span');
		ringWave.className = 'ring-wave';
		ringWave.style.left = `${x}px`;
		ringWave.style.top = `${y}px`;
		button.appendChild(ringWave);

		ripple.addEventListener('animationend', () => ripple.remove());
		ringWave.addEventListener('animationend', () => ringWave.remove());
	}
</script>

<style>
	@keyframes ripple {
		0% {
			transform: scale(0);
			opacity: 0.6;
		}
		100% {
			transform: scale(4);
			opacity: 0;
		}
	}

	@keyframes ringWave {
		0% {
			transform: translate(-50%, -50%) scale(0);
			opacity: 0.8;
		}
		100% {
			transform: translate(-50%, -50%) scale(6);
			opacity: 0;
		}
	}

	:global(.calculate-btn) {
		position: relative;
		overflow: hidden;
		animation: pulseGlow 2s ease-in-out infinite;
		transition: all 0.3s cubic-bezier(.34,1.56,.64,1);
	}

	:global(.calculate-btn:hover) {
		animation: none;
		box-shadow: 0 0 40px rgba(200, 100, 0, 0.8), 0 0 80px rgba(200, 100, 0, 0.4);
	}

	:global(.calculate-btn:hover::before) {
		content: '';
		position: absolute;
		inset: -4px;
		border: 2px solid rgba(255, 160, 50, 0.6);
		border-radius: inherit;
		animation: haloExpand 0.5s ease-out forwards;
	}

	:global(.calculate-btn:active) {
		transform: scale(0.98);
	}

	@keyframes pulseGlow {
		0%, 100% {
			box-shadow: 0 0 20px rgba(200, 100, 0, 0.3), 0 0 40px rgba(200, 100, 0, 0.1);
		}
		50% {
			box-shadow: 0 0 30px rgba(200, 100, 0, 0.6), 0 0 60px rgba(200, 100, 0, 0.3);
		}
	}

	@keyframes haloExpand {
		0% {
			inset: -2px;
			opacity: 1;
		}
		100% {
			inset: -12px;
			opacity: 0;
		}
	}

	:global(.ripple) {
		position: absolute;
		width: 10px;
		height: 10px;
		background: rgba(255, 160, 50, 0.45);
		border-radius: 50%;
		transform: translate(-50%, -50%);
		pointer-events: none;
		animation: ripple 0.6s ease-out forwards;
	}

	:global(.ring-wave) {
		position: absolute;
		width: 20px;
		height: 20px;
		border: 2px solid rgba(255, 160, 50, 0.8);
		border-radius: 50%;
		transform: translate(-50%, -50%);
		pointer-events: none;
		animation: ringWave 0.6s ease-out forwards;
	}

	@property --angle {
		syntax: '<angle>';
		initial-value: 0deg;
		inherits: false;
	}

	.price-card {
		position: relative;
		border-radius: 16px;
	}

	.price-card::before {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: 16px;
		padding: 3px;
		background: conic-gradient(from var(--angle), transparent 60%, rgba(255, 140, 30, 0.9) 75%, rgba(255, 200, 80, 1) 80%, rgba(255, 140, 30, 0.9) 85%, transparent 100%);
		animation: border-spin 3s linear infinite;
		-webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
		-webkit-mask-composite: xor;
		mask-composite: exclude;
		pointer-events: none;
	}

	.price-card-inner {
		position: relative;
		background: rgba(255, 255, 255, 0.04);
		backdrop-filter: blur(18px);
		border-radius: 13px;
		padding: 1.25rem;
		margin: 3px;
	}

	@keyframes border-spin {
		to {
			--angle: 360deg;
		}
	}

	.btc-icon {
		position: relative;
		width: 48px;
		height: 48px;
		background: #2a1800;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		animation: btc-pulse 2.2s ease-in-out infinite;
	}

	.btc-icon span {
		animation: btc-spin 2.2s ease-in-out infinite;
	}

	@keyframes btc-pulse {
		0%, 100% {
			box-shadow: 0 0 8px rgba(255, 140, 30, 0.3), 0 0 16px rgba(255, 140, 30, 0.1);
		}
		50% {
			box-shadow: 0 0 16px rgba(255, 140, 30, 0.7), 0 0 32px rgba(255, 140, 30, 0.4);
		}
	}

	@keyframes btc-spin {
		0%, 100% {
			transform: scale(1) rotate(0deg);
		}
		50% {
			transform: scale(1.06) rotate(4deg);
		}
	}

	.price-value {
		animation: price-breathe 2.2s ease-in-out infinite;
	}

	@keyframes price-breathe {
		0%, 100% {
			opacity: 1;
		}
		50% {
			opacity: 0.82;
		}
	}

	.live-dot {
		width: 8px;
		height: 8px;
		background: #22c55e;
		border-radius: 50%;
		animation: dot-pulse 1.5s ease-in-out infinite;
	}

	@keyframes dot-pulse {
		0%, 100% {
			opacity: 1;
			box-shadow: 0 0 4px rgba(34, 197, 94, 0.6);
		}
		50% {
			opacity: 0.5;
			box-shadow: 0 0 8px rgba(34, 197, 94, 0.3);
		}
	}

	@keyframes input-vibrate {
		0%, 100% { transform: translateX(0); }
		25% { transform: translateX(-1.5px); }
		75% { transform: translateX(1.5px); }
	}

	.input-glow-wrap {
		position: relative;
		border-radius: 16px;
	}

	.input-glow-wrap::before {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: 16px;
		padding: 2px;
		background: conic-gradient(from var(--angle), transparent 60%, rgba(255, 140, 30, 0.9) 75%, rgba(255, 200, 80, 1) 80%, rgba(255, 140, 30, 0.9) 85%, transparent 100%);
		animation: border-spin 3s linear infinite;
		-webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
		-webkit-mask-composite: xor;
		mask-composite: exclude;
		pointer-events: none;
	}

	.input-glow-wrap input {
		background: rgba(255, 255, 255, 0.04);
		backdrop-filter: blur(12px);
		border-radius: 14px;
		border: none;
		outline: none;
		color: inherit;
		width: 100%;
		padding: 0.5rem;
		text-align: right;
	}

	.ghost-zero {
		position: absolute;
		right: 12px;
		top: 50%;
		transform: translateY(-50%);
		color: rgba(255, 255, 255, 0.2);
		font-size: 14px;
		pointer-events: none;
		transition: opacity 0.2s ease;
	}

	.input-glow-wrap input:focus + .ghost-zero,
	.input-glow-wrap input:not([value="0"]) + .ghost-zero {
		opacity: 0;
	}

	.input-glow-wrap.pulse {
		animation: input-vibrate 0.12s ease-in-out 2;
		box-shadow: 0 0 20px rgba(255, 140, 30, 0.6);
	}

	.input-glow-wrap.pulse-green {
		box-shadow: 0 0 20px rgba(76, 175, 80, 0.5);
	}

	.input-glow-wrap.pulse-red {
		box-shadow: 0 0 20px rgba(239, 83, 80, 0.5);
	}

	.summary-card {
		padding: 1rem;
		border-radius: 12px;
		border: 2px solid transparent;
		background: rgba(255, 255, 255, 0.03);
		transition: all 0.3s cubic-bezier(.34,1.56,.64,1);
		cursor: pointer;
	}

	.summary-card:hover {
		transform: scale(1.05);
	}

	.summary-card.btc {
		border-color: rgba(247, 147, 26, 0.4);
	}

	.summary-card.btc:hover {
		border-color: rgba(247, 147, 26, 0.8);
		box-shadow: 0 0 25px rgba(247, 147, 26, 0.4);
	}

	.summary-card.investment {
		border-color: rgba(59, 130, 246, 0.4);
	}

	.summary-card.investment:hover {
		border-color: rgba(59, 130, 246, 0.8);
		box-shadow: 0 0 25px rgba(59, 130, 246, 0.4);
	}

	.summary-card.total {
		border-color: rgba(34, 197, 94, 0.4);
	}

	.summary-card.total:hover {
		border-color: rgba(34, 197, 94, 0.8);
		box-shadow: 0 0 25px rgba(34, 197, 94, 0.4);
	}

	.summary-card.goal {
		border-color: rgba(168, 85, 247, 0.4);
	}

	.summary-card.goal:hover {
		border-color: rgba(168, 85, 247, 0.8);
		box-shadow: 0 0 25px rgba(168, 85, 247, 0.4);
	}

	:global(.help-modal) {
		background: linear-gradient(160deg, #111827, #0c1420, #0a0f1a) !important;
		border: 1px solid rgba(247,147,26,0.25) !important;
		border-radius: 16px !important;
		box-shadow: 0 0 60px rgba(247,147,26,0.08), inset 0 1px 0 rgba(255,255,255,0.06) !important;
		overflow: hidden;
	}

	:global(.help-modal .hud-corners) {
		position: absolute;
		inset: 0;
		pointer-events: none;
	}

	:global(.help-modal .corner) {
		position: absolute;
		width: 40px;
		height: 40px;
	}

	:global(.help-modal .corner.top-left) { top: 0; left: 0; opacity: 0.5; }
	:global(.help-modal .corner.top-right) { top: 0; right: 0; opacity: 0.5; }
	:global(.help-modal .corner.bottom-left) { bottom: 0; left: 0; opacity: 0.3; }
	:global(.help-modal .corner.bottom-right) { bottom: 0; right: 0; opacity: 0.3; }

	:global(.help-modal .energy-line) {
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 2px;
		pointer-events: none;
	}

	:global(.help-modal .flow-line) {
		animation: flowLine 2s linear infinite;
	}

	@keyframes flowLine {
		0% { stroke-dashoffset: 200; }
		100% { stroke-dashoffset: 0; }
	}

	:global(.help-modal .header-content) {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	:global(.help-modal .btc-icon-modal) {
		animation: pulse 2.5s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { filter: drop-shadow(0 0 6px #f7931a); opacity: 1; }
		50% { filter: drop-shadow(0 0 14px #f7931a); opacity: 0.7; }
	}

	:global(.help-modal .modal-sections .section) {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		padding-left: 14px;
		border-left: 2px solid;
	}

	:global(.help-modal .modal-sections .s1) { border-left-color: rgba(247,147,26,0.6); }
	:global(.help-modal .modal-sections .s2) { border-left-color: rgba(247,147,26,0.45); }
	:global(.help-modal .modal-sections .s3) { border-left-color: rgba(247,147,26,0.35); }
	:global(.help-modal .modal-sections .s4) { border-left-color: rgba(247,147,26,0.25); }

	:global(.help-modal .section-icon) {
		width: 32px;
		height: 32px;
		background: rgba(247,147,26,0.1);
		border: 1px solid rgba(247,147,26,0.3);
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	:global(.help-modal .section-content span) {
		color: #ffffff;
		font-weight: 500;
		font-size: 13px;
	}

	:global(.help-modal .section-content p) {
		color: rgba(180,195,220,0.75);
		font-size: 12px;
	}

	:global(.help-modal .connector) {
		display: flex;
		align-items: center;
		margin-left: 24px;
		height: 16px;
	}

	:global(.help-modal .connector .dot) {
		width: 5px;
		height: 5px;
		background: #f7931a;
		border-radius: 50%;
		opacity: 0.4;
		animation: shimmer 2s ease-in-out infinite;
	}

	:global(.help-modal .connector:nth-child(2) .dot) { animation-delay: 0s; }
	:global(.help-modal .connector:nth-child(4) .dot) { animation-delay: 0.5s; }
	:global(.help-modal .connector:nth-child(6) .dot) { animation-delay: 1s; }
	:global(.help-modal .connector:nth-child(8) .dot) { animation-delay: 1.5s; }

	@keyframes shimmer {
		0%, 100% { opacity: 0.3; }
		50% { opacity: 0.8; }
	}

	:global(.help-modal .connector .line) {
		flex: 1;
		height: 1px;
		background: repeating-linear-gradient(to right, rgba(247,147,26,0.3) 0, rgba(247,147,26,0.3) 4px, transparent 4px, transparent 8px);
		margin-left: 6px;
	}

	:global(.help-modal .separator) {
		height: 1px;
		background: linear-gradient(to right, transparent, rgba(247,147,26,0.25), transparent);
		margin: 16px 0;
	}

	:global(.help-modal .dca-text) {
		color: rgba(247,147,26,0.8);
		font-style: normal;
		font-weight: 500;
	}

	.error-message {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 14px;
		background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(220,38,38,0.1));
		border: 1px solid rgba(239,68,68,0.4);
		border-radius: 10px;
		animation: shakeError 0.4s ease-out;
	}

	.error-message svg {
		flex-shrink: 0;
		color: #ef4444;
		animation: pulseError 1.5s ease-in-out infinite;
	}

	.error-message span {
		color: #fca5a5;
		font-size: 13px;
		font-weight: 500;
	}

	@keyframes shakeError {
		0%, 100% { transform: translateX(0); }
		20% { transform: translateX(-4px); }
		40% { transform: translateX(4px); }
		60% { transform: translateX(-3px); }
		80% { transform: translateX(2px); }
	}

	@keyframes pulseError {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: 0.7; transform: scale(1.1); }
	}

</style>

<div class="space-y-8">
	<div class="space-y-2">
		<h1 class="text-3xl font-bold tracking-tight">Pensiones</h1>
		<p class="text-muted-foreground">
			Planifica tu futuro financiero con Bitcoin.
		</p>
	</div>

	{#if !hasCalculated}
		<Card>
			<CardHeader>
				<div class="flex items-center justify-between">
					<CardTitle>Tu situación actual</CardTitle>
					<Dialog.Root>
						<Dialog.Trigger>
							<Button variant="ghost" size="sm">?</Button>
						</Dialog.Trigger>
						<Dialog.Content class="help-modal max-w-2xl" showCloseButton={false}>
							<Dialog.Close class="absolute top-3 right-3 text-muted-foreground hover:text-foreground transition-colors">
								<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
									<line x1="4" y1="4" x2="16" y2="16"/>
									<line x1="16" y1="4" x2="4" y2="16"/>
								</svg>
							</Dialog.Close>
							<div class="hud-corners">
								<svg class="corner top-left" viewBox="0 0 40 40"><path d="M0 20 L0 0 L20 0" fill="none" stroke="#f7931a" stroke-width="1.5"/></svg>
								<svg class="corner top-right" viewBox="0 0 40 40"><path d="M40 20 L40 0 L20 0" fill="none" stroke="#f7931a" stroke-width="1.5"/></svg>
								<svg class="corner bottom-left" viewBox="0 0 40 40"><path d="M0 20 L0 40 L20 40" fill="none" stroke="#f7931a" stroke-width="1.5"/></svg>
								<svg class="corner bottom-right" viewBox="0 0 40 40"><path d="M40 20 L40 40 L20 40" fill="none" stroke="#f7931a" stroke-width="1.5"/></svg>
							</div>
							<div class="energy-line">
								<svg width="2" height="100%">
									<line x1="1" y1="0" x2="1" y2="100%" stroke="#f7931a" stroke-width="1.5" stroke-dasharray="8 4" class="flow-line"/>
								</svg>
							</div>
							<Dialog.Header>
								<div class="header-content">
									<div class="btc-icon-modal">
										<svg width="34" height="34" viewBox="0 0 34 34">
											<circle cx="17" cy="17" r="17" fill="rgba(247,147,26,0.15)"/>
											<circle cx="17" cy="17" r="14" fill="rgba(247,147,26,0.2)"/>
											<circle cx="17" cy="17" r="11" fill="#f7931a"/>
											<text x="17" y="21" text-anchor="middle" fill="white" font-size="14" font-weight="bold">₿</text>
										</svg>
									</div>
									<Dialog.Title>¿Cómo funciona esta calculadora?</Dialog.Title>
								</div>
							</Dialog.Header>
							<div class="py-4 space-y-4">
								<div class="space-y-3 text-sm modal-sections">
									<div class="section s1">
										<div class="section-icon">
											<svg width="20" height="20" viewBox="0 0 20 20"><text x="10" y="15" text-anchor="middle" fill="#f7931a" font-size="14">₿</text></svg>
										</div>
										<div class="section-content">
											<span class="font-medium">BTC que tienes hoy</span>
											<p class="text-muted-foreground">La cantidad de Bitcoin que ya posees actualmente. Puede ser 0 si aún no tienes.</p>
										</div>
									</div>
									<div class="connector"><span class="dot"></span><span class="line"></span></div>
									<div class="section s2">
										<div class="section-icon">
											<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#f7931a" stroke-width="1.5">
												<rect x="3" y="4" width="14" height="13" rx="2"/>
												<line x1="3" y1="8" x2="17" y2="8"/>
												<line x1="7" y1="2" x2="7" y2="5"/>
												<line x1="13" y1="2" x2="13" y2="5"/>
											</svg>
										</div>
										<div class="section-content">
											<span class="font-medium">Años hasta el retiro</span>
											<p class="text-muted-foreground">El número de años que faltan para tu retiro. Mientras más tiempo, más oportunidad de acumular BTC mediante DCA.</p>
										</div>
									</div>
									<div class="connector"><span class="dot"></span><span class="line"></span></div>
									<div class="section s3">
										<div class="section-icon">
											<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#f7931a" stroke-width="1.5">
												<circle cx="10" cy="10" r="7"/>
												<circle cx="10" cy="10" r="4"/>
												<circle cx="10" cy="10" r="1" fill="#f7931a"/>
											</svg>
										</div>
										<div class="section-content">
											<span class="font-medium">Meta de retiro (USD)</span>
											<p class="text-muted-foreground">La cantidad de dinero en dólares que necesitas tener cuando te jubiles. Esta es tu meta final.</p>
										</div>
									</div>
									<div class="connector"><span class="dot"></span><span class="line"></span></div>
									<div class="section s4">
										<div class="section-icon">
											<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#f7931a" stroke-width="1.5">
												<circle cx="10" cy="10" r="7"/>
												<path d="M10 6v8M7 8.5c0-1.5 1.5-2.5 3-2.5s3 1 3 2.5-1.5 2-3 2.5-3 1-3 2.5 1.5 2.5 3 2.5 3-1 3-2.5"/>
											</svg>
										</div>
										<div class="section-content">
											<span class="font-medium">Aportación mensual (DCA)</span>
											<p class="text-muted-foreground">La cantidad de dólares que aportarás cada mes mediante Dollar Cost Averaging (DCA). Comprarás BTC automáticamente cada mes, sin importar el precio.</p>
										</div>
									</div>
								</div>
								<div class="separator"></div>
								<p class="text-xs text-muted-foreground italic">
									<span class="dca-text">DCA</span> (Dollar Cost Averaging) es una estrategia donde inviertes una cantidad fija regularmente, sin importar si el precio sube o baja. Esto reduce el impacto de la volatilidad.
								</p>
							</div>
						</Dialog.Content>
					</Dialog.Root>
				</div>
			</CardHeader>
			<CardContent class="space-y-6">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div class="space-y-2">
						<Label for="btcOwned">BTC que tienes hoy</Label>
						<div class="flex items-center gap-2">
							<div class="input-glow-wrap flex-1">
								<Input
									id="btcOwned"
									type="number"
									step="0.0001"
									bind:value={btcOwned}
									min="0"
									placeholder="0.0"
									class="w-full"
								/>
							</div>
							<span class="text-muted-foreground">BTC</span>
						</div>
					</div>

					<div class="space-y-2">
						<Label for="yearsToRetirement">Años hasta el retiro</Label>
						<div class="flex items-center gap-2">
							<div class="input-glow-wrap flex-1">
								<Input
									id="yearsToRetirement"
									type="number"
									bind:value={yearsToRetirement}
									min="0"
									max="50"
									placeholder="0"
									class="w-full"
									oninput={() => errors.years = ''}
								/>
							</div>
							<span class="text-muted-foreground">años</span>
						</div>
						{#if errors.years}
							<div class="error-message">
								<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
									<path d="M8 1.5a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-1 0v-5a.5.5 0 0 1 .5-.5zm0 12a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5zM8 15a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/>
									<path fill-rule="evenodd" d="M7.493 1.528a1 1 0 0 1 .142.053L8.5 2.46l.855-.879a1 1 0 0 1 1.29 1.542l-1.146 1.186.27.45a1 1 0 0 1-.136 1.32l-1.08 1.08a1 1 0 0 1-1.322.117l-.855-.85-1.043 1.03A1 1 0 0 1 4 7.857l3.737-3.47.848.793a1 1 0 0 1-.103 1.544L6.753 8.38l-.269.448a1 1 0 0 1-1.325.11l-1.107-1.08a1 1 0 0 1-.11-1.32l.45-.27 1.85-2.13a1 1 0 0 1 1.64.138z"/>
								</svg>
								<span>{errors.years}</span>
							</div>
						{/if}
					</div>

					<div class="space-y-2">
						<Label for="retirementGoal">Meta de retiro (USD)</Label>
						<div class="flex items-center gap-2">
							<div class="input-glow-wrap flex-1">
								<Input
									id="retirementGoal"
									type="number"
									step="10000"
									bind:value={retirementGoal}
									min="0"
									placeholder="0"
									class="w-full"
									oninput={() => errors.goal = ''}
								/>
							</div>
							<span class="text-muted-foreground">USD</span>
						</div>
						{#if errors.goal}
							<div class="error-message">
								<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
									<path d="M8 1.5a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-1 0v-5a.5.5 0 0 1 .5-.5zm0 12a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5zM8 15a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/>
									<path fill-rule="evenodd" d="M7.493 1.528a1 1 0 0 1 .142.053L8.5 2.46l.855-.879a1 1 0 0 1 1.29 1.542l-1.146 1.186.27.45a1 1 0 0 1-.136 1.32l-1.08 1.08a1 1 0 0 1-1.322.117l-.855-.85-1.043 1.03A1 1 0 0 1 4 7.857l3.737-3.47.848.793a1 1 0 0 1-.103 1.544L6.753 8.38l-.269.448a1 1 0 0 1-1.325.11l-1.107-1.08a1 1 0 0 1-.11-1.32l.45-.27 1.85-2.13a1 1 0 0 1 1.64.138z"/>
								</svg>
								<span>{errors.goal}</span>
							</div>
						{:else if toNumber(retirementGoal) > 0}
							<p class="text-sm text-amber-500/80 font-medium">
								${toNumber(retirementGoal).toLocaleString('es-MX', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
							</p>
						{/if}
					</div>

					<div class="space-y-2">
						<Label for="monthlyDCA">USD mensuales a invertir (DCA)</Label>
						<div class="flex items-center gap-2">
							<div class="input-glow-wrap flex-1">
								<Input
									id="monthlyDCA"
									type="number"
									bind:value={monthlyDCA}
									min="0"
									placeholder="0"
									class="w-full"
									oninput={() => errors.dca = ''}
								/>
							</div>
							<span class="text-muted-foreground">USD</span>
						</div>
						{#if errors.dca}
							<div class="error-message">
								<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
									<path d="M8 1.5a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-1 0v-5a.5.5 0 0 1 .5-.5zm0 12a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5zM8 15a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/>
									<path fill-rule="evenodd" d="M7.493 1.528a1 1 0 0 1 .142.053L8.5 2.46l.855-.879a1 1 0 0 1 1.29 1.542l-1.146 1.186.27.45a1 1 0 0 1-.136 1.32l-1.08 1.08a1 1 0 0 1-1.322.117l-.855-.85-1.043 1.03A1 1 0 0 1 4 7.857l3.737-3.47.848.793a1 1 0 0 1-.103 1.544L6.753 8.38l-.269.448a1 1 0 0 1-1.325.11l-1.107-1.08a1 1 0 0 1-.11-1.32l.45-.27 1.85-2.13a1 1 0 0 1 1.64.138z"/>
								</svg>
								<span>{errors.dca}</span>
							</div>
						{:else if toNumber(monthlyDCA) > 0}
							<p class="text-sm text-amber-500/80 font-medium">
								${toNumber(monthlyDCA).toLocaleString('es-MX', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
							</p>
						{/if}
					</div>
				</div>

				<div class="price-card">
					<div class="price-card-inner">
						<div class="flex items-center gap-3">
							<div class="btc-icon">
								<span class="text-2xl">₿</span>
							</div>
							<div class="flex-1">
								<p class="text-sm text-muted-foreground font-medium">Precio actual de tu BTC</p>
								<p class="price-value text-2xl font-bold text-primary tracking-tight">{formatUSDFull(btcValueUSD)}</p>
							</div>
							<div class="flex-shrink-0">
								<div class="live-dot"></div>
							</div>
						</div>
					</div>
				</div>

				<Button onclick={handleCalculate} class="calculate-btn w-full" onmouseenter={handleRipple}>
					Calcular
				</Button>
			</CardContent>
		</Card>
	{:else}
		<div class="space-y-6">
			<Button variant="outline" onclick={() => hasCalculated = false}>
				Volver a calcular
			</Button>

			<Card>
				<CardHeader>
					<div class="flex items-center justify-between">
						<CardTitle>Tu resumen</CardTitle>
						<Dialog.Root bind:open={showComparison} onOpenChange={handleComparisonOpenChange}>
							<Dialog.Trigger>
								<Button variant="outline" size="sm">Modo comparación</Button>
							</Dialog.Trigger>
							<Dialog.Content class="w-[95vw] max-w-[1800px]">
								<Dialog.Header>
									<Dialog.Title>Modo comparación</Dialog.Title>
									<Dialog.Description>
										Compara tu estrategia con otras opciones usando el precio base de $500,000.
									</Dialog.Description>
								</Dialog.Header>
								<div class="py-4 space-y-4">
									<ComparisonChart
										bind:this={comparisonChartRef}
										years={toNumber(yearsToRetirement)}
										goalValue={toNumber(retirementGoal)}
										{livePrice}
										{btcOwned}
										monthlyDCA={toNumber(monthlyDCA)}
									/>
									<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
										<div class="flex items-center gap-2">
											<div class="w-4 h-0.5 bg-blue-500"></div>
											<span class="text-sm">Tú (con DCA)</span>
											<span class="text-sm font-medium ml-auto">{comparisonValues ? formatUSD(comparisonValues.youDCA) : '-'}</span>
										</div>
										<div class="flex items-center gap-2">
											<div class="w-4 h-0.5 border-t-2 border-dashed border-gray-400"></div>
											<span class="text-sm">Sin invertir</span>
											<span class="text-sm font-medium ml-auto">{comparisonValues ? formatUSD(comparisonValues.noInvest) : '-'}</span>
										</div>
										<div class="flex items-center gap-2">
											<div class="w-4 h-0.5 border-t-2 border-dashed border-purple-500"></div>
											<span class="text-sm">Doble DCA</span>
											<span class="text-sm font-medium ml-auto">{comparisonValues ? formatUSD(comparisonValues.doubleDCA) : '-'}</span>
										</div>
										<div class="flex items-center gap-2">
											<div class="w-4 h-0.5 border-t-2 border-dashed border-red-500"></div>
											<span class="text-sm">Inflación USD</span>
											<span class="text-sm font-medium ml-auto">{comparisonValues ? formatUSD(comparisonValues.inflation) : '-'}</span>
										</div>
										<div class="flex items-center gap-2">
											<div class="w-4 h-0.5 border-t-2 border-dashed border-gray-600"></div>
											<span class="text-sm">Meta</span>
											<span class="text-sm font-medium ml-auto">{comparisonValues ? formatUSD(comparisonValues.meta) : '-'}</span>
										</div>
									</div>
								</div>
							</Dialog.Content>
						</Dialog.Root>
					</div>
				</CardHeader>
				<CardContent>
					<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
						<div class="summary-card btc text-center">
							<div class="text-2xl font-bold">{formatBTC(btcOwned)} BTC</div>
							<div class="text-sm text-muted-foreground">Tienes hoy</div>
							<div class="text-xs text-muted-foreground mt-1">≈ {formatUSDFull(btcOwned * livePrice)}</div>
						</div>
						<div class="summary-card investment text-center">
							<div class="text-2xl font-bold">{formatUSDFull(toNumber(monthlyDCA) * toNumber(yearsToRetirement) * 12)}</div>
							<div class="text-sm text-muted-foreground">Inversión total</div>
							<div class="text-xs text-muted-foreground mt-1">{toNumber(monthlyDCA)}/mes × {toNumber(yearsToRetirement) * 12} meses</div>
						</div>
						<div class="summary-card total text-center">
							<div class="text-2xl font-bold">{formatBTC(btcOwned + (toNumber(monthlyDCA) / livePrice) * toNumber(yearsToRetirement) * 12)} BTC</div>
							<div class="text-sm text-muted-foreground">BTC total al retiro</div>
							<div class="text-xs text-muted-foreground mt-1">+ {(toNumber(monthlyDCA) / livePrice * toNumber(yearsToRetirement) * 12).toFixed(4)} BTC vía DCA</div>
						</div>
						<div class="summary-card goal text-center">
							<div class="text-2xl font-bold">{formatUSDFull(toNumber(retirementGoal))}</div>
							<div class="text-sm text-muted-foreground">Meta de retiro</div>
							<div class="text-xs text-muted-foreground mt-1">{(toNumber(retirementGoal) / (btcOwned * livePrice + toNumber(monthlyDCA) * toNumber(yearsToRetirement) * 12)).toFixed(1)}x necesitas</div>
						</div>
					</div>
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<div class="flex items-center justify-between">
						<CardTitle>Tasa de retorno anual — tres escenarios</CardTitle>
						<Dialog.Root>
							<Dialog.Trigger>
								<Button variant="ghost" size="sm">?</Button>
							</Dialog.Trigger>
<Dialog.Content class="help-modal max-w-7xl" showCloseButton={false}>
								<Dialog.Close class="absolute top-3 right-3 text-muted-foreground hover:text-foreground transition-colors">
									<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
										<line x1="4" y1="4" x2="16" y2="16"/>
										<line x1="16" y1="4" x2="4" y2="16"/>
									</svg>
								</Dialog.Close>
								<div class="hud-corners">
									<svg class="corner top-left" viewBox="0 0 40 40"><path d="M0 20 L0 0 L20 0" fill="none" stroke="#f7931a" stroke-width="1.5"/></svg>
									<svg class="corner top-right" viewBox="0 0 40 40"><path d="M40 20 L40 0 L20 0" fill="none" stroke="#f7931a" stroke-width="1.5"/></svg>
									<svg class="corner bottom-left" viewBox="0 0 40 40"><path d="M0 20 L0 40 L20 40" fill="none" stroke="#f7931a" stroke-width="1.5"/></svg>
									<svg class="corner bottom-right" viewBox="0 0 40 40"><path d="M40 20 L40 40 L20 40" fill="none" stroke="#f7931a" stroke-width="1.5"/></svg>
								</div>
								<div class="energy-line">
									<svg width="2" height="100%">
										<line x1="1" y1="0" x2="1" y2="100%" stroke="#f7931a" stroke-width="1.5" stroke-dasharray="8 4" class="flow-line"/>
									</svg>
								</div>
								<Dialog.Header>
									<div class="header-content">
										<div class="btc-icon-modal">
											<svg width="34" height="34" viewBox="0 0 34 34">
												<circle cx="17" cy="17" r="17" fill="rgba(247,147,26,0.15)"/>
												<circle cx="17" cy="17" r="14" fill="rgba(247,147,26,0.2)"/>
												<circle cx="17" cy="17" r="11" fill="#f7931a"/>
												<text x="17" y="21" text-anchor="middle" fill="white" font-size="14" font-weight="bold">₿</text>
											</svg>
										</div>
										<Dialog.Title>¿Cómo funciona?</Dialog.Title>
									</div>
								</Dialog.Header>
								<div class="py-4 space-y-4">
									<div class="space-y-3 text-sm modal-sections">
										<div class="section s1">
											<div class="section-icon">
												<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#f7931a" stroke-width="1.5">
													<line x1="4" y1="6" x2="16" y2="6"/>
													<line x1="4" y1="10" x2="16" y2="10"/>
													<line x1="4" y1="14" x2="12" y2="14"/>
												</svg>
											</div>
											<div class="section-content">
												<span class="font-medium">BTC @ $XXX</span>
												<p class="text-muted-foreground">Precio proyectado del BTC en ese escenario al año de retiro.</p>
											</div>
										</div>
										<div class="connector"><span class="dot"></span><span class="line"></span></div>
										<div class="section s2">
											<div class="section-icon">
												<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#f7931a" stroke-width="1.5">
													<rect x="3" y="5" width="14" height="12" rx="2"/>
													<path d="M7 5V3.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 .5.5V5"/>
												</svg>
											</div>
											<div class="section-content">
												<span class="font-medium">Valor estimado del portafolio</span>
												<p class="text-muted-foreground">Tu BTC total × precio del escenario. Muestra cuánto valdrá tu inversión.</p>
											</div>
										</div>
										<div class="connector"><span class="dot"></span><span class="line"></span></div>
										<div class="section s3">
											<div class="section-icon">
												<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#f7931a" stroke-width="1.5">
													<polyline points="4,12 8,8 12,10 16,5"/>
													<circle cx="16" cy="5" r="2"/>
												</svg>
											</div>
											<div class="section-content">
												<span class="font-medium">Meta alcanzada</span>
												<p class="text-muted-foreground">Indica si tu portafolio llega a la meta de retiro. Muestra el porcentaje alcanzado (ej: 260%).</p>
											</div>
										</div>
										<div class="connector"><span class="dot"></span><span class="line"></span></div>
										<div class="section s4">
											<div class="section-icon">
												<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#f7931a" stroke-width="1.5">
													<circle cx="10" cy="10" r="7"/>
													<path d="M10 6v8M7 8.5c0-1.5 1.5-2.5 3-2.5s3 1 3 2.5-1.5 2-3 2.5-3 1-3 2.5 1.5 2.5 3 2.5 3-1 3-2.5"/>
												</svg>
											</div>
											<div class="section-content">
												<span class="font-medium">BTC necesario / BTC faltante</span>
												<p class="text-muted-foreground">La cantidad de BTC que necesitarías y cuánto te falta para alcanzar la meta.</p>
											</div>
										</div>
										<div class="connector"><span class="dot"></span><span class="line"></span></div>
										<div class="section s1">
											<div class="section-icon">
												<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#f7931a" stroke-width="1.5">
													<path d="M3 17l4-4 3 3 4-5 3 3"/>
													<polyline points="3,17 7,13 10,16 14,11 17,14"/>
												</svg>
											</div>
											<div class="section-content">
												<span class="font-medium">Ganancia estimada y Multiplicador</span>
												<p class="text-muted-foreground">Ganancia total en USD, porcentaje y cuántas veces crece tu inversión.</p>
											</div>
										</div>
										<div class="connector"><span class="dot"></span><span class="line"></span></div>
										<div class="section s2">
											<div class="section-icon">
												<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#f7931a" stroke-width="1.5">
													<circle cx="10" cy="17" r="2" fill="#f7931a"/>
													<circle cx="10" cy="10" r="7"/>
													<path d="M10 7v6l3 2"/>
												</svg>
											</div>
											<div class="section-content">
												<span class="font-medium">BTC acumulado vía DCA</span>
												<p class="text-muted-foreground">Cantidad de BTC comprado mediante tus aportaciones mensuales.</p>
											</div>
										</div>
									</div>
								</div>
							</Dialog.Content>
						</Dialog.Root>
					</div>
				</CardHeader>
				<CardContent class="space-y-6">
					<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
						{#each scenarios as scenario}
							<div class="p-4 border-2 rounded-lg space-y-4 transition-all duration-300 hover:scale-105 hover:-translate-y-1 cursor-pointer {scenario.name === 'Pesimista' ? 'border-red-400 hover:shadow-[0_0_30px_rgba(239,68,68,0.6),0_0_60px_rgba(239,68,68,0.3)]' : scenario.name === 'Base' ? 'border-amber-500 hover:shadow-[0_0_30px_rgba(234,179,8,0.6),0_0_60px_rgba(234,179,8,0.3)]' : 'border-green-500 hover:shadow-[0_0_30px_rgba(34,197,94,0.6),0_0_60px_rgba(34,197,94,0.3)]'}">
								<div class="flex items-center justify-between">
									<h3 class="text-lg font-semibold">{scenario.name}</h3>
								</div>

								<div class="space-y-2 text-sm">
									<div class="flex justify-between">
										<span class="text-muted-foreground">BTC @ {formatUSD(scenario.btcAtPrice)}</span>
									</div>
									<div class="flex justify-between">
										<span class="text-muted-foreground">valor estimado del portafolio ({formatBTC(scenario.portfolioValue / scenario.btcAtPrice)} BTC)</span>
									</div>
									<div class="flex justify-between">
										<span class="text-muted-foreground">Meta alcanzada</span>
										<span class="font-medium {scenario.covered === 'Sí' ? 'text-green-500' : 'text-red-500'}">
											{scenario.covered} ({Math.round(scenario.goalPercent)}%)
										</span>
									</div>
									<div class="flex justify-between">
										<span class="text-muted-foreground">BTC necesario</span>
										<span class="font-medium">{formatBTC(scenario.btcNeeded)} BTC</span>
									</div>
									<div class="flex justify-between">
										<span class="text-muted-foreground">BTC faltante</span>
										<span class="font-medium">{formatBTC(scenario.btcFaltante)} BTC</span>
									</div>
									<div class="flex justify-between">
										<span class="text-muted-foreground">Ganancia estimada</span>
										<span class="font-medium text-green-500">
											+{formatUSD(scenario.totalGain)} ({Math.round(scenario.gainPercent)}%)
										</span>
									</div>
									<div class="flex justify-between">
										<span class="text-muted-foreground">Multiplicador</span>
										<span class="font-medium">{scenario.multiplier.toFixed(1)}x</span>
									</div>
								</div>

								<div class="pt-2 border-t">
									<div class="text-xs text-muted-foreground mb-1">BTC acumulado vía DCA</div>
									<div class="text-xl font-bold">{formatBTC(scenario.dcaBtcAccumulated)} BTC</div>
								</div>
							</div>
						{/each}
					</div>
				</CardContent>
			</Card>

			<Card>
				<CardContent class="pt-6">
					<GrowthChart
						years={toNumber(yearsToRetirement)}
						goalValue={toNumber(retirementGoal)}
						{livePrice}
						{btcOwned}
						monthlyDCA={toNumber(monthlyDCA)}
					/>
				</CardContent>
			</Card>

			<p class="text-xs text-muted-foreground italic text-center">
				Precio interpolado linealmente desde el precio actual hasta la proyección. No es asesoría financiera.
			</p>
		</div>
	{/if}
</div>

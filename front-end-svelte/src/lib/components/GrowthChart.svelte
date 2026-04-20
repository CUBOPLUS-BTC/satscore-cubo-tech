<script lang="ts">
	import { onMount } from 'svelte';
	import Chart from 'chart.js/auto';
	import { i18n } from '$lib/i18n/index.svelte';

	interface ComparisonData {
		label: string;
		data: { x: number; y: number }[];
		borderColor: string;
	}

	interface Props {
		years: number;
		goalValue: number;
		livePrice: number;
		btcOwned: number;
		monthlyDCA: number;
		showComparison?: boolean;
		comparisonData?: ComparisonData[];
		chartDatasets?: any[];
	}

	let { years, goalValue, livePrice, btcOwned, monthlyDCA, showComparison = false, comparisonData = [], chartDatasets }: Props = $props();

	let canvas: HTMLCanvasElement;
	let chartInstance: Chart | null = null;

	function formatUSD(value: number): string {
		if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
		if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
		return `$${value.toFixed(0)}`;
	}

	function hexToRgba(hex: string, alpha: number): string {
		const r = parseInt(hex.slice(0, 2), 16);
		const g = parseInt(hex.slice(2, 4), 16);
		const b = parseInt(hex.slice(4, 6), 16);
		return `rgba(${r}, ${g}, ${b}, ${alpha})`;
	}

	function buildDatasets(ctx: CanvasRenderingContext2D | null, chartHeight: number) {
		if (showComparison && comparisonData.length > 0) {
			return comparisonData.map(c => {
				const color = c.borderColor;
				const gradient = ctx ? ctx.createLinearGradient(0, 0, 0, chartHeight) : null;
				if (gradient) {
					gradient.addColorStop(0, hexToRgba(color.replace(/[^a-fA-F0-9]/g, ''), 0.3));
					gradient.addColorStop(1, 'transparent');
				}
				return {
					label: c.label,
					data: c.data,
					borderColor: color,
					backgroundColor: gradient || color,
					borderDash: [] as number[],
					tension: 0.3,
					fill: true,
					pointRadius: 0,
					pointHoverRadius: 4,
					shadowBlur: 8,
					shadowColor: color,
					shadowOffsetX: 0,
					shadowOffsetY: 0
				};
			});
		}

		const scenarios = [
			{ label: i18n.t.pension.pessimistic, btcPrice: 150000, borderDash: [6, 3] as number[], color: 'rgb(220, 100, 100)', glowColor: '#dc6464' },
			{ label: i18n.t.pension.base, btcPrice: 500000, borderDash: [4, 2] as number[], color: 'rgb(234, 179, 8)', glowColor: '#eab308' },
			{ label: i18n.t.pension.optimistic, btcPrice: 1000000, borderDash: [] as number[], color: 'rgb(34, 197, 94)', glowColor: '#22c55e' }
		];

		const datasets = scenarios.map(s => {
			const data: { x: number; y: number }[] = [];
			const dcaBtcPerMonth = monthlyDCA / livePrice;

			for (let year = 0; year <= years; year++) {
				const interpolatedPrice = livePrice + (s.btcPrice - livePrice) * (year / years);
				const btcAccumulated = btcOwned + dcaBtcPerMonth * 12 * year;
				const portfolioValue = btcAccumulated * interpolatedPrice;
				data.push({ x: year, y: portfolioValue });
			}

			const gradient = ctx ? ctx.createLinearGradient(0, 0, 0, chartHeight) : null;
			if (gradient) {
				const rgbaColor = hexToRgba(s.glowColor.replace('#', ''), 0.35);
				gradient.addColorStop(0, rgbaColor);
				gradient.addColorStop(1, 'transparent');
			}

			return {
				label: s.label,
				data,
				borderDash: s.borderDash,
				borderColor: s.color,
				backgroundColor: gradient || s.color,
				tension: 0.3,
				fill: true,
				pointRadius: 0,
				pointHoverRadius: 4,
				shadowBlur: 10,
				shadowColor: s.glowColor,
				shadowOffsetX: 0,
				shadowOffsetY: 0
			};
		});

		const goalData: { x: number; y: number }[] = [];
		for (let year = 0; year <= years; year++) {
			goalData.push({ x: year, y: goalValue });
		}

		datasets.push({
			label: i18n.t.pension.totalInvested,
			data: goalData,
			borderColor: 'rgb(100, 100, 100)',
			backgroundColor: 'transparent',
			borderDash: [3, 3],
			tension: 0,
			fill: false,
			pointRadius: 0,
			pointHoverRadius: 3,
			shadowBlur: 0,
			shadowColor: 'transparent',
			shadowOffsetX: 0,
			shadowOffsetY: 0
		});

		return datasets;
	}

	function createChart() {
		if (!canvas) return;

		if (chartInstance) {
			chartInstance.destroy();
		}

		const ctx = canvas.getContext('2d');
		if (!ctx) return;

		const labels = Array.from({ length: years + 1 }, (_, i) => i);
		const chartHeight = canvas.height || 320;

		chartInstance = new Chart(ctx, {
			type: 'line',
			data: {
				labels,
				datasets: buildDatasets(ctx, chartHeight)
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: {
					intersect: false,
					mode: 'index'
				},
				plugins: {
					legend: {
						display: true,
						position: 'top',
						labels: {
							usePointStyle: true,
							padding: 20,
							font: { size: 12 }
						}
					},
					tooltip: {
						callbacks: {
							label: (ctx) => {
								return `${ctx.dataset.label}: ${formatUSD(ctx.parsed.y ?? 0)}`;
							}
						}
					}
				},
				scales: {
					x: {
						title: {
							display: true,
							text: i18n.t.pension.years
						},
						ticks: {
							stepSize: Math.ceil(years / 10) || 1
						}
					},
					y: {
						title: {
							display: true,
							text: i18n.t.pension.finalValue + ' (USD)'
						},
						ticks: {
							callback: (v) => formatUSD(Number(v))
						}
					}
				}
			}
		});
	}

	onMount(() => {
		createChart();

		return () => {
			if (chartInstance) {
				chartInstance.destroy();
			}
		};
	});

	$effect(() => {
		if (years && livePrice && goalValue) {
			createChart();
		}
	});

	$effect(() => {
		if (showComparison !== undefined && comparisonData !== undefined) {
			createChart();
		}
	});
</script>

<div class="space-y-4">
	<h3 class="text-lg font-semibold text-center">
		{i18n.t.pension.scenarioProjection}
	</h3>

	<div class="relative w-full h-80">
		<canvas bind:this={canvas}></canvas>
	</div>

	<p class="text-xs text-muted-foreground text-center italic">
		{i18n.t.pension.disclaimer}
	</p>
</div>

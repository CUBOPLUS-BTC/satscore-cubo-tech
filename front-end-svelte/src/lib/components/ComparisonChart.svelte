<script lang="ts">
	import { onMount } from 'svelte';
	import Chart from 'chart.js/auto';

	interface Props {
		years: number;
		goalValue: number;
		livePrice: number;
		btcOwned: number;
		monthlyDCA: number;
	}

	let { years, goalValue, livePrice, btcOwned, monthlyDCA }: Props = $props();

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
		const pBase = 500000;
		const interpolatedPriceBase = (year: number) => livePrice + (pBase - livePrice) * (year / years);

		const scenarios = [
			{
				label: 'Tú (con DCA)',
				color: 'rgb(59, 130, 246)',
				glowColor: '#3b82f6',
				borderDash: [] as number[],
				calc: (year: number) => {
					const btcAcc = btcOwned + (monthlyDCA / livePrice) * 12 * year;
					return btcAcc * interpolatedPriceBase(year);
				}
			},
			{
				label: 'Sin invertir',
				color: 'rgb(156, 163, 175)',
				glowColor: '#9ca3af',
				borderDash: [6, 3] as number[],
				calc: (year: number) => {
					return btcOwned * interpolatedPriceBase(year);
				}
			},
			{
				label: 'Doble DCA',
				color: 'rgb(168, 85, 247)',
				glowColor: '#a855f7',
				borderDash: [4, 2] as number[],
				calc: (year: number) => {
					const btcAcc = btcOwned + ((monthlyDCA * 2) / livePrice) * 12 * year;
					return btcAcc * interpolatedPriceBase(year);
				}
			},
			{
				label: 'Inflación USD',
				color: 'rgb(239, 68, 68)',
				glowColor: '#ef4444',
				borderDash: [2, 2] as number[],
				calc: (year: number) => {
					return goalValue * Math.pow(1.03, year);
				}
			}
		];

		const datasets = scenarios.map(s => {
			const data: { x: number; y: number }[] = [];
			for (let year = 0; year <= years; year++) {
				data.push({ x: year, y: s.calc(year) });
			}

			const gradient = ctx ? ctx.createLinearGradient(0, 0, 0, chartHeight) : null;
			if (gradient) {
				const rgbaColor = hexToRgba(s.glowColor.replace('#', ''), 0.3);
				gradient.addColorStop(0, rgbaColor);
				gradient.addColorStop(1, 'transparent');
			}

			return {
				label: s.label,
				data,
				borderColor: s.color,
				backgroundColor: gradient || s.color,
				borderDash: s.borderDash,
				tension: 0.3,
				fill: true,
				pointRadius: 0,
				pointHoverRadius: 4,
				shadowBlur: 8,
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
			label: 'Meta',
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
		const chartHeight = canvas.height || 384;

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
						display: false
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
							text: 'Años'
						},
						ticks: {
							stepSize: Math.ceil(years / 10) || 1
						}
					},
					y: {
						title: {
							display: true,
							text: 'Valor (USD)'
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

	export function destroyChart() {
		if (chartInstance) {
			chartInstance.destroy();
			chartInstance = null;
		}
	}

	export function renderChart() {
		createChart();
	}
</script>

<div class="relative w-full h-96">
	<canvas bind:this={canvas}></canvas>
</div>

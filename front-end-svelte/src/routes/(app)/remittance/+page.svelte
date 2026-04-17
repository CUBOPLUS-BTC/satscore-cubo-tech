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
	let yearsToRetirement = $state(0);
	let retirementGoal = $state(0);
	let monthlyDCA = $state(0);

	let hasCalculated = $state(false);
	let showComparison = $state(false);
	let comparisonChartRef: ComparisonChart;

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
		if (!livePrice || !hasCalculated || yearsToRetirement < 1) return [];

		const rateOptions = [
			{ name: 'Pesimista', annualRate: 0.04, btcPrice: 150000 },
			{ name: 'Base', annualRate: 0.07, btcPrice: 500000 },
			{ name: 'Optimista', annualRate: 0.10, btcPrice: 1000000 }
		];

		const months = yearsToRetirement * 12;
		const dcaBtcPerMonth = monthlyDCA / livePrice;
		const dcaBtcAccumulated = dcaBtcPerMonth * months;
		const totalBtc = btcOwned + dcaBtcAccumulated;
		const totalInvested = monthlyDCA * months;

		return rateOptions.map(rate => {
			const portfolioValue = totalBtc * rate.btcPrice;
			const btcNeeded = retirementGoal / rate.btcPrice;
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
			const goalPercent = retirementGoal > 0 
				? (portfolioValue / retirementGoal) * 100 
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
		if (!livePrice || yearsToRetirement < 1) return null;

		const pBase = 500000;
		const interpolatedPriceBase = livePrice + (pBase - livePrice);

		const youDCA = btcOwned + (monthlyDCA / livePrice) * 12 * yearsToRetirement;
		const youDCAValue = youDCA * interpolatedPriceBase;

		const noInvest = btcOwned * interpolatedPriceBase;

		const doubleDCA = btcOwned + ((monthlyDCA * 2) / livePrice) * 12 * yearsToRetirement;
		const doubleDCAValue = doubleDCA * interpolatedPriceBase;

		const inflationValue = retirementGoal * Math.pow(1.03, yearsToRetirement);

		return {
			youDCA: youDCAValue,
			noInvest: noInvest,
			doubleDCA: doubleDCAValue,
			inflation: inflationValue,
			meta: retirementGoal
		};
	});

	$effect(() => {
		priceStore.startAutoRefresh();
		return () => priceStore.stopAutoRefresh();
	});
</script>

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
						<Dialog.Content class="max-w-lg">
							<Dialog.Header>
								<Dialog.Title>¿Cómo funciona esta calculadora?</Dialog.Title>
							</Dialog.Header>
							<div class="py-4 space-y-4">
								<div class="space-y-3 text-sm">
									<div>
										<span class="font-medium">BTC que tienes hoy</span>
										<p class="text-muted-foreground">La cantidad de Bitcoin que ya posees actualmente. Puede ser 0 si aún no tienes.</p>
									</div>
									<div>
										<span class="font-medium">Años hasta el retiro</span>
										<p class="text-muted-foreground">El número de años que faltan para tu retiro. Mientras más tiempo, más oportunidad de acumular BTC mediante DCA.</p>
									</div>
									<div>
										<span class="font-medium">Meta de retiro (USD)</span>
										<p class="text-muted-foreground">La cantidad de dinero en dólares que necesitas tener cuando te jubiles. Esta es tu meta final.</p>
									</div>
									<div>
										<span class="font-medium">Aportación mensual (DCA)</span>
										<p class="text-muted-foreground">La cantidad de dólares que aportarás cada mes mediante Dollar Cost Averaging (DCA). Comprarás BTC automáticamente cada mes, sin importar el precio.</p>
									</div>
								</div>
								<p class="text-xs text-muted-foreground italic pt-2 border-t">
									DCA (Dollar Cost Averaging) es una estrategia donde inviertes una cantidad fija regularmente, sin importar si el precio sube o baja. Esto reduce el impacto de la volatilidad.
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
							<Input
								id="btcOwned"
								type="number"
								step="0.0001"
								bind:value={btcOwned}
								min="0"
							/>
							<span class="text-muted-foreground">BTC</span>
						</div>
					</div>

					<div class="space-y-2">
						<Label for="yearsToRetirement">Años hasta el retiro</Label>
						<div class="flex items-center gap-2">
							<Input
								id="yearsToRetirement"
								type="number"
								bind:value={yearsToRetirement}
								min="0"
								max="50"
							/>
							<span class="text-muted-foreground">años</span>
						</div>
					</div>

					<div class="space-y-2">
						<Label for="retirementGoal">Meta de retiro (USD)</Label>
						<div class="flex items-center gap-2">
							<Input
								id="retirementGoal"
								type="number"
								step="10000"
								bind:value={retirementGoal}
								min="0"
							/>
							<span class="text-muted-foreground">USD</span>
						</div>
						<p class="text-2xl font-bold text-primary">{formatUSDFull(retirementGoal)}</p>
					</div>

					<div class="space-y-2">
						<Label for="monthlyDCA">USD mensuales a invertir (DCA)</Label>
						<div class="flex items-center gap-2">
							<Input
								id="monthlyDCA"
								type="number"
								bind:value={monthlyDCA}
								min="0"
							/>
							<span class="text-muted-foreground">USD</span>
						</div>
					</div>
				</div>

				<div class="relative overflow-hidden bg-gradient-to-br from-primary/10 via-primary/5 to-transparent border border-primary/20 rounded-xl p-5">
					<div class="flex items-center gap-3">
						<div class="flex-shrink-0 w-12 h-12 bg-primary/15 rounded-full flex items-center justify-center">
							<span class="text-2xl">₿</span>
						</div>
						<div class="flex-1">
							<p class="text-sm text-muted-foreground font-medium">Precio actual de tu BTC</p>
							<p class="text-2xl font-bold text-primary tracking-tight">{formatUSDFull(btcValueUSD)}</p>
						</div>
						<div class="flex-shrink-0">
							<div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
						</div>
					</div>
				</div>

				<Button onclick={handleCalculate} class="w-full">
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
										years={yearsToRetirement}
										goalValue={retirementGoal}
										{livePrice}
										{btcOwned}
										monthlyDCA={monthlyDCA}
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
						<div class="p-4 bg-muted rounded-lg text-center">
							<div class="text-2xl font-bold">{formatBTC(btcOwned)} BTC</div>
							<div class="text-sm text-muted-foreground">Tienes hoy</div>
							<div class="text-xs text-muted-foreground mt-1">≈ {formatUSDFull(btcOwned * livePrice)}</div>
						</div>
						<div class="p-4 bg-muted rounded-lg text-center">
							<div class="text-2xl font-bold">{formatUSDFull(monthlyDCA * yearsToRetirement * 12)}</div>
							<div class="text-sm text-muted-foreground">Inversión total</div>
							<div class="text-xs text-muted-foreground mt-1">{monthlyDCA}/mes × {yearsToRetirement * 12} meses</div>
						</div>
						<div class="p-4 bg-muted rounded-lg text-center">
							<div class="text-2xl font-bold">{formatBTC(btcOwned + (monthlyDCA / livePrice) * yearsToRetirement * 12)} BTC</div>
							<div class="text-sm text-muted-foreground">BTC total al retiro</div>
							<div class="text-xs text-muted-foreground mt-1">+ {(monthlyDCA / livePrice * yearsToRetirement * 12).toFixed(4)} BTC vía DCA</div>
						</div>
						<div class="p-4 bg-muted rounded-lg text-center">
							<div class="text-2xl font-bold">{formatUSDFull(retirementGoal)}</div>
							<div class="text-sm text-muted-foreground">Meta de retiro</div>
							<div class="text-xs text-muted-foreground mt-1">{(retirementGoal / (btcOwned * livePrice + monthlyDCA * yearsToRetirement * 12)).toFixed(1)}x necesitas</div>
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
							<Dialog.Content class="max-w-lg">
								<Dialog.Header>
									<Dialog.Title>¿Cómo funciona?</Dialog.Title>
								</Dialog.Header>
								<div class="py-4 space-y-4">
									<div class="space-y-3 text-sm">
										<div>
											<span class="font-medium">BTC @ $XXX</span>
											<p class="text-muted-foreground">Precio proyectado del BTC en ese escenario al año de retiro.</p>
										</div>
										<div>
											<span class="font-medium">Valor estimado del portafolio</span>
											<p class="text-muted-foreground">Tu BTC total × precio del escenario. Muestra cuánto valdrá tu inversión.</p>
										</div>
										<div>
											<span class="font-medium">Meta alcanzada</span>
											<p class="text-muted-foreground">Indica si tu portafolio llega a la meta de retiro. Muestra el porcentaje alcanzado (ej: 260%).</p>
										</div>
										<div>
											<span class="font-medium">BTC necesario</span>
											<p class="text-muted-foreground">La cantidad de BTC que necesitarías tener al precio del escenario para alcanzar tu meta.</p>
										</div>
										<div>
											<span class="font-medium">BTC faltante</span>
											<p class="text-muted-foreground">Cuánto BTC te falta para alcanzar la meta. Si es 0, ya llegaste.</p>
										</div>
										<div>
											<span class="font-medium">Ganancia estimada</span>
											<p class="text-muted-foreground">Ganancia total en USD y porcentaje sobre tu inversión inicial + valor actual.</p>
										</div>
										<div>
											<span class="font-medium">Multiplicador</span>
											<p class="text-muted-foreground">Cuántas veces crece tu inversión total. Ej: 2.0x significa que duplicas tu dinero.</p>
										</div>
										<div>
											<span class="font-medium">BTC acumulado vía DCA</span>
											<p class="text-muted-foreground">Cantidad de BTC comprado mediante tus aportaciones mensuales (DCA = Dollar Cost Averaging).</p>
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
							<div class="p-4 border-2 rounded-lg space-y-4 {scenario.name === 'Pesimista' ? 'border-red-400' : scenario.name === 'Base' ? 'border-amber-500' : 'border-green-500'}">
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
						years={yearsToRetirement}
						goalValue={retirementGoal}
						{livePrice}
						{btcOwned}
						monthlyDCA={monthlyDCA}
					/>
				</CardContent>
			</Card>

			<p class="text-xs text-muted-foreground italic text-center">
				Precio interpolado linealmente desde el precio actual hasta la proyección. No es asesoría financiera.
			</p>
		</div>
	{/if}
</div>

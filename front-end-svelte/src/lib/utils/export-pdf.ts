import jsPDF from 'jspdf';
import { toPng } from 'html-to-image';
import autoTable from 'jspdf-autotable';
import type { ChannelComparison } from '$lib/models/remittance';
import type { ProjectionScenario } from '$lib/models/savings';

const BRAND_COLOR: [number, number, number] = [234, 88, 12]; // orange-600
const PAGE_MARGIN = 14;

/** jspdf-autotable augments jsPDF.prototype but doesn't export the property type */
type JsPDFWithAutoTable = jsPDF & { lastAutoTable: { finalY: number } };

const fmtUSD = (v: number) =>
  `$${v.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

const fmtUSDCents = (v: number) =>
  `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const fmtBtc = (v: number) => `${v.toFixed(6)} BTC`;

/** Static label map for savings scenario names */
const SCENARIO_LABELS: Record<string, string> = {
  conservative: 'Conservador',
  moderate: 'Moderado',
  optimistic: 'Optimista',
};

/** SVG de Geo con colores hardcodeados (sin CSS vars) para entornos fuera del DOM de la app */
const GEO_SVG = `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="100" cy="180" rx="35" ry="6" fill="rgba(0,0,0,0.08)"/>
  <rect x="45" y="80" width="110" height="90" rx="16" fill="#E5E7EB" stroke="#9CA3AF" stroke-width="4"/>
  <path d="M 55 155 L 70 155 L 75 165" fill="none" stroke="#9CA3AF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M 145 155 L 130 155 L 125 165" fill="none" stroke="#9CA3AF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
  <ellipse cx="75" cy="125" rx="7" ry="11" fill="#111827"/>
  <ellipse cx="125" cy="125" rx="7" ry="11" fill="#111827"/>
  <circle cx="72" cy="120" r="2.5" fill="#FFFFFF"/>
  <circle cx="122" cy="120" r="2.5" fill="#FFFFFF"/>
  <ellipse cx="58" cy="135" rx="7" ry="4" fill="rgba(234,88,12,0.3)"/>
  <ellipse cx="142" cy="135" rx="7" ry="4" fill="rgba(234,88,12,0.3)"/>
  <path d="M 92 133 Q 100 142 108 133" stroke="#111827" stroke-width="3.5" fill="none" stroke-linecap="round"/>
  <rect x="35" y="70" width="130" height="12" rx="6" fill="#EA580C" stroke="#9CA3AF" stroke-width="2"/>
  <path d="M 50 72 C 50 30 150 30 150 72 Z" fill="#EA580C" stroke="#9CA3AF" stroke-width="2"/>
  <path d="M 100 35 L 100 70" stroke="rgba(255,255,255,0.4)" stroke-width="4" stroke-linecap="round"/>
  <path d="M 75 42 L 75 70" stroke="rgba(255,255,255,0.25)" stroke-width="3" stroke-linecap="round"/>
  <path d="M 125 42 L 125 70" stroke="rgba(255,255,255,0.25)" stroke-width="3" stroke-linecap="round"/>
  <rect x="85" y="50" width="30" height="24" rx="4" fill="#FFFFFF" stroke="#9CA3AF" stroke-width="2"/>
  <circle cx="100" cy="62" r="8" fill="#fbbf24"/>
</svg>`;

/** Lazy cache — el SVG nunca cambia, no tiene sentido rasterizarlo más de una vez */
let _geoPngCache: string | null = null;

async function getGeoPng(): Promise<string> {
  if (_geoPngCache) return _geoPngCache;

  return new Promise((resolve, reject) => {
    const img = new Image();
    const svgBlob = new Blob([GEO_SVG], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 200;
      canvas.height = 200;
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(img, 0, 0, 200, 200);
      URL.revokeObjectURL(url);
      _geoPngCache = canvas.toDataURL('image/png');
      resolve(_geoPngCache);
    };

    img.onerror = (err) => {
      URL.revokeObjectURL(url);
      reject(err);
    };

    img.src = url;
  });
}

async function addHeader(doc: jsPDF, title: string) {
  doc.setFillColor(...BRAND_COLOR);
  doc.rect(0, 0, 210, 16, 'F');

  try {
    const geoPng = await getGeoPng();
    doc.addImage(geoPng, 'PNG', PAGE_MARGIN, 0, 14, 14);
  } catch (err) {
    console.warn('[export-pdf] Failed to render Geo mascot:', err);
  }

  doc.setTextColor(255, 255, 255);
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('Magma', PAGE_MARGIN + 16, 10);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(title, 210 - PAGE_MARGIN, 10, { align: 'right' });
  doc.setTextColor(0, 0, 0);
}

function addFooter(doc: jsPDF) {
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(7);
    doc.setTextColor(150);
    doc.text(
      `Generado por Magma · magma.app · ${new Date().toLocaleDateString('es-SV')}`,
      PAGE_MARGIN,
      doc.internal.pageSize.height - 6
    );
    doc.text(
      `${i} / ${pageCount}`,
      210 - PAGE_MARGIN,
      doc.internal.pageSize.height - 6,
      { align: 'right' }
    );
  }
}

/** Captura un elemento del DOM como PNG y lo embebe en el PDF. Devuelve el nuevo cursor Y. */
async function addDomSection(doc: jsPDF, el: HTMLElement, yStart: number): Promise<number> {
  const dataUrl = await toPng(el, { cacheBust: true, pixelRatio: 2 });
  const imgProps = doc.getImageProperties(dataUrl);
  const usableWidth = 210 - PAGE_MARGIN * 2;
  const imgHeight = (imgProps.height * usableWidth) / imgProps.width;

  if (yStart + imgHeight > 280) {
    doc.addPage();
    yStart = 20;
  }

  doc.addImage(dataUrl, 'PNG', PAGE_MARGIN, yStart, usableWidth, imgHeight);
  return yStart + imgHeight + 6;
}

export interface PensionPdfData {
  monthlySaving: number;
  snapshots: Array<{
    years: number;
    piggyBank: number;
    currentValue: number;
    btcAccumulated: number;
  }>;
  avgBuyPrice: number;
  currentBtcPrice: number;
  scenarioData: Array<{
    name: string;
    btcPrice: number;
    portfolioValue: number;
    gain: number;
    gainPct: number;
    multiplier: number;
  }> | null;
  chartEl: HTMLElement | null;
}

export async function exportPensionPdf(data: PensionPdfData) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

  await addHeader(doc, 'Plan de Pensión Bitcoin');

  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('Proyección de Retiro con Bitcoin', PAGE_MARGIN, 26);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100);
  doc.text(
    `Ahorro mensual: ${fmtUSD(data.monthlySaving)} · Precio BTC actual: ${fmtUSD(data.currentBtcPrice)}`,
    PAGE_MARGIN, 32
  );
  doc.setTextColor(0);

  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('Proyección por horizonte', PAGE_MARGIN, 42);

  autoTable(doc, {
    startY: 45,
    head: [['Horizonte', 'Guardado (alcancía)', 'Valor BTC (DCA)', 'BTC Acumulado', 'Multiplicador']],
    body: data.snapshots.map(s => {
      const mult = s.piggyBank > 0 ? (s.currentValue / s.piggyBank).toFixed(1) + 'x' : '—';
      return [`${s.years} años`, fmtUSD(s.piggyBank), fmtUSD(s.currentValue), fmtBtc(s.btcAccumulated), mult];
    }),
    styles: { fontSize: 9, cellPadding: 3 },
    headStyles: { fillColor: BRAND_COLOR },
  });

  let y = (doc as JsPDFWithAutoTable).lastAutoTable.finalY + 10;

  doc.setFontSize(9);
  doc.setTextColor(80);
  doc.text(
    `Precio promedio de compra: ${fmtUSD(data.avgBuyPrice)}  ·  Precio actual BTC: ${fmtUSD(data.currentBtcPrice)}`,
    PAGE_MARGIN, y
  );
  y += 8;
  doc.setTextColor(0);

  if (data.scenarioData) {
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.text('Escenarios de precio BTC (25 años)', PAGE_MARGIN, y);
    y += 3;

    autoTable(doc, {
      startY: y,
      head: [['Escenario', 'Precio BTC', 'Valor portafolio', 'Ganancia', 'Ganancia %', 'Multiplicador']],
      body: data.scenarioData.map(s => [
        s.name,
        `$${(s.btcPrice / 1000).toFixed(0)}K`,
        fmtUSD(s.portfolioValue),
        fmtUSD(s.gain),
        `${s.gainPct.toFixed(0)}%`,
        `${s.multiplier.toFixed(1)}x`,
      ]),
      styles: { fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: BRAND_COLOR },
    });

    y = (doc as JsPDFWithAutoTable).lastAutoTable.finalY + 10;
  }

  if (data.chartEl) {
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.text('Gráfico de proyección', PAGE_MARGIN, y);
    y += 4;
    y = await addDomSection(doc, data.chartEl, y);
  }

  doc.setFontSize(7);
  doc.setTextColor(130);
  doc.text(
    'Esto no es consejo financiero. Basado en precios históricos, el futuro puede variar. Bitcoin es volátil — solo ahorrá lo que puedas permitirte.',
    PAGE_MARGIN, y, { maxWidth: 180 }
  );

  addFooter(doc);
  doc.save(`magma-pension-${Date.now()}.pdf`);
}

export interface RemittancePdfData {
  amountUsd: number;
  frequency: string;
  bestChannel: string;
  savingsVsWorst: number;
  annualSavings: number;
  channels: ChannelComparison[];
}

export async function exportRemittancePdf(data: RemittancePdfData) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

  await addHeader(doc, 'Comparación de Remesas');

  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('Comparación de Canales de Envío', PAGE_MARGIN, 26);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100);
  doc.text(`Monto: ${fmtUSDCents(data.amountUsd)} · Frecuencia: ${data.frequency}`, PAGE_MARGIN, 32);
  doc.setTextColor(0);

  doc.setFillColor(240, 253, 244);
  doc.roundedRect(PAGE_MARGIN, 36, 182, 14, 3, 3, 'F');
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(22, 163, 74);
  doc.text(
    `Con Lightning ahorrás ${fmtUSDCents(data.savingsVsWorst)} por envío · ${fmtUSDCents(data.annualSavings)} al año`,
    PAGE_MARGIN + 4, 44
  );
  doc.setTextColor(0);

  autoTable(doc, {
    startY: 54,
    head: [['Canal', 'Comisión %', 'Comisión USD', 'Recibe', 'Tiempo', '']],
    body: data.channels.map(ch => [
      ch.name,
      `${ch.fee_percent.toFixed(2)}%`,
      fmtUSDCents(ch.fee_usd),
      fmtUSDCents(ch.amount_received),
      ch.estimated_time,
      ch.is_recommended ? '★ Mejor' : '',
    ]),
    styles: { fontSize: 9, cellPadding: 3 },
    headStyles: { fillColor: BRAND_COLOR },
    didParseCell: (cellData) => {
      if (cellData.column.index === 5 && cellData.cell.raw === '★ Mejor') {
        cellData.cell.styles.textColor = [22, 163, 74];
        cellData.cell.styles.fontStyle = 'bold';
      }
    },
  });

  addFooter(doc);
  doc.save(`magma-remesas-${Date.now()}.pdf`);
}

export interface SavingsPdfData {
  monthlyAmount: number;
  years: number;
  scenarios: ProjectionScenario[];
  traditionalValue: number;
  chartEl: HTMLElement | null;
}

export async function exportSavingsPdf(data: SavingsPdfData) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

  await addHeader(doc, 'Proyección de Ahorro Bitcoin');

  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('Proyección de Ahorro en Bitcoin', PAGE_MARGIN, 26);
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100);
  doc.text(
    `${fmtUSD(data.monthlyAmount)}/mes · ${data.years} años · Total invertido: ${fmtUSD(data.monthlyAmount * 12 * data.years)}`,
    PAGE_MARGIN, 32
  );
  doc.setTextColor(0);

  autoTable(doc, {
    startY: 38,
    head: [['Escenario', 'Retorno anual', 'Valor proyectado', 'Multiplicador', 'vs Ahorro tradicional']],
    body: data.scenarios.map(s => {
      const vsTraditional = data.traditionalValue > 0
        ? `${(s.projected_value / data.traditionalValue).toFixed(1)}x más`
        : '—';
      return [
        SCENARIO_LABELS[s.name] ?? s.name,
        `${s.annual_return_pct}%`,
        fmtUSD(s.projected_value),
        `${s.multiplier}x`,
        vsTraditional,
      ];
    }),
    styles: { fontSize: 9, cellPadding: 3 },
    headStyles: { fillColor: BRAND_COLOR },
  });

  let y = (doc as JsPDFWithAutoTable).lastAutoTable.finalY + 6;

  doc.setFontSize(9);
  doc.setTextColor(80);
  doc.text(`Ahorro tradicional (2% anual): ${fmtUSD(data.traditionalValue)}`, PAGE_MARGIN, y);
  y += 10;
  doc.setTextColor(0);

  if (data.chartEl) {
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.text('Gráfico de crecimiento', PAGE_MARGIN, y);
    y += 4;
    y = await addDomSection(doc, data.chartEl, y);
  }

  addFooter(doc);
  doc.save(`magma-ahorro-${Date.now()}.pdf`);
}

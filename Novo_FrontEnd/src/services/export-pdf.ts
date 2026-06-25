import { logger } from '@/lib/logger';
/**
 * PDF Export — gera um relatório semanal completo em PDF usando jsPDF + jspdf-autotable.
 * Executado 100% no browser — sem Edge Functions.
 */

import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

interface ExportPDFOptions {
  rows: Array<{
    nome: string;
    dias: Record<string, {
      producaoReal: number;
      entregas: number;
      diaria: number;
      taxa: number;
      valorPago: number;
      shifts?: Array<{ name: string; producaoReal: number; entregas: number }>;
    }>;
    totalDiaria: number;
    totalTaxa: number;
    taxaCorridas: number;
    adiantamentos: number;
    totalLiquido: number;
    producaoExibida: number;
    totalProducaoReal: number;
    totalEntregas: number;
    payoutTotal: number;
  }>;
  weekDates: { iso: string; dayName: string; fullLabel?: string }[];
  reportType: 'producao' | 'garantida' | 'garantida_horas';
  includeTaxaCorridas: boolean;
  companyName: string;
  periodLabel: string;
  totalGeral: number;
  txAdm?: number;
  txSupervisao?: number;
  debitoPendente?: number;
  totalALiquidar?: number;
}

function fmtBRL(val: number): string {
  return `R$ ${val.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`;
}

function fmtShort(val: number): string {
  return val.toFixed(2).replace('.', ',');
}

// Paleta de cores institucional
const BRAND = { r: 229, g: 92, b: 0 };       // #E55C00 — laranja Expresso Neves
const DARK  = { r: 24,  g: 24, b: 27 };       // zinc-900
const LIGHT = { r: 249, g: 249, b: 250 };     // zinc-50
const WHITE = { r: 255, g: 255, b: 255 };
const EMERALD = { r: 5, g: 150, b: 105 };     // verde para total líquido

export function exportToPDF(options: ExportPDFOptions): void {
  try {
  const {
    rows, weekDates, reportType, includeTaxaCorridas,
    companyName, periodLabel, totalGeral,
    txAdm = 0, txSupervisao = 0, debitoPendente = 0,
    totalALiquidar,
  } = options;

  const isProducao = reportType === 'producao';
  const effectiveTotalALiquidar = totalALiquidar ?? (totalGeral + txAdm + txSupervisao + debitoPendente);
  const emitidoEm = new Date().toLocaleDateString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });

  const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
  const pw = doc.internal.pageSize.getWidth();   // 297mm
  const ph = doc.internal.pageSize.getHeight();  // 210mm

  // ── Cabeçalho ─────────────────────────────────────────────────────────────
  // Fundo laranja
  doc.setFillColor(BRAND.r, BRAND.g, BRAND.b);
  doc.rect(0, 0, pw, 28, 'F');

  // Logo textual à esquerda
  doc.setTextColor(WHITE.r, WHITE.g, WHITE.b);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.text('NevesGo', 12, 11);
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.text('Expresso Neves', 12, 16);

  // Nome da empresa + período — centro
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.text(companyName, pw / 2, 10, { align: 'center' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.text(`Período: ${periodLabel}`, pw / 2, 16, { align: 'center' });

  // Modo + emissão — direita
  const modoBadge =
    reportType === 'producao' ? 'Produção' :
    reportType === 'garantida_horas' ? 'Garantida por Horas' : 'Garantida Mínima';
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.text(`Modo: ${modoBadge}`, pw - 12, 10, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.text(`Emitido em: ${emitidoEm}`, pw - 12, 15, { align: 'right' });

  // Linha separadora
  doc.setDrawColor(BRAND.r, BRAND.g, BRAND.b);
  doc.setLineWidth(0.4);
  doc.line(0, 28, pw, 28);

  // ── Tabela Principal ───────────────────────────────────────────────────────
  const dayHeaders = weekDates.map(d => ({ content: d.dayName + (d.fullLabel ? `\n${d.fullLabel}` : ''), styles: { halign: 'center' as const, fontSize: 7.5 } }));

  const baseColsLeft = [{ content: 'MOTOBOY', styles: { fontStyle: 'bold' as const, fontSize: 8 } }];
  const baseColsRight = isProducao
    ? [
        { content: 'DIÁRIA',    styles: { halign: 'right' as const } },
        { content: 'TX',        styles: { halign: 'right' as const } },
      ]
    : [
        { content: 'PRODUÇÃO',  styles: { halign: 'right' as const } },
        { content: 'GARANTIDO', styles: { halign: 'right' as const } },
      ];
  const txCol = includeTaxaCorridas ? [{ content: 'TX CORR.', styles: { halign: 'right' as const } }] : [];
  const fixedColsRight = [
    ...txCol,
    { content: 'ADTO.',        styles: { halign: 'right' as const } },
    { content: 'TOTAL LÍQ.',   styles: { halign: 'right' as const, fontStyle: 'bold' as const } },
  ];

  const head = [[...baseColsLeft, ...dayHeaders, ...baseColsRight, ...fixedColsRight]];

  const body = rows.map(row => {
    const cells: any[] = [{ content: row.nome, styles: { fontStyle: 'bold', fontSize: 7.5 } }];

    weekDates.forEach(d => {
      const day = row.dias[d.iso];
      const hasData = day && (day.producaoReal > 0 || day.entregas > 0 || day.diaria > 0 || (day.shifts && day.shifts.length > 0));
      if (!hasData) {
        cells.push({ content: '—', styles: { halign: 'center', textColor: [180, 180, 185], fontSize: 7 } });
      } else {
        if (reportType === 'garantida_horas' && day.shifts && day.shifts.length > 0) {
          const shiftContent = day.shifts.map((s: any) => `${s.name}: R$ ${fmtShort(s.producaoReal)}`).join('\n');
          const entContent = day.shifts.some((s: any) => s.entregas > 0) 
            ? `\n${day.shifts.filter((s:any) => s.entregas > 0).map((s:any) => `${s.name}:${s.entregas}`).join(' | ')}`
            : '';
          cells.push({
            content: shiftContent + entContent,
            styles: { halign: 'center', fontSize: 6.5, textColor: [5, 150, 105] },
          });
        } else {
          const displayVal = isProducao
            ? (day.producaoReal > 0 ? day.producaoReal : day.diaria)
            : day.valorPago;
          cells.push({
            content: `${fmtShort(displayVal)}${day.entregas > 0 ? `\n${day.entregas}ent` : ''}`,
            styles: { halign: 'center', fontSize: 7, textColor: [5, 150, 105] },
          });
        }
      }
    });

    if (isProducao) {
      cells.push(
        { content: fmtShort(row.totalDiaria), styles: { halign: 'right', fontSize: 7.5 } },
        { content: fmtShort(row.totalTaxa),   styles: { halign: 'right', fontSize: 7.5 } },
      );
    } else {
      cells.push(
        { content: fmtShort(row.totalProducaoReal), styles: { halign: 'right', fontSize: 7.5 } },
        { content: fmtShort(row.payoutTotal),        styles: { halign: 'right', fontSize: 7.5 } },
      );
    }

    if (includeTaxaCorridas) {
      cells.push({ content: fmtShort(row.taxaCorridas), styles: { halign: 'right', fontSize: 7.5 } });
    }
    cells.push(
      { content: row.adiantamentos > 0 ? `-${fmtShort(row.adiantamentos)}` : '—', styles: { halign: 'right', fontSize: 7.5, textColor: [220, 38, 38] } },
      { content: fmtShort(row.totalLiquido), styles: { halign: 'right', fontSize: 8, fontStyle: 'bold', textColor: [EMERALD.r, EMERALD.g, EMERALD.b] } },
    );

    return cells;
  });

  // Linha de totais
  const totalRowCells: any[] = [{ content: 'TOTAL', styles: { fontStyle: 'bold', fontSize: 7.5 } }];
  weekDates.forEach(d => {
    const daySum = rows.reduce((s, row) => {
      const day = row.dias[d.iso];
      if (!day) return s;
      return s + (isProducao ? (day.producaoReal > 0 ? day.producaoReal : day.diaria) : day.valorPago);
    }, 0);
    totalRowCells.push({ content: daySum > 0 ? fmtShort(daySum) : '—', styles: { halign: 'center', fontStyle: 'bold', fontSize: 7 } });
  });

  if (isProducao) {
    totalRowCells.push(
      { content: fmtShort(rows.reduce((s, r) => s + r.totalDiaria, 0)),  styles: { halign: 'right', fontStyle: 'bold' } },
      { content: fmtShort(rows.reduce((s, r) => s + r.totalTaxa, 0)),    styles: { halign: 'right', fontStyle: 'bold' } },
    );
  } else {
    totalRowCells.push(
      { content: fmtShort(rows.reduce((s, r) => s + r.totalProducaoReal, 0)), styles: { halign: 'right', fontStyle: 'bold' } },
      { content: fmtShort(rows.reduce((s, r) => s + r.payoutTotal, 0)),        styles: { halign: 'right', fontStyle: 'bold' } },
    );
  }
  if (includeTaxaCorridas) {
    totalRowCells.push({ content: fmtShort(rows.reduce((s, r) => s + r.taxaCorridas, 0)), styles: { halign: 'right', fontStyle: 'bold' } });
  }
  totalRowCells.push(
    { content: `-${fmtShort(rows.reduce((s, r) => s + r.adiantamentos, 0))}`, styles: { halign: 'right', fontStyle: 'bold', textColor: [220, 38, 38] } },
    { content: fmtShort(totalGeral), styles: { halign: 'right', fontStyle: 'bold', fontSize: 8, textColor: [EMERALD.r, EMERALD.g, EMERALD.b] } },
  );

  autoTable(doc, {
    head,
    body: [...body, totalRowCells],
    startY: 32,
    margin: { left: 8, right: 8 },
    styles: { fontSize: 7.5, cellPadding: 2, overflow: 'linebreak', font: 'helvetica' },
    headStyles: {
      fillColor: [DARK.r, DARK.g, DARK.b],
      textColor: [WHITE.r, WHITE.g, WHITE.b],
      fontSize: 7.5,
      fontStyle: 'bold',
      halign: 'center',
    },
    alternateRowStyles: { fillColor: [LIGHT.r, LIGHT.g, LIGHT.b] },
    didParseCell(data) {
      // Destaque na última linha (totais)
      if (data.row.index === body.length) {
        data.cell.styles.fillColor = [DARK.r, DARK.g, DARK.b];
        data.cell.styles.textColor = [WHITE.r, WHITE.g, WHITE.b];
        data.cell.styles.fontStyle = 'bold';
      }
    },
  });

  // ── Bloco de Resumo Financeiro ─────────────────────────────────────────────
  const finalY: number = (doc as any).lastAutoTable.finalY + 6;
  const boxW = 90;
  const boxH = 38;
  const boxX = pw - boxW - 8;

  // Fundo escuro para o bloco de resumo
  doc.setFillColor(DARK.r, DARK.g, DARK.b);
  doc.roundedRect(boxX, finalY, boxW, boxH, 3, 3, 'F');

  doc.setTextColor(WHITE.r, WHITE.g, WHITE.b);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.text('RESUMO FINANCEIRO', boxX + 4, finalY + 5);

  const lines = [
    { label: 'Logística Total (tabela)',       val: fmtBRL(totalGeral) },
    { label: 'Taxa ADM',                       val: fmtBRL(txAdm) },
    { label: 'Taxa Supervisão',                val: fmtBRL(txSupervisao) },
    { label: 'Débito Pendente',                val: fmtBRL(debitoPendente) },
  ];

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  lines.forEach((line, i) => {
    const y = finalY + 10 + i * 5;
    doc.text(line.label, boxX + 4, y);
    doc.text(line.val, boxX + boxW - 4, y, { align: 'right' });
  });

  // Linha divisória
  doc.setDrawColor(BRAND.r, BRAND.g, BRAND.b);
  doc.setLineWidth(0.3);
  doc.line(boxX + 4, finalY + 30, boxX + boxW - 4, finalY + 30);

  // Total a Liquidar em destaque
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(BRAND.r, BRAND.g, BRAND.b);
  doc.text('TOTAL A LIQUIDAR', boxX + 4, finalY + 36);
  doc.setTextColor(255, 220, 150);
  doc.text(fmtBRL(effectiveTotalALiquidar), boxX + boxW - 4, finalY + 36, { align: 'right' });

  // ── Rodapé em todas as páginas ────────────────────────────────────────────
  const totalPages = (doc.internal as any).getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.5);
    doc.setTextColor(150, 150, 160);
    doc.text(
      `NevesGo · Expresso Neves  |  ${companyName}  |  ${periodLabel}`,
      pw / 2, ph - 4, { align: 'center' }
    );
    doc.text(`Página ${i} de ${totalPages}`, pw - 8, ph - 4, { align: 'right' });
  }

  // ── Download ──────────────────────────────────────────────────────────────
  const filename = `relatorio_${companyName.replace(/\s+/g, '_')}_${periodLabel.replace(/\s+/g, '').replace(/[–\/]/g, '-')}.pdf`;
  doc.save(filename);
  } catch (err) {
    logger.error('[exportToPDF] Falha ao gerar relatório:', err);
    alert('Erro ao gerar o relatório PDF. Verifique se há dados válidos e tente novamente.');
  }
}


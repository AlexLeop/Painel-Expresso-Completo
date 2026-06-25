import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from finance.models import WeeklyStoreInvoice, WeeklyInvoiceLineItem

class InvoicePDFBuilder:
    """
    Gera as faturas B2B semanais para as Lojas (Restaurantes).
    Formata o breakdown de todas as taxas (Corridas, Mensalidade, Setup, Repasse Motorista).
    """
    def __init__(self, invoice: WeeklyStoreInvoice):
        self.invoice = invoice
        self.operator = invoice.operator
        self.store = invoice.store
        self.line_items = WeeklyInvoiceLineItem.objects.filter(invoice=invoice)
        self.buffer = io.BytesIO()

    def _format_money(self, cents: int) -> str:
        return f"R$ {(cents / 100):.2f}".replace('.', ',')

    def build(self) -> bytes:
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=18
        )
        
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']
        
        elements = []
        
        # Cabeçalho
        elements.append(Paragraph(f"FATURA DE SERVIÇOS LOGÍSTICOS - {self.operator.name}", title_style))
        elements.append(Spacer(1, 12))
        
        # Dados da Loja
        elements.append(Paragraph(f"<b>Cliente:</b> {self.store.name}", normal_style))
        elements.append(Paragraph(f"<b>Período:</b> {self.invoice.startDate.strftime('%d/%m/%Y')} até {self.invoice.endDate.strftime('%d/%m/%Y')}", normal_style))
        elements.append(Paragraph(f"<b>Fatura ID:</b> {self.invoice.id}", normal_style))
        elements.append(Spacer(1, 24))
        
        # Resumo Financeiro
        summary_data = [
            ["Resumo da Fatura", "Valor"],
            ["Produção Líquida (Entregas)", self._format_money(self.invoice.totalNetProducaoCents)],
            ["Garantidas (Diárias/Horas)", self._format_money(self.invoice.totalNetGarantidaCents)],
            ["Taxa Administrativa do Operador", self._format_money(self.invoice.administrativeFeeCents)],
            ["Taxa de Supervisão/Software", self._format_money(self.invoice.supervisionFeeCents)],
            ["Débitos Anteriores (Rollover)", self._format_money(self.invoice.pendingDebitCarriedCents)],
            ["TOTAL A PAGAR", self._format_money(self.invoice.totalCents)]
        ]
        
        t_summary = Table(summary_data, colWidths=[350, 150])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold') # Bold na ultima linha
        ]))
        
        elements.append(t_summary)
        elements.append(Spacer(1, 36))
        
        # Breakdown Line Items
        elements.append(Paragraph("<b>Detalhamento de Cobranças (Breakdown)</b>", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        item_data = [["Data", "Motorista", "Descrição", "Valor"]]
        for item in self.line_items:
            data_str = item.businessDate.strftime('%d/%m/%Y') if item.businessDate else "N/A"
            driver_name = item.driver.name if item.driver else "N/A"
            item_data.append([
                data_str,
                driver_name,
                item.description,
                self._format_money(item.amountCents)
            ])
            
        t_items = Table(item_data, colWidths=[70, 120, 230, 80])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(t_items)
        elements.append(Spacer(1, 48))
        
        # Rodapé PIX / Boleto (Dummy para exemplo)
        if self.invoice.pixCopyPaste:
            elements.append(Paragraph("<b>Chave PIX (Copia e Cola):</b>", normal_style))
            elements.append(Paragraph(self.invoice.pixCopyPaste, normal_style))
        elif self.invoice.barcode:
            elements.append(Paragraph("<b>Código de Barras do Boleto:</b>", normal_style))
            elements.append(Paragraph(self.invoice.barcode, normal_style))
            
        doc.build(elements)
        
        pdf_bytes = self.buffer.getvalue()
        self.buffer.close()
        return pdf_bytes

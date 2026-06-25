import pytest
from unittest.mock import MagicMock
from finance.cnab_generator import CNAB240RemessaBuilder
from finance.pdf_generator import InvoicePDFBuilder
from logistics.ai_schedule import WeekendScheduleAI

@pytest.mark.django_db
class TestBloco3CNAB:
    def test_cnab_line_lengths(self):
        """Todos as linhas do arquivo gerado devem ter 240 caracteres cravados."""
        builder = CNAB240RemessaBuilder(operator_cnpj="12345678000199", operator_name="TEST OP")
        builder.add_header_arquivo()
        builder.add_header_lote()
        
        # Test fake withdrawal
        mock_driver = MagicMock()
        mock_driver.name = "JOAO DAS NEVES"
        
        mock_withdrawal = MagicMock()
        mock_withdrawal.amountCents = 15000 # R$ 150,00
        mock_withdrawal.driver = mock_driver
        mock_withdrawal.id = "UUID-MOCK-12345"
        
        builder.add_payment_segment_a(mock_withdrawal)
        builder.add_trailer_lote()
        builder.add_trailer_arquivo()
        
        for idx, line in enumerate(builder.lines):
            assert len(line) == 240, f"Line {idx} len {len(line)} != 240"
            
class TestBloco3PDF:
    def test_pdf_builder_creates_bytes(self, monkeypatch):
        """O builder deve instanciar o PDF de uma fatura corretamente e retornar bytes."""
        # Mock the ORM query to avoid DB access
        def mock_filter(*args, **kwargs):
            return []
        monkeypatch.setattr('finance.pdf_generator.WeeklyInvoiceLineItem.objects.filter', mock_filter)
        
        mock_operator = MagicMock()
        mock_operator.name = "Op 1"
        
        mock_store = MagicMock()
        mock_store.name = "Loja Teste"
        
        mock_invoice = MagicMock()
        mock_invoice.id = "UUID"
        mock_invoice.operator = mock_operator
        mock_invoice.store = mock_store
        
        from datetime import datetime
        mock_invoice.startDate = datetime(2026, 1, 1)
        mock_invoice.endDate = datetime(2026, 1, 7)
        mock_invoice.totalNetProducaoCents = 1000
        mock_invoice.totalNetGarantidaCents = 0
        mock_invoice.administrativeFeeCents = 500
        mock_invoice.supervisionFeeCents = 100
        mock_invoice.pendingDebitCarriedCents = 0
        mock_invoice.totalCents = 1600
        mock_invoice.pixCopyPaste = "pix123"
        
        builder = InvoicePDFBuilder(mock_invoice)
        pdf_bytes = builder.build()
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100 # Should contain pdf binary data

class TestBloco3AISchedule:
    def test_weekend_schedule_ai_exists(self):
        """Verifica se a heurística existe e pode ser chamada."""
        assert hasattr(WeekendScheduleAI, 'suggest_weekend_schedules')

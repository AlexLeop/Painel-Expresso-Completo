from typing import List
from datetime import datetime
from finance.models import WithdrawalRequest


class CNAB240RemessaBuilder:
    """
    Construtor leve e determinístico de arquivos de remessa bancária
    no padrão FEBRABAN CNAB 240 focado em Transferências (PIX/TED).
    """

    def __init__(self, operator_cnpj: str, operator_name: str, bank_code: str = "341"):
        self.operator_cnpj = operator_cnpj.zfill(14)[:14]
        self.operator_name = operator_name.ljust(30)[:30]
        self.bank_code = bank_code.zfill(3)[:3]
        self.lines: List[str] = []
        self.lote_sequencial = 1
        self.registro_sequencial = 1
        self.total_amount_cents = 0

    def _pad(self, value, length: int, pad_char: str = " ", align: str = "left") -> str:
        value = str(value)
        if len(value) > length:
            return value[:length]
        if align == "left":
            return value.ljust(length, pad_char)
        return value.rjust(length, pad_char)

    def add_header_arquivo(self):
        # 000: Banco, 0000: Lote(0000), 0: Registro(0),
        # Cnpj, Nome, Data, etc. Total 240 posições.
        now = datetime.now()
        line = (
            f"{self.bank_code}"  # 001-003: Código do Banco
            f"0000"  # 004-007: Lote de Arquivo
            f"0"  # 008-008: Tipo de Registro (0=Header Arquivo)
            f"{self._pad('', 9)}"  # 009-017: Branco
            f"2"  # 018-018: Tipo Inscrição (2=CNPJ)
            f"{self._pad(self.operator_cnpj, 14, '0', 'right')}"  # 019-032: CNPJ
            f"{self._pad('', 20)}"  # 033-052: Convênio/Conta
            f"{self.operator_name}"  # 053-082: Nome da Empresa
            f"{self._pad('NOME DO BANCO', 30)}"  # 083-112: Nome do Banco
            f"{self._pad('', 10)}"  # 113-122: Branco
            f"1"  # 123-123: Remessa(1)/Retorno(2)
            f"{now.strftime('%d%m%Y')}"  # 124-131: Data Geracao
            f"{now.strftime('%H%M%S')}"  # 132-137: Hora Geracao
            f"{self._pad('000001', 6)}"  # 138-143: Seq. Arquivo
            f"080"  # 144-146: Versao Layout
            f"{self._pad('', 5)}"  # 147-151: Densidade
            f"{self._pad('', 20)}"  # 152-171: Reservado Banco
            f"{self._pad('', 20)}"  # 172-191: Reservado Empresa
            f"{self._pad('', 29)}"  # 192-220: Branco
            f"{self._pad('', 20)}"  # 221-240: Branco
        )
        assert len(line) == 240, f"Header line length is {len(line)} != 240"
        self.lines.append(line)

    def add_header_lote(self):
        line = (
            f"{self.bank_code}"  # 001-003: Banco
            f"0001"  # 004-007: Lote Servico
            f"1"  # 008-008: Header Lote (1)
            f"C"  # 009-009: Operacao (C=Credito)
            f"20"  # 010-011: Servico (20=Pagamento Fornecedor)
            f"01"  # 012-013: Forma Pagamento (01=Credito Conta, 41=PIX)
            f"040"  # 014-016: Versao Layout Lote
            f"{self._pad('', 1)}"  # 017-017: Branco
            f"2"  # 018-018: Inscrição(2=CNPJ)
            f"{self._pad(self.operator_cnpj, 14, '0', 'right')}"  # 019-032: CNPJ
            f"{self._pad('', 20)}"  # 033-052: Convenio
            f"{self._pad('', 20)}"  # 053-072: Branco
            f"{self.operator_name}"  # 073-102: Nome Empresa
            f"{self._pad('', 40)}"  # 103-142: Mensagem
            f"{self._pad('', 40)}"  # 143-182: Endereco Empresa
            f"{self._pad('', 48)}"  # 183-230: Branco
            f"{self._pad('', 10)}"  # 231-240: Ocorrencias
        )
        assert len(line) == 240, f"Header Lote length is {len(line)} != 240"
        self.lines.append(line)

    def add_payment_segment_a(self, withdrawal: WithdrawalRequest):
        amount_fmt = self._pad(str(withdrawal.amountCents), 15, "0", "right")
        name_fmt = self._pad(
            withdrawal.driver.name if withdrawal.driver.name else "MOTORISTA", 30
        )

        line = (
            f"{self.bank_code}"  # 001-003: Banco
            f"0001"  # 004-007: Lote
            f"3"  # 008-008: Tipo Registro(3)
            f"{self._pad(str(self.registro_sequencial), 5, '0', 'right')}"  # 009-013: Num Seq Registro
            f"A"  # 014-014: Segmento A
            f"0"  # 015-015: Movimento(0=Inclusao)
            f"00"  # 016-017: Codigo Instrucao Movimento
            f"{self._pad('000', 3)}"  # 018-020: Camara Compensacao
            f"{self._pad('00000', 5)}"  # 021-025: Banco Favorecido
            f"{self._pad('', 20)}"  # 026-045: Conta Favorecido
            f"{name_fmt}"  # 046-075: Nome Favorecido
            f"{self._pad(str(withdrawal.id), 20)}"  # 076-095: Seu Numero
            f"{datetime.now().strftime('%d%m%Y')}"  # 096-103: Data Pagamento
            f"BRL"  # 104-106: Moeda
            f"{self._pad('0', 15, '0', 'right')}"  # 107-121: Quantidade Moeda
            f"{amount_fmt}"  # 122-136: Valor Pagamento (Cents -> Sem decimais pq ja é integer)
            f"{self._pad(str(withdrawal.amountCents), 15, '0', 'right')}"  # 137-151: Nosso Numero / Valor Real
            f"{self._pad('', 20)}"  # 152-171: Data Real
            f"{self._pad('', 22)}"  # 172-193: Valor Real
            f"{self._pad('', 47)}"  # 194-240: Outros / Informacao PIX (Restante)
        )
        assert len(line) == 240, f"Segment A length is {len(line)} != 240"
        self.lines.append(line)
        self.registro_sequencial += 1
        self.total_amount_cents += withdrawal.amountCents

    def add_trailer_lote(self):
        line = (
            f"{self.bank_code}"  # 001-003: Banco
            f"0001"  # 004-007: Lote
            f"5"  # 008-008: Tipo Registro (5=Trailer Lote)
            f"{self._pad('', 9)}"  # 009-017: Branco
            f"{self._pad(str(self.registro_sequencial + 1), 6, '0', 'right')}"  # 018-023: Qtde Registros Lote
            f"{self._pad(str(self.total_amount_cents), 18, '0', 'right')}"  # 024-041: Somatoria Valores
            f"{self._pad('0', 18, '0', 'right')}"  # 042-059: Somatoria Moedas
            f"{self._pad('', 171)}"  # 060-230: Branco
            f"{self._pad('', 10)}"  # 231-240: Ocorrencias
        )
        assert len(line) == 240, f"Trailer Lote length is {len(line)} != 240"
        self.lines.append(line)

    def add_trailer_arquivo(self):
        line = (
            f"{self.bank_code}"  # 001-003: Banco
            f"9999"  # 004-007: Lote (9999)
            f"9"  # 008-008: Registro (9=Trailer Arquivo)
            f"{self._pad('', 9)}"  # 009-017: Branco
            f"{self._pad('1', 6, '0', 'right')}"  # 018-023: Qtde Lotes Arquivo
            f"{self._pad(str(self.registro_sequencial + 3), 6, '0', 'right')}"  # 024-029: Qtde Registros Arquivo
            f"{self._pad('', 6)}"  # 030-035: Qtde Contas Conciliacao
            f"{self._pad('', 205)}"  # 036-240: Branco
        )
        assert len(line) == 240, f"Trailer Arquivo length is {len(line)} != 240"
        self.lines.append(line)

    def build(self, withdrawals: List[WithdrawalRequest]) -> str:
        self.add_header_arquivo()
        self.add_header_lote()
        for w in withdrawals:
            self.add_payment_segment_a(w)
        self.add_trailer_lote()
        self.add_trailer_arquivo()

        return "\n".join(self.lines) + "\n"

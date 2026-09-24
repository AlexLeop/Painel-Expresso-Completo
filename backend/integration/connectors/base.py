from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID


@dataclass(frozen=True)
class DeliveryStop:
    """Representa um ponto de entrega (dropoff) com dados de endereço e cliente."""
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    customer_name: str = ""
    customer_phone: Optional[str] = None
    instructions: Optional[str] = None


@dataclass(frozen=True)
class OrderIntent:
    """
    Formato canônico normalizado que todo connector produz.
    Contrato único entre os conectores externos e a criação de corridas (Order).
    """
    integration_id: UUID
    external_order_id: str
    idempotency_key: str  # e.g., "{connector_slug}:{external_order_id}"

    # Origem (Coleta / Loja)
    pickup_store_id: UUID
    pickup_address: str
    pickup_lat: Optional[float] = None
    pickup_lng: Optional[float] = None
    pickup_instructions: Optional[str] = None

    # Destino(s) da Entrega
    deliveries: List[DeliveryStop] = field(default_factory=list)

    # Financeiro & Pagamento
    total_amount_cents: int = 0
    delivery_fee_cents: int = 0
    distance_meters: Optional[int] = None
    payment_method: str = "online"  # "online", "cash", "card_on_delivery"

    # Cliente & Itens
    customer_name: str = ""
    customer_phone: Optional[str] = None
    items_summary: str = ""
    notes: Optional[str] = None

    # Cronograma / SLA
    scheduled_for: Optional[datetime] = None
    estimated_prep_minutes: Optional[int] = None

    # Rastreabilidade
    source_platform: str = ""
    raw_payload_ref: str = ""


class BaseConnector(ABC):
    """
    Interface abstrata que todo conector de plataforma (Generic, iFood, Saipos, etc.)
    deve implementar para integrar com o Hub de Integrações.
    """

    slug: str = ""
    name: str = ""

    @abstractmethod
    def verify_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        integration: Any,
    ) -> bool:
        """
        Verifica a autenticidade do webhook (HMAC, Token, API Key).
        Retorna True se legítimo, False caso contrário (gerará 401).
        """
        ...

    @abstractmethod
    def parse_payload(
        self,
        body: bytes,
        content_type: str = "application/json",
    ) -> dict[str, Any]:
        """
        Converte os bytes do payload recebido em dicionário Python.
        Levanta ValueError se malformado.
        """
        ...

    @abstractmethod
    def normalize(
        self,
        parsed: dict[str, Any],
        integration: Any,
    ) -> OrderIntent:
        """
        Mapeia o payload proprietário do conector para o formato padronizado OrderIntent.
        Levanta ValueError se faltarem campos obrigatórios.
        """
        ...

    @abstractmethod
    def compute_dedup_key(self, parsed: dict[str, Any]) -> str:
        """
        Gera uma chave única de deduplicação a partir do payload parseado.
        """
        ...

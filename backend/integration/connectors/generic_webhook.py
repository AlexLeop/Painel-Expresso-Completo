import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any, Optional

from .base import BaseConnector, DeliveryStop, OrderIntent

logger = logging.getLogger(__name__)


class GenericWebhookConnector(BaseConnector):
    """
    Conector genérico de webhooks com assinatura HMAC-SHA256.
    Permite que qualquer PDV, cardápio digital ou sistema proprietário
    envie pedidos padronizados diretamente para o Expresso Neves.
    """

    slug = "generic-webhook"
    name = "Webhook Genérico"

    def verify_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        integration: Any,
    ) -> bool:
        """
        Verifica a assinatura HMAC-SHA256 no header X-Webhook-Signature.
        Formato aceito: 'sha256=<hex>' ou '<hex>'.
        """
        # Obter o segredo configurado na integração (descriptografado em memória)
        secret = (
            (integration.get_webhook_secret() if hasattr(integration, "get_webhook_secret") else None)
            or (integration.get_client_secret() if hasattr(integration, "get_client_secret") else None)
            or (integration.get_api_key() if hasattr(integration, "get_api_key") else None)
            or getattr(integration, "webhook_secret", None)
        )
        if not secret:
            logger.warning("GenericWebhook: integração %s não possui webhook_secret configurado.", getattr(integration, "id", None))
            return False

        # Normalizar headers para busca case-insensitive
        header_map = {k.lower(): v for k, v in headers.items()}
        signature_header = (
            header_map.get("x-webhook-signature")
            or header_map.get("x-signature")
            or header_map.get("x-hub-signature-256")
        )

        if not signature_header:
            logger.warning("GenericWebhook: cabeçalho de assinatura ausente.")
            return False

        raw_sig = signature_header.strip()
        if raw_sig.startswith("sha256="):
            received_hash = raw_sig[7:].strip()
        else:
            received_hash = raw_sig

        # Computar HMAC-SHA256 sobre os bytes exatos do body
        computed_hash = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed_hash.lower(), received_hash.lower())

    def parse_payload(
        self,
        body: bytes,
        content_type: str = "application/json",
    ) -> dict[str, Any]:
        """Parseia o payload JSON do body."""
        if "application/json" not in content_type.lower():
            raise ValueError("Content-Type deve ser application/json.")
        try:
            text = body.decode("utf-8")
            return json.loads(text)
        except Exception as e:
            raise ValueError(f"Payload JSON inválido: {str(e)}")

    def compute_dedup_key(self, parsed: dict[str, Any]) -> str:
        """Chave de deduplicação idempotente."""
        order_id = str(parsed.get("order_id") or parsed.get("external_order_id") or "")
        return f"{self.slug}:{order_id}"

    def normalize(
        self,
        parsed: dict[str, Any],
        integration: Any,
    ) -> OrderIntent:
        """
        Normaliza o JSON recebido no modelo canônico OrderIntent.
        """
        external_order_id = str(
            parsed.get("order_id")
            or parsed.get("external_order_id")
            or ""
        ).strip()
        if not external_order_id:
            raise ValueError("Campo 'order_id' obrigatório no payload do webhook.")
        if len(external_order_id) > 255:
            raise ValueError("order_id excede 255 caracteres.")

        # Cliente
        customer_raw = parsed.get("customer") or {}
        if isinstance(customer_raw, dict):
            customer_name = customer_raw.get("name", "Cliente")
            customer_phone = customer_raw.get("phone")
        else:
            customer_name = str(customer_raw)
            customer_phone = None

        # Endereço de entrega (Dropoff)
        delivery_raw = parsed.get("delivery_address") or {}
        if isinstance(delivery_raw, dict):
            street = delivery_raw.get("street") or delivery_raw.get("address", "")
            number = delivery_raw.get("number", "")
            neighborhood = delivery_raw.get("neighborhood", "")
            city = delivery_raw.get("city", "")
            state = delivery_raw.get("state", "")
            zipcode = delivery_raw.get("zip") or delivery_raw.get("zipcode", "")
            instructions = delivery_raw.get("instructions") or parsed.get("notes")

            addr_parts = [p for p in [f"{street}, {number}".strip(" ,"), neighborhood, city, state, zipcode] if p]
            if not addr_parts:
                raise ValueError("Endereço de entrega obrigatório.")
            full_address = ", ".join(addr_parts)

            lat = float(delivery_raw["lat"]) if delivery_raw.get("lat") is not None else None
            lng = float(delivery_raw["lng"]) if delivery_raw.get("lng") is not None else None
            if (lat is None) != (lng is None):
                raise ValueError("Latitude e longitude devem ser informadas juntas.")
            if lat is not None and not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError("Coordenadas de entrega inválidas.")
        else:
            full_address = str(delivery_raw)
            lat, lng, instructions = None, None, parsed.get("notes")
            if not full_address.strip():
                raise ValueError("Endereço de entrega obrigatório.")

        dropoff = DeliveryStop(
            address=full_address,
            lat=lat,
            lng=lng,
            customer_name=customer_name,
            customer_phone=customer_phone,
            instructions=instructions,
        )

        # Itens e total
        items_raw = parsed.get("items") or []
        items_summary_parts = []
        computed_total = 0
        if isinstance(items_raw, list):
            for item in items_raw:
                if isinstance(item, dict):
                    name = item.get("name", "Item")
                    qty = int(item.get("qty", 1))
                    price = int(item.get("price_cents", 0))
                    if qty <= 0 or price < 0:
                        raise ValueError("Item possui quantidade ou preço inválido.")
                    computed_total += qty * price
                    items_summary_parts.append(f"{qty}x {name}")
                elif isinstance(item, str):
                    items_summary_parts.append(item)

        items_summary = ", ".join(items_summary_parts) if items_summary_parts else "Itens diversos"

        total_amount_cents = parsed.get("total_cents")
        if total_amount_cents is None:
            total_amount_cents = parsed.get("total_amount_cents", computed_total)
        total_amount_cents = int(total_amount_cents)
        if total_amount_cents < 0 or total_amount_cents > 100_000_000:
            raise ValueError("Valor total do pedido fora do limite permitido.")

        integration_config = getattr(integration, "config", None) or {}
        raw_delivery_fee = parsed.get("delivery_fee_cents")
        if raw_delivery_fee is None:
            raw_delivery_fee = integration_config.get("default_delivery_fee_cents")
        if raw_delivery_fee is None:
            raise ValueError(
                "Taxa de entrega ausente e nenhuma taxa padrão foi configurada."
            )
        delivery_fee_cents = int(raw_delivery_fee)
        if delivery_fee_cents < 0 or delivery_fee_cents > 10_000_000:
            raise ValueError("Taxa de entrega fora do limite permitido.")

        raw_distance_meters = parsed.get("distance_meters")
        distance_meters = None if raw_distance_meters is None else int(raw_distance_meters)
        if distance_meters is not None and not 0 <= distance_meters <= 2_000_000:
            raise ValueError("Distância do pedido fora do limite permitido.")

        payment_method = str(parsed.get("payment_method", "online")).lower()
        notes = parsed.get("notes")

        # Agendamento
        scheduled_for: Optional[datetime] = None
        raw_scheduled = parsed.get("scheduled_for")
        if raw_scheduled:
            try:
                scheduled_for = datetime.fromisoformat(raw_scheduled.replace("Z", "+00:00"))
            except Exception:
                pass

        # Informações da Loja de Coleta (Pickup)
        store = getattr(integration, "store", None)
        pickup_address = "Loja de Coleta"
        pickup_lat, pickup_lng = None, None
        if store:
            pickup_address = getattr(store, "address", None) or getattr(store, "name", "Loja de Coleta")
            geom = getattr(store, "geom", None)
            if geom:
                try:
                    pickup_lat = float(geom.y)
                    pickup_lng = float(geom.x)
                except Exception:
                    pass

        return OrderIntent(
            integration_id=integration.id,
            external_order_id=external_order_id,
            idempotency_key=f"{self.slug}:{external_order_id}",
            pickup_store_id=integration.store_id,
            pickup_address=pickup_address,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            pickup_instructions=None,
            deliveries=[dropoff],
            total_amount_cents=total_amount_cents,
            delivery_fee_cents=delivery_fee_cents,
            distance_meters=distance_meters,
            payment_method=payment_method,
            customer_name=customer_name,
            customer_phone=customer_phone,
            items_summary=items_summary,
            notes=notes,
            scheduled_for=scheduled_for,
            source_platform=self.slug,
        )

"""Webhook receiver para notificações de eventos PIX da Efí Pay (BaaS SPI Bacen)."""

from __future__ import annotations

import json
import logging
import hmac
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import connection, transaction

from config.core_models import tenant_context
from finance.models import WithdrawalRequest
from finance.tasks import notify_payout_success_task

logger = logging.getLogger("finance.webhooks")


def _process_pix_event(event: dict, tx_id: str | None, e2e_id: str | None) -> bool:
    """Atualiza um saque já isolado no tenant e agenda a notificação após commit."""
    with transaction.atomic():
        query = WithdrawalRequest.objects.select_for_update()
        withdrawal = None
        if tx_id:
            withdrawal = query.filter(baasTransactionId=tx_id).first()
        if not withdrawal and e2e_id:
            withdrawal = query.filter(baasTransactionId=e2e_id).first()

        if not withdrawal:
            logger.warning(
                "Nenhum saque localizado para os identificadores autenticados do webhook."
            )
            return False

        if withdrawal.status == WithdrawalRequest.WithdrawalStatus.PAID:
            return False

        withdrawal.status = WithdrawalRequest.WithdrawalStatus.PAID
        withdrawal.processedAt = timezone.now()
        raw = withdrawal.baasRawResponse or {}
        raw["webhook_event"] = event
        if e2e_id and not raw.get("e2eId"):
            raw["e2eId"] = e2e_id
        withdrawal.baasRawResponse = raw
        withdrawal.save(
            update_fields=["status", "processedAt", "baasRawResponse", "updatedAt"]
        )
        withdrawal_id = str(withdrawal.id)
        transaction.on_commit(
            lambda: notify_payout_success_task.delay(withdrawal_id)  # type: ignore
        )
        logger.info("Saque %s atualizado para PAID via webhook Efí.", withdrawal.id)
        return True


@csrf_exempt
@require_POST
def efi_pix_webhook(request):
    """
    Webhook receptor de notificações Pix da Efí Pay.
    Processa eventos assíncronos de liquidação enviados pelo Banco Central / Efí.
    """
    expected_hmac = getattr(settings, "EFI_WEBHOOK_HMAC", "")
    received_hmac = request.GET.get("hmac", "")
    if not expected_hmac or not hmac.compare_digest(received_hmac, expected_hmac):
        logger.warning("Webhook Efí rejeitado por HMAC ausente ou inválido.")
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if getattr(settings, "EFI_REQUIRE_MTLS_HEADER", True):
        verified = request.headers.get("X-Client-Cert-Verified", "").upper()
        if verified not in {"SUCCESS", "VERIFIED"}:
            logger.warning("Webhook Efí rejeitado: certificado cliente não verificado.")
            return JsonResponse({"error": "Unauthorized"}, status=401)

    if len(request.body) > 1_048_576:
        return JsonResponse({"error": "Payload too large"}, status=413)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as exc:
        logger.error("Payload JSON inválido no webhook Efí: %s", exc)
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    logger.info("Webhook Efí PIX autenticado e recebido.")

    # A Efí Pay envia {"pix": [...]} ou lista de eventos
    pix_events = data.get("pix", []) if isinstance(data, dict) else data
    if not isinstance(pix_events, list):
        pix_events = [data]

    processed_count = 0
    for event in pix_events:
        if not isinstance(event, dict):
            continue

        tx_id = event.get("txid") or event.get("idEnvio")
        e2e_id = event.get("endToEndId") or event.get("e2eId")

        if not tx_id and not e2e_id:
            continue

        try:
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT resolve_withdrawal_operator(%s, %s)", [tx_id, e2e_id]
                    )
                    row = cursor.fetchone()
                operator_id = row[0] if row else None
                if not operator_id:
                    logger.warning(
                        "Nenhum saque localizado para os identificadores autenticados do webhook."
                    )
                    continue
                with tenant_context(operator_id):
                    processed_count += int(_process_pix_event(event, tx_id, e2e_id))
            else:
                processed_count += int(_process_pix_event(event, tx_id, e2e_id))

        except Exception as exc:
            logger.exception("Erro ao processar evento Pix individual no webhook: %s", exc)

    return JsonResponse({"status": "received", "processed": processed_count}, status=200)

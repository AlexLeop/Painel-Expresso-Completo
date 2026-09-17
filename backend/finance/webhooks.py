"""Webhook receiver para notificações de eventos PIX da Efí Pay (BaaS SPI Bacen)."""

from __future__ import annotations

import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction

from finance.models import WithdrawalRequest
from finance.tasks import notify_payout_success_task

logger = logging.getLogger("finance.webhooks")


@csrf_exempt
@require_POST
def efi_pix_webhook(request):
    """
    Webhook receptor de notificações Pix da Efí Pay.
    Processa eventos assíncronos de liquidação enviados pelo Banco Central / Efí.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as exc:
        logger.error("Payload JSON inválido no webhook Efí: %s", exc)
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    logger.info("Webhook Efí PIX recebido: %s", data)

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
            with transaction.atomic():
                query = WithdrawalRequest.objects.select_for_update()
                withdrawal = None
                if tx_id:
                    withdrawal = query.filter(baasTransactionId=tx_id).first()
                if not withdrawal and e2e_id:
                    withdrawal = query.filter(baasTransactionId=e2e_id).first()

                if not withdrawal:
                    logger.warning(
                        "Nenhum saque localizado para txid=%s, e2e=%s no webhook.",
                        tx_id,
                        e2e_id,
                    )
                    continue

                if withdrawal.status != WithdrawalRequest.WithdrawalStatus.PAID:
                    withdrawal.status = WithdrawalRequest.WithdrawalStatus.PAID
                    withdrawal.processedAt = timezone.now()
                    raw = withdrawal.baasRawResponse or {}
                    raw["webhook_event"] = event
                    if e2e_id and not raw.get("e2eId"):
                        raw["e2eId"] = e2e_id
                    withdrawal.baasRawResponse = raw
                    withdrawal.save(
                        update_fields=[
                            "status",
                            "processedAt",
                            "baasRawResponse",
                            "updatedAt",
                        ]
                    )
                    logger.info(
                        "Saque %s atualizado para PAID via Webhook Efí.",
                        withdrawal.id,
                    )

                    notify_payout_success_task.delay(str(withdrawal.id))
                    processed_count += 1

        except Exception as exc:
            logger.exception("Erro ao processar evento Pix individual no webhook: %s", exc)

    return JsonResponse({"status": "received", "processed": processed_count}, status=200)

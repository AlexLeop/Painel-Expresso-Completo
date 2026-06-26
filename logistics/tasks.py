from celery import shared_task
import json
from math import radians, cos, sin, asin, sqrt
from datetime import timedelta
from django.utils import timezone as django_tz
from logistics.models import (
    Order,
    Stop,
    ComplianceRetentionPolicy,
    DriverConsentAcceptance,
    DriverDeviceSecurityEvent,
    DriverIncident,
    DriverOfflineSyncBatch,
    Proof,
)
from logistics.compliance import minimized_metadata
from config.core_models import tenant_context
from config.redis_client import get_redis

r = get_redis()


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in meters between two points
    on the earth (specified in decimal degrees)
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r_earth = 6371000  # Raio da terra em metros
    return c * r_earth


import logging

logger = logging.getLogger(__name__)


def _apply_retention_policy(
    policy: ComplianceRetentionPolicy, cutoff_at, executed_at
) -> int:
    processed = 0

    if policy.resourceType == "DRIVER_CONSENT_ACCEPTANCE":
        records = DriverConsentAcceptance.objects.filter(
            operator=policy.operator,
            acceptedAt__lt=cutoff_at,
        )
        for record in records.iterator():
            updated_metadata = minimized_metadata(
                record.metadata,
                marker="driver_consent_acceptance",
                preserve_keys=("accepted_via", "revoked_via"),
            )
            if (
                record.deviceIdentifier is None
                and record.ipAddress is None
                and record.userAgent is None
                and record.metadata == updated_metadata
            ):
                continue
            record.deviceIdentifier = None
            record.ipAddress = None
            record.userAgent = None
            record.metadata = updated_metadata
            record.save(
                update_fields=["deviceIdentifier", "ipAddress", "userAgent", "metadata"]
            )
            processed += 1
        return processed

    if policy.resourceType == "DRIVER_OFFLINE_SYNC_BATCH":
        records = DriverOfflineSyncBatch.objects.filter(
            operator=policy.operator,
            createdAt__lt=cutoff_at,
        )
        for record in records.iterator():
            updated_payload = minimized_metadata(
                record.payload if isinstance(record.payload, dict) else {},
                marker="driver_offline_sync_batch",
                extra={"item_count": record.itemCount, "status": record.status},
            )
            if record.payload == updated_payload:
                continue
            record.payload = updated_payload
            record.save(update_fields=["payload"])
            processed += 1
        return processed

    if policy.resourceType == "DRIVER_DEVICE_SECURITY_EVENT":
        records = DriverDeviceSecurityEvent.objects.filter(
            operator=policy.operator,
            createdAt__lt=cutoff_at,
        )
        for record in records.iterator():
            updated_flags = minimized_metadata(
                record.flags if isinstance(record.flags, dict) else {},
                marker="driver_device_security_event",
                extra={"risk_level": record.riskLevel},
            )
            if record.flags == updated_flags:
                continue
            record.flags = updated_flags
            record.save(update_fields=["flags"])
            processed += 1
        return processed

    if policy.resourceType == "DRIVER_INCIDENT":
        records = DriverIncident.objects.filter(
            operator=policy.operator,
            createdAt__lt=cutoff_at,
        )
        for record in records.iterator():
            updated_metadata = minimized_metadata(
                record.metadata,
                marker="driver_incident",
                extra={"type": record.type, "status": record.status},
            )
            if record.metadata == updated_metadata:
                continue
            record.metadata = updated_metadata
            record.save(update_fields=["metadata"])
            processed += 1
        return processed

    if policy.resourceType == "PROOF":
        records = Proof.objects.filter(
            operator=policy.operator,
            capturedAt__lt=cutoff_at,
        )
        for record in records.iterator():
            updated_metadata = minimized_metadata(
                record.metadata,
                marker="proof",
                extra={"stage": record.stage, "type": record.type},
            )
            if (
                record.deviceIdentifier is None
                and record.confirmationCode is None
                and record.qrCode is None
                and record.barcode is None
                and record.metadata == updated_metadata
            ):
                continue
            record.deviceIdentifier = None
            record.confirmationCode = None
            record.qrCode = None
            record.barcode = None
            record.metadata = updated_metadata
            record.save(
                update_fields=[
                    "deviceIdentifier",
                    "confirmationCode",
                    "qrCode",
                    "barcode",
                    "metadata",
                ]
            )
            processed += 1
        return processed

    return processed


@shared_task
def process_telemetry_batch():
    """
    Task analítica que calcula distância acumulada por driver.

    NÃO consome a fila bruta do Redis (queue:telemetry_raw_*).
    Lê dados de uma fila secundária (analytics:telemetry_batch_{operator_id})
    populada pelo persist_telemetry_buffer, evitando canibalismo de dados.
    """
    cursor = 0
    total_processed = 0

    while True:
        cursor, keys = r.scan(
            cursor=cursor, match="analytics:telemetry_batch_*", count=100
        )

        for key in keys:
            # Consome apenas da fila analítica (cópia), não da fila bruta
            raw_events = r.lpop(key, count=500)
            if not raw_events:
                continue

            driver_events = {}
            for raw_event_bytes in raw_events:
                if isinstance(raw_event_bytes, bytes):
                    raw_event_str = raw_event_bytes.decode("utf-8")
                else:
                    raw_event_str = str(raw_event_bytes)

                event = json.loads(raw_event_str)
                drv_id = event.get("driver_id")
                if not drv_id:
                    continue

                if drv_id not in driver_events:
                    driver_events[drv_id] = []
                driver_events[drv_id].append(event)
                total_processed += 1

            # Processamento Analítico
            for drv_id, events in driver_events.items():
                events.sort(key=lambda x: x.get("ts_server", x.get("ts", 0)))

                distance_accumulated = 0.0
                for i in range(1, len(events)):
                    p1 = events[i - 1]
                    p2 = events[i]
                    if (
                        p1.get("lat")
                        and p1.get("lng")
                        and p2.get("lat")
                        and p2.get("lng")
                    ):
                        dist = haversine(p1["lng"], p1["lat"], p2["lng"], p2["lat"])
                        distance_accumulated += dist

                if distance_accumulated > 0:
                    operator_id = events[0].get("operator_id")
                    if operator_id:
                        from logistics.models import Manifest

                        with tenant_context(operator_id):
                            active_manifest = (
                                Manifest.objects.filter(
                                    operator_id=operator_id,
                                    driver_id=drv_id,
                                    status__in=[
                                        Manifest.ManifestStatus.OPEN,
                                        Manifest.ManifestStatus.LOCKED,
                                    ],
                                )
                                .order_by("-createdAt")
                                .first()
                            )

                            if active_manifest:
                                dist_int = int(distance_accumulated)
                                if dist_int > 0:
                                    stats_key = (
                                        f"stats:manifest:{active_manifest.id}:distance"
                                    )
                                    r.incrby(stats_key, dist_int)
                                    r.expire(stats_key, 604800)
                                    logger.info(
                                        f"[TELEMETRY] Driver {drv_id} acumulou +{dist_int}m no Manifest {active_manifest.id}."
                                    )

        if cursor == 0:
            break

    return f"Processados {total_processed} eventos de telemetria."


@shared_task
def persist_telemetry_buffer():
    """
    Consome a fila queue:telemetry_raw_{operator_id} do Redis e faz
    bulk_create na tabela Position (particionada por mês).

    Contrato de Segurança 2.3: Usa ts_server como fonte da verdade
    para capturedAt (particionamento). ts_device é descartado neste worker.

    Roda a cada 2 minutos via Celery Beat.
    """
    from django.contrib.gis.geos import Point
    from django.utils import timezone as tz
    from datetime import datetime
    from accounts.models import Operator
    from logistics.models import Position

    BATCH_SIZE = 500
    operators = Operator.objects.values_list("id", flat=True)
    total_persisted = 0

    for operator_id in operators:
        queue_key = f"queue:telemetry_raw_{operator_id}"

        # PASSO 1: Ler SEM deletar (peek, não pop)
        raw_items = r.lrange(queue_key, 0, BATCH_SIZE - 1)
        if not raw_items:
            continue

        positions_to_create = []
        for raw_bytes in raw_items:
            try:
                if isinstance(raw_bytes, bytes):
                    raw_str = raw_bytes.decode("utf-8")
                else:
                    raw_str = str(raw_bytes)
                event = json.loads(raw_str)

                # ts_server é a ÚNICA fonte da verdade para capturedAt (Contrato 2.3)
                ts_key = event.get("ts_server") or event.get("ts")
                if not ts_key:
                    continue
                captured_at = datetime.fromtimestamp(ts_key, tz=tz.utc)

                positions_to_create.append(
                    Position(
                        operator_id=event["operator_id"],
                        driver_id=event["driver_id"],
                        geom=Point(float(event["lng"]), float(event["lat"]), srid=4326),
                        heading=event.get("heading", 0),
                        speedKmh=event.get("speed", 0),
                        capturedAt=captured_at,
                    )
                )
            except (KeyError, ValueError, json.JSONDecodeError):
                # Pings malformados são silenciosamente descartados
                continue

        # PASSO 2: Persistir no PostgreSQL (dados ainda estão seguros no Redis)
        if positions_to_create:
            with tenant_context(operator_id):
                Position.objects.bulk_create(positions_to_create, ignore_conflicts=True)
            total_persisted += len(positions_to_create)

        # PASSO 3: SÓ AGORA deletar do Redis (ack-first: Postgres confirmou)
        # Se crash antes daqui: dados duplicam no próximo ciclo (ignore_conflicts cuida)
        # Se crash depois: dados já estão no Postgres, tudo seguro.
        r.ltrim(queue_key, len(raw_items), -1)

        # PASSO 4: Copiar para fila analítica
        if positions_to_create:
            analytics_key = f"analytics:telemetry_batch_{operator_id}"
            analytics_pipe = r.pipeline()
            for raw_item in raw_items:
                analytics_pipe.rpush(analytics_key, raw_item)
            analytics_pipe.expire(analytics_key, 3600)  # TTL de 1h
            analytics_pipe.execute()

    return f"Persisted {total_persisted} telemetry pings to PostgreSQL."


@shared_task
def ensure_position_partitions():
    """
    Cria partições mensais na tabela Position para os próximos 2 meses.
    Deve rodar mensalmente via Celery Beat (1o dia de cada mês).

    Doutrina I.4 do Manifesto: "Tabelas de hiper-crescimento SEMPRE
    utilizarão Particionamento Declarativo por Tempo."
    """
    from django.db import connection
    from django.utils import timezone as tz
    from dateutil.relativedelta import relativedelta

    now = tz.now()

    for month_offset in range(3):  # Mês atual + 2 meses futuros
        target = now + relativedelta(months=month_offset)
        next_month = target + relativedelta(months=1)

        partition_name = f"Position_{target.strftime('%Y_%m')}"
        start_date = target.strftime("%Y-%m-01")
        end_date = next_month.strftime("%Y-%m-01")

        sql = f"""
            CREATE TABLE IF NOT EXISTS "{partition_name}" 
            PARTITION OF "Position" 
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """

        with connection.cursor() as cursor:
            try:
                cursor.execute(sql)
            except Exception:
                pass

    return "Position partitions ensured for the next 3 months."


@shared_task
def process_geofence_triggers():
    """
    Consome da fila geofence_triggers do Redis e processa as
    transições de máquina de estado (Auto-Arrive).
    """
    while True:
        raw_events = r.lpop("geofence_triggers", count=100)
        if not raw_events:
            break

        for raw_event in raw_events:
            if isinstance(raw_event, bytes):
                raw_event = raw_event.decode("utf-8")

            try:
                payload = json.loads(raw_event)
                driver_id = payload.get("driver_id")
                stop_id = payload.get("stop_id")

                if not stop_id:
                    continue

                stop = Stop.objects.select_related("order").filter(id=stop_id).first()
                if not stop:
                    continue

                order = stop.order
                with tenant_context(order.operator_id):
                    order.refresh_from_db()
                    # Se for STARTED, muda pra ARRIVED automaticamente
                    if order.status == Order.OrderStatus.STARTED:
                        from django.utils import timezone as django_tz

                        Order.validate_status_transition(
                            order.status, Order.OrderStatus.ARRIVED
                        )
                        updated = Order.objects.filter(
                            pk=order.pk, status=Order.OrderStatus.STARTED
                        ).update(
                            status=Order.OrderStatus.ARRIVED, arrivedAt=django_tz.now()
                        )

                        if updated:
                            # Limpa do Redis para não engatilhar repetidamente
                            r.srem(f"active_stops:driver:{driver_id}", str(stop.id))

                            # Publica evento de webhook
                            from integration.models import IntegrationOutbox

                            IntegrationOutbox.objects.create(
                                operator_id=order.operator_id,
                                aggregateType="ORDER",
                                aggregateId=order.id,
                                eventType="ORDER_ARRIVED",
                                payload={"id": str(order.id), "status": "ARRIVED"},
                            )

            except Exception as e:
                logger.error(f"Failed to process geofence trigger: {e}")


@shared_task
def monitor_expiring_documents():
    """
    [Flow 4.5] Monitoramento de Vencimento
    Roda diariamente (configurado no Celery Beat)
    Inativa motoristas cujos documentos obrigatórios venceram
    """
    from datetime import date
    from logistics.models import DriverDocument, Driver

    today = date.today()

    # 1. Encontra documentos vencidos hoje (ou antes)
    expired_docs = DriverDocument.objects.filter(
        expiresAt__lte=today, status__in=["PENDING_APPROVAL", "APPROVED"]
    ).select_related("driver")

    driver_ids = set()
    for doc in expired_docs:
        doc.status = "REJECTED"  # Ou EXPIRED se tivéssemos no enum
        doc.save(update_fields=["status"])
        driver_ids.add(doc.driver_id)

    # 2. Bloqueia os motoristas afetados
    if driver_ids:
        Driver.objects.filter(id__in=driver_ids).update(
            onboarding_status="BLOCKED", active=False
        )
        logger.info(f"Blocked {len(driver_ids)} drivers due to expired documents.")

    # 3. Disparar Push Notifications (FCM) para motoristas bloqueados
    if driver_ids:
        from logistics.models import DriverDevice
        from logistics.notifications import send_push_notification

        devices = DriverDevice.objects.filter(driver_id__in=driver_ids, status="ACTIVE")
        for device in devices:
            fcm_token = (
                device.metadata.get("fcm_token")
                if isinstance(device.metadata, dict)
                else None
            )
            if fcm_token:
                send_push_notification(
                    device_token=fcm_token,
                    title="Documentos Expirados",
                    body="Seu acesso foi suspenso devido a documentos expirados. Por favor, regularize-os.",
                )


@shared_task
def execute_retention_policies():
    """
    Executa minimização de dados sensíveis por recurso, respeitando a retenção por operador.
    O objetivo aqui é reduzir PII operacional antiga sem destruir trilha mínima de auditoria.
    """
    executed_at = django_tz.now()
    summaries = []

    policies = (
        ComplianceRetentionPolicy.objects.filter(
            active=True,
        )
        .select_related("operator")
        .order_by("operator_id", "resourceType")
    )

    for policy in policies:
        cutoff_at = executed_at - timedelta(days=policy.retentionDays)
        with tenant_context(policy.operator_id):
            processed = _apply_retention_policy(policy, cutoff_at, executed_at)
            policy.lastExecutedAt = executed_at
            policy.save(update_fields=["lastExecutedAt", "updatedAt"])

        summaries.append(
            {
                "operator_id": str(policy.operator_id),
                "resource_type": policy.resourceType,
                "retention_days": policy.retentionDays,
                "processed": processed,
            }
        )
        logger.info(
            "[LGPD] Retention policy executed for operator=%s resource=%s processed=%s",
            policy.operator_id,
            policy.resourceType,
            processed,
        )

    return {
        "processed_policies": len(summaries),
        "executed_at": executed_at.isoformat(),
        "resources": summaries,
    }

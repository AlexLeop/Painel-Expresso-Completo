import os
from celery import Celery

# Seta o módulo de configurações default do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("expresso_neves")

# O namespace 'CELERY' faz com que todas as variáveis de configuração de celery
# dentro de settings.py devam ter o prefixo `CELERY_`
app.config_from_object("django.conf:settings", namespace="CELERY")

# Carrega tasks.py de todas as aplicações Django registradas automaticamente
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    "hourly-cutoff-billing": {
        "task": "finance.tasks.run_hourly_cutoff_billing",
        "schedule": crontab(minute=0),  # Executa a cada hora cheia
    },
    "global-cutoff-billing": {
        "task": "finance.tasks.run_global_cutoff_billing",
        "schedule": crontab(hour=4, minute=0),  # Executa globalmente às 04:00 AM
    },
    "telemetry-consumer": {
        "task": "logistics.tasks.process_telemetry_batch",
        "schedule": 10.0,  # Roda a cada 10 segundos
    },
    "telemetry-persist": {
        "task": "logistics.tasks.persist_telemetry_buffer",
        "schedule": 120.0,  # Roda a cada 2 minutos
    },
    "position-partitions": {
        "task": "logistics.tasks.ensure_position_partitions",
        "schedule": crontab(
            day_of_month="1", hour=3, minute=0
        ),  # 1o dia do mês às 03:00
    },
    "flush-integration-outbox-10s": {
        "task": "integration.tasks.flush_outbox_events",
        "schedule": 10.0,
    },
    "process-inbound-webhooks-10s": {
        "task": "integration.tasks.process_inbound_webhooks",
        "schedule": 10.0,
    },
    "poll-partner-events-15s": {
        "task": "integration.tasks.poll_partner_events",
        "schedule": 15.0,
    },
    "process-geofence-triggers-5s": {
        "task": "logistics.tasks.process_geofence_triggers",
        "schedule": 5.0,
    },
    "execute-retention-policies-daily": {
        "task": "logistics.tasks.execute_retention_policies",
        "schedule": crontab(hour=2, minute=30),
    },
}

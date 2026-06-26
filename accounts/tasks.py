import logging
from celery import shared_task
from django.db import transaction
from logistics.models import Driver

logger = logging.getLogger(__name__)

@shared_task
def process_biometrics_webhook(driver_id: str, status: str):
    logger.info(f"Processando webhook de biometria para driver {driver_id}: {status}")
    with transaction.atomic():
        try:
            # We select_for_update to avoid race conditions with other updates
            driver = Driver.objects.select_for_update().get(id=driver_id)
            driver.onboarding_status = status
            driver.save(update_fields=['onboarding_status'])
            logger.info(f"Driver {driver_id} atualizado para {status}")
        except Driver.DoesNotExist:
            logger.error(f"Driver {driver_id} não encontrado no webhook biométrico.")

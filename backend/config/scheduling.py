from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from config.redis_client import get_redis
from logistics.models import Driver, DriverDocument, ScheduleEntry, Store, Turno


def validate_schedule_driver(driver):
    if not driver.active or driver.onboarding_status != "APPROVED":
        raise HttpError(422, "O motoboy deve estar ativo e aprovado para ser escalado.")
    if DriverDocument.objects.filter(
        driver=driver, expiresAt__lt=timezone.localdate()
    ).exists():
        raise HttpError(422, "O motoboy possui documentos vencidos.")
    if get_redis().get(f"deny_list:driver:{driver.id}"):
        raise HttpError(422, "Motoboy bloqueado para escala.")


@transaction.atomic
def schedule_driver(operator, driver_id, store_id, turno_id, target_date, minimum_override):
    if operator is None:
        raise HttpError(422, "Selecione o operador logístico.")
    try:
        day = date.fromisoformat(str(target_date))
        driver = get_object_or_404(Driver.objects.select_for_update(), pk=driver_id, operator=operator)
        store = get_object_or_404(Store, pk=store_id, operator=operator)
        turno = get_object_or_404(Turno, pk=turno_id, operator=operator, store=store)
    except (ValueError, ValidationError) as exc:
        raise HttpError(422, "Informe os identificadores e a data da escala.") from exc
    validate_schedule_driver(driver)
    return ScheduleEntry.objects.get_or_create(
        operator=operator, driver=driver, store=store, turno=turno, date=day,
        defaults={"minGuaranteedOverrideCents": minimum_override},
    )

from datetime import datetime, time, timedelta
from typing import Optional

from django.utils import timezone


def derive_business_date_from_cutoff(
    reference_dt: Optional[datetime],
    cutoff_hour: int,
    cutoff_minute: int = 0,
):
    current_dt = timezone.localtime(reference_dt) if reference_dt else timezone.localtime()
    cutoff_dt = current_dt.replace(
        hour=cutoff_hour,
        minute=cutoff_minute,
        second=0,
        microsecond=0,
    )
    if current_dt < cutoff_dt:
        return (current_dt - timedelta(days=1)).date()
    return current_dt.date()


def resolve_store_business_date(store, explicit_business_date=None, reference_dt: Optional[datetime] = None):
    if explicit_business_date is not None:
        return explicit_business_date

    contract = getattr(store, "contract", None)
    if contract:
        return derive_business_date_from_cutoff(
            reference_dt=reference_dt,
            cutoff_hour=contract.cutoffHour,
            cutoff_minute=getattr(contract, "cutoffMinute", 0) or 0,
        )

    localized = timezone.localtime(reference_dt) if reference_dt else timezone.localtime()
    return localized.date()

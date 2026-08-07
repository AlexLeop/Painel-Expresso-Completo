from datetime import datetime
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from finance.business_date import (
    derive_business_date_from_cutoff,
    resolve_store_business_date,
)


class BusinessDateTests(SimpleTestCase):
    @override_settings(USE_TZ=True, TIME_ZONE="America/Sao_Paulo")
    def test_derive_business_date_before_cutoff_rolls_back_one_day(self):
        reference = timezone.make_aware(datetime(2026, 6, 22, 1, 59, 0))
        business_date = derive_business_date_from_cutoff(
            reference, cutoff_hour=2, cutoff_minute=0
        )
        self.assertEqual(str(business_date), "2026-06-21")

    @override_settings(USE_TZ=True, TIME_ZONE="America/Sao_Paulo")
    def test_derive_business_date_after_cutoff_keeps_same_day(self):
        reference = timezone.make_aware(datetime(2026, 6, 22, 2, 1, 0))
        business_date = derive_business_date_from_cutoff(
            reference, cutoff_hour=2, cutoff_minute=0
        )
        self.assertEqual(str(business_date), "2026-06-22")

    def test_resolve_store_business_date_prefers_explicit_value(self):
        store = SimpleNamespace(contract=SimpleNamespace(cutoffHour=2, cutoffMinute=0))
        business_date = resolve_store_business_date(
            store, explicit_business_date=timezone.datetime(2026, 6, 21).date()
        )
        self.assertEqual(str(business_date), "2026-06-21")

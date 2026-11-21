from uuid import UUID

from django.db import models, transaction
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from accounts.auth import platform_admin_required
from finance.models import WeeklyInvoiceLineItem, WeeklyStoreInvoice

router = Router(tags=["Fechamentos"])


class InvoiceSnapshot(models.Model):
    invoice_id = models.UUIDField(primary_key=True)
    operator_id = models.UUIDField()
    createdBy = models.UUIDField()
    createdAt = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()

    class Meta:
        app_label = "config"
        db_table = "InvoiceSnapshot"
        managed = False


def invoice_data(invoice):
    lines = WeeklyInvoiceLineItem.objects.filter(
        invoice_id=invoice.id, operator_id=invoice.operator_id,
    ).order_by("businessDate", "id")
    return {
        "invoice_id": str(invoice.id), "store_name": invoice.store.name,
        "start_date": invoice.startDate.isoformat(), "end_date": invoice.endDate.isoformat(),
        "status": invoice.status, "total_cents": invoice.totalCents,
        "lines": [
            {"description": line.description, "amount_cents": line.amountCents,
             "date": line.businessDate.isoformat() if line.businessDate else None,
             "status": line.status}
            for line in lines
        ],
    }


def detail(invoice, snapshot):
    return {
        **(snapshot.payload if snapshot else invoice_data(invoice)),
        "captured_at": snapshot.createdAt.isoformat() if snapshot else None,
    }


@router.get("/{invoice_id}")
def get_snapshot(request, invoice_id: UUID):
    platform_admin_required(request)
    invoice = get_object_or_404(WeeklyStoreInvoice.objects.select_related("store"), pk=invoice_id)
    return detail(invoice, InvoiceSnapshot.objects.filter(invoice_id=invoice_id).first())


@router.post("/{invoice_id}")
@transaction.atomic
def capture_snapshot(request, invoice_id: UUID):
    admin = platform_admin_required(request)
    invoice = get_object_or_404(WeeklyStoreInvoice.objects.select_for_update(), pk=invoice_id)
    snapshot = InvoiceSnapshot.objects.filter(invoice_id=invoice_id).first()
    if snapshot:
        return detail(invoice, snapshot)
    if invoice.status not in {"FINALIZED", "LOCKED", "PAID"}:
        raise HttpError(409, "Finalize o fechamento antes de gerar o snapshot.")
    snapshot = InvoiceSnapshot.objects.create(
        invoice_id=invoice.id, operator_id=invoice.operator_id,
        createdBy=admin.id, payload=invoice_data(invoice),
    )
    return detail(invoice, snapshot)

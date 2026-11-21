from django.core.management.base import BaseCommand
from django.db import transaction

from integration.models import StoreIntegration, get_cipher
from accounts.models import Operator
from config.core_models import tenant_context


class Command(BaseCommand):
    help = "Re-encrypt connector credentials with the first configured key; dry-run by default."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        cipher = get_cipher()
        count = 0
        for operator_id in Operator.objects.values_list("id", flat=True).iterator():
            with tenant_context(operator_id):
                integrations = StoreIntegration.objects.select_for_update().filter(operator_id=operator_id)
                for integration in integrations.iterator():
                    fields = []
                    for field in ("clientSecret", "apiKey", "webhook_secret"):
                        token = getattr(integration, field)
                        if token:
                            # An undecryptable value aborts the whole transaction.
                            setattr(integration, field, cipher.encrypt(cipher.decrypt(token.encode())).decode())
                            fields.append(field)
                    if fields and options["apply"]:
                        integration.save(update_fields=fields)
                    count += 1
        self.stdout.write(f"{count} connectors checked. Applied: {options['apply']}.")

import uuid
from django.db import models


class TenantModel(models.Model):
    """
    Classe base para todos os modelos Tenant-Aware.
    Garante o espelhamento exato com o schema DDL (managed = False).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Em todos os modelos derivados, o 'operator' referenciará o Operator da infraestrutura principal.
    # O on_delete=models.CASCADE será respeitado no banco, mas declaramos para o Django.

    class Meta:
        abstract = True
        managed = (
            False  # O DB-First paradigm impera. O Supabase CLI é a fonte da verdade.
        )


class TimeStampedTenantModel(TenantModel):
    """
    Classe base contendo timestamps para tabelas que usam createdAt e updatedAt.
    """

    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updatedAt = models.DateTimeField(auto_now=True, db_column="updatedAt")

    class Meta:
        abstract = True
        managed = False


from contextlib import contextmanager
from django.db import connection, transaction
import json


@contextmanager
def tenant_context(operator_id: uuid.UUID):
    """Scope database work to the operator and restore any surrounding context."""
    claims = json.dumps(
        {"app_metadata": {"operator_id": str(operator_id)}, "role": "authenticated"}
    )

    with transaction.atomic():
        if connection.vendor != "postgresql":
            yield
            return
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('request.jwt.claims', true)")
            previous = cursor.fetchone()[0] or "{}"
            cursor.execute(
                "SELECT set_config('request.jwt.claims', %s, true);", [claims]
            )
        yield
        # On an exception the enclosing savepoint restores the previous settings.
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('request.jwt.claims', %s, true)", [previous])

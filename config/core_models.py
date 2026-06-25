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
        managed = False  # O DB-First paradigm impera. O Supabase CLI é a fonte da verdade.

class TimeStampedTenantModel(TenantModel):
    """
    Classe base contendo timestamps para tabelas que usam createdAt e updatedAt.
    """
    createdAt = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updatedAt = models.DateTimeField(auto_now=True, db_column='updatedAt')

    class Meta:
        abstract = True
        managed = False

from contextlib import contextmanager
from django.db import connection, transaction
import json

@contextmanager
def tenant_context(operator_id: uuid.UUID):
    """
    Gerenciador de Contexto para Background Workers (Celery).
    Dropa os privilégios da conexão para 'authenticated'
    e injeta as claims do operator em app_metadata, assegurando que o 
    Postgres RLS (via current_operator_id()) rejeite qualquer transação 
    que tente cruzar a fronteira do inquilino.
    
    ATENÇÃO: O yield DEVE acontecer DENTRO do transaction.atomic() para que
    o SET LOCAL ROLE e set_config (transaction-local) permaneçam vivos.
    """
    # Claims formatadas para alinhar com current_operator_id() do schema.sql:
    # current_setting('request.jwt.claims')::json->'app_metadata'->>'operator_id'
    claims = json.dumps({
        "app_metadata": {"operator_id": str(operator_id)},
        "role": "authenticated"
    })
    
    with transaction.atomic():
        with connection.cursor() as cursor:
            # 1. Injeta a Identidade (transaction-local: morre ao commit/rollback)
            cursor.execute("SELECT set_config('request.jwt.claims', %s, true);", [claims])
            # 2. Dropa Privilégios (SET LOCAL morre ao fechar o atomic block)
            cursor.execute("SET LOCAL ROLE authenticated;")
        
        # O yield acontece DENTRO do atomic, garantindo que RLS sobrevive
        yield

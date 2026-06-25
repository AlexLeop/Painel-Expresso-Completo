"""
Management Command: Warm-up da Deny-list do Redis.

Lê a tabela SecurityDenylist (PostgreSQL) e reconstrói as chaves 
deny_list:driver:{id} e deny_list:operator:{id} no Redis.

Deve ser executado:
- Na inicialização de cada container Django (entrypoint do Docker)
- Após qualquer reinício do Redis
- Manualmente via: python manage.py warmup_denylist
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from accounts.models import SecurityDenylist, Operator
from config.redis_client import get_redis


class Command(BaseCommand):
    help = "Reconstrói a Deny-list no Redis a partir da tabela SecurityDenylist no PostgreSQL."

    def handle(self, *args, **options):
        r = get_redis()
        now = timezone.now()
        
        # 1. Warm-up de Drivers e Staff bloqueados
        active_blocks = SecurityDenylist.objects.filter(
            Q(expiresAt__isnull=True) | Q(expiresAt__gt=now)
        )
        
        driver_count = 0
        pipeline = r.pipeline()
        
        for block in active_blocks:
            if block.targetType == 'DRIVER':
                key = f"deny_list:driver:{block.targetId}"
                if block.expiresAt:
                    ttl = int((block.expiresAt - now).total_seconds())
                    if ttl > 0:
                        pipeline.setex(key, ttl, "1")
                else:
                    # Banimento permanente: TTL de 30 dias (renovado pelo cron)
                    pipeline.setex(key, 30 * 24 * 3600, "1")
                driver_count += 1
            elif block.targetType == 'STAFF':
                key = f"deny_list:staff:{block.targetId}"
                pipeline.setex(key, 30 * 24 * 3600, "1")
        
        # 2. Warm-up de Operators suspensos
        operator_count = 0
        suspended_operators = Operator.objects.filter(
            status__in=[Operator.OperatorStatus.SUSPENDED, Operator.OperatorStatus.CANCELED]
        )
        for op in suspended_operators:
            pipeline.setex(f"deny_list:operator:{op.id}", 30 * 24 * 3600, "1")
            operator_count += 1
        
        pipeline.execute()
        
        self.stdout.write(self.style.SUCCESS(
            f"Deny-list reconstruída: {driver_count} drivers + {operator_count} operators carregados no Redis."
        ))

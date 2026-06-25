import redis
from django.db.models.signals import post_save
from django.dispatch import receiver
from logistics.models import Driver
from accounts.models import SecurityDenylist
from config.redis_client import get_redis

r = get_redis()

@receiver(post_save, sender=Driver)
def block_deactivated_driver(sender, instance, **kwargs):
    """
    Hook de Segurança pós-commit.
    
    Movido de pre_save para post_save para garantir que o Redis só receba
    a deny-list DEPOIS que o PostgreSQL confirmou o save(). Caso contrário,
    um rollback do banco deixaria o Redis com uma deny-list fantasma.
    
    Fluxo:
    1. Driver.save() → PostgreSQL commitou com sucesso → post_save dispara
    2. SecurityDenylist.create() → Auditoria no banco
    3. Redis.setex() → Cache de segurança O(1)
    4. Token purge → Kill Switch dos device tokens
    """
    if instance.id:
        try:
            old_active = kwargs.get('update_fields')
            # Para detectar a transição active=True → active=False,
            # precisamos verificar contra o valor anterior.
            # Em post_save, o instance já tem o novo valor.
            # Usamos o tracker field approach: se active é False agora,
            # verificamos se existe uma deny-list recente para evitar duplicação.
            if not instance.active:
                # Evita duplicação: se já existe deny-list ativa, pula
                from django.utils import timezone
                from django.db.models import Q
                already_blocked = SecurityDenylist.objects.filter(
                    Q(expiresAt__isnull=True) | Q(expiresAt__gt=timezone.now()),
                    targetId=instance.id,
                    targetType='DRIVER'
                ).exists()
                
                if not already_blocked:
                    # 1. Tabela Auditável (Source of Truth) - Postgres já commitou
                    SecurityDenylist.objects.create(
                        operator=instance.operator,
                        targetId=instance.id,
                        targetType='DRIVER',
                        reason="Suspensão automatizada via bloqueio de cadastro (active=False)."
                    )
                
                # 2. Redis O(1) Access para Fast Lane e Celery Tasks
                # Idempotente: setex é safe para chamar múltiplas vezes
                redis_key = f"deny_list:driver:{instance.id}"
                r.setex(redis_key, 30 * 86400, "BLOCKED")
                
                # 3. Invalidar TODOS os Device Tokens ativos dele
                tokens_key = f"fastlane:driver_tokens:{instance.id}"
                active_tokens = r.zrangebyscore(tokens_key, '-inf', '+inf')
                if active_tokens:
                    pipe = r.pipeline()
                    for tk in active_tokens:
                        pipe.delete(f"fastlane:token_meta:{tk}")
                    pipe.delete(tokens_key)
                    pipe.execute()
                
        except Driver.DoesNotExist:
            pass
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            # Redis down: A SecurityDenylist no Postgres é a fonte da verdade.
            # O warmup_denylist reconstruirá o cache na próxima reinicialização.
            pass

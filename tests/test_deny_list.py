import pytest
from unittest.mock import patch, MagicMock
from logistics.models import Driver
from accounts.models import Operator, SecurityDenylist
import uuid


@pytest.mark.django_db
class TestDenyListSignals:
    @patch("accounts.signals.r")
    @patch.object(SecurityDenylist.objects, "filter")
    @patch.object(SecurityDenylist.objects, "create")
    def test_driver_deactivation_triggers_denylist(
        self, mock_create_denylist, mock_filter, mock_redis
    ):
        """post_save: motorista desativado deve criar deny-list + setar Redis."""
        operator_id = uuid.uuid4()
        driver_id = uuid.uuid4()

        # Simula que não existe deny-list duplicada
        mock_qs = MagicMock()
        mock_qs.exists.return_value = False
        mock_filter.return_value = mock_qs

        # Mock do ZRANGEBYSCORE retornando lista vazia
        mock_redis.zrangebyscore.return_value = []

        # A instância que está sendo salva (AGORA inativa)
        new_driver = MagicMock(spec=Driver)
        new_driver.id = driver_id
        new_driver.active = False
        new_driver.operator_id = operator_id
        new_driver.operator = MagicMock(spec=Operator)

        # Chama a função de signal manualmente (post_save)
        from accounts.signals import block_deactivated_driver

        block_deactivated_driver(sender=Driver, instance=new_driver)

        # Verifica se o Source of Truth foi gravado
        mock_create_denylist.assert_called_once_with(
            operator=new_driver.operator,
            targetId=new_driver.id,
            targetType="DRIVER",
            reason="Suspensão automatizada via bloqueio de cadastro (active=False).",
        )

        # Verifica se o Redis foi alimentado
        mock_redis.setex.assert_called_once_with(
            f"deny_list:driver:{driver_id}",
            2592000,  # 30 dias em segundos
            "BLOCKED",
        )

    @patch("accounts.signals.r")
    @patch.object(SecurityDenylist.objects, "filter")
    @patch.object(SecurityDenylist.objects, "create")
    def test_already_blocked_driver_skips_denylist_creation(
        self, mock_create, mock_filter, mock_redis
    ):
        """Se o driver já está na deny-list, NÃO deve criar duplicata."""
        mock_qs = MagicMock()
        mock_qs.exists.return_value = True  # Já existe!
        mock_filter.return_value = mock_qs
        mock_redis.zrangebyscore.return_value = []

        driver = MagicMock(spec=Driver)
        driver.id = uuid.uuid4()
        driver.active = False
        driver.operator = MagicMock(spec=Operator)

        from accounts.signals import block_deactivated_driver

        block_deactivated_driver(sender=Driver, instance=driver)

        # NÃO deve criar duplicata
        mock_create.assert_not_called()

        # MAS Redis deve ser atualizado (setex é idempotente)
        mock_redis.setex.assert_called_once()

    @patch("accounts.signals.r")
    def test_active_driver_does_not_trigger_denylist(self, mock_redis):
        """Se o driver está ativo, nada deve acontecer."""
        driver = MagicMock(spec=Driver)
        driver.id = uuid.uuid4()
        driver.active = True

        from accounts.signals import block_deactivated_driver

        block_deactivated_driver(sender=Driver, instance=driver)

        mock_redis.setex.assert_not_called()
        mock_redis.zrangebyscore.assert_not_called()

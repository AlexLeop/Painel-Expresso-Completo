import pytest
from accounts.models import Operator
from django.test import Client
import uuid

@pytest.mark.django_db
class TestPlatformBillingEngine:
    def test_calculate_platform_fee_floor_applied(self):
        """Quando o volume gerado é menor que o piso mínimo garantido, cobra o piso mínimo."""
        op = Operator(
            id=uuid.uuid4(),
            name="Operador Teste",
            platformCostPerDeliveryCents=40,    # R$ 0,40
            platformMinMonthlyFloorCents=29900,  # R$ 299,00
        )
        # 100 entregas * R$ 0,40 = R$ 40,00 (menor que R$ 299,00)
        res = op.calculate_platform_fee(100)
        assert res["deliveries_count"] == 100
        assert res["calculated_cents"] == 4000
        assert res["floor_cents"] == 29900
        assert res["final_fee_cents"] == 29900
        assert res["final_fee_reais"] == 299.00
        assert res["applied_floor"] is True

    def test_calculate_platform_fee_volume_exceeds_floor(self):
        """Quando o volume gerado ultrapassa o piso mínimo, fatura pelo volume total."""
        op = Operator(
            id=uuid.uuid4(),
            name="Operador Grande",
            platformCostPerDeliveryCents=40,    # R$ 0,40
            platformMinMonthlyFloorCents=29900,  # R$ 299,00
        )
        # 20.000 entregas * R$ 0,40 = R$ 8.000,00 (exemplo exato do usuário)
        res = op.calculate_platform_fee(20000)
        assert res["deliveries_count"] == 20000
        assert res["calculated_cents"] == 800000
        assert res["final_fee_cents"] == 800000
        assert res["final_fee_reais"] == 8000.00
        assert res["applied_floor"] is False

    def test_calculate_platform_fee_volume_tiers(self):
        """Calcula faixas progressivas quando configuradas."""
        op = Operator(
            id=uuid.uuid4(),
            name="Operador Faixas",
            platformCostPerDeliveryCents=40,
            platformMinMonthlyFloorCents=29900,
            platformVolumeTiers=[
                {"max": 1000, "rateCents": 50},   # até 1.000: R$ 0,50
                {"max": 5000, "rateCents": 40},   # de 1.001 a 5.000: R$ 0,40
                {"max": None, "rateCents": 30},   # acima de 5.000: R$ 0,30
            ]
        )
        # 6.000 entregas:
        # 1.000 * 50 = 50.000 (R$ 500)
        # 4.000 * 40 = 160.000 (R$ 1.600)
        # 1.000 * 30 = 30.000 (R$ 300)
        # Total calculado = 240.000 centavos = R$ 2.400,00
        res = op.calculate_platform_fee(6000)
        assert res["deliveries_count"] == 6000
        assert res["calculated_cents"] == 240000
        assert res["final_fee_cents"] == 240000
        assert res["final_fee_reais"] == 2400.00
        assert res["applied_floor"] is False

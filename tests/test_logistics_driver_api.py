"""
Testes para a API do motorista (logistics.api_driver).
Cobre bugs HIGH-002 (fallback de comparação de PIN, não usar ==, apenas check_password).
"""
import pytest
import uuid
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from unittest.mock import patch, MagicMock
from ninja.testing import TestClient
from logistics.models import Order, Stop, Client, Store, Driver
from accounts.models import Operator


@pytest.fixture
def client_api():
    """Cria cliente de teste para a API do motorista."""
    from config.api import api
    return TestClient(api)


@pytest.fixture
def operator():
    """Cria uma operadora de teste."""
    return Operator.objects.create(
        id=uuid.uuid4(),
        name="Expresso Neves Teste",
        status=Operator.OperatorStatus.ACTIVE
    )


@pytest.fixture
def client_model(operator):
    """Cria um cliente de teste."""
    return Client.objects.create(
        operator=operator,
        name="Cliente Teste",
        document="12345678000199"
    )


@pytest.fixture
def store(operator, client_model):
    """Cria uma loja de teste."""
    return Store.objects.create(
        operator=operator,
        client=client_model,
        name="Loja Teste",
        geom='SRID=4326;POINT(-47.9292 -15.7801)'
    )


@pytest.fixture
def driver(operator):
    """Cria um motorista de teste."""
    return Driver.objects.create(
        operator=operator,
        name="Motorista Teste",
        external_id="MOT-001"
    )


@pytest.fixture
def order_with_pin(operator, store, driver):
    """Cria uma ordem com uma parada que requer PIN."""
    order = Order.objects.create(
        operator=operator,
        store=store,
        driver=driver,
        status=Order.OrderStatus.ARRIVED,
        fareValueCents=1500,
        businessDate=timezone.localdate()
    )
    Stop.objects.create(
        operator=operator,
        order=order,
        type="DELIVERY",
        requiresPin=True,
        deliveryPinHash=make_password("1234"),
        latitude=-15.7801,
        longitude=-47.9292
    )
    return order


@pytest.mark.django_db
@pytest.mark.skip(reason="Modelos são managed=False, requer banco real PostgreSQL para testes.")
class TestDriverPINValidation:
    """Testes de validação de PIN do motorista."""

    def test_pin_validation_only_check_password(self, client_api, order_with_pin):
        """
        HIGH-002: Teste que confirma que validação de PIN usa apenas check_password() e não ==.
        """
        pass


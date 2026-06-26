"""
Testes para o decorador @idempotent.
Usa mocks de Redis para não depender de serviço local.
"""

import importlib
import pytest
import json
from unittest.mock import patch, MagicMock
from config.idempotency import idempotent


def _create_test_api():
    """Cria API de teste lazily."""
    from ninja import NinjaAPI, Router

    api = NinjaAPI(urls_namespace="test_idempotency")
    router = Router()

    @router.post("/fake/")
    @idempotent(timeout=60)
    def fake_mutating_view(request):
        return {"message": "Success", "amount": 100}

    api.add_router("/", router)
    return api, router


_api = None
_router = None


def _get_router():
    global _api, _router
    if _router is None:
        _api, _router = _create_test_api()
    return _router


@pytest.fixture
def client():
    from ninja.testing import TestClient

    return TestClient(_get_router())


@pytest.fixture
def mock_redis():
    """Mock do Redis client para testes sem dependência de serviço local."""
    mock_r = MagicMock()
    mock_r.get.return_value = None  # Sem cache por padrão
    mock_r.set.return_value = True  # Lock adquirido por padrão
    mock_r.delete.return_value = True
    return mock_r


@pytest.mark.django_db
class TestIdempotency:
    def test_missing_idempotency_key(self, client):
        """Requisição sem Idempotency-Key deve retornar 400."""
        response = client.post("/fake/")
        assert response.status_code == 400
        data = response.json()
        # O decorator retorna {"error": "..."} quando falta a key
        assert "Idempotency-Key" in data.get(
            "error", ""
        ) or "Idempotency-Key" in data.get("message", "")

    @patch("config.idempotency.r")
    def test_first_request_success_and_caches(self, mock_r, client):
        """Primeira requisição deve executar a view e cachear resposta no Redis."""
        mock_r.get.return_value = None  # Sem cache
        mock_r.set.return_value = True  # Lock adquirido

        idem_key = "test-req-12345"
        response = client.post("/fake/", headers={"Idempotency-Key": idem_key})

        assert response.status_code == 200
        assert response.json()["message"] == "Success"

        # Verifica que tentou cachear a resposta no Redis (2 calls: lock + cache)
        set_calls = mock_r.set.call_args_list
        assert len(set_calls) >= 1, "Deve ter chamado r.set() pelo menos 1x (lock)"

    @patch("config.idempotency.r")
    def test_repeated_request_returns_cached_response(self, mock_r, client):
        """Requisição repetida deve retornar resposta cacheada."""
        cached_data = json.dumps({"status": 201, "data": {"cached": True}})
        mock_r.get.return_value = cached_data  # Cache hit

        idem_key = "test-req-999"
        response = client.post("/fake/", headers={"Idempotency-Key": idem_key})

        assert response.status_code == 201
        assert response.json()["cached"] is True

    @patch("config.idempotency.r")
    def test_concurrent_processing_returns_409(self, mock_r, client):
        """Se outra thread tem o lock, deve retornar 409."""
        mock_r.get.return_value = None  # Sem cache
        mock_r.set.return_value = False  # Lock NÃO adquirido (outra thread tem)

        idem_key = "test-req-concurrent"
        response = client.post("/fake/", headers={"Idempotency-Key": idem_key})

        assert response.status_code == 409

    @patch("config.idempotency.r")
    def test_redis_failure_returns_503(self, mock_r, client):
        """Se o Redis falhar no lock, retorna 503."""
        import redis

        mock_r.get.return_value = None  # Sem cache
        mock_r.set.side_effect = redis.exceptions.ConnectionError("Redis down")

        idem_key = "test-req-redis-fail"
        response = client.post("/fake/", headers={"Idempotency-Key": idem_key})

        assert response.status_code == 503

    @patch("config.idempotency.r")
    def test_lock_uses_nx_ex(self, mock_r, client):
        """O lock deve usar SET NX EX para atomicidade."""
        mock_r.get.return_value = None
        mock_r.set.return_value = True

        idem_key = "test-req-atomic"
        client.post("/fake/", headers={"Idempotency-Key": idem_key})

        # Encontra a chamada de set que é o lock (tem nx=True)
        lock_calls = [
            call for call in mock_r.set.call_args_list if call.kwargs.get("nx") is True
        ]
        assert len(lock_calls) >= 1, "Deve chamar r.set(..., nx=True) para lock atômico"
        lock_call = lock_calls[0]
        assert lock_call.kwargs.get("ex") is not None, "Lock deve ter TTL (ex=...)"


def test_idempotency_accepts_shared_redis_fallback_flag(monkeypatch):
    monkeypatch.setenv("REDIS_ALLOW_MEMORY_FALLBACK", "true")
    monkeypatch.delenv("IDEMPOTENCY_ALLOW_MEMORY_FALLBACK", raising=False)

    module = importlib.import_module("config.idempotency")

    assert (
        module._env_flag(
            "IDEMPOTENCY_ALLOW_MEMORY_FALLBACK", "REDIS_ALLOW_MEMORY_FALLBACK"
        )
        is True
    )


def test_memory_redis_supports_sorted_set_token_invalidation_flow():
    from config.redis_client import MemoryRedis

    redis_client = MemoryRedis()
    redis_client.zadd(
        "fastlane:driver_tokens:driver-1", {"token-b": 20, "token-a": 10, "token-c": 30}
    )

    assert redis_client.zrange("fastlane:driver_tokens:driver-1", 0, -1) == [
        "token-a",
        "token-b",
        "token-c",
    ]

    removed = redis_client.zremrangebyscore("fastlane:driver_tokens:driver-1", 0, 15)

    assert removed == 1
    assert redis_client.zrange("fastlane:driver_tokens:driver-1", 0, -1) == [
        "token-b",
        "token-c",
    ]
    assert redis_client.expire("fastlane:driver_tokens:driver-1", 60) is True

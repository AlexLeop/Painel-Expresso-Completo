import json
import pytest
from unittest.mock import Mock, patch
from django.db import connection
from config.middleware import NativeAuthRLSMiddleware
from accounts.security import create_access_token
from contextlib import nullcontext


def test_rls_claims_use_is_local_true():
    """Garante que request.jwt.claims usa is_local=true (escopo de transação local)
    para evitar vazamento de contexto de tenant em poolers como PgBouncer."""
    middleware = NativeAuthRLSMiddleware(Mock(return_value="OK"))
    request = Mock()

    claims_payload = {
        "sub": "user-123",
        "email": "test@tenant.com",
        "role": "store_admin",
        "operator_id": "op-999",
        "store_id": "store-1",
        "is_platform_admin": False,
    }
    token = create_access_token(claims_payload)
    request.META = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    executed_queries = []

    class MockCursor:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def execute(self, sql, params=None):
            executed_queries.append((sql, params))

    with patch.object(connection, "vendor", "postgresql"):
        with patch.object(connection, "cursor", return_value=MockCursor()), patch(
            "config.middleware.transaction.atomic", return_value=nullcontext()
        ):
            response = middleware(request)

    assert response == "OK"
    assert len(executed_queries) >= 1

    first_sql, first_params = executed_queries[0]
    assert "set_config('request.jwt.claims', %s, true)" in first_sql, (
        f"A query RLS deve usar is_local=true para evitar vazamento no PgBouncer! SQL atual: {first_sql}"
    )
    
    parsed_claims = json.loads(first_params[0])
    assert parsed_claims["sub"] == "user-123"
    assert parsed_claims["app_metadata"]["operator_id"] == "op-999"


def test_runtime_ddl_disabled_in_db_api():
    """Garante que _ensure_database_schema no db_api é no-op para evitar DDL em runtime."""
    from config import db_api
    
    with patch("django.db.connection.cursor") as mock_cursor:
        db_api._ensure_database_schema()
        # Não deve executar nenhum cursor/DDL
        mock_cursor.assert_not_called()

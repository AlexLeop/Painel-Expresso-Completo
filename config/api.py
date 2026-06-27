import os
import jwt
from typing import Any, Optional
from ninja.security import HttpBearer
from ninja import NinjaAPI
from django.http import HttpRequest

SUPABASE_JWT_SECRET = os.environ.get(
    "SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-characters-long"
)
SUPABASE_JWT_AUDIENCE = os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")


class SupabaseJWTAuth(HttpBearer):
    """
    Extrator e Validador JWT do Supabase para o Django Ninja.
    Como o banco já usa RLS, esta classe atua garantindo que a API só seja acessada
    se a assinatura do token JWT for válida, populando o request com as claims.
    """

    def authenticate(self, request: HttpRequest, token: str) -> Optional[Any]:
        try:
            decoded = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience=SUPABASE_JWT_AUDIENCE,
            )
            return decoded

        except jwt.ExpiredSignatureError:
            return None  # Ninja mapeia None para 401 Unauthorized
        except jwt.InvalidTokenError:
            return None


# Importar Roters (A serem criados/recriados no Ninja)
from logistics.api_driver import router as driver_router
from logistics.api_operator import router as operator_router
from logistics.api_client import router as client_router
from logistics.api_admin import router as logistics_admin_router
from finance.api import router as finance_router
from finance.api_admin import router as finance_admin_router
from accounts.api import router as accounts_router
from accounts.api_admin import router as accounts_admin_router
from integration.api import router as integration_router
from todos.api import router as todos_router

api = NinjaAPI(
    title="Expresso Neves API",
    description="API de Gestão Logística e Financeira (Django Ninja)",
    version="1.0.0",
    auth=SupabaseJWTAuth(),
)

api.add_router("/driver/", driver_router)
api.add_router("/operator/", operator_router)
api.add_router("/client/", client_router)
api.add_router("/finance/", finance_router)
api.add_router("/accounts/", accounts_router)
api.add_router("/integration/", integration_router)
api.add_router("/todos/", todos_router)
api.add_router("/admin/accounts/", accounts_admin_router)
api.add_router("/admin/finance/", finance_admin_router)
api.add_router("/admin/logistics/", logistics_admin_router)


@api.exception_handler(Exception)
def global_exception_handler(request, exc):
    """
    Tratação global de exceções para a API Ninja.
    Captura exceções específicas (como transições de status inválidas) e
    retorna respostas com códigos de status e mensagens claras.
    """
    from logistics.exceptions import InvalidOrderStatusTransitionError

    if isinstance(exc, InvalidOrderStatusTransitionError):
        return api.create_response(
            request, {"success": False, "error": str(exc)}, status=400
        )

    # Para outras exceções não tratadas, loga silenciosamente e retorna 500 genérico
    import logging

    logger = logging.getLogger(__name__)
    logger.error("Unhandled API Exception:", exc_info=exc)

    return api.create_response(
        request, {"success": False, "error": "Erro interno do servidor."}, status=500
    )


@api.get("/health", auth=None)
def health_check(request):
    """Endpoint aberto para liveness probe com check no banco de dados."""
    from django.db import connection
    try:
        connection.ensure_connection()
        return {"status": "ok", "service": "slow_lane_django_ninja"}
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Health check falhou: {e}")
        return api.create_response(
            request, {"status": "error", "service": "slow_lane_django_ninja"}, status=503
        )

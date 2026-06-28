import os
import jwt
import logging
from typing import Any, Optional
from ninja.security import HttpBearer
from ninja.errors import HttpError
from django.http import HttpRequest
from ninja import NinjaAPI

SUPABASE_JWT_SECRET = os.environ.get(
    "SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-characters-long"
)
SUPABASE_JWT_AUDIENCE = os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")

logger = logging.getLogger(__name__)

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
            logger.error("Token Supabase expirado.")
            raise HttpError(401, "Token expirado")
        except jwt.InvalidTokenError as e_jwt:
            logger.error(f"jwt.decode falhou (InvalidTokenError): {e_jwt}. SUPABASE_JWT_SECRET configurado? {bool(os.environ.get('SUPABASE_JWT_SECRET'))}")
            # Fallback: tentar validar usando a API do Supabase diretamente
            # Isso é útil caso SUPABASE_JWT_SECRET não esteja configurado corretamente
            try:
                from config.supabase_client import supabase
                if not supabase:
                    logger.error("Fallback do Supabase falhou: cliente não inicializado (falta URL/KEY).")
                    raise HttpError(401, f"Falha na validação local ({str(e_jwt)}) e supabase_client não configurado no Django (SUPABASE_URL/SUPABASE_KEY ausentes)")
                
                user_res = supabase.auth.get_user(token)
                if user_res and getattr(user_res, 'user', None):
                    # A API confirmou a autenticidade, extrai as claims ignorando assinatura local
                    return jwt.decode(token, options={"verify_signature": False})
                
                logger.error("Token inválido via Supabase API")
                raise HttpError(401, "Token inválido via Supabase API")
            except HttpError:
                raise
            except Exception as e:
                logger.error(f"Erro no fallback do Supabase Auth: {e}")
                raise HttpError(401, f"Erro no fallback do Supabase Auth: {str(e)}")
            
            raise HttpError(401, f"Token inválido (InvalidTokenError: {str(e_jwt)})")


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

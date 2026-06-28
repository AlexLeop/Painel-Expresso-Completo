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
        """
        Extrai e valida o token JWT do Supabase recebido no header Authorization.
        
        A validação da assinatura é rigorosamente executada de forma local usando o 
        SUPABASE_JWT_SECRET para garantir complexidade de tempo O(1) e evitar ataques DoS.
        O uso de validação remota (fallback) está bloqueado por motivos de segurança.
        
        Args:
            request (HttpRequest): O contexto atual da requisição Django.
            token (str): O token Bearer JWT passado pelo cliente.
            
        Returns:
            Optional[Any]: Dicionário contendo as claims decodificadas do JWT.
            
        Raises:
            HttpError: 401 Unauthorized se a assinatura falhar ou o token expirar.
            
        Example:
            >>> auth = SupabaseJWTAuth()
            >>> claims = auth.authenticate(request, "eyJhbG...")
            >>> print(claims["sub"])
        """
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
            # Não logar a exceção crua se puder vazar dados confidenciais (por precaução).
            # Removida menção ao SUPABASE_JWT_SECRET nos logs para evitar vazamento.
            logger.error("Validação local do JWT falhou (InvalidTokenError).")
            # Sem fallback remoto: segurança em primeiro lugar (Fail-Closed).
            raise HttpError(401, "Token inválido (Assinatura rejeitada).")


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
from config.panel_api import panel_api
from config.db_api import router as db_router

api = NinjaAPI(
    title="Expresso Neves API",
    description="API de Gestão Logística e Financeira (Django Ninja)",
    version="1.0.0",
    auth=SupabaseJWTAuth(),
)

api.add_router("/db/", db_router)
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
    Tratação global de exceções genéricas para a API Ninja.
    """
    from logistics.exceptions import InvalidOrderStatusTransitionError
    from pydantic import ValidationError
    from postgrest.exceptions import APIError
    
    if isinstance(exc, InvalidOrderStatusTransitionError):
        return api.create_response(
            request, {"success": False, "error": str(exc)}, status=400
        )
    
    # Catch Pydantic Validation Errors
    if isinstance(exc, ValidationError):
        return api.create_response(
            request, 
            {"success": False, "error": "Erro de validação nos dados fornecidos.", "details": exc.errors()}, 
            status=422
        )
        
    # Catch PostgREST API Errors
    if isinstance(exc, APIError):
        # APIError has a dict payload: {'message': ..., 'details': ..., 'hint': ..., 'code': ...}
        # To avoid leaking sensitive DB details, we can return a sanitized version.
        error_info = exc.json() if hasattr(exc, 'json') and callable(exc.json) else str(exc)
        if isinstance(error_info, dict):
            # Safe keys
            safe_details = {
                "message": error_info.get("message", "Database Error"),
                "code": error_info.get("code")
            }
        else:
            safe_details = {"message": "Database interaction failed"}
        return api.create_response(
            request, 
            {"success": False, "error": "Erro de integração externa.", "details": safe_details}, 
            status=502
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

import os
import logging
from ninja import NinjaAPI
from accounts.auth import NativeJWTAuth, SupabaseJWTAuth

logger = logging.getLogger(__name__)

# Importar Routers
from logistics.api_driver import router as driver_router
from logistics.api_operator import router as operator_router
from logistics.api_client import router as client_router
from logistics.api_admin import router as logistics_admin_router
from finance.api import router as finance_router
from finance.api_admin import router as finance_admin_router
from accounts.api import router as accounts_router, api_auth_router
from accounts.api_admin import router as accounts_admin_router
from integration.api import router as integration_router
from todos.api import router as todos_router
from config.db_api import router as db_router

api = NinjaAPI(
    title="Expresso Neves API",
    description="API de Gestão Logística e Financeira (Django Ninja)",
    version="1.0.0",
    auth=NativeJWTAuth(),
)

api.add_router("/auth/", api_auth_router)

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
    Tratamento global de exceções para a API Ninja.
    """
    from ninja.errors import HttpError
    from logistics.exceptions import InvalidOrderStatusTransitionError
    from pydantic import ValidationError
    from postgrest.exceptions import APIError
    
    if isinstance(exc, HttpError):
        return api.create_response(
            request,
            {"success": False, "error": exc.message or str(exc)},
            status=exc.status_code,
        )

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
        error_info = exc.json() if hasattr(exc, 'json') and callable(exc.json) else str(exc)
        if isinstance(error_info, dict):
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

    # Para outras exceções não tratadas, loga stacktrace completo e retorna 500 genérico
    import logging
    logger = logging.getLogger(__name__)
    logger.exception(f"Unhandled API Exception: {exc}")

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

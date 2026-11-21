import json
import logging
from django.db import connection, transaction
from accounts.security import decode_token, SecurityError

logger = logging.getLogger(__name__)


class NativeAuthRLSMiddleware:
    """
    Middleware que intercepta o Bearer JWT nativo da plataforma,
    extrai o payload e, em conexões PostgreSQL, injeta os claims na sessão.
    Garante que o ORM do Django e o RLS do banco reflitam a identidade do usuário.
    Usa is_local=true para escopo local de transação, blindando contra vazamento
    de sessão em conexões agrupadas (PgBouncer/Supabase pooler).
    """
    ALLOWED_ROLES = {"authenticated", "service_role", "anon"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")

        jwt_payload = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                jwt_payload = decode_token(token, expected_type="access")
            except SecurityError as e:
                # Token expirado ou inválido
                logger.debug(f"Falha na validação do token nativo: {e}")
            except Exception as e:
                logger.warning(f"Erro inesperado na validação do token: {e}")

        if jwt_payload:
            request.auth = jwt_payload

        if connection.vendor == "postgresql":
            rls_claims = {}
            if jwt_payload:
                rls_claims = {
                    "sub": jwt_payload.get("sub"),
                    "email": jwt_payload.get("email"),
                    "app_metadata": {
                        "role": "platform_admin" if jwt_payload.get("is_platform_admin") else jwt_payload.get("role"),
                        "operator_id": str(jwt_payload.get("operator_id") or ""),
                    },
                }
            with transaction.atomic():
                if jwt_payload and jwt_payload.get("is_platform_admin"):
                    from uuid import UUID
                    from accounts.models import PlatformAdmin
                    try:
                        admin_id = UUID(str(jwt_payload.get("sub")))
                    except ValueError:
                        admin_id = None
                    if not admin_id or not PlatformAdmin.objects.filter(pk=admin_id).exists():
                        rls_claims = {}
                # Public authentication endpoints need tenant discovery while
                # their credential checks remain subject to ordinary policies.
                if not jwt_payload and request.path.rstrip("/") in {
                    "/api/auth/login", "/api/auth/refresh", "/api/auth/recover",
                    "/api/v1/auth/login", "/api/v1/auth/refresh",
                }:
                    identity = ""
                    try:
                        body = json.loads(request.body or b"{}")
                        identity = str(body.get("email") or "")
                        if request.path.rstrip("/").endswith("/refresh"):
                            token = request.COOKIES.get("neves_refresh") or body.get("refresh_token")
                            identity = str(decode_token(token, expected_type="refresh").get("sub", "")) if token else ""
                    except (ValueError, TypeError, AttributeError, SecurityError):
                        pass
                    if identity:
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT public.native_auth_operator(%s)", [identity])
                            row = cursor.fetchone()
                        if row and row[0]:
                            rls_claims = {"app_metadata": {"operator_id": str(row[0])}}
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('request.jwt.claims', %s, true);",
                        [json.dumps(rls_claims)],
                    )
                response = self.get_response(request)
                # Django can convert a view exception to an HTTP response before
                # returning through middleware. Never commit its partial writes.
                if getattr(response, "status_code", 200) >= 500:
                    transaction.set_rollback(True)
                return response

        # Requests sem auth rodam sem claims ou com SET LOCAL ROLE anon no Postgres
        return self.get_response(request)


# Mantém alias para retrocompatibilidade em settings.py
SupabaseRLSMiddleware = NativeAuthRLSMiddleware

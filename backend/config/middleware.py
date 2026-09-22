import json
import logging
from django.db import connection
from accounts.security import decode_token, SecurityError

logger = logging.getLogger(__name__)


class NativeAuthRLSMiddleware:
    """
    Middleware que intercepta o Bearer JWT nativo da plataforma,
    extrai o payload e, em conexões PostgreSQL, injeta os claims na sessão.
    Garante que o ORM do Django e o RLS do banco reflitam a identidade do usuário.
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
                jwt_payload = decode_token(token)
            except SecurityError as e:
                # Token expirado ou inválido
                logger.debug(f"Falha na validação do token nativo: {e}")
            except Exception as e:
                logger.warning(f"Erro inesperado na validação do token: {e}")

        if jwt_payload:
            request.auth = jwt_payload

            # Se a conexão for PostgreSQL, injeta os claims para conformidade com RLS
            if connection.vendor == "postgresql":
                rls_claims = {
                    "sub": jwt_payload.get("sub"),
                    "email": jwt_payload.get("email"),
                    "app_metadata": {
                        "role": "platform_admin" if jwt_payload.get("is_platform_admin") else jwt_payload.get("role"),
                        "operator_id": str(jwt_payload.get("operator_id") or ""),
                    },
                }
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT set_config('request.jwt.claims', %s, false);",
                            [json.dumps(rls_claims)],
                        )
                    return self.get_response(request)
                finally:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT set_config('request.jwt.claims', '', false);")

        # Requests sem auth rodam sem claims ou com SET LOCAL ROLE anon no Postgres
        return self.get_response(request)


# Mantém alias para retrocompatibilidade em settings.py
SupabaseRLSMiddleware = NativeAuthRLSMiddleware

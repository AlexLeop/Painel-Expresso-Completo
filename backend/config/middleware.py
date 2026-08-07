import os
import json
import jwt
from django.db import connection


class SupabaseRLSMiddleware:
    """
    Middleware que intercepta o JWT enviado pelo client (gerado pelo Supabase Auth),
    extrai o payload e injeta na transação atual do PostgreSQL.
    Dessa forma, o ORM do Django obedece estritamente ao RLS definido no banco.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")

        jwt_payload = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decodificação Estrita de Segurança
                secret = os.environ.get(
                    "SUPABASE_JWT_SECRET",
                    "super-secret-jwt-token-with-at-least-32-characters-long",
                )
                audience = os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")
                jwt_payload = jwt.decode(
                    token, secret, algorithms=["HS256"], audience=audience
                )
            except Exception as e:
                # Fallback: Se o token usar RS256 (novo padrão do Supabase) ou houver erro local,
                # validamos o token fazendo uma chamada oficial para a API do Supabase.
                try:
                    from config.supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if not supabase:
                        raise e
                    user_res = supabase.auth.get_user(token)
                    if user_res and getattr(user_res, 'user', None):
                        # A API do Supabase confirmou que o token é autêntico e válido!
                        # Agora podemos extrair as claims com segurança ignorando a assinatura local
                        jwt_payload = jwt.decode(token, options={"verify_signature": False})
                    else:
                        raise e
                except Exception as fallback_e:
                    from django.http import JsonResponse
                    return JsonResponse(
                        {"detail": "Invalid or expired token.", "error": str(e), "fallback_error": str(fallback_e)}, status=401
                    )

        # Antes de executar a view, abrimos o contexto no banco atrelado à transação
        if jwt_payload:
            # 1. Injetamos o payload no request para as rotas conseguirem ler a identidade
            request.auth = jwt_payload

            from django.db import transaction

            # 2. Abrimos uma Transação Atômica do início ao fim do Request.
            # Isso é vital pois o `set_config(..., true)` morreria imediatamente se o Django
            # continuasse no modo AUTOCOMMIT puro.
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Injeta os claims na sessão atual para o RLS ler via current_setting
                    claims_json = json.dumps(jwt_payload)
                    cursor.execute(
                        "SELECT set_config('request.jwt.claims', %s, true);",
                        [claims_json],
                    )

                    # SEGURANÇA: Drop de Privilégios (Sai de Superuser para Role Restrito)
                    role = jwt_payload.get("role", "authenticated")
                    # Whitelist estrita: impede injection via claim 'role' forjado no JWT
                    ALLOWED_ROLES = {"authenticated", "service_role"}
                    if role in ALLOWED_ROLES:
                        cursor.execute(f"SET LOCAL ROLE {role};")

                response = self.get_response(request)

                # O `true` no set_config garante que a variável morre ao dar o commit/rollback
                # ao final deste bloco transacional local.
                return response
        else:
            # Requisito não autenticado
            # Bloqueia vazamentos forçando a transação a rodar como visitante ('anon')
            from django.db import transaction

            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL ROLE anon;")
                return self.get_response(request)

# SUPERSEDED — HISTÓRICO — NÃO AUTORIZA GO-LIVE

> **AVISO DE AUTORIDADE:** Este documento foi **SUPERSEDED** e é mantido estritamente como registro histórico.
> A **ÚNICA AUTORIDADE NORMATIVA ATIVA** para ordem de execução, critérios, gates (G0–G10), piloto, homologação e go-live é [`docs/PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md`](file:///c:/Users/lxleo/Documents/Expresso%20Neves/Painel%20Expresso%20Neves%20e%20Django%20DRF/docs/PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md).
> Nenhuma afirmação ou checklist neste arquivo histórico autoriza implantação em produção.

---

# Plano de Implementação Avançado para Prontidão em Produção (Histórico)

> **Artigo de referência:** `docs/PLANO_IMPLEMENTACAO_PRODUCAO.md` (este arquivo - HISTÓRICO)
> **Derivado de:** Análise completa de prontidão (60+ lacunas mapeadas, 21 de criticidade alta)
> **Veredito base:** Sistema NÃO pronto para produção.
> **Estratégia:** Documento arquivado/substituído pelo V2.


---

## Índice

- [Convenções e Precedência](#convenções-e-precedência)
- [Onda 0 — Bloqueadores de Segurança](#onda-0--bloqueadores-de-segurança)
  - [T0-01 Restringir CORS a origens explícitas](#t0-01-restringir-cors-a-origens-explícitas)
  - [T0-02 Remover fallback JWT sem assinatura (fail-closed)](#t0-02-remover-fallback-jwt-sem-assinatura-fail-closed)
  - [T0-03 Aplicar auth global no panel_api](#t0-03-aplicar-auth-global-no-panel_api)
  - [T0-04 Remover headers de identidade populados pelo client](#t0-04-remover-headers-de-identidade-populados-pelo-client)
  - [T0-05 Webhook inbound fail-closed para provedores desconhecidos](#t0-05-webhook-inbound-fail-closed-para-provedores-desconhecidos)
  - [T0-06 Remover GEMINI_API_KEY do bundle do frontend](#t0-06-remover-gemini_api_key-do-bundle-do-frontend)
  - [T0-07 Desativar MockInterceptor em release no Android](#t0-07-desativar-mockinterceptor-em-release-no-android)
  - [T0-08 Trocar BASE_URL hardcoded do Android por BuildConfig](#t0-08-trocar-base_url-hardcoded-do-android-por-buildconfig)
  - [T0-09 Remover defaults inseguros de secrets em compose/easypanel](#t0-09-remover-defaults-inseguros-de-secrets-em-composeeasypanel)
  - [T0-10 Resolver conflito documental de homologação](#t0-10-resolver-conflito-documental-de-homologação)
- [Onda 1 — Resiliência Financeira e Deploy](#onda-1--resiliência-financeira-e-deploy)
  - [T1-01 Idempotência por order em settle_order (anti-duplo crédito)](#t1-01-idempotência-por-order-em-settle_order-anti-duplo-crédito)
  - [T1-02 acks_late + time_limit no Celery](#t1-02-acks_late--time_limit-no-celery)
  - [T1-03 Healthchecks e depends_on condicional no compose](#t1-03-healthchecks-e-depends_on-condicional-no-compose)
  - [T1-04 restart: unless-stopped em todos serviços do compose](#t1-04-restart-unless-stopped-em-todos-serviços-do-compose)
  - [T1-05 Migrar migrate do boot do container para job único](#t1-05-migrar-migrate-do-boot-do-container-para-job-único)
  - [T1-06 Limites de recursos no compose](#t1-06-limites-de-recursos-no-compose)
  - [T1-07 Race condition em get_or_create de Wallet/Invoice](#t1-07-race-condition-em-get_or_create-de-walletinvoice)
  - [T1-08 Idempotência: lock TTL por endpoint e hash do body](#t1-08-idempotência-lock-ttl-por-endpoint-e-hash-do-body)
  - [T1-09 MemoryRedis: implementar TTL no fallback](#t1-09-memoryredis-implementar-ttl-no-fallback)
  - [T1-10 TLS e senha no broker Redis em produção](#t1-10-tls-e-senha-no-broker-redis-em-produção)
- [Onda 2 — Observabilidade e Tratamento de Erros](#onda-2--observabilidade-e-tratamento-de-erros)
  - [T2-01 Sentry no frontend e Crashlytics no mobile](#t2-01-sentry-no-frontend-e-crashlytics-no-mobile)
  - [T2-02 Handler global de exceções no panel_api](#t2-02-handler-global-de-exceções-no-panel_api)
  - [T2-03 Exceções de domínio substituindo ValueError em finance](#t2-03-exceções-de-domínio-substituindo-valueerror-em-finance)
  - [T2-04 Correlation IDs propagando Django→Celery→Supabase](#t2-04-correlation-ids-propagando-djangocelerysupabase)
  - [T2-05 Logging estruturado independente de DEBUG](#t2-05-logging-estruturado-independente-de-debug)
  - [T2-06 Driver de log Docker com rotação](#t2-06-driver-de-log-docker-com-rotação)
  - [T2-07 ErrorBoundary na raiz do React com report remoto](#t2-07-errorboundary-na-raiz-do-react-com-report-remoto)
- [Onda 3 — Testes e CI/CD](#onda-3--testes-e-cicd)
  - [T3-01 Suíte de integração conectada ao PostGIS real](#t3-01-suite-de-integração-conectada-ao-postgis-real)
  - [T3-02 Testes de auth/RBAC/JWT e fallback sem assinatura](#t3-02-testes-de-authrbacjwt-e-fallback-sem-assinatura)
  - [T3-03 Vitest + Testing Library no frontend](#t3-03-vitest--testing-library-no-frontend)
  - [T3-04 Testes de contrato Retrofit no mobile + testDebugUnitTest no CI](#t3-04-testes-de-contrato-retrofit-no-mobile--testdebugunittest-no-ci)
  - [T3-05 Deploy automatizado no CI](#t3-05-deploy-automatizado-no-ci)
  - [T3-06 Scanning de segurança (Trivy/pip-audit/npm audit/gitleaks)](#t3-06-scanning-de-segurança-trivypip-auditnpm-auditgitleaks)
  - [T3-07 Lint gate não-bloqueante + paths filter + makemigrations --check](#t3-07-lint-gate-não-bloqueante--paths-filter--makemigrations---check)
- [Onda 4 — LGPD e Conformidade](#onda-4--lgpd-e-conformidade)
  - [T4-01 Workflows de DSAR (acesso/apagamento/portabilidade)](#t4-01-workflows-de-dsar-acessoapagamentoportabilidade)
  - [T4-02 Trilha de auditoria genérica (AuditEvent)](#t4-02-trilha-de-auditoria-genérica-auditevent)
  - [T4-03 Criptografia em colunas PII via pgcrypto](#t4-03-criptografia-em-colunas-pii-via-pgcrypto)
  - [T4-04 Validação completa de CPF (dígitos verificadores)](#t4-04-validação-completa-de-cpf-dígitos-verificadores)
- [Onda 5 — UX e Mobile](#onda-5--ux-e-mobile)
  - [T5-01 Implementar TrackingService real com FusedLocationProviderClient](#t5-01-implementar-trackingservice-real-com-fusedlocationproviderclient)
  - [T5-02 Forced update do mobile via endpoint /api/version-check](#t5-02-forced-update-do-mobile-via-endpoint-apiversion-check)
  - [T5-03 loadProfile com finally { setIsLoading(false) }](#t5-03-loadprofile-com-finally-setisloadingfalse)
  - [T5-04 Acessibilidade: role=alert e aria-live](#t5-04-acessibilidade-rolealert-e-aria-live)
  - [T5-05 Pinning de certificado no Android](#t5-05-pinning-de-certificado-no-android)
- [Onda 6 — Documentação](#onda-6--documentação)
  - [T6-01 Runbook operacional](#t6-01-runbook-operacional)
  - [T6-02 Diagrama ER e diagrama de sequência ponta-a-ponta](#t6-02-diagrama-er-e-diagrama-de-sequência-ponta-a-ponta)
  - [T6-03 ADRs para decisões-chave](#t6-03-adrs-para-decisões-chave)
- [Onda 7 — Hub de Integrações Plug-and-Play (CRM, ERP e Cardápios Digitais)](#onda-7--hub-de-integrações-plug-and-play-crm-erp-e-cardápios-digitais)
  - [7.1 Mapeamento Completo das Plataformas (54 plataformas)](#71-mapeamento-completo-das-plataformas-crm-erp-cardápios-delivery-logística-fidelidade)
  - [7.2 Arquitetura do Hub de Integrações](#72-arquitetura-do-hub-de-integrações)
  - [T7-01 Onboarding de Plataformas e Checklist de Documentação](#t7-01-onboarding-de-plataformas-e-checklist-de-documentação)
  - [T7-02 Refatoração: ABC + Registry + Circuit Breaker](#t7-02-refatoração-abc--registry--circuit-breaker)
  - [T7-03 Modelagem ProviderDefinition e DB-First Schema](#t7-03-modelagem-providerdefinition-e-db-first-schema)
  - [T7-04 Idempotência de Webhook Inbound (deduplicação)](#t7-04-idempotência-de-webhook-inbound-deduplicação)
  - [T7-05 Plano de Testes (Unit / Integração / Carga / Homologação)](#t7-05-plano-de-testes-unit--integração--carga--homologação)
  - [T7-06 Indicadores de Sucesso (SLI/SLO)](#t7-06-indicadores-de-sucesso-slislo)
  - [T7-07 Cronograma de Implementação por Fases](#t7-07-cronograma-de-implementação-por-fases)
  - [T7-08 Manutenibilidade, Escalabilidade e Compatibilidade com Versões Futuras](#t7-08-manutenibilidade-escalabilidade-e-compatibilidade-com-versões-futuras)
  - [T7-09 Sync Bidirecional com Reconciliação](#t7-09-sync-bidirecional-com-reconciliação)
- [Resumo de Precedência e Validação Hφil](#resumo-de-precedência-e-validação-høil)

---

## Convenções e Precedência

- **Crit batida**: Cada tarefa tem campo `Criticidade` (Alta/Média/Baixa), `Arquivos afetados`,
  `Validação`, `Risco se não fezer` e `Dependências`.
- **SNIPPETS**: Os exemplos de código contêm as alterações mínimas e diretas. Não devem ser
  colados cegamente — leia o arquivo e adapte ao redor.
- **Ordem**: Execute em ordem dentro de cada onda. Ondas anteriores são pré-requisito das
  posteriores (por ex., O2 depende de O1 due àsçe do tempo de falha de deploy).
- **Tarefas marcadas (BLOCK)** são bloqueadores de go-live; as demais são mitigadoras.
- **Commits atômicos**: Cada tarefa = 1 commit isolado, com verificação de testes verificados no
  respectivo `Validação`. Esta prática facilita rollback pelo `gsd-undo`.

---

## Onda 0 — Bloqueadores de Segurança

Esta onda reúne vulnerabilidades que poderiam comprometer a confidencialidade, integridade ou
disponibilidade imediatas. Nenhum deploy de produção deve ocorrer enquanto estas tarefas não
estiverem concluídas e validadas.

### T0-01 Restringir CORS a origens explícitas

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `settings.py:59-60` define `CORS_ALLOW_ALL_ORIGINS = True` junto de
`CORS_ALLOW_CREDENTIALS = True`, permitindo que qualquer origem faça requests autenticados. A env
`CORS_ALLOWED_ORIGINS` do `.env.example:16` fica inócuad.

**Risco se não fizer:** Qualquer site malicioso pode realizar operações autenticadas em nome do
usuário (CSRF + CORS override).

**Arquivos afetados:**
- `backend/config/settings.py`

**Correção:**

```python
# backend/config/settings.py — substituir linhas 58-67
# Em vez de CORS_ALLOW_ALL_ORIGINS=True (perigoso com credentials):
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

# Origens explícitas via env (lista separada por vírgula)
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173"
    ).split(",") if o.strip()
]

# Em dev, opcionalmente permitir todas (NUNCA em produção)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-request-id",  # correlation ID — ver T2-04
]
# Removidos: x-user-role, x-user-email, x-tenant-id  (ver T0-04)
```

**Validação:**
- `curl -I -H "Origin: https://site-malicioso.com" https://api.seu-dominio.com/api/v1/health`
  deve retornar sem `Access-Control-Allow-Origin: *`.
- `curl -I -H "Origin: https://seu-dominio.com" ...` deve incluir o header permitido.
- Teste automatizado: `backend/tests/test_settings.py` adiciona `test_cors_blocked_origin`.

### T0-02 Remover fallback JWT sem assinatura (fail-closed)

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `middleware.py:42-45` e `api.py:61-69` fazem `jwt.decode(token,
options={"verify_signature": False})` quando a validação local falha e o `supabase.auth.get_user`
retorna user. O comentário em `api.py:29-30` diz "fallback remoto bloqueado", mas o código faz o
oposto — aceita tokens sem verificar assinatura.

**Risco se não fizer:** Token manipulado com claims arbitrárias (ex.: `role=service_role`) é
aceito; bypass de RLS e RBAC.

**Arquivos afetados:**
- `backend/config/middleware.py`
- `backend/config/api.py`

**Correção (middleware):**

```python
# backend/config/middleware.py — substituir linhas 23-52
            try:
                # Decodificação Estrita de Segurança — fail-closed
                secret = os.environ.get("SUPABASE_JWT_SECRET")
                if not secret:
                    # Sem secret em produção = falha de config; não prosseguir
                    import logging
                    logging.getLogger(__name__).error(
                        "SUPABASE_JWT_SECRET ausente — requisição rejeitada (fail-closed)"
                    )
                    from django.http import JsonResponse
                    return JsonResponse(
                        {"detail": "Configuração de autenticação ausente."},
                        status=503,
                    )
                audience = os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")
                jwt_payload = jwt.decode(
                    token, secret, algorithms=["HS256"], audience=audience
                )
            except jwt.ExpiredSignatureError:
                from django.http import JsonResponse
                logging.getLogger(__name__).warning(
                    "Token expirado — rejeitando (fail-closed)"
                )
                return JsonResponse({"detail": "Token expirado."}, status=401)
            except jwt.InvalidTokenError as e:
                # Falha local = rejeitar. NUNCA fazer fallback remoto com verify_signature=False.
                logging.getLogger(__name__).warning(
                    "Assinatura/claims inválidas — rejeitando (fail-closed): %s", e
                )
                from django.http import JsonResponse
                return JsonResponse(
                    {"detail": "Token inválido."}, status=401
                )
            except Exception as e:
                logging.getLogger(__name__).exception(
                    "Erro inesperado na validação JWT — rejeitando (fail-closed)"
                )
                from django.http import JsonResponse
                return JsonResponse(
                    {"detail": "Erro de autenticação."}, status=401
                )
```

**Correção (api.py):**

```python
# backend/config/api.py — substituir linhas 47-77
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
            logger.warning("Token Supabase expirado.")
            raise HttpError(401, "Token expirado")
        except jwt.InvalidTokenError as e_jwt:
            # Fail-closed: sem fallback remoto que aceita token sem assinatura.
            logger.warning("Token inválido (assinatura/claims): %s", e_jwt)
            raise HttpError(401, "Token inválido")
```

**Validação:**
- Teste `test_auth.py::test_forged_token_rejected` com token assinado com secret errado deve
  retornar 401 sem `fallback_error` no corpo.
- Confirmar que token válido (assinado com `SUPABASE_JWT_SECRET` real) ainda retorna 200.

### T0-03 Aplicar auth global no panel_api

**Criticidade:** Alta (BLOCK) · **Dependências:** T0-02 (auth fail-closed)

**Problema:** `panel_api.py:7` instancia `NinjaAPI` sem `auth=`, deixando endpoints como
`POST /machine/rides/create` (`panel_api.py:253`), `POST /machine/rides/cancel` (`panel_api.py:375`),
`GET /machine/credits/driver/balance` (`panel_api.py:205`) e `GET /machine/rides` (`panel_api.py:85`)
abertos a qualquer origin. Diversos endpoints admin fazem checagem inline (`panel_api.py:462,482`)
em vez de usar dependência Ninja reutilizável.

**Risco se não fizer:** Qualquer pessoa na internet pode criar/cancelar corridas e verificar saldos
de motoristas sem autenticação.

**Arquivos afetados:**
- `backend/config/panel_api.py`

**Correção:**

```python
# backend/config/panel_api.py — substituir linhas 7-8
panel_api = NinjaAPI(
    urls_namespace="panel_api",
    auth=SupabaseJWTAuth(),  # auth global — todos endpoints exigem JWT por padrão
)

# Endpoint público (health/echo) pode abrir exceção explícita:
# @panel_api.get("/healthz", auth=None)
# def panel_healthz(request): ...
```

Para endpoints admin, padronizar via dependência reutilizável em vez de checagem inline:

```python
# Exemplo para /admin/operators (substituir checagem inline em panel_api.py:462,482)
from accounts.auth import platform_admin_required

@panel_api.get("/admin/operators", auth=SupabaseJWTAuth())
@platform_admin_required  # dependência que consulta PlatformAdmin no banco
def list_operators(request):
    ...
```

**Observação:** `accounts/auth.py` já provê `platform_admin_required` (depois de T0-04, pode ser
simplificado — neste ponto ainda depende da correção). Aplicar `auth_bearer` em todos os endpoints
sem `auth=` atuais: `change-tenant` (`panel_api.py:77`), `get_rides` (`panel_api.py:85`),
`get_schedules` (`panel_api.py:143`), `get_drivers` (`panel_api.py:186`), `get_driver_balance`
(`panel_api.py:205`), `get_rides_tracking` (`panel_api.py:214`), `create_ride` (`panel_api.py:253`),
`cancel_ride` (`panel_api.py:375`), `get_receipt` (`panel_api.py:445`).

**Validação:**
- `curl -X POST https://api.seu-dominio.com/api/machine/rides/create` sem header deve retornar 401.
- `curl` com token válido deve retornar 200/422 (não 500).
- Teste `test_panel_api_auth.py` cobrindo 401 em cada endpoint antes protegido.

### T0-04 Remover headers de identidade populados pelo client

**Criticidade:** Alta (BLOCK) · **Dependências:** T0-03

**Problema:** `frontend/src/lib/api.ts:17-34` injeta `X-Tenant-Id`, `X-User-Role` e
`X-User-Email` a partir do `localStorage`; `settings.py:64-67` permite esses headers via CORS.
Se o backend os utilizar (em especial o fast_lane ou rotas de admin), há bypass de RBAC e
escalada de tenant.

**Risco se não fizer:** Cliente malicioso pode forjar `role=admin` e acessar endpoints admin sem
ser admin.

**Arquivos afetados:**
- `frontend/src/lib/api.ts`
- `backend/config/settings.py` (removido em T0-01)
- Qualquer backend que leia esses headers (auditar `request.META.get("HTTP_X_USER_ROLE")` etc.)

**Correção (frontend):**

```typescript
// frontend/src/lib/api.ts — substituir linhas 14-34
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);

  // REMOVIDO: população de X-Tenant-Id, X-User-Role, X-User-Email via localStorage.
  // Toda identidade DEVE vir exclusivamente do JWT decodificado pelo backend.
  // Ver T0-02 para o fluxo autoritativo (middleware extrai claims do token).

  // Correlation ID (ver T2-04)
  headers.set("X-Request-Id", crypto.randomUUID());

  if (
    options.body &&
    (!options.headers ||
      !(options.headers as Record<string, string>)["Content-Type"])
  ) {
    headers.set("Content-Type", "application/json");
  }
```

**Auditoria backend:** Buscar por `HTTP_X_TENANT_ID`, `HTTP_X_USER_ROLE`, `HTTP_X_USER_EMAIL` em
todo o backend e substituir por leitura de `request.auth.get("tenant_id", ...)` etc. onde
necessário. Se o fast_lane usa esses headers, aplicar T0-04 a ele também e mapear via JWT.

**Validação:**
- `grep -r "HTTP_X_TENANT_ID\|HTTP_X_USER_ROLE" backend/` deve retornar vazio.
- Teste `test_auth.py::test_role_from_jwt_not_header` simula header forjado `role=admin` em cliente
  não-admin e assegura 403.

### T0-05 Webhook inbound fail-closed para provedores desconhecidos

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `integration/adapters.py:207-209` retorna `True` se `provider_name` não for
`DELIVERY_DIRETO` nem `ANOTA_AI`. Qualquer provedor (iFood, 99Food, atacante) tem webhook aceito
sem validação de assinatura.

**Risco se não fizer:** Atacante dispara webhooks falsos que criam/cancelam pedidos em nome de
provedores reais.

**Arquivos afetados:**
- `backend/integration/adapters.py`

**Correção:**

```python
# backend/integration/adapters.py — substituir linhas 206-209
    provider_name = normalize_provider(provider)

    # Whitelist explícita de provedores suportados. Falhar fechado (fail-closed)
    # para qualquer outro; implementar verificação específica antes de habilitar.
    if provider_name == "DELIVERY_DIRETO":
        pass  # fluxo HMAC SHA256 abaixo
    elif provider_name == "ANOTA_AI":
        pass  # fluxo token compartilhado abaixo
    elif provider_name == "IFOOD":
        # TODO(P0): implementar verificação x-siteguard-signature própria do iFood.
        # Atualmente, REJEITAR até implementar (não confiar cegamente).
        return False
    else:
        # Provedor não suportado: rejeitar por padrão (fail-closed).
        return False

    # Fluxo ANOTA_AI (preservado):
    if provider_name == "ANOTA_AI":
        if not secret:
            return False
        query_token = (query_params or {}).get("token")
        header_token = (
            get_header(headers, "x-integration-token")
            or get_header(headers, "x-anota-token")
            or _extract_bearer_token(headers)
        )
        received_token = query_token or header_token
        if not received_token:
            return False
        return hmac.compare_digest(str(received_token), str(secret))

    # Fluxo DELIVERY_DIRETO (preservado):
    if not secret:
        return False
    received_signature = get_header(headers, "x-deliverydireto-signature")
    if not received_signature:
        return False
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, received_signature)
```

**Validação:**
- `test_integration_adapters.py::test_unknown_provider_rejected` (novo): provedor `99_FOOD` sem
  signature deve retornar `False` (antes era `True`).
- `test_integration_adapters.py::test_ifood_rejected_until_implemented`: retorna `False`.

### T0-06 Remover GEMINI_API_KEY do bundle do frontend

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `vite.config.ts:40` injeta `process.env.GEMINI_API_KEY` no bundle do cliente via
`define`. Chave de IA paga exposta no JS do navegador.

**Risco se não fizer:** Qualquer visitante extrai a chave do bundle e abusa da IA paga.

**Arquivos afetados:**
- `frontend/vite.config.ts`
- `frontend/package.json` (remover `@google/genai` de dependencies — T-paralelo)
- Backend: criar endpoint proxy `POST /api/v1/integration/ai/complete` com auth + rate limit (T3-06
  adiciona rate limit; este endpoint pode ser stub agora)

**Correção (vite.config.ts):**

```typescript
// frontend/vite.config.ts — remover linhas 40-43 do bloco define
    define: {
      "import.meta.env.VITE_SUPABASE_URL": JSON.stringify(supabaseUrl),
      "import.meta.env.VITE_SUPABASE_ANON_KEY": JSON.stringify(supabaseAnonKey),
      // REMOVIDO: process.env.GEMINI_API_KEY e process.env.GOOGLE_MAPS_PLATFORM_KEY
      // (qualquer chamada de IA deve ser proxy no backend com auth; ver T0-06/T3-06).
      // Se maps for obrigatório no client, usar VITE_GOOGLE_MAPS_BROWSER_KEY (restrita
      // por HTTP referrer no console do Google) — não a chave Platform server-side.
    },
```

**Ação paralela (package.json):** Remover `@google/genai` de `dependencies` e adicionar um endpoint
backend:

```python
# backend/integration/api.py (novo router montado em T3-05 se necessário)
# @api.post("/integration/ai/complete", auth=SupabaseJWTAuth())
# def ai_complete(request, payload: AICompleteIn) -> AICompleteOut:
#     # Proxy para Gemini usando GEMINI_API_KEY server-side; rate limit por user.
#     ...
```

**Validação:**
- `grep -r "GEMINI_API_KEY\|AIza" frontend/dist/` retorna vazio após `npm run build`.
- `npm run build` deve continuar verde sem `@google/genai`.

### T0-07 Desativar MockInterceptor em release no Android

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `NetworkModule.kt:48` adiciona `MockInterceptor()` no `OkHttpClient` em todas as
builds, incluindo release. Respostas fictícias em produção.

**Risco se não fizer:** App de produção retorna dados mockados sem saber (silencioso).

**Arquivos afetados:**
- `mobile/app/src/main/java/com/nevesgo/app/di/NetworkModule.kt`
- `mobile/app/src/main/java/com/nevesgo/app/di/MockInterceptor.kt` (manter, mas envolver em BuildConfig.DEBUG)

**Correção:**

```kotlin
// mobile/app/src/main/java/com/nevesgo/app/di/NetworkModule.kt — substituir linhas 43-50
    @Provides
    @Singleton
    fun provideOkHttpClient(authInterceptor: Interceptor): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)

        // Mock apenas em build debug — nunca em release
        if (BuildConfig.DEBUG) {
            builder.addInterceptor(MockInterceptor())
        }

        // TODO(T5-05): adicionar CertificatePinner aqui

        return builder.build()
    }
```

**Validação:**
- Build release `./gradlew assembleRelease` — `MockInterceptor` não deve aparecer no APK (verificar
  via `apkanalyzer` ou observando requests reais em staging).
- Build debug continua com mock (comportamento preservado).

### T0-08 Trocar BASE_URL hardcoded do Android por BuildConfig

**Criticidade:** Alta (BLOCK) · **Dependências:** T0-07

**Problema:** `NetworkModule.kt:29` define `BASE_URL = "http://10.0.2.2:8000/api/v1/"` (emulador).
Em dispositivo real, todas as chamadas falham. `BuildConfig.API_BASE_URL` já existe
(`build.gradle.kts:29`).

**Risco se não fizer:** App de produção instalado em dispositivo real não consegue falar com a API.

**Arquivos afetados:**
- `mobile/app/src/main/java/com/nevesgo/app/di/NetworkModule.kt`
- `mobile/app/build.gradle.kts` (confirmar default em produção)

**Correção (NetworkModule.kt):**

```kotlin
// mobile/app/src/main/java/com/nevesgo/app/di/NetworkModule.kt — substituir linhas 28-29
    // Base URL via BuildConfig (definida em build.gradle.kts:29 a partir de NEVESGO_API_BASE_URL).
    // Em debug, default cai em 10.0.2.2 (emulador); em release, DEVE ser definição de produção.
    private const val BASE_URL = com.nevesgo.app.BuildConfig.API_BASE_URL
```

**build.gradle.kts** — fortalecer o default:

```kotlin
// mobile/app/build.gradle.kts — substituir linhas 12-15
val configuredApiBaseUrl = providers.gradleProperty("NEVESGO_API_BASE_URL")
  .orElse(providers.environmentVariable("NEVESGO_API_BASE_URL"))
  .get()  // SEM default seguro — falhar em release se não definido

// ... em buildTypes:
  buildTypes {
    release {
      // ...
      // Garantir que produção não caia em URL de emulador
      val resolvedUrl = configuredApiBaseUrl
      check(!resolvedUrl.contains("10.0.2.2")) {
          "NEVESGO_API_BASE_URL em release não pode apontar para 10.0.2.2 (emulador)"
      }
      buildConfigField("String", "API_BASE_URL", "\"$resolvedUrl\"")
    }
    debug {
      // default de debug pode ser 10.0.2.2
      val debugUrl = if (configuredApiBaseUrl.contains("10.0.2.2")) configuredApiBaseUrl
                     else "http://10.0.2.2:8000/api/v1/"
      buildConfigField("String", "API_BASE_URL", "\"$debugUrl\"")
    }
  }
```

**Nota:** O snippet acima separa `buildConfigField` por buildType — mover a linha existente
(`build.gradle.kts:29`) do `defaultConfig` para dentro de `release`/`debug`.

**Validação:**
- Build release sem `NEVESGO_API_BASE_URL` falha com mensagem clara.
- Build release com URL de produção contém essa URL no `BuildConfig`.

### T0-09 Remover defaults inseguros de secrets em compose/easypanel

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `docker-compose.yml:23-50` traz `SUPABASE_JWT_SECRET=${...:-super-secret-...}`,
`DJANGO_SECRET_KEY=${...:-sua-chave-secreta-aqui}`, `DATABASE_URL=${...:-...senha...}`. Se `.env`
faltar, serviços sobem com placeholders. `easypanel-schema.json:33,61,89,120,145` tem
`DJANGO_ALLOWED_HOSTS=*`. Redis sem senha em `docker-compose.yml:34`.

**Risco se não fizer:** Em ambientes onde `.env` é acidentalmente omitido, produção fica exposta
com secret default.

**Arquivos afetados:**
- `docker-compose.yml`
- `docker-compose.local.yml`
- `easypanel-schema.json`
- `easypanel-template.json`

**Correção (docker-compose.yml — bloco django):**

```yaml
# docker-compose.yml — substituir environment em django, celery_worker, celery_beat, fastapi
    environment:
      # SEM defaults de secrets — subir falha se .env faltar
      - SUPABASE_URL=${SUPABASE_URL:?SUPABASE_URL obrigatório}
      - SUPABASE_KEY=${SUPABASE_KEY:?SUPABASE_KEY obrigatório}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET:?SUPABASE_JWT_SECRET obrigatório}
      - DATABASE_URL=${DATABASE_URL:?DATABASE_URL obrigatório}
      - DIRECT_URL=${DIRECT_URL:?DIRECT_URL obrigatório}
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY obrigatório}
      - DJANGO_DEBUG=False
      - DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS:?DJANGO_ALLOWED_HOSTS obrigatório}
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS:?CORS_ALLOWED_ORIGINS obrigatório}
      - SECURE_SSL_REDIRECT=True
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - REDIS_URL=${REDIS_URL:?REDIS_URL obrigatório}
      - CELERY_BROKER_URL=${CELERY_BROKER_URL:?CELERY_BROKER_URL obrigatório}
      - GEMINI_API_KEY=${GEMINI_API_KEY:?GEMINI_API_KEY obrigatório}
      - GOOGLE_MAPS_PLATFORM_KEY=${GOOGLE_MAPS_PLATFORM_KEY:?GOOGLE_MAPS_PLATFORM_KEY obrigatório}
      - EVOLUTION_API_URL=${EVOLUTION_API_URL:?EVOLUTION_API_URL obrigatório}
      - EVOLUTION_API_KEY=${EVOLUTION_API_KEY:?EVOLUTION_API_KEY obrigatório}
      - EVOLUTION_INSTANCE_NAME=${EVOLUTION_INSTANCE_NAME:?EVOLUTION_INSTANCE_NAME obrigatório}
      - EVOLUTION_INSTANCE_TOKEN=${EVOLUTION_INSTANCE_TOKEN:?EVOLUTION_INSTANCE_TOKEN obrigatório}
      - NEVESGO_API_BASE_URL=${NEVESGO_API_BASE_URL:?NEVESGO_API_BASE_URL obrigatório}
```

**Redis com senha:**

```yaml
# docker-compose.yml — serviço redis
  redis:
    image: redis:7-alpine
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD:?REDIS_PASSWORD obrigatório}"]
    volumes:
      - redis_data:/data

# Ajustar REDIS_URL em todos os serviços:
  - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
```

**easypanel-schema.json:** Remover todos os valores literais de secrets; referenciar o secret
store do EasyPanel (`${SECRET_NEVESGO_JWT}`) — documentação específica do EasyPanel. Eliminar
`DJANGO_ALLOWED_HOSTS=*`.

**docker-compose.local.yml:** Pode manter defaults para dev, mas comente explícito avisando "DEV
APENAS".

**Validação:**
- `docker compose up` sem `.env` deve falhar com mensagem clara ("DJANGO_SECRET_KEY obrigatório").
- Em ambiental de dev com `.env` completo, todos os serviços sobem.
- EasyPanel deploy falha se secrets não configurados no secret store.

### T0-10 Resolver conflito documental de homologação

**Criticidade:** Alta (BLOCK) · **Dependências:** T0-01 a T0-09 concluídas

**Problema:** `docs/matriz_homologacao.md` afirma "SISTEMA APTO PARA PRODUÇÃO" (14 itens
Aprovado), contradizendo as 3 perícias técnicas (`PERICIA_INFRA_DEPLOY.md`,
`PERICIA_PRONTIDAO_FUNCIONAL.md`, `NEVESGO_AUDITORIA_E_PLANO_TATICO.md`) que concluem "não apto".
A divergência induce decisões erradas.

**Risco se não fizer:** Decisão de go-live baseada em documento falso positivo.

**Arquivos afetados:**
- `docs/matriz_homologacao.md` (revisar/reescrever ou arquivar)
- Não há código — decisão documental.

**Ação:**
1. Revisar cada um dos 14 itens "Aprovado" contra os achados das 3 perícias.
2. Para itens onde a perícia contradiz, marcar como "Reprovado" ou "Parcial" com link para a
   evidência (ex.: item X — ver `PERICIA_PRONTIDAO_FUNCIONAL.md:144-154` — era Reprovado).
3. Decidir explicitamente qual documento é a fonte de verdade daqui em diante. Recomendação:
   `matriz_homologacao.md` passa a ser derivada das perícias + deste plano, e qualquer item
   "Aprovado" precisa referenciar evidência de code/teste.
4. Atualizar o "Veredito" conforme conclusões desta análise parcial (após Onda 0+1).

**Validação:**
- Leitura cruzada: cada item "Aprovado" deve ter correspondente em `PERICIA_*` concordando OU uma
  nota explícita explicando divergência resolvida.
- Reunião de alinhamento com CEO/CTO registrada em ata referenciada no documento.

---

## Onda 1 — Resiliência Financeira e Deploy

Esta onda elimina riscos de perda de dados financeiros (duplo crédito), quedas sem recuperação e
downtime evitável. Após esta onda, o sistema está apto a um go-live controlado.

### T1-01 Idempotência por order em settle_order (anti-duplo crédito)

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `finance/services.py:29` envolve a operação em `transaction.atomic()`, mas não
verifica se a order já foi liquidada. Se o Celery rodar `settle_order` duas vezes para mesma order
(retry sem ack tardio), há **duplo crédito** ao motorista e duplicação de line item na fatura.

**Risco se não fizer:** Perda financeira; reconsiliação manual; perda de confiança do motorista.

**Arquivos afetados:**
- `backend/finance/services.py`
- `backend/finance/models.py` (confirmar constraint unique em `WalletTransaction(order, category=PAYOUT)`)

**Correção:**

```python
# backend/finance/services.py — substituir linhas 18-29
class SettlementEngine:
    @staticmethod
    def settle_order(order: Order):
        """
        Liquida uma Order com idempotência por order — evita duplo crédito em retries Celery.
        """
        if order.status != Order.OrderStatus.COMPLETED:
            # Exceção de domínio (ver T2-03) em vez de ValueError opaco.
            from finance.exceptions import InvalidSettlementState
            raise InvalidSettlementState(
                "Apenas ordens concluídas podem ser liquidadas."
            )

        with transaction.atomic():
            # Select for update na order para bloquear reentry concorrente
            locked_order = Order.objects.select_for_update().get(pk=order.pk)

            # IDEMPOTÊNCIA: se já existe PAYOUT para esta order, não reprocessar.
            already_settled = WalletTransaction.objects.filter(
                source_operator_wallet__operator=locked_order.operator,
                category=WalletTransaction.TransactionCategory.PAYOUT,
                destination_driver_wallet__driver=locked_order.driver,
                # O modelo deve ter FK para order; se não tiver, adicionar (abaixo).
                order=locked_order,
            ).exists()
            if already_settled:
                logger.info(
                    "Order %s já liquidada — idempotência evitou duplo crédito.",
                    locked_order.id,
                )
                return

            # ... restante do método (linhas 31-141 originais) preservado ...
```

**Migration necessária:** Adicionar FK `order` em `WalletTransaction` (com `null=True` para
histórico) + `unique_together = ("order", "category")` para garantir a idempotência no nível do
banco:

```python
# backend/finance/models.py — em class WalletTransaction
    order = models.ForeignKey(
        "logistics.Order",
        on_delete=models.PROTECT,
        null=True,  # histórico pode ser nulo
        related_name="wallet_transactions",
    )
    class Meta:
        # managed=False alinhado ao schema Supabase; a constraint precisa ser
        # adicionada também em docs/schema.sql (migration Supabase CLI).
        constraints = [
            models.UniqueConstraint(
                fields=["order", "category"],
                name="unique_order_payout_per_category",
                condition=models.Q(category="PAYOUT"),
            )
        ]
```

**schema.sql (Supabase migration):**

```sql
-- docs/schema.sql e migration Supabase CLI
ALTER TABLE finance_wallettransaction
    ADD COLUMN IF NOT EXISTS order_id UUID REFERENCES logistics_order(id);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_payout_per_order
    ON finance_wallettransaction(order_id, category)
    WHERE category = 'PAYOUT';
```

**Validação:**
- `test_concurrency_finance.py` (remover `@pytest.mark.skip`): criar order COMPLETED, chamar
  `settle_order` duas vezes e assegurar só 1 `WalletTransaction` PAYOUT.
- Confirmar constraint no banco (tentar insert duplicado deve falhar).

### T1-02 acks_late + time_limit no Celery

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `config/celery.py` não configura `task_acks_late` nem `task_time_limit`. Tasks de
billing e integração podem travar indefinidamente ou serem perdidas em crash sem reexecução.

**Risco se não fizer:** Task de billing horário perdida em crash = não liquidação; task de
integração travada consome worker indefinidamente.

**Arquivos afetados:**
- `backend/config/settings.py`

**Correção:**

```python
# backend/config/settings.py — adicionar após linha 178 (CELERY block)
CELERY_TASK_ACKS_LATE = True              # só dar ack após conclusão (reexecuta em crash)
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # rejeitar se worker morre mid-task
CELERY_TASK_TIME_LIMIT = 300              # 5 minutos hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 240         # 4 minutos soft (exceção SoftTimeLimitExceeded)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1     # fair scheduling (1 task por worker de cada vez)
CELERY_TASK_DEFAULT_QUEUE = "default"
# Filas separadas por prioridade (worker dedicado por fila via compose)
CELERY_TASK_ROUTES = {
    "finance.tasks.*": {"queue": "billing"},
    "integration.tasks.*": {"queue": "integration"},
    "logistics.tasks.process_telemetry_*": {"queue": "telemetry"},
    "logistics.tasks.process_geofence_*": {"queue": "telemetry"},
}
```

**docker-compose.yml** — ajustar worker para filas dedicadas:

```yaml
# docker-compose.yml — celery_worker (substituir command)
  celery_worker:
    command: celery -A config worker -Q billing,integration,default -l info --concurrency=2
  # Opcionalmente adicionar serviço separado para telemetry:
  celery_worker_telemetry:
    build: { context: ./backend, dockerfile: Dockerfile }
    command: celery -A config worker -Q telemetry -l info --concurrency=4 --max-tasks-per-child=1000
```

**Validação:**
- Teste de resiliência: matar o worker mid-task e confirmar que a task reexecuta (não fica
  stranded).
- Task que excede 240s recebe `SoftTimeLimitExceeded` e falha graciosamente.

### T1-03 Healthchecks e depends_on condicional no compose

**Criticidade:** Alta (BLOCK) · **Dependências:** T0-09

**Problema:** `docker-compose.yml` não tem `healthcheck` em nenhum serviço. `depends_on` é simples
— nginx pode iniciar antes de django estar ouvindo, gerando 502.

**Risco se não fizer:** Restart do host = 502 durante startup; sem auto-detecção de unhealthy.

**Arquivos afetados:**
- `backend/config/urls.py` (adicionar `/healthz`)
- `backend/config/api.py` (já tem `/health` sem auth — auditar)
- `docker-compose.yml`
- `docker-compose.local.yml`

**Correção (backend — `/healthz`):**

```python
# backend/config/urls.py — adicionar
from django.http import JsonResponse

def healthz(request):
    """Healthcheck readiness — leve, sem depender de auth/DB pesado."""
    from django.db import connections
    from django.db.utils import OperationalError
    try:
        connections["default"].cursor().execute("SELECT 1")
    except OperationalError:
        return JsonResponse({"status": "unhealthy"}, status=503)
    return JsonResponse({"status": "ok"}, status=200)

urlpatterns = [
    # ...
    path("healthz/", healthz),  # sem auth
]
```

**docker-compose.yml:**

```yaml
# docker-compose.yml — adicionar em cada serviço
  redis:
    image: redis:7-alpine
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD}"]
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    volumes:
      - redis_data:/data

  django:
    # ...
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 30s  # dá tempo para migrate/collectstatic
    depends_on:
      redis:
        condition: service_healthy

  fastapi:
    # ...
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/healthz')"]
      interval: 15s
      timeout: 5s
      retries: 5
    depends_on:
      redis:
        condition: service_healthy

  frontend:
    # ...
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:5173/api/health', r=>process.exit(r.statusCode===200?0:1))"]
      interval: 15s
      timeout: 5s
      retries: 5

  nginx:
    # ...
    depends_on:
      django:
        condition: service_healthy
      fastapi:
        condition: service_healthy
      frontend:
        condition: service_healthy
```

**Validação:**
- `docker compose up` observa ordem: nginx só inicia após django saudável.
- `docker inspect --format='{{.State.Health.Status}}' <container>` mostra `healthy` em 60s.

### T1-04 restart: unless-stopped em todos serviços do compose

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `docker-compose.yml` não tem `restart` em nenhum serviço. Se um processo cai, o
container não reinicia automaticamente.

**Risco se não fizer:** Quada de Celery/gunicorn = serviço morto até intervenção manual.

**Arquivos afetados:** `docker-compose.yml`, `docker-compose.local.yml`

**Correção:**

```yaml
# Adicionar em TODOS serviços do docker-compose.yml:
    restart: unless-stopped

# Em docker-compose.local.yml, também (mas pode ser `restart: "no"` em dev para debug).
```

**Validação:**
- `docker compose kill django` e observar reinício automático.

### T1-05 Migrar migrate do boot do container para job único

**Criticidade:** Alta (BLOCK) · **Dependências:** T1-03

**Problema:** `docker-compose.yml:12-16` roda `migrate && warmup_denylist && collectstatic &&
gunicorn` em série. Durante a migration, nginx aponta para um container que ainda não ouve 8000 →
502. Impossibilita zero-downtime mesmo com rolling.

**Risco se não fizer:** Toda subida = 502 por N segundos/minutes; migração de schema demorada =
indisponibilidade prolongada.

**Arquivos afetados:**
- `docker-compose.yml`
- Opcional: novo serviço `django_migrate` (job one-shot)

**Correção (job one-shot antes do django):**

```yaml
# docker-compose.yml — novo serviço que roda migrações uma vez
  django_migrate:
    build: { context: ./backend, dockerfile: Dockerfile }
    command: >
      bash -c "python manage.py migrate --no-input &&
               python manage.py warmup_denylist &&
               python manage.py collectstatic --no-input"
    environment:
      # ... mesmas envs do django (pode usar YAML anchor para evitar duplicação)
    depends_on:
      redis:
        condition: service_healthy
    restart: "no"  # job one-shot

  django:
    build: { context: ./backend, dockerfile: Dockerfile }
    command: gunicorn --bind 0.0.0.0:8000 --workers 3 --max-requests 1000 --max-requests-jitter 50 config.wsgi:application
    # ...
    depends_on:
      django_migrate:
        condition: service_completed  # só sobe após migrate terminar
      redis:
        condition: service_healthy
```

**Para zero-downtime real em produção:** Migrações devem ser backward-compatíveis (não-breaking
schema changes primeiro, deploy do código depois). Princípio:
1. Migration A: adiciona colunas/views (não-breaking).
2. Deploy código que usa novas colunas.
3. Migration B: remove colunas antigas (após código novo 100% em rollout).

**Validação:**
- Na primeira subida, `django_migrate` completa antes de `django` iniciar.
- Deploy subsequente sem mudança de schema: `django_migrate` é rápido (no-op).

### T1-06 Limites de recursos no compose

**Criticidade:** Média · **Dependências:** T1-03

**Problema:** `docker-compose.yml` não tem `deploy.resources.limits`/`reservations`. Workers Celery
podem OOM no host compartilhado (EasyPanel).

**Risco se não fizer:** Um pico de telemetria/migration derruba outros serviços no mesmo host.

**Arquivos afetados:** `docker-compose.yml`

**Correção:**

```yaml
# Exemplo para django:
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          memory: 256M

# celery_worker:
    deploy:
      resources:
        limits:
          cpus: "1.5"
          memory: 1G

# fastapi:
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M

# nginx:
    deploy:
      resources:
        limits:
          cpus: "0.25"
          memory: 64M

# frontend:
    deploy:
      resources:
        limits:
          cpus: "0.25"
          memory: 128M
```

**Observação:** `deploy.resources` em compose non-swarm é respeitado pelo Docker Compose v2
(`docker compose`cmd). Verificar versão instalada no host EasyPanel.

**Validação:**
- `docker stats` mostra limites em vigor.

### T1-07 Race condition em get_or_create de Wallet/Invoice

**Criticidade:** Alta (BLOCK) · **Dependências:** T1-01

**Problema:** `finance/services.py:52` e `:67` fazem `Wallet.objects.get_or_create(...)` antes do
`select_for_update`. Dois requests simultâneos criando wallet para mesmo driver podem causar
race; `:99-119` cria `WeeklyStoreInvoice` sem lock.

**Risco se não fizer:** Constraint unique impede duplicação mas gera `IntegrityError` não tratado
→ 500; em sistemas sem a constraint, cria saldos duplicados.

**Arquivos afetados:**
- `backend/finance/services.py`

**Correção:**

```python
# backend/finance/services.py — substituir linhas 51-72
            # 2. Resgatar carteiras — DENTRO do lock pessimista para evitar race
            operator_wallet, _ = OperatorInternalWallet.objects.select_for_update().get_or_create(
                operator=order.operator
            )

            store_cost = (
                order.fareValueCents
                if getattr(order, "fareValueCents", None)
                else contract.rideFeePerDeliveryCents
            )

            if order.driver:
                driver_wallet, _ = Wallet.objects.select_for_update().get_or_create(
                    driver=order.driver, operator=order.operator
                )
                # O resto do bloco (75-88) preservado ...
```

**WeeklyStoreInvoice com lock:**

```python
# backend/finance/services.py — substituir linhas 99-119
            # Lock pessimista em semana existente; criar com get_or_create dentro do atomic
            import datetime
            weekday = b_date.weekday()
            start_date = b_date - datetime.timedelta(days=weekday)
            end_date = start_date + datetime.timedelta(days=6)

            invoice, created = WeeklyStoreInvoice.objects.select_for_update().get_or_create(
                store=order.store,
                operator=order.operator,
                startDate=start_date,
                endDate=end_date,
                defaults={"status": WeeklyStoreInvoice.InvoiceStatus.DRAFT},
            )
            # Se existia mas estava FINALIZED, abrir exceção é opção — aqui mantém apenas se DRAFT.
            if invoice.status != WeeklyStoreInvoice.InvoiceStatus.DRAFT:
                from finance.exceptions import InvoiceAlreadyFinalized
                raise InvoiceAlreadyFinalized(
                    f"Fatura da loja {order.store.id} para semana {start_date} não está DRAFT."
                )
```

**Validação:**
- `test_concurrency_finance.py::test_settle_order_concurrent_same_driver`: disparar 2
  `settle_order` concorrentes e assegurar só 1 PAYOUT.

### T1-08 Idempotência: lock TTL por endpoint e hash do body

**Criticidade:** Alta (BLOCK) · **Dependências:** T0-02, T1-09

**Problema:** `config/idempotency.py:117` usa `ex=60` (lock expira em 60s — inadequado para
requests lentos como integrações). O cache não inclui hash do body — dois requests com mesmo
`Idempotency-Key` mas payloads diferentes compartilham resposta.

**Risco se não fizer:** Request lento deixa lock expirar; outro request entra; violação da
garantia de idempotência. Hash ausente permite que cliente malicioso use mesma key com payload
diferente para obter resposta errada.

**Arquivos afetados:**
- `backend/config/idempotency.py`

**Correção:**

```python
# backend/config/idempotency.py — substituir linhas 67-122
def idempotent(timeout=86400, schema=None, lock_timeout=300):
    """
    Decorador para endpoints mutáveis (POST, PUT, PATCH).
    - timeout: TTL do cache da resposta (default 24h).
    - lock_timeout: TTL do lock (default 5min — adequado para integrações lentas).
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method not in ["POST", "PUT", "PATCH"]:
                return view_func(request, *args, **kwargs)

            idem_key = request.headers.get("Idempotency-Key")
            if not idem_key:
                return JsonResponse(
                    {"error": "Idempotency-Key header is required"}, status=400
                )

            user_id = (
                request.auth.get("sub", "anonymous")
                if hasattr(request, "auth") and request.auth
                else "anonymous"
            )
            path = request.path

            # Hash do body incluído na chave para evitar colisão entre payloads diferentes
            import hashlib
            body_hash = hashlib.sha256(request.body or b"").hexdigest()[:16]

            redis_lock_key = f"idempotency:lock:{user_id}:{path}:{idem_key}"
            redis_response_key = (
                f"idempotency:response:{user_id}:{path}:{idem_key}:{body_hash}"
            )

            # Cache hit retorna resposta anterior
            try:
                cached_response = r.get(redis_response_key)
                if cached_response:
                    data = json.loads(cached_response)
                    return JsonResponse(data.get("data"), status=data.get("status"))
            except Exception:
                if ALLOW_MEMORY_FALLBACK:
                    cached = _mem_get(redis_response_key)
                    if cached:
                        return JsonResponse(
                            cached.get("data"), status=cached.get("status")
                        )

            # Lock com TTL configurável (default 5min para requests lentos)
            mem_lock_acquired = False
            try:
                acquired = r.set(redis_lock_key, "PROCESSING", nx=True, ex=lock_timeout)
                if not acquired:
                    return JsonResponse(
                        {"message": "Requisição duplicada e em processamento."},
                        status=409,
                    )
            except Exception:
                if not ALLOW_MEMORY_FALLBACK:
                    return JsonResponse({"error": "Failed to acquire lock"}, status=503)
                mem_lock_acquired = _mem_acquire(redis_lock_key)
                if not mem_lock_acquired:
                    return JsonResponse(
                        {"message": "Requisição duplicada e em processamento."},
                        status=409,
                    )

            try:
                response = view_func(request, *args, **kwargs)
                # ... restante (linhas 137-167) preservado
```

**Nota:** Aplicar o decorador em TODOS endpoints mutáveis do `panel_api` (T0-03 já exige auth; aqui
adiciona idempotência): `create_ride`, `cancel_ride`, `change_tenant`, `create_operator`.

**Validação:**
- `test_idempotency.py::test_different_body_same_key_returns_diff_response`: mesma key com body
  diferente não compartilha cache.
- `test_idempotency.py::test_lock_timeout_5min`: simular request > 60s não deixa lock expirar.

### T1-09 MemoryRedis: implementar TTL no fallback

**Criticidade:** Alta (BLOCK) · **Dependências:** Nenhuma

**Problema:** `config/redis_client.py:23-33` ignora `ex` em `set` e `_timeout` em `setex`. Locks
in-memory nunca expiram — viés de inanição de locks em fallback.

**Risco se não fizer:** Em produção sem Redis (fallback), locks nunca liberam; idempotência
denega requisições legítimas indefinidamente.

**Arquivos afetados:**
- `backend/config/redis_client.py`

**Correção:**

```python
# backend/config/redis_client.py — substituir linhas 11-35
class MemoryRedis:
    def __init__(self):
        self._values: dict[str, Any] = {}
        self._expirations: dict[str, float] = {}  # novo: rastreia expiração
        self._sets: dict[str, set[str]] = {}
        self._zsets: dict[str, dict[str, float]] = {}
        self._lists: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def _evict_expired(self, key: str):
        """Remove chave se expirou (lazy eviction)."""
        exp = self._expirations.get(key)
        if exp is not None and exp < time.time():
            self._values.pop(key, None)
            self._expirations.pop(key, None)

    def ping(self):
        return True

    def get(self, key: str):
        with self._lock:
            self._evict_expired(key)
            return self._values.get(key)

    def set(self, key: str, value: Any, nx: bool = False, ex: Optional[int] = None):
        import time
        with self._lock:
            self._evict_expired(key)
            if nx and key in self._values:
                return False
            self._values[key] = value
            if ex is not None:
                self._expirations[key] = time.time() + int(ex)
            else:
                self._expirations.pop(key, None)
            return True

    def setex(self, key: str, timeout: int, value: Any):
        import time
        with self._lock:
            self._values[key] = value
            self._expirations[key] = time.time() + int(timeout)
            return True
```

**Em `delete`, limpar `_expirations`:**

```python
    def delete(self, key: str):
        with self._lock:
            removed = 0
            if key in self._values:
                del self._values[key]
                removed += 1
            self._expirations.pop(key, None)
            if key in self._sets:
                del self._sets[key]
                removed += 1
            if key in self._zsets:
                del self._zsets[key]
                removed += 1
            return removed
```

**Validação:**
- `test_idempotency.py::test_memory_redis_ttl`: chamar `setex(k, 1, v)`, aguardar 2s, `get(k)`
  retorna `None`.
- `set(k, v, nx=True, ex=1)` similar.

### T1-10 TLS e senha no broker Redis em produção

**Criticidade:** Média · **Dependências:** T0-09

**Problema:** `docker-compose.yml:34` usa `redis://redis:6379/1` sem TLS nem senha em produção.
Configurado em T0-09 para ter senha; aqui reforçamos TLS em produção.

**Arquivos afetados:** `.env.example`, `settings.py`, `celery.py`

**Ação:**
- Documentar em `.env.example`: em produção, `REDIS_URL=rediss://:senha@redis:6379/1` (note
  `rediss://` com TLS).
- Redis em container local não precisa TLS (network interno); em EasyPanel com Redis externo,
  requerer `rediss://`.
- Validar no boot: `if "rediss://" in REDIS_URL: ...` (já suportado pelo client `redis`).

**Validação:**
- Em staging/produção, `REDIS_URL=rediss://...` e workers conectam sem erro.

---

## Onda 2 — Observabilidade e Tratamento de Erros

Após esta onda, falhas deixam de ser silenciosas: há rastreabilidade ponta-a-ponta, captura de
erros no client, e o backend responde com semântica HTTP apropriada em vez de 500 opaco.

### T2-01 Sentry no frontend e Crashlytics no mobile

**Criticidade:** Alta · **Dependências:** Nenhuma

**Problema:** `frontend/src/lib/logger.ts:17-19` só faz `console.error`; `frontend/src/components/ErrorBoundary.tsx:25-27` só loga no console. `NevesGoApplication.kt` é vazio — sem `UncaughtExceptionHandler`; `mobile/app/build.gradle.kts` não traz `firebase-crashlytics` (embora tenha `firebase-bom`).

**Risco se não fizer:** Bugs em produção são invisíveis para o time; usuários reportam falhas genéricas sem contexto.

**Arquivos afetados:**
- `frontend/package.json` (adicionar `@sentry/react`)
- `frontend/src/main.tsx` (inicializar Sentry)
- `frontend/src/components/ErrorBoundary.tsx` (capturar e reportar)
- `mobile/app/build.gradle.kts` (adicionar `firebase-crashlytics`)
- `mobile/app/src/main/java/com/nevesgo/app/NevesGoApplication.kt` (inicializar)

**Correção (frontend):**

```typescript
// frontend/src/main.tsx — substituir conteúdo
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import App from "./App.tsx";
import "./index.css";

if (import.meta.env.PROD) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
    tracesSampleRate: 0.1, // 10% de traces em prod para custo controlado
    denyUrls: [/localhost/],
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Sentry.ErrorBoundary fallback={<p>Algo deu errado. Recarregue a página.</p>}>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </Sentry.ErrorBoundary>
  </StrictMode>,
);
```

```typescript
// frontend/src/components/ErrorBoundary.tsx — em componentDidCatch
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary capturou:", error, info);
    // Sentry.ErrorBoundary já captura se envolto; aqui reportamos contexto extra.
    import("@sentry/react").then((Sentry) => {
      Sentry.captureException(error, { extra: { componentStack: info.componentStack } });
    });
  }
```

**Adicionar `.env`**: `VITE_SENTRY_DSN=https://...` (não é secret, pode ficar no bundle).

**Correção (mobile):**

```kotlin
// mobile/app/build.gradle.kts — em dependencies (adicionar)
  implementation(platform(libs.firebase.bom))
  implementation("com.google.firebase:firebase-crashlytics-ktx")
```

```kotlin
// mobile/app/src/main/java/com/nevesgo/app/NevesGoApplication.kt — substituir vazio
package com.nevesgo.app

import android.app.Application
import com.google.firebase.FirebaseApp
import com.google.firebase.crashlytics.FirebaseCrashlytics
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class NevesGoApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        FirebaseApp.initializeApp(this)
        FirebaseCrashlytics.getInstance().isCrashlyticsCollectionEnabled = !BuildConfig.DEBUG
    }
}
```

**Observação:** Adicionar plugin `com.google.firebase.crashlytics` em `plugins {}` do `build.gradle.kts`.

**Validação:**
- Frontend: forçar `throw new Error("test")` em uma página; ver evento no Sentry.
- Mobile: `throw RuntimeException("test")` em uma tela; ver crash no Crashlytics.

### T2-02 Handler global de exceções no panel_api

**Criticidade:** Alta · **Dependências:** T0-03

**Problema:** `config/panel_api.py` não define `@panel_api.exception_handler(Exception)`. Exceções viram 500 do Django com `DEBUG` exposto; o `catch-all` (`panel_api.py:538`) mascara erros. `str(e)` é vazado em `api_admin.py:65,107`, `middleware.py:50`, `panel_api.py:533`.

**Risco se não fizer:** Erros expõem stack traces/details internos; sem status code semântico.

**Arquivos afetados:**
- `backend/config/panel_api.py`

**Correção:**

```python
# backend/config/panel_api.py — adicionar após a definição de panel_api (linha 8)
import logging
from ninja.errors import HttpError
from pydantic import ValidationError
from logistics.exceptions import InvalidOrderStatusTransitionError

panel_logger = logging.getLogger("panel_api")


@panel_api.exception_handler(InvalidOrderStatusTransitionError)
def panel_order_transition_handler(request, exc):
    return panel_api.create_response(
        request, {"success": False, "error": str(exc)}, status=400
    )


@panel_api.exception_handler(ValidationError)
def panel_validation_handler(request, exc):
    return panel_api.create_response(
        request, {"success": False, "error": exc.errors()}, status=422
    )


@panel_api.exception_handler(HttpError)
def panel_http_error_handler(request, exc):
    # Preserva status code; não loga (erros esperados como 401/403/404).
    return panel_api.create_response(
        request, {"success": False, "error": str(exc)}, status=exc.status_code
    )


@panel_api.exception_handler(Exception)
def panel_global_handler(request, exc):
    # Loga internamente com WARNING; não expõe str(exc) ao cliente.
    panel_logger.exception("Erro não tratado no panel_api: %s", exc)
    return panel_api.create_response(
        request,
        {"success": False, "error": "Erro interno do servidor. Tente novamente."},
        status=500,
    )
```

**Padronizar em todo o backend:** Remover `str(e)` de respostas 401/500 em `api_admin.py:65,107`, `middleware.py:50-52`. Logar `logger.exception` internamente; responder `{"detail": "..."}` genérico.

**Validação:**
- `curl -X POST .../api/machine/rides/create` com payload inválido retorna 422 (não 500).
- Endpoint que lança `Exception` retorna `{"error": "Erro interno do servidor..."}` (sem stack trace).

### T2-03 Exceções de domínio substituindo ValueError em finance

**Criticidade:** Média · **Dependências:** T2-02

**Problema:** `finance/services.py:27,40` usa `raise ValueError(...)`. O handler global `api.py:113-161` não mapeia `ValueError` → resposta 500 opaca perdendo contexto de erro de negócio.

**Risco se não fizer:** Client não consegue distinguir "ordem não pode ser liquidada" (422) de "erro interno" (500).

**Arquivos afetados:**
- `backend/finance/exceptions.py` (novo)
- `backend/finance/services.py`
- `backend/config/api.py` (handler global já estendido em T2-02)

**Correção:**

```python
# backend/finance/exceptions.py (novo arquivo)
class FinanceDomainError(Exception):
    """Base para erros de domínio financeiro — mapeada para 422."""
    status_code = 422

class InvalidSettlementState(FinanceDomainError):
    pass

class InvoiceAlreadyFinalized(FinanceDomainError):
    pass

class InsufficientFunds(FinanceDomainError):
    status_code = 409
```

```python
# backend/finance/services.py — substituir linhas 27 e 40
from finance.exceptions import InvalidSettlementState
# ...
    if order.status != Order.OrderStatus.COMPLETED:
        raise InvalidSettlementState("Apenas ordens concluídas podem ser liquidadas.")
# ...
    raise InvalidSettlementState("Loja sem contrato ativo. Não é possível liquidar a corrida.")
```

```python
# backend/config/api.py — estender global_exception_handler (linhas 113-161)
from finance.exceptions import FinanceDomainError

@api.exception_handler(FinanceDomainError)
def finance_domain_handler(request, exc: FinanceDomainError):
    return api.create_response(
        request, {"success": False, "error": str(exc)}, status=exc.status_code
    )
```

**Validação:**
- `settle_order` em order não-COMPLETED retorna 422 com `{"error": "Apenas ordens concluídas..."}`.

### T2-04 Correlation IDs propagando Django→Celery→Supabase

**Criticidade:** Média · **Dependências:** Nenhuma

**Problema:** Django, FastAPI e Celery logam sem ID de correlação entre request → task → chamada externa. Impossível rastrear latência ponta-a-ponta.

**Risco se não fizer:** Debug de incidentes requerSlash correlação manual por timestamp; investigação lenta.

**Arquivos afetados:**
- `backend/config/middleware.py` (gerar/propagar `X-Request-Id`)
- `backend/config/celery.py` (propagar via `task_id` ou header customizado)
- `nginx.conf` (gerar/encaminhar)
- `backend/config/settings.py` (logging filter)

**Correção (middleware):**

```python
# backend/config/middleware.py — adicionar no topo e no início de __call__
import uuid

class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.correlation_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        response = self.get_response(request)
        response["X-Request-Id"] = request.correlation_id
        return response
```

```python
# backend/config/settings.py — MIDDLEWARE (adicionar no início)
MIDDLEWARE = [
    "config.middleware.CorrelationIdMiddleware",
    # ... restante
]

# LOGGING formatter JSON (adicionar correlation_id):
formatters = {
    "json": {
        "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "corr": "%(correlation_id)s", "message": "%(message)s"}',
    }
}
# Filter:
filters = {
    "correlation": {
        "()": "config.logging_filters.CorrelationIdFilter",
    }
}
# Aplicar `filters: ["correlation"]` no handler console.
```

```python
# backend/config/logging_filters.py (novo)
import logging
from threading import local

_local = local()
_local.correlation_id = "-"

def set_correlation_id(cid: str):
    _local.correlation_id = cid

class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        from django.utils import timezone
        record.correlation_id = getattr(_local, "correlation_id", "-")
        return True
```

**Celery:** usar `before_task_publish` e `task_prerun` signals para propagar:

```python
# backend/config/celery.py — adicionar
from celery.signals import task_prerun

@task_prerun.connect
def set_task_correlation(task_id, task, *args, **kwargs):
    from config.logging_filters import set_correlation_id
    # Correlation = task_id (celery) para correlacionar logs de tasks.
    set_correlation_id(f"task:{task_id}")
```

**Nginx:** gerar ID se header não presente:

```nginx
# nginx.conf — em server block
proxy_set_header X-Request-Id $http_x_request_id;  # se vier do client
# Adicionar add_header X-Request-Id $request_id; na resposta
```

**Validação:**
- Fazer request ao Django → observar `corr` no log.
- Task Celery disparada pelo endpoint → log da task carrega `corr: task:...` (ou correlacionada).

### T2-05 Logging estruturado independente de DEBUG

**Criticidade:** Média · **Dependências:** Nenhuma

**Problema:** `settings.py:189` define `LOGGING` condicional apenas `if not DEBUG`. Em dev, logs sem JSON.

**Risco se não fizer:** Logs de dev não têm formato consistente; ferramentas de parsing quebram em staging dev.

**Arquivos afetados:** `backend/config/settings.py`

**Correção:**

```python
# backend/config/settings.py — mover LOGGING para fora do `if not DEBUG`
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation": {"()": "config.logging_filters.CorrelationIdFilter"},
    },
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "corr": "%(correlation_id)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["correlation"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
}

# Manter SECURE_* dentro do `if not DEBUG` (hardening de produção), mas LOGGING fora.
```

**Validação:**
- Em dev (`DEBUG=True`), logs em formato JSON.
- Em prod, mesmo formato + hardening.

### T2-06 Driver de log Docker com rotação

**Criticidade:** Média · **Dependências:** T1-03

**Problema:** `docker-compose.yml` e `docker-compose.local.yml` não têm driver de log (default `json-file` sem limite → disco cheio).

**Risco se não fizer:** Disco do host EasyPanel enche em semanas/meses; queda de serviços.

**Arquivos afetados:** `docker-compose.yml`, `docker-compose.local.yml`

**Correção:**

```yaml
# Em cada serviço do docker-compose.yml:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Alternativa avançada (O3 do relatório):** usar `loki` driver para centralização.

**Validação:**
- Gerar logs > 10MB e observar rotação em `/var/lib/docker/containers/*/`.

### T2-07 ErrorBoundary na raiz do React com report remoto

**Criticidade:** Média · **Dependências:** T2-01

**Problema:** `frontend/src/main.tsx` não envolve `<App/>` com `ErrorBoundary`; só é local em mapas/abas. Erros em Usuarios, Configuracoes, Financeiro não têm boundary.

**Risco se não fizer:** Erro em uma página quebra a árvore inteira; usuário vê tela branca.

**Arquivos afetados:** `frontend/src/main.tsx` (corrigido em T2-01 com `Sentry.ErrorBoundary` + `ErrorBoundary` duplo)

**Ação:** Já coberta em T2-01 (`main.tsx` envolto em `ErrorBoundary`). Validar que páginas sem boundary local (Usuarios, Configuracoes, Financeiro) agora são capturadas pela raiz.

**Validação:**
- Forçar erro em `Usuarios.tsx` → página mostra fallback do `Sentry.ErrorBoundary` em vez de tela branca.

---

## Onda 3 — Testes e CI/CD

Esta onda elimina a "cobertura ilusória" documentada em `PERICIA_PRONTIDAO_FUNCIONAL.md:120-129` (97 pass/7 skip/0 fail na real), habilita testes no frontend/mobile e automatiza deploy + security scanning.

### T3-01 Suíte de integração conectada ao PostGIS real

**Criticidade:** Alta · **Dependências:** T1-01, T1-07

**Problema:** `backend/tests/test_settings.py:4-6` força SQLite in-memory e remove `django.contrib.gis`. 4 arquivos (`test_concurrency_finance.py:14`, `test_finance_services.py:88`, `test_finance_tasks.py:117`, `test_logistics_driver_api.py:84`) estão `@pytest.mark.skip` + `pass`. CI provisiona PostGIS+Redis (`backend-ci.yml:57-62`) que não são usados.

**Risco se não fizer:** Bugs de RLS, geofence, concorrência finanças, PIN não são capturados antes de produção.

**Arquivos afetados:**
- `backend/pytest.ini`
- `backend/tests/test_settings.py` (manter para unit; adicionar `test_settings_integration.py`)
- `backend/tests/conftest.py` (fixtures para integration)
- 4 arquivos `test_*` skipados (remover skip e implementar)

**Correção (pytest.ini):**

```ini
# backend/pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = tests.test_settings
python_files = tests.py test_*.py *_tests.py
addopts = -ra --strict-markers
markers =
    integration: tests requiring PostgreSQL+PostGIS+Redis (CI integration)
    unit: fast unit tests (default)
```

```python
# backend/tests/test_settings_integration.py (novo)
# Settings alternativo ativado via cmd: pytest -m integration --override-ini=DJANGO_SETTINGS_MODULE=tests.test_settings_integration
from tests.test_settings import *  # noqa
import os

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("TEST_DB_NAME", "test_expresso_neves"),
        "USER": os.environ.get("TEST_DB_USER", "postgres"),
        "PASSWORD": os.environ.get("TEST_DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("TEST_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("TEST_DB_PORT", "5432"),
    }
}
INSTALLED_APPS = [a for a in INSTALLED_APPS]  # preserve
if "django.contrib.gis" not in INSTALLED_APPS:
    INSTALLED_APPS.append("django.contrib.gis")
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/2")
CELERY_TASK_ALWAYS_EAGER = False
```

```python
# backend/tests/conftest.py — fixtures compartilhadas
import pytest
from model_bakery import baker  # adicionar em requirements.txt

@pytest.fixture
def operator(db):
    return baker.make("accounts.Operator", id="...", name="Op Test")

# Outras fixtures: driver, store, contract, order, wallet
```

**CI (`backend-ci.yml`):** Rodar 2 jobs pytest — um para `-m unit` (SQLite) e outro para `-m integration` (PostGIS provisionado):

```yaml
# .github/workflows/backend-ci.yml — adicionar steps
      - name: Run unit tests
        run: python -m pytest tests/ -v -m "unit or not integration"
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_expresso_neves
          REDIS_URL: redis://localhost:6379/1
          DJANGO_SETTINGS_MODULE: tests.test_settings_integration
        run: |
          python manage.py migrate --run-syncdb --no-input  # ou db setup
          python -m pytest tests/ -v -m integration
```

**Implementar testes skipados:** Remover `@pytest.mark.skip` + `pass` e implementar:
- `test_concurrency_finance.py::test_settle_order_concurrent`: usar `ThreadPool` com 2 chamadas concorrentes e `select_for_update` no banco real.
- `test_finance_services.py::test_settle_completed_only`, `test_contract_missing_raises`.
- `test_logistics_driver_api.py::test_pin_validation`: criar driver com PIN e validar `check_password` (verifica o bug `==` vs `check_password` do achado HIGH-002).
- `test_finance_tasks.py::test_hourly_cutoff`: chamar task `run_hourly_cutoff_billing` com DB real e assegurar faturas.

**Validação:**
- CI mostra 2 jobs PHPUnit_Time; contagem de skips = 0.
- Cobertura ascende do finance/logistics módulos.

### T3-02 Testes de auth/RBAC/JWT e fallback sem assinatura

**Criticidade:** Alta · **Dependências:** T0-02, T3-01

**Problema:** Nenhum teste de `SupabaseJWTAuth.authenticate`, RBAC, nem do fallback que aceita token sem assinatura (vulnerabilidade H5 em `PERICIA_PRONTIDAO_FUNCIONAL.md:144-154`). Endpoints `panel_api` sem auth global (H4) sem contraprova.

**Arquivos afetados:**
- `backend/tests/test_auth.py` (novo)
- `backend/tests/test_rbac.py` (novo)
- `backend/tests/test_panel_api_auth.py` (novo)

**Correção (exemplos):**

```python
# backend/tests/test_auth.py (parcial)
import jwt
from datetime import datetime, timedelta
import pytest

SECRET = "test-secret"
AUDIENCE = "authenticated"

def make_token(claims, secret=SECRET):
    payload = {"exp": datetime.utcnow() + timedelta(hours=1), "aud": AUDIENCE, **claims}
    return jwt.encode(payload, secret, algorithm="HS256")

@pytest.fixture
def settings_with_secret(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", AUDIENCE)

@pytest.mark.django_db
def test_valid_token_accepted(settings_with_secret):
    token = make_token({"sub": "user-1", "role": "authenticated"})
    # Chamar endpoint via Ninja TestClient
    from ninja.testing import TestClient
    from config.api import api
    client = TestClient(api)
    response = client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

@pytest.mark.django_db
def test_forged_signature_rejected(settings_with_secret):
    token = make_token({"sub": "user-1", "role": "service_role"}, secret="wrong-secret")
    from ninja.testing import TestClient
    from config.api import api
    client = TestClient(api)
    response = client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "fallback_error" not in response.json()  # não vaza detalhe

@pytest.mark.django_db
def test_expired_token_rejected(settings_with_secret):
    payload = {"exp": datetime.utcnow() - timedelta(hours=1), "aud": AUDIENCE, "sub": "user-1"}
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    from ninja.testing import TestClient
    from config.api import api
    client = TestClient(api)
    response = client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
```

```python
# backend/tests/test_rbac.py — exemplo
@pytest.mark.django_db
def test_non_admin_cannot_create_operator(settings_with_secret):
    token = make_token({"sub": "driver-1", "role": "authenticated"})
    client = TestClient(api)
    response = client.post("/admin/accounts/operators", json={...}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
```

```python
# backend/tests/test_panel_api_auth.py — exemplo
@pytest.mark.django_db
def test_panel_create_ride_requires_auth():
    from ninja.testing import TestClient
    from config.panel_api import panel_api
    client = TestClient(panel_api)
    response = client.post("/machine/rides/create", json={})
    assert response.status_code == 401  # após T0-03
```

**Validação:**
- `pytest tests/test_auth.py tests/test_rbac.py tests/test_panel_api_auth.py -v` ≥ 95% dos cenários.

### T3-03 Vitest + Testing Library no frontend

**Criticidade:** Alta · **Dependências:** Nenhuma

**Problema:** `frontend/package.json:6-13` não tem script `test` nem deps de teste. Nenhum arquivo `*.test.tsx` no `frontend/`. CI (`frontend-ci.yml:33-39`) não roda testes.

**Risco se não fizer:** Regressões no frontend entram produção sem detecção.

**Arquivos afetados:**
- `frontend/package.json` (adicionar `vitest`, `@testing-library/react`, `jsdom`, `@testing-library/jest-dom`)
- `frontend/vite.config.ts` (config `test`)
- `frontend/src/test/setup.ts` (novo)
- `frontend/src/tests/` (novo diretório)
- `.github/workflows/frontend-ci.yml`

**Correção:**

```json
// frontend/package.json — em devDependencies
  "@testing-library/jest-dom": "^6.1.0",
  "@testing-library/react": "^16.0.0",
  "@testing-library/user-event": "^14.0.0",
  "jsdom": "^25.0.0",
  "vitest": "^2.0.0"
// Em scripts:
  "test": "vitest run",
  "test:watch": "vitest"
```

```typescript
// frontend/vite.config.ts — adicionar `test` em defineConfig
/// <reference types="vitest" />
export default defineConfig(({ mode }) => {
  // ...
  return {
    // ...
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      css: true,
    },
  }
});
```

```typescript
// frontend/src/test/setup.ts
import "@testing-library/jest-dom";
```

**Teste inicial (AuthContext):**

```typescript
// frontend/src/tests/AuthContext.test.tsx
import { render, screen } from "@testing-library/react";
import { AuthProvider } from "../contexts/AuthContext";
import { describe, it, expect } from "vitest";

describe("AuthProvider", () => {
  it("shows loader initially", () => {
    render(<AuthProvider><div>child</div></AuthProvider>);
    // Ajustar de acordo com o spinner exato do AuthContext
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
```

**CI (`frontend-ci.yml`):**

```yaml
# .github/workflows/frontend-ci.yml — adicionar step
      - name: Run frontend tests
        run: npm run test
```

**Priorizar testes:** `AuthContext`, `FilaDinamica`, `CreditQueuePanel`, `RideMapModal` (componentes críticos identificados em `docs/frontend/product-roadmap-frontend.md`).

**Validação:**
- `npm run test` executa e passa; CI passa.

### T3-04 Testes de contrato Retrofit no mobile + testDebugUnitTest no CI

**Criticidade:** Média · **Dependências:** Nenhuma

**Problema:** Mobile tem apenas 3 stubs `Example*` (`mobile/app/src/test/java/com/example/`). CI (`mobile-ci.yml:33-34`) não roda `testDebugUnitTest` nem `lint`. `build.gradle.kts:62-64` desliga lint.

**Risco se não fizer:** Contrato divergente backend-mobile (reconhecido em `NEVESGO_AUDITORIA_E_PLANO_TATICO.md:95-123`) entre produção sem detecção.

**Arquivos afetados:**
- `mobile/app/build.gradle.kts` (reabilitar lint)
- `mobile/app/src/test/java/com/nevesgo/app/` (substituir `example` por nós reais)
- `.github/workflows/mobile-ci.yml`

**Correção (lint):**

```kotlin
// mobile/app/build.gradle.kts — substituir linhas 61-64
  lint {
    checkReleaseBuilds = true
    abortOnError = true
    warningsAsErrors = false  // permitir warnings, falhar em errors
  }
```

**Teste de contrato (WireMock):**

```kotlin
// mobile/app/src/test/java/com/nevesgo/app/data/api/CorridaApiContractTest.kt (novo)
package com.nevesgo.app.data.api

import com.github.tomakehurst.wiremock.client.WireMock.*
import com.github.tomakehurst.wiremock.junit5.WireMockExtension
import okhttp3.OkHttpClient
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.extension.RegisterExtension
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import org.junit.jupiter.api.Assertions.assertEquals

class CorridaApiContractTest {

    @RegisterExtension
    val wireMock = WireMockExtension.newInstance().build()

    @Test
    fun `listar corridas retorna lista parseable`() {
        wireMock.stubFor(
            get(urlEqualTo("/api/v1/driver/orders"))
                .willReturn(okJson("""[{"id":"ord-1","status":"OFFERED"}]"""))
        )

        val api = Retrofit.Builder()
            .baseUrl(wireMock.baseUrl() + "/api/v1/")
            .client(OkHttpClient())
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(CorridaApi::class.java)

        val response = api.listOrders().execute()
        assertEquals(200, response.code())
        assertEquals(1, response.body()?.size)
    }
}
```

Adicionar WireMock em `testImplementation`.

**CI (`mobile-ci.yml`):**

```yaml
# .github/workflows/mobile-ci.yml — substituir step de build
      - name: Run unit tests & lint
        run: ./gradlew testDebugUnitTest lintDebug
      - name: Build release APK (gate after tests)
        run: ./gradlew assembleRelease
```

**Validação:**
- `./gradlew testDebugUnitTest` executa testes reais (não stubs).
- `lintDebug` falha CI em erros.

### T3-05 Deploy automatizado no CI

**Criticidade:** Alta · **Dependências:** T1-03

**Problema:** Workflows só fazem testes/build; nenhum step de deploy. Sem push para GHCR/EasyPanel. APK salvo como artifact mas não vai para Play Store.

**Risco se não fizer:** Deploy manual = erro humano; rollback manual lento.

**Arquivos afetados:**
- `.github/workflows/backend-ci.yml` (adicionar job deploy)
- `.github/workflows/frontend-ci.yml`
- `.github/workflows/mobile-ci.yml`

**Correção (backend — exemplo EasyPanel deploy hook):**

```yaml
# .github/workflows/backend-ci.yml — adicionar job deploy
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push image
        run: |
          echo "${{ secrets.GHCR_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker build -t ghcr.io/${{ github.repository }}/backend:${{ github.sha }} -f backend/Dockerfile backend/
          docker push ghcr.io/${{ github.repository }}/backend:${{ github.sha }}
      - name: Trigger EasyPanel redeploy
        run: |
          curl -X POST "${{ secrets.EASYPANEL_DEPLOY_HOOK }}" \
            -H "Content-Type: application/json" \
            -d '{"image":"ghcr.io/${{ github.repository }}/backend:${{ github.sha }}"}'
```

**Tags de versão:** Sempre tagear imagem com `${{ github.sha }}` (não `latest`) para permitir rollback via troca de tag.

**Mobile:** Adicionar Firebase App Distribution no job deploy (para testadores internos).

**Validação:**
- Push em `main` faz deploy automático; SHA da imagem visível no EasyPanel.

### T3-06 Scanning de segurança (Trivy/pip-audit/npm audit/gitleaks)

**Criticidade:** Alta · **Dependências:** Nenhuma

**Problema:** Nenhum `codeql-action`, `trivy`, `pip-audit`, `npm audit`, `gitleaks` nos workflows. `GEMINI_API_KEY` no `vite define` (corrigido em T0-06) ilustra o risco de commit de secrets.

**Arquivos afetados:**
- `.github/workflows/security.yml` (novo workflow)

**Correção:**

```yaml
# .github/workflows/security.yml (novo)
name: Security Scan
on: [push, pull_request]
jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  trivy-fs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Trivy filesystem scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          scan-ref: .
          severity: HIGH,CRITICAL
          exit-code: 1

  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.14" }
      - run: pip install pip-audit
      - run: pip-audit -r backend/requirements.txt

  npm-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci --prefix frontend
      - run: npm audit --omit=dev --prefix frontend --audit-level=high
```

**Adicionar Dependabot (`/.github/dependabot.yml`):**

```yaml
version: 2
updates:
  - package-ecosystem: pip
    directory: /backend
    schedule: { interval: weekly }
  - package-ecosystem: npm
    directory: /frontend
    schedule: { interval: weekly }
  - package-ecosystem: gradle
    directory: /mobile
    schedule: { interval: weekly }
  - package-ecosystem: github-actions
    directory: /
    schedule: { interval: weekly }
```

**Validação:**
- Pipeline falha em HIGH/CRITICAL.
- Dependabot abre PRs semanais.

### T3-07 Lint gate não-bloqueante + paths filter + makemigrations --check

**Criticidade:** Média · **Dependências:** Nenhuma

**Problema:** `frontend-ci.yml:37` faz `npm run lint || echo "..."` (falhas não quebram pipeline). Backend CI não filtra por paths. Sem `makemigrations --check` (risco A1 em `PERICIA_INFRA_DEPLOY.md:290-300` — drift models↔schema).

**Arquivos afetados:**
- `.github/workflows/backend-ci.yml` (paths filter + makemigrations check)
- `.github/workflows/frontend-ci.yml` (remover `|| echo`)
- `.github/workflows/mobile-ci.yml` (já coberto em T3-04)

**Correção (`backend-ci.yml`):**

```yaml
on:
  push:
    branches: [main]
    paths:
      - backend/**
      - .github/workflows/backend-ci.yml
  pull_request:
    paths:
      - backend/**
      - .github/workflows/backend-ci.yml

jobs:
  test:
    steps:
      # ...
      - name: Check migrations drift
        run: python manage.py makemigrations --check --dry-run
```

**`frontend-ci.yml`:**

```yaml
      - name: Lint (non-blocking removed)
        run: npm run lint
```

**Validação:**
- Lint error frontend falha build.
- Drift de model vs schema falha CI.

---

## Onda 4 — LGPD e Conformidade

### T4-01 Workflows de DSAR (acesso/apagamento/portabilidade)

**Criticidade:** Alta · **Dependências:** T4-02 (AuditEvent)

**Problema:** `logistics/compliance.py:6-13` define constantes `ACCESS, RECTIFICATION, ERASURE, PORTABILITY, RESTRICTION, ANONYMIZATION` (direitos do titular LGPD, art. 18) mas não há endpoint/task automatizado para processá-los.

**Risco se não fizer:** Descumprimento LGPD → sanções (art. 52, multa de até 2% do faturamento).

**Arquivos afetados:**
- `backend/accounts/models.py` (modelo `DSARRequest`)
- `backend/accounts/api.py` (endpoint `POST /compliance/dsar`)
- `backend/accounts/tasks.py` (task Celery `process_dsar`)
- Migration Supabase CLI

**Correção (modelo):**

```python
# backend/accounts/models.py — adicionar
class DSARRequest(models.Model):
    class RequestType(models.TextChoices):
        ACCESS = "ACCESS"
        RECTIFICATION = "RECTIFICATION"
        ERASURE = "ERASURE"
        PORTABILITY = "PORTABILITY"
        RESTRICTION = "RESTRICTION"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_type = models.CharField(max_length=20, choices=RequestType.choices)
    subject_email = models.EmailField()
    subject_supabase_uid = models.CharField(max_length=64, null=True)
    status = models.CharField(max_length=20, default="OPEN")  # OPEN, IN_PROGRESS, FULFILLED, OVERDUE
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField()  # created_at + 15 days (LGPD art. 19)
    fulfilled_at = models.DateTimeField(null=True)
    payload = models.JSONField(default=dict)  # ver minimization

    class Meta:
        managed = False
        db_table = "accounts_dsarrequest"
```

**Endpoint/triggers Celery (esboço):** recebe o pedido, valida identidade, dispara `process_dsar` Celery task com `countdown` para SLA de 15 dias; alerta se OVERDUE.

**schema.sql (Supabase migration):** Tabela correspondente + gatilho RLS.

**Validação:**
- `POST /compliance/dsar` cria `DSARRequest`; task executa/anonymiza dados do `subject`.

### T4-02 Trilha de auditoria genérica (AuditEvent)

**Criticidade:** Média · **Dependências:** Nenhuma

**Problema:** `OperatorAuditLog` existe apenas para mudança de status de Operator. Operações críticas sem trilha: `settle_order`, `withdraw`, CNAB gerado, `login_callback`, denylist add/remove, biometria.

**Arquivos afetados:**
- `backend/config/core_models.py` (modelo `AuditEvent`)
- Points de chamada espalhados (services.py, tasks.py)

**Correção:**

```python
# backend/config/core_models.py — adicionar
class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_supabase_uid = models.CharField(max_length=64, null=True)
    actor_role = models.CharField(max_length=32)
    action = models.CharField(max_length=64)  # ex: "finance.settle_order"
    target_type = models.CharField(max_length=64)  # "Order", "Operator"
    target_id = models.CharField(max_length=64, null=True)
    metadata = models.JSONField(default=dict)  # já minimizado via compliance.minimized_metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "config_auditevent"
        indexes = [
            models.Index(fields=["actor_supabase_uid"]),
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
        ]
```

**Helper:**

```python
# backend/config/audit.py (novo)
from config.core_models import AuditEvent
from logistics.compliance import minimized_metadata

def record_audit(actor_uid, actor_role, action, target_type=None, target_id=None, **metadata):
    AuditEvent.objects.create(
        actor_supabase_uid=actor_uid,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        metadata=minimized_metadata(metadata),
    )
```

**Chamadas:** em `finance/services.py:settle_order`:

```python
from config.audit import record_audit
record_audit(
    actor_uid=request.auth.get("sub") if hasattr(request, "auth") else "celery",
    actor_role="system",
    action="finance.settle_order",
    target_type="Order",
    target_id=locked_order.id,
    order_status=locked_order.status,
    amount_cents=driver_fee,
)
```

**Validação:**
- Cada operação financeira/admin gera `AuditEvent`.

### T4-03 Criptografia em colunas PII via pgcrypto

**Criticidade:** Média · **Dependências:** Nenhuma

**Problema:** `Operator.cnpj`, `StaffMember.email`, `PlatformAdmin.email`, CPF em `pixKey` (`accounts/api.py:95`) sem criptografia em repouso documentada.

**Risco se não fizer:** Vazamento de dump de banco expõe PII legível.

**Arquivos afetados:**
- `docs/schema.sql` (ativar `pgcrypto`, FUNCTIONS de cryptage)
- Models PII (adicionar properties de getter/setter se transparent encryption)

**Ação:**

```sql
-- Supabase migration
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Para CNPJ/email: usar colunas encrypt ao invés de índices diretos.
-- Criar FUNCTION que recebe plaintext e grava ciphertext:
CREATE OR REPLACE FUNCTION accounts_encrypt_pii(pii TEXT, pii_type TEXT)
RETURNS BYTEA AS $$
    SELECT pgp_sym_encrypt(pii::text, current_setting('app.pii_key', true))
$$ LANGUAGE sql;

-- Hash deterministic para lookup (ex: busca por email):
CREATE OR REPLACE FUNCTION accounts_pii_hmac(pii TEXT)
RETURNS TEXT AS $$
    SELECT hmac(pii::text, current_setting('app.pii_hmac_key', true), 'sha256')::text;
$$ LANGUAGE sql;

-- Exemplo para StaffMember.email:
ALTER TABLE accounts_staffmember ADD COLUMN IF NOT EXISTS email_encrypted BYTEA;
ALTER TABLE accounts_staffmember ADD COLUMN IF NOT EXISTS email_hmac TEXT;
-- Migrar dados existentes (script); depois DROP coluna email (após verificação).
```

**RLS:** `app.pii_key` é secret injetado via `set_config` no middleware (similar ao JWT).

**Validação:**
- `SELECT email FROM accounts_staffmember` retorna bytes, não plaintext.
- Busca por `email_hmac` funciona.

### T4-04 Validação completa de CPF (dígitos verificadores)

**Criticidade:** Média · **Dependências:** Nenhuma

**Problema:** `accounts/api.py:54` valida CPF apenas por `len != 11`, sem dígitos verificadores.

**Arquivos afetados:**
- `backend/shared_schemas/accounts.py` (validator CPF)
- Onde usado (accounts/api.py, stores).

**Correção:**

```python
# backend/shared_schemas/accounts.py — adicionar validador
def validate_cpf(cpf: str) -> str:
    cpf = re.sub(r"\D", "", cpf or "")
    if len(cpf) != 11:
        raise ValueError("CPF deve ter 11 dígitos.")
    if len(set(cpf)) == 1:
        raise ValueError("CPF inválido (todos iguais).")
    # Dígitos verificadores
    for i in (9, 10):
        soma = sum(int(cpf[j]) * (11 - i + j) for j in range(i))
        dv = 11 - (soma % 11)
        dv = 0 if dv >= 10 else dv
        if int(cpf[i]) != dv:
            raise ValueError("CPF inválido (dígitos verificadores).")
    return cpf
```

**Usar no Pydantic schema** em vez de validação manual.

**Validação:**
- CPFs fáceis (todos iguais, dígitos errados) rejeitados.

---

## Onda 5 — UX e Mobile

### T5-01 Implementar TrackingService real com FusedLocationProviderClient

**Criticidade:** Alta · **Dependências:** Nenhuma

**Problema:** `mobile/app/src/main/java/com/nevesgo/app/services/TrackingService.kt:18-28` apenas mostra notificação e retorna `START_STICKY`. Não coleta localização de fato.

**Arquivos afetados:**
- `mobile/app/src/main/java/com/nevesgo/app/services/TrackingService.kt`

**Correção (esboço):**

```kotlin
package com.nevesgo.app.services

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority

class TrackingService : Service() {

    private lateinit var fusedClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        fusedClient = LocationServices.getFusedLocationProviderClient(this)
        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.let { loc ->
                    // TODO: enqueue to Room queue + Retrofit upload via WorkManager
                    android.util.Log.i("Tracking", "loc=${loc.latitude},${loc.longitude}")
                }
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Rastreamento Ativo")
            .setContentText("NevesGo rastreando sua localização para entregas.")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } else {
            startForeground(1, notification)
        }

        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 5000L)
            .setMinUpdateIntervalMillis(2000L)
            .build()
        // Verificar permissão antes de requestLocationUpdates (posto em T5-01)
        if (checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED) {
            fusedClient.requestLocationUpdates(request, locationCallback, mainLooper)
        } else {
            stopSelf()  // sem permissão, não pretença rastrear
        }
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::locationCallback.isInitialized && ::fusedClient.isInitialized) {
            fusedClient.removeLocationUpdates(locationCallback)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Tracking Service Channel",
                NotificationManager.IMPORTANCE_LOW  // não tocar a cada update
            )
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    companion object {
        const val CHANNEL_ID = "TrackingServiceChannel"
    }
}
```

**Ação paralela:** Implementar `WorkManager` para retry de uploads em background.

**Validação:**
- Testes instrumentados que validam `onLocationResult` recebe atualizações.

### T5-02 Forced update do mobile via endpoint /api/version-check

**Criticidade:** Média · **Dependências:** Nenhuma

**Problema:** `build.gradle.kts:25` define `versionCode=1` fixo. Sem endpoint de checagem.

**Arquivos afetados:**
- `backend/accounts/api.py` (novo endpoint `/api/v1/app/version-check`)
- `mobile/app/src/main/java/com/nevesgo/app/main/` (interceptador que bloqueia UI)

**Correção (backend):**

```python
# backend/config/api.py (ou accounts/api.py) — novo endpoint
@api.get("/app/version-check", auth=None)  # sem auth — app precisa saber antes do login
def app_version_check(request, platform: str, version_code: int):
    min_version = int(os.environ.get(f"MIN_VERSION_{platform.upper()}", "1"))
    return {
        "minimumRequired": min_version,
        "updateRequired": version_code < min_version,
        "latestVersion": int(os.environ.get(f"LATEST_VERSION_{platform.upper()}", "1")),
        "downloadUrl": os.environ.get("APP_DOWNLOAD_URL_ANDROID"),
    }
```

**Mobile:** interceptor OkHttp que chama endpoint no boot e bloqueia UI com diálogo de update obrigatório se `updateRequired=true`.

**Validação:**
- Release com `MIN_VERSION_ANDROID=2`拦as versão 1.

### T5-03 loadProfile com finally { setIsLoading(false) }

**Criticidade:** Baixa · **Dependências:** T2-01

**Problema:** `frontend/src/contexts/AuthContext.tsx:49-72` pode deixar `isLoading=true` para sempre em rejeição do `supabase.auth.getSession()`.

**Arquivos afetados:** `frontend/src/contexts/AuthContext.tsx`

**Correção:**

```typescript
// frontend/src/contexts/AuthContext.tsx — loadProfile
  const loadProfile = async () => {
    setIsLoading(true);
    try {
      const { data: { session }, error } = await supabase.auth.getSession();
      // ... (lógica preservada)
    } catch (e) {
      // logger.error(e);
    } finally {
      setIsLoading(false);
    }
  };
```

**Validação:**
- Simular `supabase.auth.getSession()` reject e spinner não ficar preso.

### T5-04 Acessibilidade: role=alert e aria-live

**Criticidade:** Baixa · **Dependências:** T2-07

**Problema:** `ErrorBoundary.tsx:43` sem `role="alert"`; spinner em `App.tsx:59-61,73-75` sem `role="status"`.

**Arquivos afetados:**
- `frontend/src/components/ErrorBoundary.tsx`
- `frontend/src/App.tsx` (fallback spinner)

**Correção:**

```tsx
// ErrorBoundary.tsx — render do card de erro
    <div role="alert" className="...">
      {/* ... */}
    </div>

// App.tsx — fallback de Suspense
    <Suspense fallback={
      <div role="status" aria-live="polite" className="...">
        <LoadingSpinner />
      </div>
    }>
```

**Validação:**
- NVDA/VoiceOver anuncia erro e loading.

### T5-05 Pinning de certificado no Android

**Criticidade:** Média · **Dependências:** T5-01

**Problema:** `NetworkModule.kt:45-49` não tem `CertificatePinner`. Man-in-the-middle em Wi-Fi público possível.

**Arquivos afetados:**
- `mobile/app/src/main/java/com/nevesgo/app/di/NetworkModule.kt`

**Correção:**

```kotlin
// NetworkModule.kt — em provideOkHttpClient, adicionar CertificatePinner
import okhttp3.CertificatePinner

    @Provides
    @Singleton
    fun provideOkHttpClient(authInterceptor: Interceptor): OkHttpClient {
        val pinner = CertificatePinner.Builder()
            .add("api.seu-dominio.com", "sha256/AAAA...")   // pino primary
            .add("api.seu-dominio.com", "sha256/BBBB...")   // pino backup
            .build()

        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .certificatePinner(pinner)
            .also { if (BuildConfig.DEBUG) it.addInterceptor(MockInterceptor()) }
            .build()
    }
```

**Observação:** Pinos SHA256 devem ser gerados do cert real + um backup. Documentar rotação em `docs/runbook-operacional.md`.

**Validação:**
- Tentar chamar API com certificado diferente rejeita com SSLPeerUnverified.

---

## Onda 6 — Documentação

### T6-01 Runbook operacional

**Criticidade:** Média · **Dependências:** Nenhuma

**Arquivos afetados:** `docs/runbook-operacional.md` (novo)

**Conteúdo:**
- Deploy via EasyPanel (passo a passo com imagens).
- Rollback de imagem (troca de tag SHA).
- Reexecução manual de `warmup_denylist`.
- Reinscrição de webhooks por provedor (iFood/Anota AI).
- Reconstrução de denylist do banco (T4-04).
- Rotação de pinos de certificado (T5-05).
- Troca de secret do Supabase JWT (rodízio).
- Procedimento de incidente (5xx pico, OOM do Celery, fila de billing atolada).

### T6-02 Diagrama ER e diagrama de sequência ponta-a-ponta

**Criticidade:** Baixa · **Dependências:** Nenhuma

**Arquivos afetados:**
- `docs/er-diagram.png` (gerado via `eralchemy` ou dbdiagram.io)
- `docs/API_CONTRACT.md` (adicionar diagrama Mermaid sequence)

**Mermaid exemplo (sequence pedido):**

```mermaid
sequenceDiagram
    participant App as App Mobile
    participant API as Django Ninja
    participant DB as Postgres (RLS)
    participant Celery as Celery
    participant Supabase as Supabase Auth
    App->>Supabase: login (email/senha)
    Supabase-->>App: JWT
    App->>API: POST /machine/rides/create (Bearer)
    API->>DB: SELECT set_config('request.jwt.claims', ...)
    API->>DB: SET LOCAL ROLE authenticated
    API->>DB: INSERT INTO logistics_order
    API-->>App: 201 order_id
    App->>API: POST /driver/orders/{id}/accept
    API->>DB: UPDATE order status (select_for_update)
    API-->>App: 200
    App->>API: POST /driver/orders/{id}/complete-batch
    API->>DB: UPDATE status=COMPLETED
    API->>Celery: enqueue settle_order(order_id)
    Celery->>DB: SELECT order (FOR UPDATE)
    Celery->>DB: INSERT WalletTransaction (idempotência)
    Celery->>DB: INSERT WeeklyInvoiceLineItem
```

### T6-03 ADRs para decisões-chave

**Criticidade:** Baixa · **Dependências:** T6-01

**Arquivos afetados:**
- `docs/adr/0001-rls-isolation.md` (RLS como mecanismo de isolamento de tenant)
- `docs/adr/0002-bigint-centavos.md` (BigInt para moeda, evitar float)
- `docs/adr/0003-fast-slow-lane.md` (FastAPI para telemetria, Django para lenta)
- `docs/adr/0004-idempotency-redis.md` (decorador `@idempotent` e Redis NX/EX)
- `docs/adr/0005-denylist-fail-closed.md` (fail-closed do Redis)

Cada ADR em formato Michael Nygard: Contexto, Decisão, Status, Consequências.

---

## Resumo de Precedência e Validação Hφil

```
Onda 0 (10 tarefas) ─── Bloqueadores de Segurança ─── PRÉ GO-LIVE
  └─ T0-10 (resolve conflito documental) depende de T0-01..T0-09

Onda 1 (10 tarefas) ─── Resiliência Financeira & Deploy ─── PRÉ GO-LIVE
  ├─ T1-01..T1-07 (financeiro, idempotência, race, deploy)
  ├─ T1-08 (locks) depende de T0-02, T1-09
  └─ T1-05 (migrate job) depende de T1-03 (healthchecks)

### APÓS GO-LIVE CONTROLADO ###

Onda 2 (7 tarefas) ─── Observabilidade & Erros
  ├─ T2-01 (Sentry/Crashlytics) independente
  └─ T2-07 (ErrorBoundary raiz) depende de T2-01

Onda 3 (7 tarefas) ─── Testes & CI/CD
  ├─ T3-01 (integração PostGIS) depende de T1-01, T1-07
  ├─ T3-02 (auth/RBAC) depende de T0-02, T3-01
  └─ T3-05 (deploy CI) depende de T1-03

Onda 4 (4 tarefas) ─── LGPD
  └─ T4-01 (DSAR) depende de T4-02 (AuditEvent)

Onda 5 (5 tarefas) ─── UX & Mobile
  ├─ T5-01 (TrackingService) independente (BLOCK de UX)
  ├─ T5-02 (forced update) independente
  ├─ T5-03 (loadProfile) depende de T2-01 (logger)
  ├─ T5-04 (a11y) depende de T2-07
  └─ T5-05 (pinning) depende de T5-01

Onda 6 (3 tarefas) ─── Documentação
  └─ T6-03 (ADRs) depende de T6-01
```

### Critérios de Aceitação por Onda

| Onda | Critério de Conclusão | Métrica |
|---|---|---|
| 0 | Security scan passa sem HIGH/CRITICAL; `matriz_homologacao.md` alinhada às perícias | `trivy fs .` 0High, audit documental revisado |
| 1 | Healthchecks healthy em 60s; `settle_order` idempotente em concorrência; restart automático verificado | `docker compose kill django` sobrevive; teste de concorrência green |
| 2 | Sentry/Crashlytics capturam erros forçados; logs JSON em dev e prod com `corr` | Eventos no Sentry/Crashlytics |
| 3 | `-m integration` no CI passa; frontend `npm run test` verde; mobile `testDebugUnitTest` verde; deploy em push de `main` | CI badges 100% green |
| 4 | `POST /compliance/dsar` funcional; `AuditEvent` em settle/withdraw; CPF rejeita dígitos errados | E2E de DSAR em staging |
| 5 | TrackingService envia localização a cada 5s; app bloqueia versões antigas; pinning rejeita MITM | Teste instrumentado de tracking |
| 6 | Runbook revisado em cenário de incidente simulado; ADRs linkados nos PRs relevantes | Simulação de incidente documentada |

### Commits Atômicos (Padrão)

Cada tarefa = 1 commit com mensagem no formato:

```
[T<id>] <título curto>

<criticidade> · <onda>

- Altera <arquivo>: <mudança>
- Adiciona <arquivo>: <novo>
- <validação feita>

Refs: docs/PLANO_IMPLEMENTACAO_PRODUCAO.md#<ancora>
```

Exemplo:

```
[T0-01] Restringir CORS a origens explícitas

Alta (BLOCK) · Onda 0

- Altera backend/config/settings.py: CORS_ALLOW_ALL_ORIGINS=False, CORS_ALLOWED_ORIGINS via env
- Validação: curl com Origin bloqueado retorna sem ACAO; CI backend green

Refs: docs/PLANO_IMPLEMENTACAO_PRODUCAO.md#t0-01-restringir-cors-a-origens-explícitas
```

---

## Onda 7 — Hub de Integrações Plug-and-Play (CRM, ERP e Cardápios Digitais)

> **Módulo estratégico** para transformar o `backend/integration` em um hub centralizado
> de integrações plug-and-play, agregando todas as plataformas listadas no repositório
> de referência `github.com/henriquefelipe/marketplace` e outras (CRM/ERP).
>
> **Estado atual do `backend/integration`**: suporta apenas 4 provedores
> (`DELIVERY_DIRETO`, `ANOTA_AI`, `IFOOD`, `99FOOD`) com lógica ad-hoc (sem ABC, sem
> registry, sem circuit breaker, sem métricas por provedor, sem idempotência de
> webhook). O hub plug-and-play resolve essas lacunas estruturais e habilita adição de
> novos parceiros sem editar um `if/elif` gigante.

### Análise do Repositório de Referência (`marketplace`)

O repositório `henriquefelipe/marketplace` (267 commits, .NET/C#, ~54 projetos)
cataloga **54 plataformas** em 4 categorias. Gaps de documentação em vermelho (sem
doc/link público identificável) demandam levantamento direto com o parceiro.

### 7.1 Mapeamento Completo das Plataformas (CRM, ERP, Cardápios, Delivery, Logística, Fidelidade)

A tabela abaixo consolida **todas as 54 plataformas** listadas, suas documentações
públicas, autenticação e categoria de integração.

| # | Plataforma | Categoria | Documentação Pública | Auth | Notas |
|--|--|--|--|--|---|
| 1 | iFood | Delivery | https://developer.ifood.com.br/ | OAuth2 client_credentials | Já parcialmente suportada (`adapters.py:7-16`); webhook ACK + polling Mercado |
| 2 | 99Food (Didi Food) | Delivery | https://openapi.didi-food.com/v4/opendelivery | OAuth2 Open Delivery | Já parcialmente suportada; polling `-events:polling`; `appShopId` (`adapters.py:175-181`) |
| 3 | Rappi | Delivery | https://dev-portal.rappi.com/ | OAuth2 + Webhook HMAC | APIREST; endpoints de pedidos/produtos; tx delivery |
| 4 | Uber Eats | Delivery | https://developers.ubereats.com/v3 | OAuth2 + Webhook | Merchant API v3; webhook HMAC-SHA256 |
| 5 | Anota AI | Delivery | https://documenter.getpostman.com/view/9867946/ | Token compartilhado | Já suportada (`adapters.py:208-221`); só inbound |
| 6 | Delivery Direto | Delivery | https://site.deliverydireto.com.br/ | HMAC-SHA256 | Já suportada (`adapters.py:222-234`); header `x-deliverydireto-signature` |
| 7 | Aiqfome | Delivery | https://app.swaggerhub.com/apis-docs/aiq6/api-aiqfome/1.0.0 | Token + MerchantId | API REST Swagger; `Token/Usuario/Senha/MerchantId` |
| 8 | Accon | Delivery | http://docs.accon.com.br | Usuario+Senha+Rede | Portal https://portal.accon.app/ |
| 9 | Americanas Delivery | Delivery | https://americanas-api.com/ (verificar) | OAuth2 | Sem doc pública; portal americanas市场 |
| 10 | B2Food | Delivery | https://www.b2food.com.br/ (verificar) | Token | Sem doc pública identificada |
| 11 | Bigdim | Delivery | Sem doc pública (contatar) | Token | Projeto no repo; campo `ordem` pode ser nulo |
| 12 | BigFish | Delivery | https://www.bigfish.com.br/ (verificar) | Token API | "Obter apenas não importados" (commit 49a74841) |
| 13 | Cardápio Web | Delivery | https://cardapioweb.com.br (verificar) | Token | Commit 38a98c3 |
| 14 | Delivery App (Neemo) | Delivery | https://deliveryapp.neemo.com.br/api/docs/?integration=true | Token | API doc Neemo |
| 15 | Epadoca | Delivery | https://epadoca.com/ (verificar) | Usuario+Senha+MerchantId+Url | Sem doc pública; campos via json |
| 16 | GloriaFood | Delivery | https://github.com/GlobalFood/integration_docs | Token | GitHub integration_docs; ORDER v1 |
| 17 | GoomerGO | Delivery | https://ajuda.goomer.com.br/integracao/ | Token + Client_ID/SECRET + MerchantId | OAuth2; URL variável |
| 18 | JotaJá | Delivery | Sem doc pública (contatar) | Token | Projeto no repo; classes API JotaJá |
| 19 | Meu Cardápio AI | Delivery | https://documenter.getpostman.com/view/3494108/ | Token | API Postman |
| 20 | Mercadoo | Delivery | Sem doc pública (contatar) | Token | Projeto no repo |
| 21 | Multi Pedido | Delivery | https://multipedido.com.br (verificar) | Token | Hotfix integrador ipos (commit 556298b) |
| 22 | OnPedido | Delivery | https://onpedido.com/ | Token | Site; sem doc técnica pública |
| 23 | PedZap (Deeliv) | Delivery | https://pedzap.docs.apiary.io/#introduction | Token (Bearer) | Apiary docs; auth Bearer |
| 24 | PixCommerce | Delivery | Sem doc pública (contatar) | Token+Usuario+Senha | Commit 8de14d7 |
| 25 | Prefiro Delivery | Delivery | Sem doc pública (contatar) | Token | Projeto no repo |
| 26 | Quero Delivery | Delivery | Sem doc pública (contatar) | Token+Enums pagamento | Commit c2b15ad |
| 27 | Super Menu | Delivery | https://supermenu.gitbook.io/api-supermenu/ | Token | Gitbook |
| 28 | Wedo | Delivery | Sem doc pública (contatar) | Token | Commit 38a98c3 |
| 29 | WooCommerce | Delivery | https://woocommerce.github.io/woocommerce-rest-api-docs/ | Consumer Key/Secret (OAuth1) | WP REST API |
| 30 | Logaroo | Logística | https://api.dev.logaroo.com.br/ | MerchantId+Usuario+Senha | API dev |
| 31 | Agilizone | Logística | Sem doc pública (contatar) | Token | Commit 32c1373 |
| 32 | Foody Delivery | Logística | Sem doc pública (contatar) | Token | Commit 5455f5 e 92527ae |
| 33 | IzzyGO | Logística | Sem doc pública (contatar) | Token+DriverName+Phone | Commit 568d25c |
| 34 | Deeliv | Logística | https://www.deeliv.com.br/ (verificar) | Token | PedZap/Deeliv relacionado; commit 5455f5 |
| 35 | Goomer | Cardápio Digital (Mesa) | https://goomer.com.br/ (verificar) | OAuth2 Token+MerchantId | Cardápio mesa ( distinto do GoomerGO delivery) |
| 36 | Goomer/Abrahão | Cardápio Digital (Mesa) | https://goomer.com.br/ (verificar) | OAuth2 + enviar produtos | Commit 70cb411 |
| 37 | Servit | Cardápio Digital (Mesa) | https://servit.com.br/ (verificar) | Token | Sem doc técnica; mesa |
| 38 | ADAC | (app próprio) | Sem doc pública (contatar) | Token | Commit 90e5e21 |
| 39 | Aipedi | (sem dados) | Sem doc pública (contatar) | ? | Sem campos/config no README |
| 40 | AtivMob | (sem dados) | Sem doc pública (contatar) | ? | Projeto no repo |
| 41 | Cinddi | (sem dados) | Sem doc pública (contatar) | ? | Projeto no repo |
| 42 | OpenDelivery | Padrão/SDK | https://github.com/open-delivery/open-delivery-standard | OAuth2 (compartilhado) | Padrão Open Delivery (Didi/99Food); já usado |
| 43 | Tray | ERP/E-commerce | https://docs.tray.com.br/ (verificar) | OAuth2 + Token | Commit 8610b70; ".. plug4sales para repediu" |
| 44 | VMarket | ERP/E-commerce | https://www.vmarket.com.br/ (verificar) | Token | Commit 35f899d |
| 45 | SelfBuyMe | ERP/E-commerce | Sem doc pública (contatar) | Token | Commit 239edc |
| 46 | Repediu | CRM/Marketplace | https://www.repediu.com.br/ (verificar) | Token | Commit 8610b70; "plug4sales para repediu" |
| 47 | CRMBonus | CRM | Sem doc pública (contatar) | Token | Commit 8ae0e9b |
| 48 | Cresce Vendas (CRM) | CRM/Cashback | https://www.crescevendas.com.br/ (verificar) | Token | Commit 8ae0e9b |
| 49 | EuFalo | CRM/Cashback | Sem doc pública (contatar) | Token | Commit 38a98c3 |
| 50 | Fidelizi | Fidelidade/Cashback | https://www.fidelizi.com.br/ (verificar) | Token | Commit 32c1373 |
| 51 | FixeCRM | CRM | Sem doc pública (contatar) | Token | Commit a646aa3 |
| 52 | LoopIzy | Fidelidade | Sem doc pública (contatar) | Token | Commit 568d25c |
| 53 | Repediu (Repediu-Plug4Sales) | CRM/Marketplace | https://www.repediu.com.br/ (verificar) | Token | Commit 8610b70 |
| 54 | Example | (template) | n/a | n/a | Projeto template do repo |

> **Observação:** Plataformas marcadas "Sem doc pública" requerem contato comercial
> técnico para obter Swagger/Postman/credenciais de sandbox. O hub plug-and-play deve
> contemplar um checklist de onboarding para cada nova plataforma (T7-01).

### 7.2 Arquitetura do Hub de Integrações

#### 7.2.1 Princípios

1. **Adapter Pattern com ABC** — Cada provedor implementa `ProviderAdapter` (interface
   Python) com métodos `fetch_orders`, `acknowledge_event`, `send_status`, `verify_signature`.
2. **Registry central** — Um `ProviderRegistry` singleton registra adapters; `register(KEY)`
   adiciona novos parceiros sem editar `adapters.py`/`tasks.py` if-elif.
3. **Configuração em DB (DB-First)** — `StoreIntegration` já armazena credenciais;
   `ProviderDefinition` (novo model) define cada plataforma (nome, auth_mode, base_url,
   docs_url, capabilities DPDL/CRM/ERP) para auto-descoberta no painel.
4. **Hub-canonical schema** — Toda plataforma converte para o schema canônico NevesGo
   (`CanonicalOrder`, `CanonicalProduct`, `CanonicalCustomer`) definido via Pydantic.
5. **Pipeline bidirecional** — Inbound (webhook + polling) e Outbound (Outbox Pattern já
   existente) com mapeamento bilateral `PlatformMapping` por provider.
6. **Segurança** — Credenciais Fernet-encrypted (já em `models.py:98-145`); trânsito TLS;
   webhook HMAC verificado por adapter (T0-05 fail-closed).
7. **Observabilidade por provedor** — Métricas Prometheus (sucesso, latência p95,
   circuit breaker state) e auditoria por evento (`IntegrationEventAudit` já existe).
8. **Circuit Breaker** — Abre após N falhas consecutivas (ex.: 5) em janela de 60s;
   half-open após timeout; fallback para polling quando suportado.

#### 7.2.2 Diagrama de Componentes (Mermaid)

```mermaid
flowchart LR
    subgraph Plataformas
        IF[iFood]
        AAI[Anota AI]
        ODS[Outras 50+]
    end
    subgraph Hub de Integrações
        REG[ProviderRegistry]
        ABC[ProviderAdapter ABC]
        CAN[Schema Canônico Pydantic]
        OUT[Outbox Pattern]
        CB[Circuit Breaker]
    end
    subgraph NevesGo
        LOG[Logistics Order]
        FIN[Finance Invoice]
        ACC[Accounts]
    end
    Plataformas -- webhook/polling --> REG
    REG --> ABC
    ABC --> CAN
    CAN --> LOG
    LOG --> OUT
    OUT --> ABC
    ABC --> Plataformas
    ABC -. métricas .- CB
    CB -. fail-open/fallback .- REG
```

#### 7.2.3 Interface do Adapter (ABC)

```python
# backend/integration/base.py (novo)
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel

class CanonicalOrder(BaseModel):
    """Schema canônico NevesGo — toda plataforma converte para este."""
    external_id: str
    merchant_reference: str
    status: str
    business_date: Optional[str] = None
    customer: Optional[dict] = None
    items: list[dict] = []
    total_cents: int
    currency: str = "BRL"

class ProviderAdapter(ABC):
    """Interface que todo provedor de integração implementa."""
    provider_key: str  # ex.: "IFOOD"
    supports_polling: bool = False
    supports_webhook: bool = True
    supports_outbound_status: bool = True

    @abstractmethod
    def verify_signature(self, raw_body: bytes, headers: dict, secret: str) -> bool:
        ...

    @abstractmethod
    def fetch_orders(self, integration: "StoreIntegration") -> list[dict]:
        ...

    @abstractmethod
    def acknowledge_event(self, integration: "StoreIntegration", event_id: str) -> bool:
        ...

    @abstractmethod
    def send_status(self, integration: "StoreIntegration", order_id: str, status: str) -> bool:
        ...

    @abstractmethod
    def to_canonical(self, raw: dict) -> CanonicalOrder:
        ...
```

#### 7.2.4 Registry Plug-and-Play

```python
# backend/integration/registry.py (novo)
from typing import Type
from integration.base import ProviderAdapter

_REGISTRY: dict[str, Type[ProviderAdapter]] = {}

def register(provider_key: str):
    """Decorator de registro: adiciona adapter sem mexer em if/elif."""
    def decorator(cls: Type[ProviderAdapter]):
        if provider_key in _REGISTRY:
            raise ValueError(f"Provider já registrado: {provider_key}")
        cls.provider_key = provider_key
        _REGISTRY[provider_key] = cls
        return cls
    return decorator

def get_adapter(provider_key: str) -> ProviderAdapter:
    key = provider_key.upper().replace("-", "_").replace(" ", "_")
    if key not in _REGISTRY:
        raise KeyError(f"Provider não suportado pelo hub: {key}")
    return _REGISTRY[key]()
```

Exemplo de uso (iFood):

```python
# backend/integration/adapters_ifood.py (novo)
from integration.registry import register
from integration.base import ProviderAdapter, CanonicalOrder

@register("IFOOD")
class IfoodAdapter(ProviderAdapter):
    supports_polling = True
    supports_webhook = True

    def verify_signature(self, raw_body, headers, secret):
        # iFood usa x-siteguard-signature HMAC-SHA256
        import hmac, hashlib
        sig = headers.get("x-siteguard-signature", "")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def fetch_orders(self, integration):
        # Usa provider_clients.poll_ifood_mercado_events (já existe)
        ...

    def to_canonical(self, raw):
        return CanonicalOrder(
            external_id=raw["codigoPedido"],
            merchant_reference=raw["merchantId"],
            status=raw["code"],  # mapeado via INBOUND_ORDER_STATUS_MAP
            total_cents=int(raw.get("total", 0)),
            currency="BRL",
        )
    # ...
```

#### 7.2.5 Circuit Breaker

```python
# backend/integration/circuit_breaker.py (novo)
import time
from config.redis_client import get_redis

class CircuitBreaker:
    """Abre após N falhas em janela; half-open após cooldown; fallback opcional."""
    def __init__(self, name: str, fail_threshold: int = 5, window_seconds: int = 60,
                 cooldown_seconds: int = 300):
        self.name = name
        r = get_redis()
        self.key_fail = f"cb:{name}:fails"
        self.key_open = f"cb:{name}:open"
        self.r = r
        self.fail_threshold = fail_threshold
        self.window = window_seconds
        self.cooldown = cooldown_seconds

    def is_open(self) -> bool:
        return bool(self.r.get(self.key_open))

    def record_failure(self):
        pipe = self.r.pipeline()
        pipe.incr(self.key_fail)
        pipe.expire(self.key_fail, self.window)
        pipe.execute()
        fails = int(self.r.get(self.key_fail) or 0)
        if fails >= self.fail_threshold:
            self.r.setex(self.key_open, self.cooldown, "1")

    def record_success(self):
        self.r.delete(self.key_fail, self.key_open)
```

#### 7.2.6 Mapeamento Bidirecional (Sync)

```python
# backend/integration/mapping.py (novo)
from pydantic import BaseModel

class PlatformMapping(BaseModel):
    """Por provedor: campo externo -> campo canônico e vice-versa."""
    provider_key: str
    status_map_inbound: dict[str, str]  # ex.: {"EMI": "PREPARING", "CAN": "CANCELED"}
    status_map_outbound: dict[str, str]  # ex.: {"COMPLETED": "delivered"}
    field_aliases: dict[str, str]  # ex.: {"codigoPedido": "external_id"}
```

### T7-01 Onboarding de Plataformas e Checklist de Documentação

**Criticidade:** Alta · **Dependências:** T0-05 (webhook fail-closed)

**Problema:** Atualmente adicionar um provedor exige editar `PROVIDER_ALIASES`,
`PROVIDER_PROFILES`, `OUTBOUND_STATUS_MAP`, `INBOUND_ORDER_STATUS_MAP`,
`DEFAULT_BASE_URLS`, `verify_inbound_signature`, `tasks.py`, `provider_clients.py`.

**Ação:**

Padronizar o checklist de onboarding (a ser preenchido por plataforma):

1. **Documentação API** — URL Swagger/Postman (ver tabela 7.1); credenciais sandbox.
2. **Auth** — OAuth2/token compartilhado/HMAC; campos necessários no `MarketPlace.json`.
3. **Inbound** — Webhook (URL/secret/HMAC header) OU Polling (endpoint + intervalo).
4. **Outbound** — Endpoint de atualização de status; mapeamento de status.
5. **Mapeamento de campos** — `PlatformMapping` (json RBAC-configurável no DB).
6. **Schema canônico** — Implementar `to_canonical` e `from_canonical` no adapter.
7. **Credenciais** — Campos necessários em `StoreIntegration` (criptografados Fernet).
8. **Testes de contrato** — WireMock/stub por adapter (T7-05).
9. **Métricas** — Label Prometheus por `provider_key`.
10. **Docs internas** — `docs/integrations/<provider>.md` com exemplo de payload.

**Arquivos afetados:**
- `backend/integration/onboarding.md` (novo checklist)
- `docs/integrations/` (novo diretório, subpasta por provedor)

### T7-02 Refatoração: ABC + Registry + Circuit Breaker

**Criticidade:** Alta · **Dependências:** T0-05, T7-01

**Problema:** Estrutura atual ad-hoc (sem ABC, sem registry, sem circuit breaker). 50+
provedores tornariam o `if/elif` ingovernável.

**Arquivos afetados:**
- `backend/integration/base.py` (novo)
- `backend/integration/registry.py` (novo)
- `backend/integration/circuit_breaker.py` (novo)
- `backend/integration/mapping.py` (novo)
- `backend/integration/adapters.py` (preservar aliases; chamar registry)
- `backend/integration/tasks.py` (refatorar para usar registry)
- `backend/integration/provider_clients.py` (migrar funções para dentro dos adapters)

**Correção (registry.py):** Ver 7.2.4 acima.

**Refatoração do tasks.py:** substituir `if provider == "DELIVERY_DIRETO"` por:

```python
# backend/integration/tasks.py — flush_outbox_events (parcial)
from integration.registry import get_adapter

# Em vez de if/elif por provider:
try:
    adapter = get_adapter(provider)
    cb = CircuitBreaker(f"outbound:{provider}")
    if cb.is_open():
        logger.warning("Circuit breaker aberto para %s — pulando evento", provider)
        # requeue com delay (não FAILED imediato)
        continue
    success = adapter.send_status(integration, external_id, status)
    if success:
        cb.record_success()
    else:
        cb.record_failure()
except KeyError:
    logger.error("Provider %s não registrado no hub", provider)
```

**Validação:**
- Novo provedor `ADAPTER_X` registrado via `@register("ADAPTER_X")` funciona sem editar
  `adapters.py` (apenas adiciona arquivo).
- Circuit breaker bloqueia 5 falhas consecutivas → open → cooldown → half-open.

### T7-03 Modelagem ProviderDefinition e DB-First Schema

**Criticidade:** Alta · **Dependências:** T7-02

**Problema:** `PROVIDER_ALIASES`, `PROVIDER_PROFILES`, `DEFAULT_BASE_URLS` são
hardcoded em Python. Hub plug-and-play precisa de auto-descoberta via DB.

**Arquivos afetados:**
- `backend/integration/models.py` (adicionar `ProviderDefinition`)
- `docs/schema.sql` (DDL Supabase)

**Correção (model):**

```python
# backend/integration/models.py — adicionar
class ProviderDefinition(models.Model):
    """Catálogo de provedores suportados pelo hub — auto-descoberta no painel."""
    PROVIDER_CATEGORIES = [
        ("DELIVERY", "Delivery"), ("MENU", "Cardápio Digital (Mesa)"),
        ("CRM", "CRM"), ("ERP", "ERP/E-commerce"),
        ("LOGISTICS", "Logística"), ("CASHBACK", "Cashback/Fidelidade"),
    ]
    provider_key = models.CharField(max_length=50, unique=True)  # IFOOD, ANOTA_AI
    display_name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=PROVIDER_CATEGORIES)
    docs_url = models.URLField(null=True)
    auth_mode = models.CharField(max_length=30)  # OAUTH2, TOKEN_SHARED, HMAC
    default_base_url = models.URLField(null=True)
    supports_polling = models.BooleanField(default=False)
    supports_webhook = models.BooleanField(default=True)
    supports_outbound = models.BooleanField(default=True)
    config_schema = models.JSONField(default=dict)  # campos esperados em StoreIntegration
    active_by_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "integration_providerdefinition"
```

```sql
-- docs/schema.sql (Supabase migration)
CREATE TABLE integration_providerdefinition (
    provider_key VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    category VARCHAR(20) NOT NULL CHECK (category IN (
        'DELIVERY','MENU','CRM','ERP','LOGISTICS','CASHBACK')),
    docs_url TEXT,
    auth_mode VARCHAR(30) NOT NULL,
    default_base_url TEXT,
    supports_polling BOOLEAN DEFAULT FALSE,
    supports_webhook BOOLEAN DEFAULT TRUE,
    supports_outbound BOOLEAN DEFAULT TRUE,
    config_schema JSONB DEFAULT '{}'::jsonb,
    active_by_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Seed inicial com as 54 plataformas da tabela 7.1
```

**Validação:**
- Painel admin exibe lista de provedores ativos baseada em `ProviderDefinition.objects.filter(active_by_default=True)`.

### T7-04 Idempotência de Webhook Inbound (deduplicação)

**Criticidade:** Alta · **Dependências:** T7-02

**Problema:** `IntegrationEventAudit.externalEventId` (`models.py:232-234`) não tem
`unique=True`. Re-entrega de webhook duplica auditoria e pode reenfileirar
processamento. Já existe `config/idempotency.py:67` (decorador para REST) mas não
aplicado em `api.py:17`.

**Ação:**

```sql
-- Supabase migration — unique em (provider, external_event_id)
CREATE UNIQUE INDEX IF NOT EXISTS uniq_integration_event_external
    ON "IntegrationEventAudit" (provider, externalEventId)
    WHERE externalEventId IS NOT NULL;
```

```python
# backend/integration/api.py — receive_webhook (após verify_signature)
from django.db import IntegrityError

try:
    audit = IntegrationEventAudit.objects.create(
        provider=provider,
        externalEventId=external_event_id,
        direction="INBOUND",
        ...
    )
except IntegrityError:
    # Já recebido — idempotente: responde 202 sem reprocessar
    return JsonResponse({"detail": "Evento já processado"}, status=200)
```

**Validação:**
- Re enviar mesmo webhook 2x → segunda retorna 200 sem criar novo outbox.

### T7-05 Plano de Testes (Unit / Integração / Carga / Homologação)

**Criticidade:** Alta · **Dependências:** T3-01, T7-02

**Tipos de teste por nível:**

| Nível | Objetivo | Ferramenta | Onde |
|---|---|---|---|
| Unit | `to_canonical`/`from_canonical` convertem corretamente | pytest + `youtubs` fixtures | `backend/tests/integration/test_adapters_<provider>.py` |
| Integração | Webhook → outbox → adapter → Order criada/atualizada | pytest `-m integration` + PostGIS + Redis | `backend/tests/integration/test_webhook_e2e.py` |
| Contrato | Adapter respeita schema plataforma (WireMock) | WireMock (Python: `wiremock` ou `responses`) | `backend/tests/integration/test_contract_<provider>.py` |
| Carga | 10k webhooks/min sem perda | Locust + análise p95 | `backend/tests/load/locustfile_webhook.py` |
| Homologação | Staging com sandbox do parceiro | manual + script e2e | `backend/scripts/e2e_<provider>.py` |

**Estrutura de testes:**

```python
# backend/tests/integration/test_adapters_ifood.py (exemplo)
import pytest
from integration.registry import get_adapter
from integration.base import CanonicalOrder

@pytest.mark.unit
def test_ifood_to_canonical():
    adapter = get_adapter("IFOOD")
    raw = {"codigoPedido": "1234", "merchantId": "m1", "code": "EMI", "total": 1990}
    canonical = adapter.to_canonical(raw)
    assert isinstance(canonical, CanonicalOrder)
    assert canonical.external_id == "1234"
    assert canonical.status == "EMI"
    assert canonical.total_cents == 1990
```

```python
# backend/tests/integration/test_webhook_e2e.py (exemplo)
@pytest.mark.integration
@pytest.mark.django_db
def test_webhook_creates_order_ifood(db_setup, ifood_integration, client):
    payload = {"codigoPedido": "ord-1", "code": "EMI", "total": 1990}
    sig = compute_hmac(ifood_integration.get_client_secret(), json.dumps(payload))
    response = client.post(
        "/api/v1/integration/webhooks/IFOOD",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_SITEGUARD_SIGNATURE=sig,
    )
    assert response.status_code == 202
    # Aguardar process_inbound_webhooks
    process_inbound_webhooks.delay()
    assert Order.objects.filter(externalOrderId="ord-1").exists()
```

**Locust (carga):**

```python
# backend/tests/load/locustfile_webhook.py (novo)
from locust import HttpUser, task, between
import json, hmac, hashlib

class WebhookUser(HttpUser):
    wait_time = between(0.1, 0.5)
    secret = "test-secret"

    @task
    def send_webhook(self):
        payload = {"codigoPedido": f"load-{self.environment.runner.user_count_count}", "code": "EMI"}
        body = json.dumps(payload).encode()
        sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
        self.client.post("/api/v1/integration/webhooks/IFOOD",
                         data=body, headers={"x-siteguard-signature": sig,
                         "Content-Type": "application/json"})
```

**Critérios de homologação (staging):**

- [ ] Webhook recebe e valida assinatura sem perda.
- [ ] Polling (quando suportado) traga eventos sem duplicar.
- [ ] Outbound atualiza status no parceiro em < 5s.
- [ ] Circuit breaker abre após 5 falhas e cura em 5 min.
- [ ] Sem perda de dados: `IntegrationEventAudit` = `IntegrationOutbox` count na janela.

### T7-06 Indicadores de Sucesso (SLI/SLO)

**Criticidade:** Média · **Dependências:** T2-04 (correlation IDs), T7-02

**Indicadores (SLI) com alvos (SLO):**

| SLI | Definição | SLO alvo |
|---|---|---|
| Taxa de sucesso de sincronização (inbound) | `INBOUND_ACK / INBOUND_TOTAL` por provedor/janela 5min | ≥ 99.5% |
| Taxa de sucesso de sincronização (outbound) | `OUTBOUND_SENT / OUTBOUND_TOTAL` por provedor/janela 5min | ≥ 99.0% |
| Latência p95 inbound → Order | `Order.createdAt - audit.createdAt`, p95 por provedor | < 10s |
| Latência p95 outbound | `IntegrationSent - event.createdAt`, p95 | < 5s |
| Ausência de perda de dados | `COUNT(INBOUND) == COUNT(Outbox PROCESSED+SENT)` por janela | 0 perdas |
| Duplicação de eventos | `COUNT(distinct externalEventId) == COUNT(audit rows)` por janela | 0 duplicações |
| Circuit breaker open frequency | Tempo em estado `open` / tempo total | < 1% |
| Reconciliação (re-sync) | Job diário compara total de orders parceiro vs NevesGo | diff < 0.1% |

**Métricas Prometheus (exemplo):**

```python
# backend/integration/metrics.py (novo)
from prometheus_client import Counter, Histogram

INBOUND_EVENTS = Counter(
    "integration_inbound_events_total", "Eventos inbound recebidos",
    ["provider", "status"]  # status: received, acknowledged, failed
)
OUTBOUND_EVENTS = Counter(
    "integration_outbound_events_total", "Eventos outbound enviados",
    ["provider", "status"]
)
WEBHOOK_LATENCY = Histogram(
    "integration_webhook_latency_seconds", "Latência webhook → Order",
    ["provider"], buckets=(0.5, 1, 2, 5, 10, 30, 60)
)
CIRCUIT_BREAKER_STATE = Counter(
    "integration_circuit_breaker_state_total", "Mudanças de estado do circuit breaker",
    ["provider", "state"]  # open, closed, half_open
)
```

**Dashboard Grafana:** Por provedor — 4 painéis (success rate, latency p95, outbox
backlog, circuit breaker state) com alerta em `success_rate < 99.5%` por 5min.

### T7-07 Cronograma de Implementação por Fases

**Criticidade:** Alta · **Dependências:** T7-02

**Estratégia:** Piloto com 4 provedores já parcialmente suportados (iFood, Anota AI,
Delivery Direto, 99Food) para validar o hub; depois onboarding em batches por
prioridade comercial.

| Fase | Duração | Marcos mensuráveis | Provedores |
|---|---|---|---|
| **F7.1 — Fundação do Hub** | 4 sem | ABC + Registry + CB + `ProviderDefinition` model + schema SQL + adapter iFood piloto | iFood |
| **F7.2 — Migração Adapters Existentes** | 3 sem | Anota AI, Delivery Direto, 99Food migrados para `@register`; testes de contrato green | Anota AI, Delivery Direto, 99Food |
| **F7.3 — CRM/ERP Piloto** | 3 sem | 2 CRMs prioritários (Cresce Vendas, CRMBonus se doc disponível); `ProviderDefinition` seeded | Cresce Vendas, CRMBonus |
| **F7.4 — Delivery Batch A** | 4 sem | 5 deliveries (Aiqfome, GoomerGO, Rappi, UberEats, Super Menu); docs internas `docs/integrations/` | +5 |
| **F7.5 — Logística + Cashback** | 3 sem | 3 (Agilizone, Foody Delivery, Fidelizi) | +3 |
| **F7.6 — Delivery Batch B + Menu Mesa** | 4 sem | 8 (Cardápio Web, Meu Cardápio AI, OnPedido, PedZap, Quero Delivery, Goomer, Goomer/Abrahão, Servit) | +8 |
| **F7.7 — WooCommerce + ERP** | 3 sem | 3 (WooCommerce, Tray, VMarket) | +3 |
| **F7.8 — Long Tail (25 restantes)** | 6 sem | Plataformas restantes (acordo comercial/doc) — instrumentado por métricas SLI | +25 |
| **F7.9 — Homologação Produção** | 2 sem | Staging com sandbox de top 10; paridade ≥ 99.5% sucesso; runbook por provedor | top 10 |

**Total:** ~32 sem para cobertura das 54 plataforma, com top 10 em ~19 sem.

### T7-08 Manutenibilidade, Escalabilidade e Compatibilidade com Versões Futuras

**Criticidade:** Média · **Dependências:** T7-03

**Manutenibilidade:**
- Cada adapter em arquivo próprio (`adapters_<provider>.py`) — isolamento de mudanças.
- Versionamento semântico de schema canônico (`CanonicalOrder` v1, v2) com campo `schema_version`.
- Changelog por provedor em `docs/integrations/<provider>/CHANGELOG.md`.
- Alertas de deprecation de API do parceiro monitorados (newsletter/developer portal).

**Escalabilidade:**
- Filas Celery dedicadas por provedor (`integration.ifood`, `integration.anota_ai`)
  via `CELERY_TASK_ROUTES` (T1-02 já estabelece a padrão).
- Worker pool por fila; autoescala baseada em backlog outbox (alerta > 1000 eventos).
- Circuit breaker por provedor isola falhas (um parceiro não derruba o hub).
- Cache de OAuth via Redis (T7-02: substituir `django.core.cache` por `get_redis()`).

**Compatibilidade com versões futuras das plataformas:**
- `ProviderDefinition.config_schema` documenta campos esperados; adapter tolerante
  a campos extras (Pydantic `Extra.allow`).
- Testes de contrato WireMock fixture congelar versão conhecida da API; CI alerta
  em regressão vs nova versão (compare contract antes/depois).
- Política de versionamento: `provider_api_version` em `ProviderDefinition`; adapter
  pode implementar `fetch_orders_v1` / `fetch_orders_v2` quando parceiro deprecia.
- Reconciliação diária (T7-06 SLI) detecta drift entre parceiro e NevesGo.

**Arquivos afetados:**
- `backend/integration/models.py` (`ProviderDefinition` com `api_version`)
- `docs/integrations/` por provedor (`README.md`, `CHANGELOG.md`, exemplo payload)
- `backend/integration/registry.py` (suporte a múltiplas versões de adapter)

### T7-09 Sync Bidirecional com Reconciliação

**Criticidade:** Média · **Dependências:** T7-02

**Problema:** Atualmente polling inbound + outbox outbound, sem reconciliação (re-sync
completo em caso de divergência entre parceiro e NevesGo).

**Correção (Celery beat diário):**

```python
# backend/integration/tasks.py — nova task
@shared_task(bind=True, max_retries=3)
def reconcile_provider_state(self, provider_key: str):
    """Reconciliação diária: compara orders do parceiro vs NevesGo e corrige drift."""
    from integration.registry import get_adapter
    adapter = get_adapter(provider_key)
    integrations = StoreIntegration.objects.filter(
        provider=provider_key, active=True
    )
    for integration in integrations:
        external_orders = adapter.fetch_orders(integration)
        neves_orders = Order.objects.filter(
            store_id=integration.store_id,
            external_source=provider_key,
        ).values("externalOrderId", "status")
        neves_map = {o["externalOrderId"]: o["status"] for o in neves_orders}
        for ext in external_orders:
            canonical = adapter.to_canonical(ext)
            if canonical.external_id not in neves_map:
                # Drift detectado: criar/atualizar
                process_inbound_webhooks.apply_async(
                    args=[canonical.external_id]
                )
                record_audit("system", "RECONCILIATION", target_type="Order",
                             target_id=canonical.external_id,
                             drift="missing_in_nevesgo")
        # Reportar SLI de reconciliação (diff count)
```

Adicionar ao `celery.py`:

```python
# backend/config/celery.py — beat_schedule
    "reconcile-ifood-daily": {
        "task": "integration.tasks.reconcile_provider_state",
        "schedule": crontab(hour=3, minute=15),
        "kwargs": {"provider_key": "IFOOD"},
    },
    # ... um por provedor
```

**Validação:**
- Em staging: simular perda de 10 webhooks e confirmar que reconciliação detecta e
  cria as orders faltantes dentro de 24h.

---

### Resumo da Onda 7

| Tarefa | Foco | Criticidade | Dependências |
|---|---|---|---|
| T7-01 | Onboarding checklist + docs por provedor | Alta | T0-05 |
| T7-02 | ABC + Registry + Circuit Breaker | Alta | T0-05, T7-01 |
| T7-03 | `ProviderDefinition` model + schema SQL | Alta | T7-02 |
| T7-04 | Idempotência de webhook inbound (unique constraint) | Alta | T7-02 |
| T7-05 | Plano de testes unit/integração/carga/homologação | Alta | T3-01, T7-02 |
| T7-06 | SLI/SLO + métricas Prometheus + dashboard | Média | T2-04, T7-02 |
| T7-07 | Cronograma por fases (F7.1-F7.9) | Alta | T7-02 |
| T7-08 | Manutenibilidade + escalabilidade + compat versões | Média | T7-03 |
| T7-09 | Reconciliação bidirecional diária | Média | T7-02 |

**Critério de aceitação da Onda 7:**
- Top 10 provedores homologados em staging com SLI ≥ 99.5% e 0 perdas de dados.
- Circuit breaker operational; novo provedor pode ser adicionado em ≤ 2 dias.
- Dashboard Grafana por provedor ativo.

**Observação:** Esta onda é **paralela às Ondas 0-6** — pode ser iniciada após
concluir Onda 0 (para herdar fail-closed em webhooks) e Onda 1 (para herdar
acks_late/filas dedicadas). O roadmap crítico de go-live não depende da Onda 7,
mas o hub de integrações é a alavanca de crescimento pós-go-live.

---

### Notas Finais

- Este plano é **vivo**: atualizar o `Status` de cada tarefa quando iniciada/concluída
  (recomendação: `[x]` no índice ou rastreio no GSD via `.planning/`).
- Tarefas marcadas `(BLOCK)` são bloqueadores de go-live; as demais são mitigadoras
  de risco e devem ter SLA pós-implantação acordado com o CEO/CTO.
- A análise que originou este plano está registrada na conversa de revisão e deve ser
  referenciada no commit final de cada onda.
- Após concluir Onda 0 + Onda 1, realizar reunião de avaliação de go-live controlado
  com gate de segurança + resiliência; só avançar para Onda 2+ após essa decisão.
- A **Onda 7 (Hub de Integrações)** é paralela às demais e habilita a estratégia
  de crescimento pós-go-live. Para iniciar, é pré-requisito ter concluído pelo menos
  a **Onda 0** (segurança fail-closed em webhooks) e a **Onda 1** (resiliência Celery).
  Top 10 provedores em ~19 semanas; cobertura completa das 54 plataformas em ~32.


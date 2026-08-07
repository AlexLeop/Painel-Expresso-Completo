# 🔍 PERÍCIA DE PRONTIDÃO FUNCIONAL (Code Readiness)
**Projeto:** Painel Expresso Neves & Django DRF — Logística/Financeiro
**Alvo de Deploy:** Produção / Easypanel
**Data:** 2026-07-01
**Metodologia:** Análise estática + execução de testes/lint/type-check. **Nenhum arquivo foi modificado.**

---

## 📊 RESUMO EXECUTIVO

| Métrica | Resultado |
|---|---|
| **Status de Deploy** | 🚫 **NÃO APTO** — bloqueadores críticos impedem o build/run em produção |
| **Testes** | 97 passaram / 7 pulados / 0 falhas — **mas cobertura ilusória** (SQLite + mocks, sem Postgres/RLS/GIS) |
| **Lint (ruff)** | "All checks passed!" — **falso positivo**: config ignora as regras mais importantes |
| **Type-check (tsc)** | Passa limpo (strict mode desligado) |
| **Achados Críticos (Blocker)** | **4** |
| **Achados Altos (High)** | **6** |
| **Achados Médios/Baixos** | **7** |

**Veredito:** A arquitetura (multi-tenant via RLS, DB-first com Supabase, FastAPI telemetry lane, Celery) é **bem concebida e internamente consistente** na camada de domínio. Porém, a **configuração de deploy está quebrada** em pontos que impedem o pipeline de funcionar: build do frontend falha (contexto do Dockerfile errado), segredos de produção (service_role) não são injetados, chaves Supabase **vazaram no histórico do git**, e `python manage.py migrate` roda no startup sem criar nada.

---

## 🚨 ACHADOS CRÍTICOS (BLOQUEADORES DE DEPLOY)

### C1. 🔴 VAZAMENTO DE CHAVE `service_role` DA SUPABASE NO GIT
**Arquivos:** `scratch/create_test_driver.py:7`, `scratch/sync_admin.py:7`, `scratch/sync_all_users.py:6`

A **chave `service_role`** de produção está **hardcoded** e **rastreada pelo git** (`git ls-files` confirma que os 3 arquivos estão versionados):
```
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIs...[JWT service_role]..."
```
A `service_role` **bypassa toda a RLS** do Supabase (acesso total ao banco). O `.gitignore` ignora `.env` e `.antigravity/`, mas **não** a pasta `scratch/`.

- **Impacto:** Qualquer pessoa com acesso ao repositório tem controle administrativo total do banco de produção. Mesmo removida agora, **permanece no histórico do git**.
- **Recomendação:**
  1. **Rotacionar imediatamente** a service_role no painel do Supabase (a atual deve ser considerada comprometida).
  2. Remover arquivos do tracking: `git rm --cached scratch/*.py` e adicionar `scratch/` ao `.gitignore`.
  3. Limpar histórico com `git filter-repo` ou BFG (`--replace-text`) já que o segredo está em commits antigos.
  4. Adicionar um pre-commit hook (e.g. `gitleaks`) para prevenir reincidência.

### C2. 🔴 BUILD DO FRONTEND FALHA NO DOCKER (contexto do Dockerfile incompatível)
**Arquivos:** `docker-compose.yml:143-146`, `docker-compose.local.yml:84-86`, `Novo_FrontEnd/Dockerfile:11-21`

O compose define:
```yaml
frontend:
  build:
    context: ./Novo_FrontEnd   # <- a RAIZ do build É a pasta do frontend
```
Mas o Dockerfile assume que a raiz é o **repo root**:
```dockerfile
COPY Novo_FrontEnd/package*.json ./   # procura ./Novo_FrontEnd/Novo_FrontEnd/ → NÃO EXISTE
COPY Novo_FrontEnd/ ./                # idem
```
Como o contexto já é `Novo_FrontEnd`, o `COPY Novo_FrontEnd/...` tenta copiar um subdiretório inexistente → **`npm install` roda sem package.json → build quebra**.

- **Impacto:** Imagem de produção do frontend **não builda** via `docker compose build`. Bloqueio total do deploy.
- **Recomendação:** Trocar no Dockerfile para paths relativos ao próprio contexto: `COPY package*.json ./` e `COPY . ./`. (Localmente `dist/server.cjs` existe porque o build foi feito manualmente com `npm run build` na máquina dev.)

### C3. 🔴 `SUPABASE_SERVICE_ROLE_KEY` NÃO É INJETADA EM PRODUÇÃO
**Arquivos:** `docker-compose.yml` (ausente), `easypanel-template.json` (ausente), `.env.example` (ausente), `config/supabase_client.py:50-60`, `config/panel_api.py:488,513`, `config/db_api.py:124,129,190,283,299`

`get_supabase_admin()` exige `SUPABASE_SERVICE_ROLE_KEY` e levanta `ValueError` se faltar:
```python
if not admin_url or not admin_key:
    raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY devem estar configurados...")
```
Porém **nenhum dos 3 artefatos de deploy** (compose, easypanel, env.example) define essa variável (`grep -c` = 0 no compose). Endpoints críticos que criam/deletam usuários no Supabase Auth a chamam:
- `POST /api/admin/operators` (criar operador + gerente)
- `POST /api/db/users` (criar usuário)
- `DELETE /api/db/users` (deletar usuário)
- `POST /api/db/company-drivers` (criar motoboy)

- **Impacto:** Em produção, **todo cadastro de operador/usuário/motoboy retorna HTTP 500**. Funcionalidade administrativa central indisponível.
- **Recomendação:** Adicionar `SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}` ao `environment` dos serviços django e celery_worker (e easypanel), e documentá-la no `.env.example`.

### C4. 🔴 RLS INCONSISTENTE EM CELERY TASKS (accounts/tasks.py) — vazamento entre tenants
**Arquivo:** `accounts/tasks.py:8-22` (comparar com `finance/tasks.py`, `integration/tasks.py`, `logistics/tasks.py`)

O padrimento correto (usado em `finance/tasks.py:33`, `integration/tasks.py` ×15, `logistics/tasks.py` ×3) é envolver a lógica em `tenant_context(operator_id)` para injetar as claims do RLS:
```python
with tenant_context(operator_id):
    # ORM respeita RLS aqui
```
Porém `process_biometrics_webhook` **NÃO usa** `tenant_context` (grep count = 0 para accounts/tasks.py). Ele executa `Driver.objects.select_for_update().get(id=driver_id)` direto, sem definir `role`/`operator_id` na sessão.

- **Impacto:** O worker Celery roda a conexão sem role injetada. Dependendo do role default da conexão no pool (`anon` → bloqueia; ou se herdar privilégios → **vazamento cross-tenant**). É uma quebra do contrato multi-tenant e silenciosa.
- **Recomendação:** Envolver a operação em `tenant_context(driver.operator_id)` (precisa buscar o `operator_id` primeiro).

---

## ⚠️ ACHADOS ALTOS (ALTO RISCO / QUEBRA DE FUNCIONALIDADE)

### H1. 🟠 `python manage.py migrate` NO STARTUP É NO-OP (modelos `managed=False`)
**Arquivos:** `docker-compose.yml:13`, `easypanel-template.json` (command do django), todos os `*/models.py`

O comando de startup do container django é:
```
bash -c "python manage.py migrate && python manage.py warmup_denylist && ..."
```
Porém **todos os modelos** (accounts, logistics, finance — verificado `managed = False` em 100% das `class Meta`) são database-first. Não há migrations Django (`find .../migrations/*.py` retorna vazio). O schema vive em `supabase/migrations/*.sql` e **só é aplicado via Supabase CLI**, que **não está orquestrada** pelo compose/easypanel.

- **Impacto:** `migrate` roda silenciosamente sem criar nada. Se o schema SQL do Supabase não tiver sido aplicado manualmente no alvo, **as tabelas não existem e tudo falha com 500**. Deploy depende de passo manual não documentado no pipeline.
- **Recomendação:** Documentar/executar a aplicação das migrations SQL do `supabase/migrations/` via `supabase db push` (usando `DIRECT_URL`) como step explícito de deploy. Remover ou justificar o `migrate` inerte.

### H2. 🟠 LINT "PASSA" APENAS PORQUE IGNORA AS REGRAS QUE IMPORTAM
**Arquivo:** `ruff.toml:1-8`

```toml
[lint]
ignore = ["E402", "F403", "F405", "E722", "F401"]
```
Ignora `F401` (unused-import), `F403/F405` (`from x import *`), `E722` (bare `except:`). Sem `[lint].select` ou `extend`, roda só o default `E4,E7,E9,F` **menos esses**. O resultado "All checks passed!" é **falso positivo de qualidade**: o código está cheio de `except Exception:` genéricos e imports mortos que o ruff foi instruído a não ver.

- **Impacto:** Falsa sensação de higiene. Bugs de `except Exception` que mascaram erros reais (vide `config/db_api.py` e `panel_api.py`) passam despercebidos.
- **Recomendação:** Adicionar um `select = ["E", "F", "I", "B", "UP", "SIM", "RUF"]` mínimo e tratar gradualmente os achados; ao menos reabilitar `F401` e `E722`.

### H3. 🟠 TESTES NÃO COBREM A CAMA CRÍTICA (Postgres/PostGIS/RLS/Supabase)
**Arquivos:** `pytest.ini:2`, `tests/test_settings.py:1-25`, `tests/gdal_mock_plugin.py`, motivos de skip em `tests/test_finance_tasks.py:117`, `tests/test_concurrency_finance.py:14`

- `pytest.ini` usa `DJANGO_SETTINGS_MODULE = tests.test_settings` → **SQLite in-memory**, sem PostGIS.
- O plugin `-p tests.gdal_mock_plugin` mocka `django.contrib.gis.gdal/geos` com `MagicMock`.
- 7 testes pulados explicitamente: *"Modelos são managed=False, requer banco real PostgreSQL para testes."*
- Resultado: os **97 passando validam apenas regras de negócio puras** (cálculo de corte, idempotência, schemas, transições de status). **Zero cobertura** de: queries PostGIS (`ST_DWithin`, geofence), enforcement de RLS, integração Supabase, tasks Celery reais, endpoints Ninja contra o DB.

- **Impacto:** "Suite verde" não prediz comportamento em produção. Regressões no SQL/RLS entram despercebidas.
- **Recomendação:** Adicionar uma suíte de testes de integração contra um Postgres+PostGIS real (CI com `supabase start` ou container `postgis/postgis`) marcada separadamente. Validar a middleware `SupabaseRLSMiddleware` com tokens forjados.

### H4. 🟠 ENDPOINTS MUTANTES DO `panel_api` SEM AUTENTICAÇÃO EXPLÍCITA
**Arquivo:** `config/panel_api.py`

O `panel_api = NinjaAPI(urls_namespace="panel_api")` é montado em `/api/` (`config/urls.py:26`) e **NÃO tem `auth=` global** (diferente do `api` principal em `config/api.py:97`). Apenas 5 de 16 endpoints usam `auth=auth_bearer`. Endpoints **sem auth** que mutam dados:
- `POST /api/machine/rides/create` (`:253`) — cria pedido
- `POST /api/machine/rides/cancel` (`:375`) — cancela pedido
- `POST /api/auth/change-tenant` (`:77`) — mock, mas exposto

E leituras sensíveis sem auth: `/machine/rides` (todos os pedidos), `/machine/drivers`, `/machine/credits/driver/balance`, `/schedules`, `/machine/rides/receipt`.

- **Impacto:** A defesa depende **unicamente** do `SupabaseRLSMiddleware` (`config/middleware.py`) que, sem token, aplica `SET LOCAL ROLE anon`. Se o RLS no SQL estiver bem configurado, o `anon` é bloqueado — mas isto é **frágil e indireto**; qualquer brecha na policy vira acesso/escrita não autenticada. Não há verificação de assinatura JWT na entrada destes endpoints.
- **Recomendação:** Aplicar `auth=auth_bearer` globalmente no `panel_api` (ou no mínimo em todos os POST/cancel/create). Manter o RLS como defesa em profundidade, não como única camada.

### H5. 🟠 FALLBACK DE AUTENTICAÇÃO JWT "VALIDA SEM ASSINATURA"
**Arquivos:** `config/api.py:60-76`, `config/middleware.py:34-52`

Em `SupabaseJWTAuth.authenticate`, quando `jwt.decode` local falha (`InvalidTokenError`), há um fallback remoto via `supabase.auth.get_user(token)`. Se o Supabase confirmar o usuário, o código **decodifica o token sem verificar assinatura**:
```python
return jwt.decode(token, options={"verify_signature": False, "verify_audience": False})
```
A middleware faz o **mesmo** (`config/middleware.py:45`). O comentário diz "validação local falhou" — mas isso também engloba **tokens com assinatura inválida/adulterada** cujo `sub`/`role` o Supabase possa acidentalmente resolver.

- **Impacto:** Superfície de ataque onde um token malformado, se aceito por `get_user`, tem suas claims (incl. `role`) lidas sem checagem criptográfica → possível escalada se `role` claim for controlável.
- **Recomendação:** Remover o fallback de "verificar sem assinatura". Se precisar de fallback, decodificar apenas claims não-sensíveis e forçar `role='authenticated'` (nunca confiar em `role`/`app_metadata` do token não-assinado). Validar com testes de token forjado.

### H6. 🟠 SEM HEALTHCHECKS EM NENHUM SERVIÇO
**Arquivos:** `docker-compose.yml`, `docker-compose.local.yml`, `easypanel-template.json`

`grep healthcheck` nos composes = **nenhum**. Existe `/api/v1/health` (`config/api.py:164`, com check de DB) e `/api/health` (frontend, mock em `server.ts`), mas **não há liveness/readiness probe** configurado em nenhum orquestrador.

- **Impacto:** Easypanel/Docker não reiniciam um container travado (ex.: Celery worker em deadlock, Redis indisponível). Deploy "verde" não significa saudável.
- **Recomendação:** Adicionar `healthcheck` (curl/wget para `/api/v1/health`) no serviço django e mapear probes no Easypanel para cada serviço. O frontend `server.ts:14` já expõe `/api/health`, mas o nginx roteia `/api/` → django (`nginx.conf:38`), então **o `/api/health` do express nunca é alcançável** — usar path distinto (ex.: `/healthz`) no frontend.

---

## 🟡 ACHADOS MÉDIOS

### M1. `gunicorn` AUSENTE do `requirements.txt`
**Arquivos:** `requirements.txt` (ausente), `Dockerfile:17`, `config/settings.py:84` (WSGI)
O `gunicorn` é instalado só via `pip install ... gunicorn` inline no Dockerfile (`:17`). Não está no `requirements.txt`, então qualquer deploy que **não** use o Dockerfile exato (ex.: build da imagem fastapi, ou deploy Easypanel por imagem com pip install separado) quebra o `CMD` do django. **Recomendação:** adicionar `gunicorn==23.0.0` ao `requirements.txt`.

### M2. `reportlab` SEM VERSION-LOCK
**Arquivos:** `requirements.txt:70`, uso em `finance/pdf_generator.py:2-5`
`reportlab` (sem versão) é a única dep não pinada. `firebase-admin==6.5.0` está pinado e é usado em `logistics/notifications.py` (inicializa só se `FIREBASE_SERVICE_ACCOUNT` existir — graceful no-op, ok). **Recomenda:** pinar `reportlab==4.x`.

### M3. ARQUIVOS TEMPORÁRIOS/MORTOS NA RAIZ (artefatos de dev)
**Arquivos:** `append.py`, `append2.py`, `patch.py`, `refactor.py`, `refactor_2.py`, `refactor_3.py`, `check_schema.py`
São scripts **one-shot de manipulação de código-fonte via string** (ex.: `append.py` faz `open("config/panel_api.py","a")`, `patch.py` faz `content.replace(...)`). São resíduo de desenvolvimento que **não devem ir para produção**. **Recomenda:** mover para `scripts/dev/` ou deletar; adicionar ao `.gitignore` ou limpar do tree.

### M4. PASTA `scratch/` COM SECRETS E SCRIPTS DE DEBUG
**Arquivos:** `scratch/*.py` (10 arquivos rastreados pelo git)
Contém scripts de sincronização/debug (`sync_admin.py`, `sync_all_users.py`, `create_test_driver.py`, `audit_db.py`, `check_db.py`) — e os segredos hardcoded (C1). **Recomenda:** `git rm -r --cached scratch/`, adicionar `scratch/` ao `.gitignore` (relacionado a C1).

### M5. CORS_ALLOW_ALL_ORIGINS=True EM PRODUÇÃO
**Arquivo:** `config/settings.py:57-59`
`CORS_ALLOW_ALL_ORIGINS = True` + `CORS_ALLOW_CREDENTIALS = True` ignora `CORS_ALLOWED_ORIGINS` do `.env`. Combinação de "todas origens" com credenciais é **anti-padrão OWASP** (o `corsheaders` envia `Access-Control-Allow-Origin: *` que com credenciais é rejeitado por browsers, quebrando ou enfraquecendo o CORS). **Recomenda:** em produção (`if not DEBUG`) forçar `CORS_ALLOW_ALL_ORIGINS = False` e usar a allowlist.

### M6. `/api/health` DO FRONTEND É INALCANÇÁVEL (sombra de rota pelo nginx)
**Arquivos:** `nginx.conf:38`, `Novo_FrontEnd/server.ts:13-15`
O express registra `GET /api/health`, mas o nginx roteia `location /api/` → `django:8000`. Logo a request cai no `/api/v1/health` (django) ou 404 — nunca no frontend. Inofensivo hoje (django tem seu próprio health), mas sinaliza desalinhamento de contrato. **Recomenda:** usar path não-colidente para o health do frontend.

### M7. `DIRECT_URL` DEFINIDO MAS NÃO CONSUMIDO PELO DJANGO
**Arquivos:** `.env.example:8`, `docker-compose.yml:25`, `config/settings.py`
`DIRECT_URL` (session pooler p/ migrations) é propagado a todos os serviços, mas `settings.py` só lê `DATABASE_URL`. Como migrations Django não existem (H1), `DIRECT_URL` é hoje **dead config**. **Recomenda:** remover dos composes ou usar explicitamente num step de `supabase db push`.

---

## 🟢 ACHADOS BAIXOS / POSITIVOS

- ✅ **Celery está bem amarrado:** `config/__init__.py:25` importa `celery_app`; `config/celery.py:14` faz `autodiscover_tasks()`; tasks registrados com `@shared_task` em todos os apps (4 em finance, 6 em logistics, 3 em integration, 1 em accounts); `beat_schedule` com 9 tarefas agendadas referenciando tasks existentes — **consistente**.
- ✅ **FastAPI fast_lane está coeso:** `fast_lane/main.py` é standalone (só Redis, sem ORM Django), autentica via `X-Device-Token` validado no Redis com **fail-closed** (503 se Redis cai), deny-list O(1). `fast_lane/Dockerfile` expõe 8001 corretamente e o `nginx.conf:10` aponta `fastapi:8001` — alinhado. Não compartilha settings com Django **por design** (lane isolada) — isto é **válido** para o padrão fast/slow lane.
- ✅ **Frontend prod serve em `0.0.0.0:5173`:** `server.ts:33` confirma `app.listen(PORT, "0.0.0.0")`, batendo com `nginx.conf:14` (`frontend:5173`).
- ✅ **Modelos `managed=False` são 100% consistentes** (DB-first legítimo) — o problema é operacional (H1), não de modelagem.
- ✅ **`tsc --noEmit` passa limpo; `dist/server.cjs` é produzido** pelo `esbuild` — o build frontend **local** funciona (o defeito é só no Docker, C2).
- ✅ **`DEFAULT_AUTO_FIELD`, `SECURE_SSL_REDIRECT`, cookies seguros, SSL proxy header** ligados em produção (`settings.py:182-186`) — hardening razoável.
- 🟡 **`SECRET_KEY` com fallback inseguro** (`settings.py:16` default `"django-insecure-..."`) — se `DJANGO_SECRET_KEY` não setada, roda com chave fraca. Baixo risco porque o compose always-seta, mas vale um `raise` se vazio em `not DEBUG`.

---

## 🗺️ MATRIZ DE AÇÃO PRIORITÁRIA

| # | Severidade | Achado | Esforço | Bloqueia Deploy? |
|---|---|---|---|---|
| C1 | 🔴 CRÍTICO | service_role vazada no git | M (rotacionar+limpar histórico) | Não, mas **incidente de segurança ativo** |
| C2 | 🔴 CRÍTICO | Build frontend Docker quebrado | P (ajustar COPY paths) | **SIM** |
| C3 | 🔴 CRÍTICO | service_role não injetada | P (env vars) | **SIM** (cadastros 500) |
| C4 | 🔴 CRÍTICO | RLS ausente em accounts/tasks | P (envolver tenant_context) | Não, mas **vazamento silencioso** |
| H1 | 🟠 ALTO | migrate no-op / schema SQL fora do pipeline | M | **SIM** (se schema não aplicado) |
| H2 | 🟠 ALTO | Lint falso-positivo | M | Não |
| H3 | 🟠 ALTO | Testes não cobrem DB/RLS/GIS | G | Não (risco de regressão) |
| H4 | 🟠 ALTO | panel_api sem auth em endpoints mutantes | M | Não (segurança) |
| H5 | 🟠 ALTO | Fallback JWT sem assinatura | M | Não (segurança) |
| H6 | 🟠 ALTO | Sem healthchecks | P | Não (observabilidade) |
| M1-M7 | 🟡 MÉDIO | deps, dead files, CORS, etc. | P-M cada | Não |

**Conclusão:** Resolva **C2, C3, H1** para conseguir um deploy funcional; **C1 e C4** são incidentes de segurança que exigem ação imediata independente do deploy. A base de código (domínio, tasks, modelagem) é sólida — o déficit está concentrado em **operação/infraestrutura e segurança**.

---
*Perícia gerada por análise estática e execução de tooling (pytest, ruff, tsc). Nenhum arquivo do projeto foi alterado — apenas este relatório foi criado.*

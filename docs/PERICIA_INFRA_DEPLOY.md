# 🔍 PERÍCIA TÉCNICA — INFRAESTRUTURA & DEPLOY

**Projeto:** Painel Expresso Neves (Django Ninja + FastAPI + Celery + Redis + Nginx + React/Vite)
**Stack alvo:** Easypanel (Docker) sobre Supabase (PostgreSQL + PostGIS)
**Data da perícia:** 2026-07-01
**Tipo:** Análise estática (read-only). **Nenhum arquivo foi modificado.**

---

## 📊 RESUMO EXECUTIVO

O projeto **NÃO está pronto para deploy em Easypanel** em seu estado atual. Há **2 bloqueios críticos** que impedem o build/deploy de acontecer, mais **1 bloqueio de runtime** e uma série de fragilidades que comprometem estabilidade, segurança e observabilidade em produção.

| Severidade | Quantidade | Significado |
|------------|------------|-------------|
| 🔴 **BLOQUEANTE** | 3 | Deploy/build falha ou serviço quebra ao subir |
| 🟠 **CRÍTICO** | 6 | Funciona, mas com risco alto de incidente/vazamento |
| 🟡 **MÉDIO** | 7 | Reduz robustez, observabilidade ou performance |
| 🔵 **BAIXO** | 4 | Boas práticas / hardening |

**Topologia analisada (7 serviços):** `redis` · `django:8000` · `fastapi:8001` · `celery_worker` · `celery_beat` · `nginx:80` · `frontend:5173`

---

## 🔴 ACHADOS BLOQUEANTES (impedem deploy/build)

### B1 — `Novo_FrontEnd/Dockerfile` QUEBRA o build do frontend
**Severidade:** 🔴 BLOQUEANTE
**Arquivos:** `Novo_FrontEnd/Dockerfile:15,19,28` · `docker-compose.yml:142-145`

O `docker-compose.yml` define o build context do frontend como `./Novo_FrontEnd`:
```yaml
frontend:
  build:
    context: ./Novo_FrontEnd      # ← contexto = o diretório Novo_FrontEnd/
    dockerfile: Dockerfile
```

Porém o Dockerfile assume que o contexto é a **raiz do projeto**:
```dockerfile
COPY Novo_FrontEnd/package*.json ./    # linha 15 — procura Novo_FrontEnd/Novo_FrontEnd/package.json
COPY Novo_FrontEnd/ ./                  # linha 19 — idem
COPY Novo_FrontEnd/package*.json ./     # linha 28 (stage 2) — idem
```

Verificação in loco:
```
$ ls Novo_FrontEnd/Novo_FrontEnd/ 2>/dev/null || echo "NO nested dir"
NO nested Novo_FrontEnd/Novo_FrontEnd dir => COPY Novo_FrontEnd/ WILL FAIL
```

**Impacto no deploy:** O `docker build` do serviço `frontend` **falha imediatamente** com erro `COPY failed: file not found`. Nenhum frontend é gerado. O `nginx` depende do `frontend` e fica sem upstream.

> ⚠️ **OBSERVAÇÃO:** O `easypanel-template.json:56-60` usa `context: "./Novo_FrontEnd"` (mesmo bug). O `easypanel-schema.json` declara o frontend como `source.type: "image"` sem caminho de build — também não builda localmente. **O bug está replicado em todos os artefatos de deploy.**

**Recomendação:** Trocar `COPY Novo_FrontEnd/package*.json ./` por `COPY package*.json ./` e `COPY Novo_FrontEnd/ ./` por `COPY . ./` (já que o contexto já é `./Novo_FrontEnd`).

---

### B2 — `collectstatic` escreve em path diferente do que o Nginx serve
**Severidade:** 🔴 BLOQUEANTE (runtime)
**Arquivos:** `config/settings.py:157` · `docker-compose.yml:18,136` · `nginx.conf:46-48`

Cadeia de causa-efeito:

1. `settings.py` define:
   ```python
   STATIC_ROOT = BASE_DIR / "staticfiles"   # → /app/staticfiles
   ```
2. O compose **não** monta volume em `/app/staticfiles`. Monta em `/app/static`:
   ```yaml
   django:  volumes: [ static_volume:/app/static ]
   nginx:   volumes: [ static_volume:/app/static ]
   ```
3. O `collectstatic --noinput` gera os arquivos em `/app/staticfiles/`.
4. O Nginx serve `/static/` via `alias /app/static/;` — diretório que **está vazio** (apenas o ponto de montagem do volume, sem conteúdo escrito dentro).

**Resultado:** Os assets estáticos do Admin Django (CSS/JS) ficam em `/app/staticfiles` (sem volume, perdidos a cada restart), enquanto o Nginx expõe `/app/static/` vazio. → **Admin Django sem estilo/JS em produção** (e qualquer `static()` resolvido por `STATIC_URL` retorna 404 via Nginx).

**Recomendação:** Igualar os paths. Opção A: `STATIC_ROOT = BASE_DIR / "static"` (alinha ao volume). Opção B: mudar o mount do volume para `/app/staticfiles` em ambos serviços e o alias do Nginx para `/app/staticfiles/`.

---

### B3 — `finance/0001` migration exige `CREAT​E TRIGGER` via pooler pgbouncer
**Severidade:** 🔴 BLOQUEANTE (condicional ao pooler)
**Arquivos:** `finance/migrations/0001_wallet_triggers.py:7-51` · `docker-compose.yml:24` · `config/settings.py:90-110`

O único migration Django existente (`finance/0001`) roda DDL pesada (`CREATE TRIGGER`, `CREATE FUNCTION ... LANGUAGE plpgsql`) via `RunPython`. Mas:

- `DATABASE_URL` aponta para o **pooler transacional (pgbouncer) na porta 6543** com `?pgbouncer=true`.
- O `settings.py` lê **apenas** `DATABASE_URL` (nunca `DIRECT_URL`) para o `migrate`. O `DIRECT_URL` só é usado por `settings_migrate.py` e `scripts/apply_schema.py`, que **não são invocados** no startup do compose (`docker-compose.yml:13-16`).

Poolers em modo transaction (Supabase `6543`) **não suportam statements multi-statement/DDL confiavelmente** e podem quebrar `CREATE FUNCTION`/`CREATE TRIGGER`. Mesmo que passe, o `CONN_MAX_AGE=600` reutiliza conexões pgbouncer — não há preparação segura para DDL.

**Impacto:** `python manage.py migrate` (linha 13 do compose) pode falhar ou deixar o trigger em estado inconsistente, **abortando todo o startup do container Django** (erro em qualquer dos comandos encadeados com `&&` derruba o `gunicorn`).

**Recomendação:** No entrypoint, usar `settings_migrate` (que usa `DIRECT_URL`/porta 5432) para `migrate`, ou aplicar o trigger via `supabase/migrations`/`psql` fora do startup do container.

---

## 🟠 ACHADOS CRÍTICOS

### C1 — Segredo JWT do Supabase exposto no disco (vazamento real)
**Severidade:** 🟠 CRÍTICO (segurança)
**Arquivos:** `.env` (não versionado, mas presente) · `.gitignore:1`

O `.env` no disco contém **credenciais reais do Supabase**:
```
DATABASE_URL="postgresql://postgres.mdrutawgropwgsmwygtz:91203095_%23%23%40@aws-1-us-west-2.pooler.supabase.com:6543/postgres?pgbouncer=true"
```
A senha do banco (`91203095_##@`) está em texto plano. Verificação de versionamento:
```
$ git ls-files -- ".env"
(vazio — .env NÃO está no git; está em .gitignore:1) ✓
```
**Bom:** não está no repositório. **Risco:** o arquivo está em uma pasta de projeto compartilhada/local; se houver backup, sync (OneDrive — note o caminho `Documents\`), ou commit acidental futuro, vaza. A senha deve ser rotacionada e o segredo movido para um secret manager / envs do Easypanel.

---

### C2 — Defaults inseguros em `${VAR:-fallback}` (deploy "funciona" com segredos vazios)
**Severidade:** 🟠 CRÍTICO
**Arquivos:** `docker-compose.yml:21-48,57-64,73-94,105-125,146-152`

Quase toda variável tem fallback embutido no compose. Se o Easypanel não injetar os envs, **o container sobe com segredos fictícios e "funciona" aparentemente**:
```yaml
- DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY:-sua-chave-secreta-aqui}
- SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET:-super-secret-jwt-token-with-at-least-32-characters-long}
- SUPABASE_KEY=${SUPABASE_KEY:-sua-chave-anon}
- GEMINI_API_KEY=${GEMINI_API_KEY:-sua-chave-gemini}
- DATABASE_URL=${DATABASE_URL:-postgresql://postgres:senha@pooler.supabase.com:6543/...}
```
`DJANGO_SECRET_KEY` default é uma string conhecida e previsível. Em produção isso permite **forja de sessões/cookies assinados**. O `settings.py:16` tem um segundo fallback ainda pior: `"django-insecure-development-key-only"`.

**Impacto:** Deploy silenciosamente inseguro se alguém esquecer de setar as envs. Erros só aparecem em runtime (conexão DB falha) ou não aparecem (secret key fraca).

**Recomendação:** Remover defaults sensíveis do compose; usar `required` (sem `:-`) em produção, ou fail-fast no `settings.py` (já existe para `DATABASE_URL` em non-DEBUG — estender para `DJANGO_SECRET_KEY`).

---

### C3 — Easypanel: discrepância de `projectName` entre os dois JSONs
**Severidade:** 🟠 CRÍTICO
**Arquivos:** `easypanel-template.json` (projectName: `expresso_neves`) · `easypanel-schema.json` (projectName: `expresso`)

```
easypanel-template.json → "projectName": "expresso_neves"
easypanel-schema.json   → "projectName": "expresso"        ← divergente
```
E no schema, internamente, há conflito adicional: o serviço Redis tem `password: "cad35b2f3964e05fd894"` (senha hardcoded em texto plano) enquanto o template usa `"sua-senha-segura-redis"`. Os dois arquivos descrevem o mesmo projeto com nomes diferentes → importação no Easypanel cria **dois projetos** ou serviços órfãos.

**Recomendação:** Unificar `projectName` em ambos os arquivos antes de importar.

---

### C4 — Conflito de nomenclatura: serviço `nginx` vs proxy reverso do próprio Easypanel
**Severidade:** 🟠 CRÍTICO
**Arquivos:** `docker-compose.yml:130-140` · `easypanel-*.json`

O compose define um serviço `nginx` que escuta na porta 80 e faz roteamento interno (`/api/`→django, `/telemetry`→fastapi, `/`→frontend). **O Easypanel já provê um proxy reverso/TLS terminator próprio (Traefik/Caddy) na borda.**

Há dois caminhos de deploy conflitantes:
- **(a)** Expor apenas o `nginx` (porta 80) no domínio → Easypanel termina TLS e repassa HTTP para o nginx interno. Funciona, mas cria **dupla proxy** (latência + headers).
- **(b)** Expor cada app em seu próprio domínio (o que o `easypanel-template.json:34-67,90-95` sugere: `api.expressoneves.com:8000`, `app.expressoneves.com:5173`, `fastapi.expressoneves.com:8001`) → **contorna o nginx**, tornando o serviço `nginx` **óbsoleto** e o `nginx.conf` morto.

Ambos os arquivos Easypanel são **inconsistentes** entre si sobre qual estratégia usar. O `easypanel-schema.json` lista o serviço `nginx` (estratégia a); o `easypanel-template.json` NÃO lista `nginx` e expõe cada app separadamente (estratégia b), com `DJANGO_ALLOWED_HOSTS=*`.

**Impacto:** Roteamento imprevisível, possível duplicação de TLS, e o `nginx.conf` pode nunca ser usado.

**Recomendação:** Decidir a estratégia explicitamente e alinhar os 3 arquivos (compose + 2 easypanel). Recomenda-se manter o nginx interno como único ponto de entrada e expor só ele no domínio raiz do Easypanel.

---

### C5 — `CORS_ALLOW_ALL_ORIGINS = True` + `CORS_ALLOW_CREDENTIALS = True` em produção
**Severidade:** 🟠 CRÍTICO (segurança)
**Arquivos:** `config/settings.py:57-59`

```python
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
```
Combinar "todas as origens" com "credenciais" é a configuração CORS **mais permissiva possível**. Qualquer site pode fazer requisições autenticadas à API. A env `CORS_ALLOWED_ORIGINS` (compose:31) é definida mas **ignorada** quando `CORS_ALLOW_ALL_ORIGINS=True`.

**Recomendação:** Em produção, `CORS_ALLOW_ALL_ORIGINS=False` e respeitar `CORS_ALLOWED_ORIGINS`.

---

### C6 — `DIRECT_URL` (session pooler, p/ migrations) nunca é usado pelo Django
**Severidade:** 🟠 CRÍTICO (relacionado a B3)
**Arquivos:** `config/settings.py:90-110` · `docker-compose.yml:25`

A Supabase orienta usar a porta **5432 (DIRECT_URL, session mode)** para migrations e **6543 (DATABASE_URL, transaction/pooler)** para a app. O projeto define as duas envs mas o `settings.py` só lê `DATABASE_URL`:
```python
db_url = os.environ.get("DATABASE_URL")   # só esta; DIRECT_URL é ignorada
```
Consequentemente o `manage.py migrate` (que roda via `DATABASE_URL` = pooler 6543) está no caminho errado. Existe um `settings_migrate.py` que leria `DIRECT_URL`, mas o compose **não seta `DJANGO_SETTINGS_MODULE=config.settings_migrate`** no passo de migrate.

**Recomendação:** Separar o `migrate` para usar `settings_migrate` (porta 5432) e deixar a app rodando via `DATABASE_URL` (6543).

---

## 🟡 ACHADOS MÉDIOS

### M1 — Nenhum `healthcheck`, `restart` policy nem `deploy.resources` no compose
**Severidade:** 🟡 MÉDIO
**Arquivos:** `docker-compose.yml` (todos os serviços)

Nenhum dos 7 serviços tem `healthcheck`, `restart`, nem limites de memória/CPU. Verificação:
- Sem `restart: unless-stopped` → se o `gunicorn`/celery cair, o container **não reinicia**.
- Sem `healthcheck` → Easypanel não sabe distinguir "container up" de "app saudável"; deploy rolling e restarts não são orientados por saúde real.
- `python manage.py migrate && ... && gunicorn` num único `command`: se qualquer passo falhar, o container entra em loop de restart no Easypanel (se houver restart policy) ou morre (se não houver) — e `migrate` **não é idempotente-safe para rodar a cada boot** de forma acoplada ao app.

**Recomendação:** Adicionar `healthcheck` (Django tem `/api/v1/health` em `config/api.py:164`; FastAPI tem `/api/health` no frontend, mas a própria FastAPI **não tem** health — ver M5), `restart: unless-stopped`, e separar `migrate`/`warmup`/`collectstatic` num job de init (one-shot) e não no comando do servidor.

---

### M2 — Nginx sem TLS, sem HSTS, sem `X-Forwarded-Proto`, sem tuning
**Severidade:** 🟡 MÉDIO
**Arquivos:** `nginx.conf` (inteiro)

- Escuta só na porta **80** (linha 19), sem `listen 443`, sem certificados. **Aceitável** se o Easypanel termina TLS na borda, **mas** o Nginx interno não repassa `X-Forwarded-Proto`.
- `settings.py:183` define `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`, mas o `nginx.conf` **não seta** `proxy_set_header X-Forwarded-Proto $scheme;` em **nenhum** location → o Django não enxerga o scheme https e o `SECURE_SSL_REDIRECT` (settings.py:186) pode redirecionar em loop ou não atuar corretamente.
- Sem HSTS (`SECURE_HSTS_*` ausentes em settings.py).
- Sem `client_max_body_size`, `proxy_read_timeout`, `gzip`, `proxy_buffering` → uploads de Proof/Comprovantes (`logistics/models.py:577 Proof`) podem bater no default 1MB do Nginx.

**Recomendação:** Adicionar `proxy_set_header X-Forwarded-Proto $scheme;` em todos locations; configurar HSTS e `client_max_body_size` adequado.

---

### M3 — `frontend` roda como dev-ish server Express (node) em produção
**Severidade:** 🟡 MÉDIO
**Arquivos:** `Novo_FrontEnd/Dockerfile:39` · `Novo_FrontEnd/server.ts` · `package.json:9`

O `package.json` `start` = `node dist/server.cjs`, que é o bundle do `server.ts` (Express). Confirma porta:
```ts
const PORT = process.env.PORT ? parseInt(process.env.PORT) : 5173;  // server.ts
```
O Nginx upstream `frontend:5173` (nginx.conf:14-15) está **consistente** com `PORT=5173` (compose:151) e `EXPOSE 5173` (Dockerfile:36). ✅ Porta correta.

Mas há **redundância arquitetural**: o `Dockerfile` já roda `vite build` (gera `dist/` estático) e ainda assim sobe um **processo Node/Express** só para servir `express.static(dist)` (server.ts:25-30). Em produção, servir estáticos via Nginx (ou CDN) é mais eficiente e remove um serviço inteiro. Hoje o Nginx já faz proxy HTTP para esse Express — layer desnecessária.

**Recomendação:** Considerar servir `dist/` diretamente pelo Nginx (volume compartilhado), eliminando o serviço `frontend` Node em produção.

---

### M4 — Dockerfiles sem multi-stage para o backend e rodam como root
**Severidade:** 🟡 MÉDIO
**Arquivos:** `Dockerfile` (raiz) · `fast_lane/Dockerfile`

- `Dockerfile` raiz: single-stage, instala `gcc libpq-dev gdal-bin libgdal-dev python3-gdal` (compiladores e -dev) **e os mantém na imagem final**. Imagem final fica grande (~1GB+) com toolchain de build desnecessário em runtime (só `gdal-bin` é preciso em runtime).
- **Roda como root**: nenhum `USER` não-root, nenhum `adduser`. Container roda gunicorn/celery como root → escalada de privilivilégio em caso de RCE.
- `gunicorn` **não está em `requirements.txt`** (instalado só no `RUN pip install ... gunicorn` do Dockerfile:17). Localmente (sem Docker) e em CI, `gunicorn` falta — inconsistência entre ambientes. O `fast_lane/Dockerfile` instala o `requirements.txt` inteiro (com Django, celery, etc.) mas a FastAPI **só usa `redis`, `fastapi`, `pydantic`** → imagem FastAPI carrega ~40 deps Django desnecessárias.

**Recomendação:** Multi-stage builder; `USER app`; adicionar `gunicorn`/`uvicorn[standard]` ao requirements; `fast_lane/Dockerfile` com requirements próprio mínimo.

---

### M5 — FastAPI sem endpoint de health
**Severidade:** 🟡 MÉDIO
**Arquivos:** `fast_lane/main.py`

O Django expõe `/api/v1/health` (`config/api.py:164`) e o frontend Express expõe `/api/health`. A FastAPI (telemetria) **não tem** rota de healthcheck. Sem isso, M1 não consegue fazer healthcheck real do serviço `fastapi`.

**Recomendação:** Adicionar `@app.get("/health")` em `fast_lane/main.py`.

---

### M6 — `manage.py migrate` no startup, acoplado e repetido a cada boot
**Severidade:** 🟡 MÉDIO
**Arquivos:** `docker-compose.yml:13-16`

O comando de startup encadeia `migrate && warmup_denylist && collectstatic && gunicorn`. Problemas:
- `migrate` roda **a cada restart/deploy**. Como o schema real vem do Supabase (`supabase/migrations/*.sql`) e os models Django são `managed=False` (ver A1), o `migrate` só roda o `finance/0001` (trigger). Em múltiplas réplicas do Django no Easypanel, **várias instâncias tentam `migrate` concorrentemente** → race condition no lock de migration do Django.
- O `&&` faz o gunicorn **não subir** se o migrate falhar — o que é desejável, mas torna o container inutilizável por um problema de DDL (ver B3).

**Recomendação:** Separar `migrate` num job init (one-shot) do Easypanel, não no comando do servidor.

---

### M7 — Nginx sem `resolver` e sem `proxy_next_upstream` para DNS dinâmico do Easypanel
**Severidade:** 🟡 MÉDIO
**Arquivos:** `nginx.conf:6-16`

Os `upstream` usam nomes fixos (`django:8000`, `fastapi:8001`, `frontend:5173`). No Easypanel, containers podem ter IPs renovados a cada deploy. O Nginx resolve esses nomes **uma vez no startup** (sem `resolver`). Se um backend reiniciar com novo IP, o Nginx mantém o IP antigo em cache → **502 Bad Gateway** até reiniciar o Nginx.

**Recomendação:** Usar `resolver 127.0.0.11 valid=10s;` + variável no `proxy_pass http://django:8000;` para re-resolução dinâmica.

---

## 🔵 ACHADOS BAIXOS / OBSERVAÇÕES

### A1 — Estratégia de migrations híbrida (Django `managed=False` + SQL Supabase) — **ESTÁ COERENTE, mas frágil**
**Severidade:** 🔵 INFO (esclarece o ponto 2 do briefing)
**Arquivos:** `*/models.py` (59× `managed = False`) · `finance/migrations/0001_*`

Os 4 apps (`accounts`, `logistics`, `integration`, `finance`) têm **59 modelos**, **todos** com `managed = False` e `db_table` apontando para tabelas PascalCase (`"Wallet"`, `"Order"`, etc.) criadas pelo `supabase/migrations/*.sql`. **Isso é por design**:

- ✅ O `manage.py migrate` **NÃO tenta criar tabelas** para accounts/logistics/integration (não há migration e os models são unmanaged). Ele só aplica `finance/0001` (trigger de wallet).
- ✅ O schema real é gerenciado pelo Supabase CLI (`supabase/migrations/20260619200249_initial_schema.sql` etc.), aplicado **fora do container** (via `scripts/apply_schema.py` usando `DIRECT_URL`).
- ⚠️ **Risco de drift:** não há garantia automatizada de que o `models.py` está sincronizado com o SQL. Ex.: o SQL define `geom GEOGRAPHY(Polygon,4326)` em `ServiceZone`; se o model não refletir, queries GeoDjango quebram. Não há teste `makemigrations --check` no CI.

**Conclusão sobre o ponto 2:** O `migrate` **faz algo útil** (aplica o trigger `finance/0001`), mas **não cria o schema de negócio**. Se o Supabase já tiver o schema aplicado, o startup não quebra por models — quebra apenas pelo trigger (ver B3, se via pooler).

### A2 — `warmup_denylist` **EXISTE** ✅
**Severidade:** 🔵 INFO (esclarece o ponto 10)
**Arquivo:** `accounts/management/commands/warmup_denylist.py`

O command existe e está corretamente registrado (`accounts/management/__init__.py`, `accounts/management/commands/__init__.py` presentes). Ele lê `SecurityDenylist` e `Operator` e popula o Redis. **Não quebra o startup por inexistência.** Porém, depende de: (a) Redis acessível em `redis://redis:6379/1`, (b) `SecurityDenylist`/`Operator` serem acessíveis via model `managed=False` contra o Supabase — se a tabela não existir no Supabase alvo, o `warmup_denylist` (linha 28-30) lança `DatabaseError` e **derruba o startup** (está encadeado com `&&`).

### A3 — Celery: `autodiscover_tasks` + `beat_schedule` **ESTÃO configurados** ✅
**Severidade:** 🔵 INFO (esclarece o ponto 5)
**Arquivos:** `config/__init__.py:25` · `config/celery.py:14,18-61`

- `config/__init__.py` importa `celery_app` corretamente (necessário p/ `@shared_task`). ✅
- `celery.py:14` chama `app.autodiscover_tasks()`. ✅
- `celery.py:18-61` define **9 schedules** no `beat_schedule` (hourly cutoff, global cutoff, telemetry consumer/persist, position partitions, outbox flush, webhooks, partner poll, geofence, retention). ✅ **Beat NÃO roda ocioso.**
- Todos os tasks referenciados existem: `finance/tasks.py`, `logistics/tasks.py`, `integration/tasks.py` (verificado). ✅
- ⚠️ Pequeno: `config/__init__.py:8-23` faz monkeypatch de `register_converter` por "bug do Django 6 com django-ninja". É um workaround frágil — vale rastrear quando o django-ninja corrigir upstream.

### A4 — PostGIS em produção: **Supabase suporta** e o schema habilita
**Severidade:** 🔵 INFO (esclarece o ponto 8)
**Arquivos:** `supabase/migrations/20260619200249_initial_schema.sql:11` · `docker/init.sql` · `config/settings.py:159-164`

- `CREATE EXTENSION IF NOT EXISTS "postgis";` está no schema Supabase (linha 11). ✅
- `settings.py` mantém `django.contrib.gis` + engine `postgis` em Linux/Docker e só desabilita em `win32`. ✅ Coerente.
- A imagem instala `gdal-bin`/`python3-gdal` (necessário p/ bindings GeoDjango). ✅
- **Porém:** `docker/init.sql` (que bootstraparia um Postgres local Docker) **NÃO habilita postgis** nem `uuid-ossp`. Esse init.sql **não é montado** em nenhum compose (não há serviço `db`/`postgres` — usa-se Supabase externo). Logo, `docker/init.sql` é **código morto** para o deploy atual. Se algum dia se usar Postgres local, o init.sql faltará as extensões e o Django quebrará ao importar `django.contrib.gis`.

---

## 📋 MATRIZ DE COBERTURA — Easypanel × docker-compose (ponto 7)

| Serviço (compose) | easypanel-template.json | easypanel-schema.json | Status |
|---|---|---|---|
| `redis` | ❌ ausente | ✅ `redis` (senha hardcode) | **Inconsistente** |
| `django` | ✅ `django` (domain) | ✅ `django` (image, sem source) | OK-ish |
| `fastapi` | ✅ `fastapi` (domain) | ✅ `fastapi` | OK |
| `celery_worker` | ✅ `celery-worker` | ✅ `celery_worker` | **nome divergente** (`-` vs `_`) |
| `celery_beat` | ✅ `celery-beat` | ✅ `celery_beat` | **nome divergente** |
| `nginx` | ❌ **ausente** | ✅ `nginx` | **template não cobre nginx** |
| `frontend` | ✅ `frontend` (domain) | ✅ `frontend` | OK |

- **compose tem 7 serviços; template cobre 6 (falta `nginx`); schema cobre 7.**
- Os dois JSONs **não concordam** entre si (projectName, nomes de serviço celery, presença/ausência do nginx, tipo de source `github` vs `image`).
- `easypanel-schema.json` usa `source.type: "image"` com `image: ""` (vazio) para django/fastapi/celery/frontend → **não builda**, exige imagem pré-publicada que não existe no projeto.

---

## ✅ CHECKLIST DE CORREÇÃO (priorizado)

### Antes de qualquer deploy (bloqueantes)
- [ ] **B1** Corrigir `COPY` paths no `Novo_FrontEnd/Dockerfile` (contexto já é `./Novo_FrontEnd`).
- [ ] **B2** Alinhar `STATIC_ROOT` ↔ volume mount ↔ `nginx alias` (mesmo path `/app/static`).
- [ ] **B3** Fazer `migrate` via `DIRECT_URL`/porta 5432 (usar `settings_migrate`) e não via pooler 6543.

### Crítico (antes de expor em produção)
- [ ] **C1** Rotacionar senha do Supabase vazada no `.env`; usar secrets do Easypanel.
- [ ] **C2** Remover defaults sensíveis do compose; fail-fast em `DJANGO_SECRET_KEY`.
- [ ] **C3** Unificar `projectName` nos 2 JSONs Easypanel.
- [ ] **C4** Definir e documentar a estratégia de proxy (nginx interno vs domínios separados).
- [ ] **C5** `CORS_ALLOW_ALL_ORIGINS=False` em produção.
- [ ] **C6** Separar `migrate` para `settings_migrate`.

### Robustez (médio)
- [ ] **M1** Adicionar `healthcheck` + `restart` + separar init-job de migrate.
- [ ] **M2** `X-Forwarded-Proto`, HSTS, `client_max_body_size` no Nginx.
- [ ] **M3** Avaliar servir estáticos do frontend via Nginx (eliminar serviço Node).
- [ ] **M4** Multi-stage Dockerfile + `USER` não-root + `gunicorn` em requirements.
- [ ] **M5** Endpoint `/health` na FastAPI.
- [ ] **M6** Tirar `migrate` do comando do servidor.
- [ ] **M7** `resolver` + re-resolução DNS no Nginx.

---

## 🔬 METODOLOGIA

Análise 100% estática, read-only, via leitura de: 3 Dockerfiles, 2 compose files, `nginx.conf`, `requirements.txt`, `config/*.py` (settings/celery/__init__/wsgi/urls/api), `*/models.py` e `*/apps.py` de 4 apps, `*/tasks.py` de 3 apps, `*/management/commands/`, `supabase/migrations/*.sql`, `docker/init.sql`, `.env`/`.env.example`, `Novo_FrontEnd/{Dockerfile,package.json,server.ts}`, ambos `easypanel-*.json`, `.gitignore`, e `git ls-files`. Compatibilidade Django 6.0.6 + Python 3.14 + django-ninja 1.3.0 + django-stubs 6.0.5 confirmada via pesquisa externa (suporte oficial do Django 6.0 a Python 3.12–3.14). **Nenhum arquivo do projeto foi alterado.**

---

*Fim do relatório — Perícia Infraestrutura & Deploy, Expresso Neves.*

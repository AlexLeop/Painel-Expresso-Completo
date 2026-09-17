# Standalone PostGIS PostgreSQL & Native Superadmin Multi-Tenant Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar 100% da infraestrutura do Expresso Neves do Supabase para o banco de dados PostgreSQL 17 + PostGIS 3.5 puro hospedado na VPS, implementando autenticação JWT nativa com soberania irrestrita para o PlatformAdmin (Superadmin Global) sobre todos os tenants.

**Architecture:** O banco de dados PostgreSQL com PostGIS recebe a execução de todo o DDL (tabelas, triggers, enums e funções). O backend Django Ninja assume a gestão de senhas com PBKDF2 e geração de tokens JWT via `PyJWT` e `DJANGO_SECRET_KEY`. O `PlatformAdmin` recebe bypass total das barreiras de RLS/tenancy e capacidade de alternar entre tenants ou visualizar tudo globalmente no frontend React.

**Tech Stack:** PostgreSQL 17 + PostGIS 3.5, Django 6 + Django Ninja, PyJWT, psycopg 3, React 18, Vite, TailwindCSS.

**Spec:** [`docs/superpowers/specs/2026-09-17-standalone-postgres-and-native-auth-design.md`](file:///c:/Users/lxleo/Documents/Expresso%20Neves/Painel%20Expresso%20Neves%20e%20Django%20DRF/docs/superpowers/specs/2026-09-17-standalone-postgres-and-native-auth-design.md)

## Global Constraints
- Nenhuma dependência externa de Supabase Auth ou Supabase DB Pooler deve permanecer ativa.
- O PostGIS 3.5 é obrigatório para tipos `GEOGRAPHY(Point, 4326)` e `GEOGRAPHY(Polygon, 4326)`.
- Senhas de banco contendo caracteres especiais `@` e `#` DEVEM ser URL-encoded (`Al147258%40%23`).
- A soberania do `PlatformAdmin` deve ser absoluta: um PlatformAdmin pode acessar qualquer endpoint de tenant (`is_platform_admin == True` faz bypass das checagens restritivas de `operator_id`).
- Senhas de usuários devem ser hasheadas com algoritmos de alto custo criptográfico (`PBKDF2-SHA256`).
- Testes automatizados com pytest devem manter 100% de aprovação (117+ testes existentes).

---

### Task 1: Environment & Database Schema Migration to VPS PostgreSQL PostGIS

**Files:**
- Modify: `.env`
- Modify: `backend/config/settings.py:90-135`
- Create: `backend/scripts/setup_database.py`
- Test: `backend/tests/test_vps_database_schema.py`

**Interfaces:**
- Consumes: `URL_EXTERNA` e `URL_INTERNA` com credenciais PostGIS da VPS.
- Produces: Banco `expresso_neves` na VPS 100% estruturado com as 16 migrações SQL aplicadas e colunas de autenticação nativa.

- [ ] **Step 1: Write test to verify VPS database connection and schema tables**
  Create `backend/tests/test_vps_database_schema.py` asserting tables `Operator`, `PlatformAdmin`, `StaffMember`, `Store`, `Driver`, `Order`, `Wallet`, `WithdrawalRequest`, `PayoutPolicyConfig` exist and have expected columns.

- [ ] **Step 2: Update `.env` and `settings.py`**
  Set `DATABASE_URL` and `DIRECT_URL` pointing to the VPS database with encoded password (`postgres://postgres:Al147258%40%23@191.101.235.244:5433/expresso_neves?sslmode=disable`). Adjust `settings.py` so that when `DATABASE_URL` is configured, it properly parses URL and handles connection.

- [ ] **Step 3: Create `setup_database.py` migration runner**
  Script reads all 16 `.sql` files in `supabase/migrations/` sequentially, runs them against the VPS database in ordered transactions, and executes `ALTER TABLE` to ensure `passwordHash` column exists on `PlatformAdmin`, `StaffMember`, `Driver`, `ClientPortalUser`.

- [ ] **Step 4: Execute database build on VPS and run verification test**
  Run `python backend/scripts/setup_database.py` and run `pytest backend/tests/test_vps_database_schema.py -v`.

- [ ] **Step 5: Commit**
  `git add .env backend/config/settings.py backend/scripts/setup_database.py backend/tests/test_vps_database_schema.py`
  `git commit -m "feat(database): build standalone postgres postgis database schema on vps"`

---

### Task 2: Backend Models & Security Service (Password Hashing & JWT)

**Files:**
- Create: `backend/accounts/security.py`
- Modify: `backend/accounts/models.py:63-180`
- Modify: `backend/logistics/models.py`
- Test: `backend/tests/test_security_service.py`

**Interfaces:**
- Consumes: `DJANGO_SECRET_KEY` de `django.conf.settings`.
- Produces: `hash_password(raw_password)`, `verify_password(raw_password, hashed)`, `create_access_token(payload)`, `create_refresh_token(payload)`, `decode_token(token)`.

- [ ] **Step 1: Write test for password hashing and JWT encoding/decoding**
  Create `backend/tests/test_security_service.py` testing hashing, password match, wrong password, token expiry, payload claims (`sub`, `email`, `role`, `is_platform_admin`, `operator_id`).

- [ ] **Step 2: Implement `backend/accounts/security.py`**
  Implement standard secure password hashing using `django.contrib.auth.hashers.make_password` and `check_password`, and JWT token creation/decoding using `jwt` (PyJWT) with `algorithms=["HS256"]`.

- [ ] **Step 3: Update models with `passwordHash` and auth helpers**
  In `accounts/models.py` add `passwordHash = models.CharField(max_length=255, null=True, blank=True, db_column="passwordHash")` to `PlatformAdmin` and `StaffMember`, and add helper methods `set_password(pwd)` and `check_password(pwd)`.

- [ ] **Step 4: Run tests and verify PASS**
  Run `pytest backend/tests/test_security_service.py -v`.

- [ ] **Step 5: Commit**
  `git add backend/accounts/security.py backend/accounts/models.py backend/tests/test_security_service.py`
  `git commit -m "feat(accounts): implement native password hashing and jwt token service"`

---

### Task 3: Native Auth Endpoints & Superadmin Sovereignty

**Files:**
- Modify: `backend/accounts/api.py`
- Modify: `backend/accounts/auth.py`
- Modify: `backend/config/api.py`
- Modify: `backend/config/middleware.py`
- Create: `backend/accounts/management/commands/create_platform_admin.py`
- Test: `backend/tests/test_native_auth_api.py`

**Interfaces:**
- Consumes: `security.py` hashing and tokens.
- Produces: Endpoints `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/refresh`, `POST /api/auth/logout`.
- Produces: `NativeJWTAuth` decorator for Ninja routers and sovereign bypass for `PlatformAdmin`.

- [ ] **Step 1: Write test for auth endpoints and Superadmin privilege**
  Create `backend/tests/test_native_auth_api.py` testing:
  - Login as PlatformAdmin -> returns 200, JWT token, `is_platform_admin=True`.
  - Login as StaffMember -> returns 200, JWT token, `operator_id` bound.
  - Login with bad password -> returns 401.
  - `GET /api/auth/me` -> returns profile. For PlatformAdmin, lists all Operators for tenant switching.
  - Superadmin access to protected operator endpoints -> bypasses tenant barrier.

- [ ] **Step 2: Implement `NativeJWTAuth` and update `accounts/auth.py`**
  Replace `SupabaseJWTAuth` with `NativeJWTAuth(HttpBearer)` validating tokens with `settings.SECRET_KEY`.
  In `require_role(roles)`: if token has `is_platform_admin=True`, grant immediate access (Superadmin sovereignty).

- [ ] **Step 3: Implement auth endpoints in `accounts/api.py`**
  Register routes:
  - `POST /auth/login` (email, password)
  - `GET /auth/me`
  - `POST /auth/refresh`
  - `POST /auth/logout`

- [ ] **Step 4: Create Django management command `create_platform_admin.py`**
  Create `backend/accounts/management/commands/create_platform_admin.py` that takes `--email`, `--name`, `--password` and creates or updates a `PlatformAdmin` with hashed password.

- [ ] **Step 5: Run tests and verify PASS**
  Run `pytest backend/tests/test_native_auth_api.py -v`.

- [ ] **Step 6: Commit**
  `git add backend/accounts/api.py backend/accounts/auth.py backend/config/api.py backend/config/middleware.py backend/accounts/management/commands/create_platform_admin.py backend/tests/test_native_auth_api.py`
  `git commit -m "feat(auth): implement native login endpoints and superadmin sovereignty bypass"`

---

### Task 4: Complete Backend Supabase Decoupling & Regression Suite

**Files:**
- Modify: `backend/config/panel_api.py`
- Modify: `backend/config/urls.py`
- Modify: `docker-compose.yml`
- Modify: `easypanel-template.json`
- Test: Full backend regression suite (`pytest backend/tests/`)

**Interfaces:**
- Consumes: Clean PostgreSQL connection and native JWT auth.
- Produces: Backend completely free of Supabase dependencies and passing 100% of tests.

- [ ] **Step 1: Clean up `panel_api.py` and remove Supabase references**
  Update `panel_api.py` to use `NativeJWTAuth` and native models.
  Remove `config/supabase_client.py` usages.

- [ ] **Step 2: Update `docker-compose.yml` and `easypanel-template.json`**
  Update environment variables in deployment manifests, replacing Supabase variables with PostgreSQL parameters.

- [ ] **Step 3: Run full backend test suite**
  Run `$env:PYTHONPATH="backend"; python -m pytest backend/tests/ -k "not TestDockerBootstrap" -q` and verify all 120+ tests pass without errors.

- [ ] **Step 4: Commit**
  `git add backend/config/panel_api.py backend/config/urls.py docker-compose.yml easypanel-template.json`
  `git commit -m "refactor(config): remove all supabase dependencies from backend and deployment configs"`

---

### Task 5: Frontend Migration to Native Auth & Tenant Switching

**Files:**
- Create: `frontend/src/lib/auth.ts`
- Modify: `frontend/src/contexts/AuthContext.tsx`
- Modify: `frontend/src/pages/Login.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/supabase.ts` (deprecate/remove)
- Test: Frontend build (`npm run build`)

**Interfaces:**
- Consumes: `/api/auth/login`, `/api/auth/me` do backend Django.
- Produces: Frontend 100% autônomo com login nativo, sessão em `localStorage` e seletor de tenant para Superadmin.

- [ ] **Step 1: Implement `frontend/src/lib/auth.ts`**
  Functions `login(email, password)`, `getProfile()`, `refreshToken()`, `logout()`.

- [ ] **Step 2: Update `AuthContext.tsx`**
  Remove `@supabase/supabase-js` imports and events.
  On mount, check `localStorage.getItem("nevesgo:token")` and call `/api/auth/me`.
  Handle `changeTenant(operatorId)` for Superadmin.

- [ ] **Step 3: Update `Login.tsx`**
  Replace `supabase.auth.signInWithPassword` with `login(email, password)`.
  Handle successful login and redirect to `/`.

- [ ] **Step 4: Update `api.ts`**
  Read token from `localStorage.getItem("nevesgo:token")` and inject `Authorization: Bearer <token>`.

- [ ] **Step 5: Run production build**
  Execute `npm run build` in `frontend/` to confirm zero compilation errors.

- [ ] **Step 6: Commit**
  `git add frontend/src/lib/auth.ts frontend/src/contexts/AuthContext.tsx frontend/src/pages/Login.tsx frontend/src/lib/api.ts`
  `git commit -m "feat(frontend): migrate auth to native django endpoints and enable superadmin tenant switcher"`

---

### Task 6: Execution on VPS Database & Superadmin Creation

**Files:**
- Execute: Database runner against VPS (`setup_database.py`)
- Execute: Superadmin creation (`create_platform_admin.py`)
- Create: `walkthrough.md` updated with verification evidence

**Interfaces:**
- Consumes: VPS PostgreSQL PostGIS na porta 5433 / 5432.
- Produces: Banco zerado completamente migrado e conta Superadmin pronta para uso.

- [ ] **Step 1: Run database setup on VPS**
  Run `python backend/scripts/setup_database.py` pointing to `URL_EXTERNA`.
  Confirm 16 migrations applied and all tables created.

- [ ] **Step 2: Create initial Superadmin account on VPS**
  Run `python backend/manage.py create_platform_admin --email admin@expressoneves.com.br --name "Administrador Global" --password "AdminMaster123@#"`

- [ ] **Step 3: Test login end-to-end**
  Simulate login request to verify token generation and `is_platform_admin: true` claims.

- [ ] **Step 4: Update walkthrough.md and finalize**
  Update `walkthrough.md` with complete documentation of the new architecture, connection details and superadmin credentials.

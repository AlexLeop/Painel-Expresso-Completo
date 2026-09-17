# Plano de Implementação: Controle de Acesso e Permissões em 3 Níveis (SuperAdmin Master, Operador Logístico e Lojista)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar o controle de acesso e autorização em 3 níveis (SuperAdmin Master, Operador Logístico e Lojista) no backend Django e no frontend React/Vite, garantindo menus adaptativos, isolamento de dados por tenant/loja e autenticação unificada.

**Architecture:** 
1. Backend: Ampliação da autenticação em `accounts/api.py` para suportar `PlatformAdmin`, `StaffMember` e `ClientPortalUser`, adicionando metadados `role`, `user_type`, `is_platform_admin`, `operator_id` e `client_id` aos tokens JWT e respostas de `/auth/login` e `/auth/me`.
2. Backend Scoping: Proteção de rotas em `config/db_api.py` e `config/panel_api.py` para isolar dados de operadores e lojistas.
3. Frontend: Reestruturação do `AppLayout.tsx` com 3 perfis primários (`superadmin`, `operador_admin`/`operador_staff`, `lojista`), adaptando a barra lateral, ocultando rotas exclusivas do SuperAdmin (`/operadores`, `/snapshots`, `/sync`, `/gerencial`) para operadores e lojistas, e implementando route guards rígidos.

**Tech Stack:** Python 3.12, Django 5, Django Ninja, PostgreSQL 17 + PostGIS, React 18, TypeScript, Tailwind CSS, Lucide React.

**Spec:** `docs/superpowers/specs/2026-09-17-hierarchical-rbac-3tiers-design.md`

## Global Constraints
- `managed = False` em todos os modelos Django (database-first).
- Não quebrar o fluxo de autenticação nativo JWT.
- Senhas geradas com hash PBKDF2 (`accounts.security.hash_password` e `verify_password`).
- Testes automatizados executados com `pytest`.
- TypeScript build validado com `npm run build` na pasta `frontend`.

---

### Task 1: Backend Domain Models & Auth Helpers
**Files:**
- Modify: `backend/logistics/models.py:41-60`
- Test: `backend/tests/test_rbac_models.py`

**Interfaces:**
- Produces: `ClientPortalUser.set_password(raw_password: str)` e `ClientPortalUser.check_password(raw_password: str) -> bool`

- [ ] **Step 1: Write the test for ClientPortalUser password hashing**
```python
import pytest
from logistics.models import ClientPortalUser

def test_client_portal_user_password_methods():
    user = ClientPortalUser(email="lojista@teste.com", name="Lojista Teste")
    user.set_password("SenhaForte123!")
    assert user.passwordHash is not None
    assert user.passwordHash != "SenhaForte123!"
    assert user.check_password("SenhaForte123!") is True
    assert user.check_password("SenhaIncorreta") is False
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_rbac_models.py -v`

- [ ] **Step 3: Update `logistics/models.py`**
Add `passwordHash` field, `set_password`, and `check_password` methods to `ClientPortalUser`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_rbac_models.py -v`

- [ ] **Step 5: Commit changes**
```bash
git add backend/logistics/models.py backend/tests/test_rbac_models.py
git commit -m "feat(auth): add passwordHash and verification methods to ClientPortalUser"
```

---

### Task 2: Backend Authentication (`accounts/api.py`) 3-Tier Login & Profile
**Files:**
- Modify: `backend/accounts/api.py:220-370`
- Test: `backend/tests/test_rbac_auth.py`

**Interfaces:**
- Consumes: `ClientPortalUser`, `StaffMember`, `PlatformAdmin`
- Produces:
  - Superadmin: `role="superadmin"`, `is_platform_admin=True`, `user_type="platform_admin"`
  - Operador Admin: `role="operador_admin"`, `is_platform_admin=False`, `user_type="operator_staff"`
  - Operador Staff: `role="operador_staff"`, `is_platform_admin=False`, `user_type="operator_staff"`
  - Lojista: `role="lojista"`, `is_platform_admin=False`, `user_type="client_portal_user"`, `client_id=...`

- [ ] **Step 1: Write tests for 3-tier login**
Test `handle_login` and `handle_me` returns for SuperAdmin, StaffMember, and ClientPortalUser.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_rbac_auth.py -v`

- [ ] **Step 3: Update `backend/accounts/api.py`**
Implement the 3 checks in `handle_login` and `handle_me`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_rbac_auth.py -v`

- [ ] **Step 5: Commit changes**
```bash
git add backend/accounts/api.py backend/tests/test_rbac_auth.py
git commit -m "feat(auth): implement 3-tier login in handle_login and handle_me"
```

---

### Task 3: Backend API Scoping & Route Protections (`config/db_api.py` and `config/panel_api.py`)
**Files:**
- Modify: `backend/config/db_api.py`
- Modify: `backend/config/panel_api.py`
- Test: `backend/tests/test_rbac_scoping.py`

**Interfaces:**
- Consumes: `request.auth` (`is_platform_admin`, `operator_id`, `client_id`, `role`)
- Produces:
  - Scoped queries for `Store`, `Driver`, `StaffMember`, `Order`
  - 403 Forbidden for non-superadmins accessing `/admin/operators` or platform configs

- [ ] **Step 1: Write test for API scoping and protection**
Verify that a `StaffMember` only sees their own operator's data, and `ClientPortalUser` only sees their store's data.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_rbac_scoping.py -v`

- [ ] **Step 3: Update `backend/config/db_api.py` and `panel_api.py`**
Implement caller tenancy filtering on `get_companies`, `get_company_drivers`, `get_users`, `create_user`, and route protections.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_rbac_scoping.py -v`

- [ ] **Step 5: Commit changes**
```bash
git add backend/config/db_api.py backend/config/panel_api.py backend/tests/test_rbac_scoping.py
git commit -m "feat(security): enforce tenant scoping and RBAC route protection on panel APIs"
```

---

### Task 4: Frontend Adaptive Navigation & Route Guards (`AppLayout.tsx`)
**Files:**
- Modify: `frontend/src/components/layout/AppLayout.tsx`
- Test: `frontend/src/__tests__/AppLayout.test.tsx` (or build validation)

**Interfaces:**
- Consumes: `session.user` (`role`, `is_platform_admin`, `user_type`, `name`, `email`)
- Produces:
  - Clean, tailored menus for `superadmin`, `operador_admin`, `operador_staff`, `lojista`
  - Route guards preventing unauthorized URL access

- [ ] **Step 1: Update navigationGroups and role mapping in `AppLayout.tsx`**
Define distinct groups:
- SuperAdmin: Operacional Global, Gestão de Operadores, Financeiro Master, Sistema (Operadores, Usuários, Snapshots, Sync, Gerencial, Configurações).
- Operador: Operacional da Central, Gestão (Motoboys, Empresas, Equipe), Financeiro (Lançamentos, Financeiro, Saques PIX, Relatórios, Histórico), Configurações.
- Lojista: Minha Loja (Dashboard, Corridas/Chamar Motoboy, Histórico), Financeiro (Faturas & Lançamentos da Loja), Configurações (Perfil).

- [ ] **Step 2: Update route guards in `useEffect`**
Protect `/operadores`, `/snapshots`, `/sync`, `/gerencial` against non-superadmins.
Protect `/motoboys`, `/empresas`, `/saques`, `/escala` against lojistas.

- [ ] **Step 3: Build frontend to verify TypeScript correctness**
Run: `npm --prefix frontend run build`

- [ ] **Step 4: Commit changes**
```bash
git add frontend/src/components/layout/AppLayout.tsx
git commit -m "feat(ui): implement 3-tier adaptive navigation and route guards in AppLayout"
```

---

### Task 5: Frontend User & Modal Adaptation (`Usuarios.tsx`, `UserModal.tsx`)
**Files:**
- Modify: `frontend/src/pages/Usuarios.tsx`
- Modify: `frontend/src/components/UserModal.tsx`

**Interfaces:**
- Consumes: `user.role`, `user.is_platform_admin`
- Produces:
  - Role selection appropriate for user's level (Superadmin can create platform staff / operator admins; Operator admin can only create their staff or lojistas).

- [ ] **Step 1: Update `UserModal.tsx` and `Usuarios.tsx`**
Filter available roles and company options according to current user privilege.

- [ ] **Step 2: Build frontend to verify TypeScript correctness**
Run: `npm --prefix frontend run build`

- [ ] **Step 3: Commit changes**
```bash
git add frontend/src/pages/Usuarios.tsx frontend/src/components/UserModal.tsx
git commit -m "feat(ui): adapt user management modal and lists to 3-tier hierarchy"
```

---

### Task 6: Full System Verification & Git Push
- [ ] **Step 1: Run complete backend test suite**
Run: `pytest backend/tests/ -v`

- [ ] **Step 2: Run frontend production build**
Run: `npm --prefix frontend run build`

- [ ] **Step 3: Push changes to `origin/main` for EasyPanel deployment**
Run: `git push origin main`

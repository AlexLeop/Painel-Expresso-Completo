# Plano de Implementação: Correção e Destravamento do Sistema (Expresso Neves)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir todas as falhas e regressões ativas no sistema, destravando o despacho de corridas no painel web, restaurando a conformidade de 100% dos testes automatizados e estabelecendo os adaptadores necessários para o avanço dos gates de produção.

**Architecture:** 
1. Resiliência de Idempotência: Tornar o backend tolerante e retrocompatível na rota `/operator/dispatch-store-ride` (gerando chave baseada em hash do payload quando não fornecida explicitamente), enquanto o frontend web passa a enviar `Idempotency-Key` (UUIDv4) em todas as mutações.
2. Contrato de Deploy e CI: Atualizar o teste de paridade de Dockerfile para aceitar topologias com múltiplos serviços Celery segregados (`celery_realtime` + `celery_integrations`).
3. Segurança e Senhas Fortes: Integrar validação de senhas com `validate_password` e piso mínimo de 10 caracteres no endpoint `/users`.
4. Integridade do Ledger e Testes Herméticos: Atualizar DDL mock do SQLite em `test_driver_wallet_management.py` com o campo `metadata` e blindar `SettlementEngine` contra objetos mock sem UUID.

**Tech Stack:** Django 6.0, Django Ninja, React 19 / TypeScript, Docker / EasyPanel, SQLite / PostgreSQL.

**Spec:** Laudo Pericial Forense de Prontidão (2026-09-26) e Master Plan (`PLANO_IMPLEMENTACAO_CORRECOES_SISTEMA_SEM_MOBILE.md`).

## Global Constraints

- Proibido qualquer bypass de tenant ou permissão.
- Não introduzir dependências externas pesadas sem suporte a fallback offline/hermético.
- Todos os testes unitários e de integração devem passar (255+ passing, 0 failed, 0 errors).
- O frontend React deve compilar sem nenhum erro de TypeScript (`npm run lint` limpo).

---

### Task 1: Resiliência de Idempotência e Desbloqueio do Painel Web

**Files:**
- Modify: `backend/config/idempotency.py:80-92`
- Modify: `frontend/src/components/CreateRideModal.tsx:440-450`
- Modify: `backend/tests/test_finance_accounting.py:504-518`
- Test: `backend/tests/test_finance_accounting.py`

**Interfaces:**
- Consumes: `Idempotency-Key` header ou fallback hash SHA-256 do body.
- Produces: `dispatch-store-ride` aceita requisições com chave explícita (frontend atualizado) ou gera chave determinística caso omitida, retornando HTTP 409 quando saldo for insuficiente (em vez de travar com HTTP 400).

- [ ] **Step 1: Ajustar `backend/config/idempotency.py` para gerar fallback determinístico se header ausente**
Se `Idempotency-Key` não for enviado, gerar hash SHA256 do payload do body + rota + user_id em vez de rejeitar com 400 caso seja configurado com `allow_fallback=True` ou por padrão tolerante.

- [ ] **Step 2: Atualizar `frontend/src/components/CreateRideModal.tsx` para enviar `Idempotency-Key`**
Adicionar `Idempotency-Key: crypto.randomUUID()` aos headers de `authFetch("/api/v1/operator/dispatch-store-ride")`.

- [ ] **Step 3: Executar teste de despacho de corrida e validar retorno 409 para saldo insuficiente**
Run: `& ".\.venv\Scripts\python.exe" -m pytest tests/test_finance_accounting.py::test_operator_dispatch_store_ride_flow --basetemp=./tmp_test -v`
Expected: PASS

---

### Task 2: Correção do Contrato de Containers EasyPanel

**Files:**
- Modify: `backend/tests/test_deploy_docker_context.py:23-30`
- Test: `backend/tests/test_deploy_docker_context.py`

**Interfaces:**
- Consumes: `docker-compose.yml` e `docker-compose.local.yml`.
- Produces: Validação flexível que exige que todos os serviços backend (`django`, `celery_*`, `migrate`) usem `dockerfile: Dockerfile` e nenhum use caminhos legados (`backend/Dockerfile`), suportando a segregação de 4 ou 5 serviços.

- [ ] **Step 1: Atualizar asserção em `backend/tests/test_deploy_docker_context.py`**
Ajustar `assert content.count("dockerfile: Dockerfile") >= 4` (ou verificar especificamente que `dockerfile: Dockerfile` é usado para cada serviço Python sem referências a `backend/Dockerfile`).

- [ ] **Step 2: Executar teste de deploy**
Run: `& ".\.venv\Scripts\python.exe" -m pytest tests/test_deploy_docker_context.py --basetemp=./tmp_test -v`
Expected: PASS (todos os testes do arquivo passam).

---

### Task 3: Validação de Senha Forte no Cadastro de Usuários

**Files:**
- Modify: `backend/config/db_api.py:430-470`
- Test: `backend/tests/test_rbac_scoping.py:test_user_creation_requires_explicit_strong_password`

**Interfaces:**
- Consumes: `payload.password` em `create_user`.
- Produces: Rejeição com HTTP 422 para senhas com menos de 10 caracteres ou senhas fracas comuns.

- [ ] **Step 1: Aplicar validação rigorosa de senha em `backend/config/db_api.py`**
Exigir `len(payload.password) >= 10` e validar contra `django.contrib.auth.password_validation.validate_password`. Se inválida, lançar `HttpError(422, ...)`.

- [ ] **Step 2: Executar teste de senha forte**
Run: `& ".\.venv\Scripts\python.exe" -m pytest tests/test_rbac_scoping.py::test_user_creation_requires_explicit_strong_password --basetemp=./tmp_test -v`
Expected: PASS

---

### Task 4: Alinhamento de Schema e Mocks no Ledger Financeiro

**Files:**
- Modify: `backend/tests/test_driver_wallet_management.py:110-140`
- Modify: `backend/finance/services.py:34-43`
- Modify: `backend/finance/tests.py:60-80`
- Test: `backend/tests/test_driver_wallet_management.py` e `backend/finance/tests.py`

**Interfaces:**
- Consumes: `WalletTransaction` com campo `metadata`.
- Produces: DDL SQLite hermético compatível; `SettlementEngine.settle_order` checando `WeeklyInvoiceLineItem` com proteção para UUID.

- [ ] **Step 1: Adicionar coluna `metadata` no DDL SQLite de `test_driver_wallet_management.py`**
Incluir `"metadata" TEXT DEFAULT '{}'` na tabela mock `WalletTransaction`.

- [ ] **Step 2: Proteger checagem de `order.id` em `backend/finance/services.py` e mockar no teste unitário**
Garantir que a checagem de `already_settled_item` trate casos em que `order` é mock ou valide `order_id` com segurança. No teste `finance/tests.py`, passar mock de `WeeklyInvoiceLineItem.objects.filter` para paridade completa.

- [ ] **Step 3: Executar testes de carteira e liquidação**
Run: `& ".\.venv\Scripts\python.exe" -m pytest tests/test_driver_wallet_management.py finance/tests.py --basetemp=./tmp_test -v`
Expected: PASS

---

### Task 5: Validação Global e Verificação de 100% da Suíte de Testes

**Files:**
- Verify: Todas as suítes backend e frontend.

- [ ] **Step 1: Executar suíte completa do backend**
Run: `& ".\.venv\Scripts\python.exe" -m pytest --basetemp=./tmp_test -q`
Expected: 0 failed, 0 errors, 255+ passed.

- [ ] **Step 2: Executar lint/typecheck do frontend**
Run: `npm run lint` em `frontend/`
Expected: Exit code 0.

- [ ] **Step 3: Commit das correções**
```bash
git add backend/config/idempotency.py frontend/src/components/CreateRideModal.tsx backend/tests/test_deploy_docker_context.py backend/config/db_api.py backend/tests/test_driver_wallet_management.py backend/finance/services.py backend/finance/tests.py
git commit -m "fix(core): resolve ride dispatch idempotency, docker contract parity, strong password validation and test ledger schema"
```

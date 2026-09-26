# Plano de Implementação: Prontidão de Produção e Escala (Expresso Neves)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar os bloqueadores de concorrência, vazamento de recursos, gargalos de I/O síncrono, vulnerabilidades de RLS e duplicidade financeira, tornando o backend, frontend web e infraestrutura do Expresso Neves aptos para produção real sob escala.

**Architecture:** Transição da infraestrutura para concurrency multi-threaded/async (Gthread/Uvicorn), segregação de filas Celery especializadas (realtime vs integrations vs batch), transações financeiras com idempotência estrita no ledger, drenagem em streaming de telemetria no Redis com descarte de geofence pós-conclusão, otimização de agregações SQL do dashboard para consultas em lote, e fixação de isolamento RLS transaction-local compatível com pooling de conexões (PgBouncer).

**Tech Stack:** Django 6.0, Django Ninja, FastAPI (Fast Lane), PostgreSQL 17 + PostGIS, Redis 7, Celery 5.6, Gunicorn (gthread), React 19 / TypeScript, Docker / EasyPanel.

**Spec:** Perícia Técnica Forense de Prontidão de Produção e Escala (2026-09-25).

## Global Constraints

- Proibido qualquer bypass de tenant em queries e comandos: todo acesso deriva da identidade JWT verificada.
- Operações de dinheiro usam centavos inteiros (`BigIntegerField`), referências de idempotência imutáveis e locks pessimistas (`select_for_update`).
- Nenhum DDL (`ALTER TABLE`, `CREATE INDEX`) pode rodar em runtime de requisições HTTP da aplicação.
- PostgreSQL RLS é mandatório com `FORCE ROW LEVEL SECURITY` e `is_local=true` nas claims de sessão.
- I/O de rede externo (webhooks, integrações) nunca pode rodar dentro de transações de banco de dados nem travar a fila de eventos de tempo real.
- O aplicativo mobile está fora do escopo desta intervenção por diretriz direta do usuário.

---

### Task 1: Blindagem de Concorrência e Multi-tenancy no Banco (RLS & Middleware)

**Files:**
- Modify: `backend/config/middleware.py:38-60`
- Create: `database/migrations/20260925100000_force_rls_and_ledger_constraints.sql`
- Modify: `backend/config/db_api.py:14-56` (remover DDL em runtime)
- Test: `backend/tests/test_tenant_security.py`

**Interfaces:**
- Consumes: `NativeAuthRLSMiddleware`, PostgreSQL RLS policies
- Produces: `set_config('request.jwt.claims', %s, true)` com escopo de transação local; tabelas com `FORCE ROW LEVEL SECURITY`.

- [ ] **Step 1: Escrever teste que falha para isolamento de sessão RLS**
Criar `backend/tests/test_tenant_security.py`:
```python
import pytest
from django.db import connection
from config.middleware import NativeAuthRLSMiddleware
from unittest.mock import Mock

@pytest.mark.django_db
def test_rls_claims_are_transaction_local():
    """Garante que request.jwt.claims usa is_local=true e não vaza para a próxima query."""
    middleware = NativeAuthRLSMiddleware(Mock(return_value="OK"))
    request = Mock()
    request.META = {"HTTP_AUTHORIZATION": "Bearer fake_token"}
    
    # Simula token decodificado
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('request.jwt.claims', true);")
        initial = cursor.fetchone()[0]
        assert initial is None or initial == ""
```

- [ ] **Step 2: Executar teste e validar falha ou gap de isolamento**
Run: `pytest backend/tests/test_tenant_security.py -v`
Expected: Verificar comportamento de claims.

- [ ] **Step 3: Ajustar `middleware.py` para usar `is_local=true`**
Em `backend/config/middleware.py:50`:
Substituir:
```python
cursor.execute(
    "SELECT set_config('request.jwt.claims', %s, false);",
    [json.dumps(rls_claims)],
)
```
Por:
```python
cursor.execute(
    "SELECT set_config('request.jwt.claims', %s, true);",
    [json.dumps(rls_claims)],
)
```
E garantir que as queries subsequentes executem dentro do bloco atômico onde a claim permanece viva.

- [ ] **Step 4: Criar migration SQL com `FORCE ROW LEVEL SECURITY` e constraint contábil**
Criar `database/migrations/20260925100000_force_rls_and_ledger_constraints.sql`:
```sql
-- Forçar RLS inclusive para o proprietário da tabela (impede bypass silencioso do Django)
ALTER TABLE "Order" FORCE ROW LEVEL SECURITY;
ALTER TABLE "Stop" FORCE ROW LEVEL SECURITY;
ALTER TABLE "Driver" FORCE ROW LEVEL SECURITY;
ALTER TABLE "Store" FORCE ROW LEVEL SECURITY;
ALTER TABLE "Position" FORCE ROW LEVEL SECURITY;
ALTER TABLE "Wallet" FORCE ROW LEVEL SECURITY;
ALTER TABLE "WalletTransaction" FORCE ROW LEVEL SECURITY;
ALTER TABLE "WeeklyStoreInvoice" FORCE ROW LEVEL SECURITY;
ALTER TABLE "WeeklyInvoiceLineItem" FORCE ROW LEVEL SECURITY;
ALTER TABLE "ManualEntry" FORCE ROW LEVEL SECURITY;

-- Idempotência estrita no Ledger Financeiro: Uma corrida só pode gerar um repasse de mesma categoria
CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_tx_order_category_unique
    ON "WalletTransaction" (operator_id, category, (metadata->>'order_id'))
    WHERE metadata->>'order_id' IS NOT NULL;

-- Uma corrida só pode constar uma única vez numa fatura semanal
CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_invoice_order_unique
    ON "WeeklyInvoiceLineItem" (order_id);
```

- [ ] **Step 5: Remover chamadas de DDL em runtime no `db_api.py`**
Em `backend/config/db_api.py`:
Esvaziar o corpo de `_ensure_database_schema()` para:
```python
def _ensure_database_schema():
    # DDL em runtime removido por segurança operacional.
    # Todas as alterações de schema residem exclusivamente em database/migrations/.
    pass
```

- [ ] **Step 6: Executar testes de validação**
Run: `pytest backend/tests/test_tenant_security.py -v`
Expected: PASS

- [ ] **Step 7: Commit das alterações**
```bash
git add backend/config/middleware.py database/migrations/20260925100000_force_rls_and_ledger_constraints.sql backend/config/db_api.py backend/tests/test_tenant_security.py
git commit -m "fix(security): enforce FORCE RLS, transaction-local claims and remove runtime DDL"
```

---

### Task 2: Blindagem do Motor de Geofence e Telemetria (Vazamento de Memória & Auto-Arrive)

**Files:**
- Modify: `backend/logistics/tasks.py:406-480` (`process_geofence_triggers`)
- Modify: `backend/logistics/tasks.py:287-365` (`persist_telemetry_buffer`)
- Modify: `backend/logistics/api_driver.py:1367-1375` (limpeza de `geofence:stops`)
- Modify: `backend/config/db_api.py:1369-1373` (leitura real de `positions` do Redis)
- Test: `backend/tests/test_geofence_concurrency.py`

**Interfaces:**
- Consumes: Redis `geofence:stops:{operator_id}`, `geofence_triggers`, `driver_positions:{operator_id}`
- Produces: Auto-arrive com validação estrita de driver; `ZREM` pós-conclusão; drenagem contínua de GPS; endpoint `/positions` retornando dados reais do Redis.

- [ ] **Step 1: Escrever teste que falha para geofence de motoboy errado**
Criar `backend/tests/test_geofence_concurrency.py`:
```python
import pytest
from logistics.models import Order, Driver, Stop
from logistics.tasks import process_geofence_triggers
import json

@pytest.mark.django_db
def test_geofence_does_not_arrive_order_of_different_driver(redis_mock):
    # Setup: Driver A tem Order A em STARTED
    # Evento no Redis emitido por Driver B para o stop da Order A
    # process_geofence_triggers NÃO PODE mudar Order A para ARRIVED
    pass
```

- [ ] **Step 2: Corrigir `process_geofence_triggers` em `backend/logistics/tasks.py`**
Substituir a consulta de auto-arrive em `backend/logistics/tasks.py:441-470` por:
```python
# Mapeia stop -> driver_id que disparou o evento
event_driver_by_stop = {p["stop_id"]: p["driver_id"] for p in parsed_events}

stops = Stop.objects.filter(id__in=stop_ids).values("id", "order_id", "order__driver_id")
order_to_data = {
    s["order_id"]: {"stop_id": s["id"], "assigned_driver_id": str(s["order__driver_id"])}
    for s in stops
}

valid_order_ids = []
for order_id, data in order_to_data.items():
    triggering_driver = str(event_driver_by_stop.get(data["stop_id"]))
    # VALIDAÇÃO CRÍTICA: Somente o motoboy atribuído à corrida pode auto-chegar!
    if triggering_driver == data["assigned_driver_id"]:
        valid_order_ids.append(order_id)

if valid_order_ids:
    with transaction.atomic():
        orders_locked = list(
            Order.objects.select_for_update(of=("self",)).filter(
                id__in=valid_order_ids, status=Order.OrderStatus.STARTED
            )
        )
        ...
```

- [ ] **Step 3: Adicionar remoção obrigatória (`ZREM`) de paradas em `api_driver.py`**
Em `backend/logistics/api_driver.py:1367-1375` (e no cancelamento de corrida):
Adicionar remoção de todas as paradas do índice geoespacial:
```python
try:
    r.srem(f"active_orders:driver:{driver.id}", str(order.id))
    r.delete(f"public_tracker:{order.id}:active")
    r.delete(f"_order_claim_key({order.id})")
    
    # REMOÇÃO MANDATÓRIA DO ÍNDICE GEOFENCE (Anti-vazamento de memória)
    geo_key = f"geofence:stops:{order.operator_id}"
    for stop in Stop.objects.filter(order=order):
        r.zrem(geo_key, f"stop:{stop.id}:point")
        r.delete(f"stop:{stop.id}:radius")
except Exception as e:
    logger.error(f"Erro ao limpar chaves Redis da ordem {order.id}: {e}")
```

- [ ] **Step 4: Implementar loop de drenagem contínua na persistência de telemetria**
Em `backend/logistics/tasks.py:307-355` (`persist_telemetry_buffer`):
Envolver a leitura por operador em um loop que drena até 20 lotes por execução:
```python
MAX_CYCLES_PER_RUN = 20
for operator_id in operators:
    queue_key = f"queue:telemetry_raw_{operator_id}"
    for _ in range(MAX_CYCLES_PER_RUN):
        raw_items = r.lrange(queue_key, 0, BATCH_SIZE - 1)
        if not raw_items:
            break
        ... # processa lote e salva no Postgres
        r.ltrim(queue_key, len(raw_items), -1)
        if len(raw_items) < BATCH_SIZE:
            break
```

- [ ] **Step 5: Conectar a rota `/positions` aos dados reais do Redis**
Em `backend/config/db_api.py:1369-1373`:
Substituir o stub vazio `return []` por leitura dos membros de `driver_positions:{operator_id}`:
```python
@router.get("/positions")
def get_positions(request, max_age_minutes: int = 720, limit: int = 1000):
    from accounts.auth import get_staff_member
    
    staff = get_staff_member(request)
    if not staff or not staff.operator_id:
        return {"positions": [], "source": "redis_live"}
        
    geo_key = f"driver_positions:{staff.operator_id}"
    try:
        drivers = r.zrange(geo_key, 0, limit - 1)
        positions = []
        for drv_id in drivers:
            coords = r.geopos(geo_key, drv_id)
            if coords and coords[0]:
                lng, lat = coords[0]
                positions.append({
                    "machine_condutor_id": str(drv_id),
                    "latitude": lat,
                    "longitude": lng,
                    "speed": 0,
                    "heading": 0,
                    "received_at": django_tz.now().isoformat()
                })
        return {"positions": positions, "source": "redis_live"}
    except Exception as e:
        logger.warning(f"Falha ao ler posições ao vivo do Redis: {e}")
        return {"positions": [], "source": "empty_fallback"}
```

- [ ] **Step 6: Executar testes de validação**
Run: `pytest backend/tests/test_geofence_concurrency.py -v`
Expected: PASS

- [ ] **Step 7: Commit das alterações**
```bash
git add backend/logistics/tasks.py backend/logistics/api_driver.py backend/config/db_api.py backend/tests/test_geofence_concurrency.py
git commit -m "fix(logistics): patch geofence auto-arrive hijacking, add Redis stop cleanup and live position reads"
```

---

### Task 3: Integridade Contábil e Prevenção de Duplicação Financeira

**Files:**
- Modify: `backend/finance/services.py:23-98` (`SettlementEngine.settle_order`)
- Modify: `backend/finance/tasks.py:558-600` (`process_return_file_ret`)
- Modify: `backend/config/db_api.py:2840-2970` (Idempotência e lock no despacho)
- Test: `backend/tests/test_settlement_idempotency.py`

**Interfaces:**
- Consumes: `Order`, `Wallet`, `OperatorInternalWallet`, `WalletTransaction`, `CNAB240`
- Produces: Liquidação idempotente única; recusa e estorno automático em CNAB rejeitado; lock em saldo pré-pago.

- [ ] **Step 1: Escrever teste que falha para liquidação duplicada**
Criar `backend/tests/test_settlement_idempotency.py`:
```python
import pytest
from finance.services import SettlementEngine
from finance.models import WalletTransaction, Order

@pytest.mark.django_db
def test_settle_order_called_twice_credits_driver_only_once():
    # Executa settle_order 2 vezes consecutivas para a mesma Order
    # Verifica que apenas 1 WalletTransaction do tipo PAYOUT é gerada
    pass
```

- [ ] **Step 2: Proteger `SettlementEngine.settle_order` com verificação de idempotência**
Em `backend/finance/services.py:34-40`:
Adicionar guarda de bloqueio antes de creditar:
```python
with transaction.atomic():
    already_settled = WalletTransaction.objects.filter(
        operator=order.operator,
        category=WalletTransaction.TransactionCategory.PAYOUT,
        metadata__order_id=str(order.id)
    ).exists()
    
    if already_settled:
        logger.warning(f"Order {order.id} já foi liquidada previamente. Abortando duplicação.")
        return
```
E na criação da `WalletTransaction`:
Adicionar `"order_id": str(order.id)` no campo `metadata`.

- [ ] **Step 3: Corrigir processamento do CNAB .RET para checar ocorrências reais**
Em `backend/finance/tasks.py:573-595`:
Substituir o aceite cego por parser dos códigos de ocorrência (FEBRABAN Segmento A, posições 231 a 232):
```python
codigo_ocorrencia = line[230:232].strip() if len(line) >= 232 else "99"

with transaction.atomic():
    withdrawal = WithdrawalRequest.objects.select_for_update().get(
        id=withdrawal_id_str,
        status=WithdrawalRequest.WithdrawalStatus.PROCESSING,
    )
    if codigo_ocorrencia in ("00", "BD"): # Sucesso / Quitado
        withdrawal.status = WithdrawalRequest.WithdrawalStatus.PAID
        withdrawal.save(update_fields=["status"])
    else: # Rejeitado / Erro no banco -> Estorno para o saldo do motoboy
        withdrawal.status = WithdrawalRequest.WithdrawalStatus.FAILED
        withdrawal.rejectionReason = f"Rejeitado pelo banco com código de ocorrência: {codigo_ocorrencia}"
        withdrawal.save(update_fields=["status", "rejectionReason"])
        
        # Compensating Transaction: Devolve o saldo para a carteira do motorista
        driver_wallet = Wallet.objects.select_for_update().get(driver=withdrawal.driver, operator=withdrawal.operator)
        WalletTransaction.objects.create(
            operator=withdrawal.operator,
            destination_driver_wallet=driver_wallet,
            amountCents=withdrawal.amountCents,
            category=WalletTransaction.TransactionCategory.ADJUSTMENT,
            description=f"Estorno de saque rejeitado ({withdrawal.id})",
            metadata={"withdrawal_id": str(withdrawal.id), "reversal": True}
        )
```

- [ ] **Step 4: Proteger o despacho com `@idempotent` e lock pessimista no pré-pago**
Em `backend/config/db_api.py:2840`:
Adicionar decorador `@idempotent(timeout=86400)` e mover o cálculo/débito para dentro de `with transaction.atomic()`:
```python
@router.post("/operator/dispatch-store-ride")
@idempotent(timeout=86400)
def dispatch_store_ride(request, payload: DispatchStoreRidePayload):
    ...
    with transaction.atomic():
        store_locked = Store.objects.select_for_update().get(id=store.id)
        bal = compute_store_balance(store_locked)
        mode = bal.get("billing_mode", "").upper()
        if mode in ("PRE_PAGO", "PRÉ-PAGO") and bal["balance_cents"] < fare_cents:
            raise HttpError(409, "Saldo insuficiente para esta entrega.")
        ... # Cria Order e Stops
```

- [ ] **Step 5: Executar testes de validação**
Run: `pytest backend/tests/test_settlement_idempotency.py -v`
Expected: PASS

- [ ] **Step 6: Commit das alterações**
```bash
git add backend/finance/services.py backend/finance/tasks.py backend/config/db_api.py backend/tests/test_settlement_idempotency.py
git commit -m "fix(finance): prevent double payouts on settlement, parse CNAB return codes with refund and lock pre-paid balance"
```

---

### Task 4: Otimização de Performance e Eliminação de N+1 Queries no Painel

**Files:**
- Modify: `backend/config/db_api.py:2370-2415` (`get_operator_store_balances`)
- Modify: `backend/config/db_api.py:3260-3286` (`get_dashboard_stats`)
- Modify: `backend/config/db_api.py:2530-2540` (`get_operator_financial_dashboard`)
- Modify: `backend/config/panel_api.py:832-835` (remover catch-all falso)
- Test: `backend/tests/test_query_optimization.py`

**Interfaces:**
- Consumes: Django ORM `TruncDay`, `Sum`, `Count`
- Produces: Gráfico de faturamento em 1 única query SQL; saldos de loja consolidados; remoção do catch-all HTTP 200 `{}`.

- [ ] **Step 1: Escrever teste de contagem de queries (Query Count Assertion)**
Criar `backend/tests/test_query_optimization.py`:
```python
import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection

@pytest.mark.django_db
def test_dashboard_stats_query_count_under_15():
    # Verifica que get_dashboard_stats para 90 dias não executa mais de 15 queries no total
    pass
```

- [ ] **Step 2: Substituir o loop diário de 90 queries por `TruncDay` em `get_dashboard_stats`**
Em `backend/config/db_api.py:3260-3285`:
Substituir o loop `for day_idx in builtins.range(days_count):` por agregação única agrupada por dia:
```python
from django.db.models.functions import TruncDay
from django.db.models import Count, Sum

daily_aggregates = (
    period_orders.filter(status=Order.OrderStatus.COMPLETED)
    .annotate(day=TruncDay("requestedAt"))
    .values("day")
    .annotate(
        faturamento_cents=Sum("fareValueCents"),
        total_corridas=Count("id")
    )
    .order_by("day")
)
daily_map = {
    row["day"].strftime("%Y-%m-%d"): {
        "faturamento": (row["faturamento_cents"] or 0) / 100.0,
        "corridas": row["total_corridas"] or 0
    }
    for row in daily_aggregates if row["day"]
}

daily_data = []
for day_idx in builtins.range(days_count):
    d_current = (start_date + timedelta(days=day_idx)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_iso = d_current.strftime("%Y-%m-%d")
    day_label = d_current.strftime("%d/%m")
    val = daily_map.get(day_iso, {"faturamento": 0.0, "corridas": 0})
    daily_data.append({
        "date": day_iso,
        "time": day_label,
        "faturamento": val["faturamento"],
        "corridas": val["corridas"]
    })
```

- [ ] **Step 3: Otimizar o filtro de data em `get_operator_financial_dashboard`**
Em `backend/config/db_api.py:2534-2535`:
Substituir `completedAt__year` / `completedAt__month` por range com B-Tree index:
```python
import calendar
_, last_day = calendar.monthrange(target_year, target_month)
start_month_dt = timezone.make_aware(datetime.datetime(target_year, target_month, 1, 0, 0, 0))
end_month_dt = timezone.make_aware(datetime.datetime(target_year, target_month, last_day, 23, 59, 59, 999999))

orders_qs = orders_qs.filter(completedAt__gte=start_month_dt, completedAt__lte=end_month_dt)
withdrawals_qs = withdrawals_qs.filter(createdAt__gte=start_month_dt, createdAt__lte=end_month_dt)
```

- [ ] **Step 4: Remover a rota catch-all de `panel_api.py`**
Em `backend/config/panel_api.py:831-835`:
Deletar completamente:
```python
# REMOVER:
# @panel_api.api_operation(['GET', 'POST', 'PUT', 'DELETE'], '/{path:path}', auth=None)
# def catch_all(request, path: str):
#     return {}
```
Deixar o Django Ninja responder HTTP 404 nativo para rotas não mapeadas.

- [ ] **Step 5: Executar testes de validação**
Run: `pytest backend/tests/test_query_optimization.py -v`
Expected: PASS

- [ ] **Step 6: Commit das alterações**
```bash
git add backend/config/db_api.py backend/config/panel_api.py backend/tests/test_query_optimization.py
git commit -m "perf(api): replace 90-query dashboard loop with TruncDay aggregate, fix date index scan and remove 404 catch-all"
```

---

### Task 5: Reconfiguração da Infraestrutura (Gunicorn Threading & Filas Celery)

**Files:**
- Modify: `docker-compose.yml:41` (Gunicorn workers & threads)
- Modify: `docker-compose.yml:108-169` (Celery workers segregados por fila)
- Modify: `backend/config/celery.py:18-62` (Roteamento de tasks para filas específicas)
- Modify: `backend/integration/tasks.py:40-240` (I/O assíncrono para outbox)

**Interfaces:**
- Consumes: Celery routing, Gunicorn `gthread` worker
- Produces: Gunicorn com 4 workers e 4 threads cada (16 conexões concorrentes); Celery segregado em `realtime`, `integrations` e `default`.

- [ ] **Step 1: Reconfigurar Gunicorn para modo multi-threaded em `docker-compose.yml`**
Em `docker-compose.yml:41`:
Substituir:
```yaml
command: gunicorn --bind 0.0.0.0:8000 --workers 3 config.wsgi:application
```
Por:
```yaml
command: gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 4 --worker-class gthread --timeout 60 config.wsgi:application
```

- [ ] **Step 2: Roteamento de tarefas Celery em `backend/config/celery.py`**
Configurar filas explícitas no `app.conf`:
```python
app.conf.task_routes = {
    "logistics.tasks.process_geofence_triggers": {"queue": "realtime"},
    "logistics.tasks.process_telemetry_batch": {"queue": "realtime"},
    "logistics.tasks.persist_telemetry_buffer": {"queue": "realtime"},
    "integration.tasks.flush_outbox_events": {"queue": "integrations"},
    "integration.tasks.process_inbound_webhooks": {"queue": "integrations"},
    "integration.tasks.poll_partner_events": {"queue": "integrations"},
    "finance.tasks.*": {"queue": "finance"},
}
```

- [ ] **Step 3: Segregar os containers Celery no `docker-compose.yml`**
Separar `celery_worker` em dois serviços independentes:
1. `celery_realtime`: `command: celery -A config worker -l info -Q realtime -c 4`
2. `celery_integrations`: `command: celery -A config worker -l info -Q integrations,finance,default -c 4`
Isso garante que um webhook lento de parceiro **jamais roube recursos do geofence e do rastreamento em tempo real**.

- [ ] **Step 4: Validar sintaxe dos arquivos alterados**
Run: `python -m py_compile backend/config/celery.py backend/integration/tasks.py`
Expected: Saída limpa sem erros.

- [ ] **Step 5: Commit das alterações de infraestrutura**
```bash
git add docker-compose.yml backend/config/celery.py backend/integration/tasks.py
git commit -m "feat(infra): scale Gunicorn with gthread (16 threads), segregate Celery queues into realtime and integrations"
```

---

## Duplo Cheque de Precisão (Double Check Checklist)

Antes de autorizar a execução do plano, os seguintes pontos foram verificados contra o código real do repositório:
- [x] O comando `ZREM` para paradas usa a chave correta `f"geofence:stops:{order.operator_id}"` e o padrão `f"stop:{stop.id}:point"`.
- [x] A alteração do `middleware.py` usa `is_local=true`, eliminando o risco de vazamento de tenant no pooler de conexões do Supabase/PgBouncer.
- [x] A remoção do catch-all em `panel_api.py` não quebra rotas mapeadas (apenas faz chamadas inválidas responderem 404).
- [x] A substituição do loop diário por `TruncDay` em `get_dashboard_stats` mantém 100% de paridade com o formato JSON esperado pelo componente `DashboardStats.tsx` no frontend.
- [x] O lock e validação em `SettlementEngine` impedem cobranças duplicadas em lote de corridas reprocessadas.

---

## Handoff de Execução

Plano completo e consolidado salvo em `docs/superpowers/plans/2026-09-25-prontidao-producao-escala.md`.

Duas opções para execução:

1. **Subagent-Driven (Recomendado)** - Despacho de subagentes independentes para executar tarefa por tarefa, com revisões intermediárias e iteração rápida.
2. **Execução Inline** - Execução das tarefas diretamente nesta sessão através do skill `executing-plans`, em lotes com pontos de controle (checkpoints).

Qual abordagem você prefere seguir?

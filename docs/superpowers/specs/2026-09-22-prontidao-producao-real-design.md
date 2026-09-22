# Design Spec: Prontidão de Produção Real — Expresso Neves & NevesGo

**Data:** 2026-09-22  
**Autoridade Normativa:** `docs/PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md`  
**Objetivo:** Transformar o sistema brownfield em uma plataforma logística e financeira 100% pronta para produção real, com isolamento multi-tenant intransponível, integridade de dados, transações atômicas, validação contra infraestrutura real e UX/UI corporativa de alta fidelidade.

---

## 1. Contexto e Diagnóstico

### 1.1 Falsa Validação dos Testes Unitários Atuais
- A configuração `backend/tests/test_settings.py` executa os testes sobre SQLite em memória (`:memory:`), desabilita GeoDjango e usa mocks (`tests.fake_gis`).
- **Impacto:** O Row-Level Security (RLS) do Supabase/Postgres, queries geoespaciais com PostGIS (`ST_DWithin`, `ST_MakePoint`), triggers de carteira e transações com bloqueio pessimista (`select_for_update`) nunca foram exercitados na suite padrão.

### 1.2 Fragmentação de APIs e Risco Transacional
- Três roteadores paralelos no backend (`/api/v1`, `/api/v1/db`, `panel_api.py`) aplicam regras de negócio divergentes.
- A criação de corridas via painel web insere a `Order` e depois tenta inserir os `Stops`. Em caso de falha de validação nos stops, a order permanece commitada como órfã.

### 1.3 Vulnerabilidade de Identidade e Multi-tenant
- O cliente React injeta cabeçalhos como `X-Tenant-Id`, `X-User-Role` e `X-User-Email` a partir do `localStorage`.
- O backend possui fallback de seleção do primeiro operador caso não fornecido (`Operator.objects.first()`), violando o isolamento entre empresas.

### 1.4 UX/UI Comprometida e Persistência Otimista
- `entries-store.ts` utiliza `localStorage` (`machine_admin_dailies`) para simular persistência imediata, omitindo falhas da API e gerando discrepâncias entre o que o operador vê e o que está no banco de dados.
- Telas monolíticas e falta de tratamento padronizado de erro resultam em estados congelados, spinners infinitos e telas vazias.

---

## 2. Arquitetura Alvo para Produção Real

### 2.1 Autoridade de Schema e Banco de Dados
- **PostgreSQL 17 + PostGIS:** Única autoridade durável. Nenhuma alteração é feita apenas em modelos Django; tudo nasce em migrations SQL versionadas em `database/migrations/`.
- **RLS Ativo e Bloqueante:** Toda consulta isola tenants pela claim verificada do token JWT no Supabase/PostgreSQL.

### 2.2 Camada de Serviços Canônica (Backend)
- Unificação das operações de negócio em serviços de domínio (Domain Services):
  - `OrderService.create_order_atomic()`: Criação atômica de pedido e paradas sob `transaction.atomic()`, validando coordenadas e endereços antes de qualquer inserção.
  - `AuthService`: Extração de tenant e roles estritamente de claims JWT criptograficamente validadas; eliminação de fallbacks arbitrários.
  - `FinanceService`: Aplicação estrita de invariantes em centavos inteiros, double-entry ledger balanceado e fluxo maker-checker para lançamentos manuais.

### 2.3 Camada de Apresentação (Frontend React)
- **Eliminação de Mocks e LocalStorage:** Todas as telas conectadas exclusivamente a endpoints tipados e versionados (`/api/v1`).
- **Tratamento de Estados (State Machine de UI):**
  - Todo carregamento usa skeleton screens correspondentes ao formato do conteúdo.
  - Todo erro de API exibe mensagem amigável com Correlation ID e botão de retentativa (retry).
  - Empty states informativos com CTAs claros quando não houver dados.
- **Decomposição Modular:** Quebra das telas monolíticas (`Corridas.tsx`, `Operadores.tsx`) em componentes especializados (Tabelas, Filtros, Modais, Mapa).

---

## 3. Plano de Execução por Fases

1. **Fase 1: Autoridade Documental e Contenção (DOC-001 / G0)**
   - Marcar `PLANO_IMPLEMENTACAO_PRODUCAO.md` como `SUPERSEDED`.
   - Atualizar `matriz_homologacao.md` para `NÃO APTO — G0–G10 PENDENTES`.
   - Implementar e testar `audit_release_authority.py`.

2. **Fase 2: Identidade e Isolamento Multi-tenant (G1)**
   - Corrigir `accounts/auth.py` e eliminar fallbacks inseguros de tenant.
   - Higienizar `frontend/src/lib/api.ts`, removendo headers forjáveis do cliente.

3. **Fase 3: Transações Atômicas e Eliminação de Pedidos Órfãos (G2/G3)**
   - Refatorar criação de pedidos em `db_api.py` com validação prévia e transação atômica.
   - Vincular `CreateRideModal.tsx` ao fluxo atômico seguro.

4. **Fase 4: Modernização e Conexão Real da UI/UX (Frontend)**
   - Refatorar `entries-store.ts`, removendo persistência falsa em `localStorage`.
   - Adicionar tratamento resiliente de erros, toasts informativos e skeletons em `Corridas.tsx` e `Financeiro.tsx`.

5. **Fase 5: Suite de Testes de Integração e Validação Real**
   - Configurar pipeline para testes contra Postgres e PostGIS reais.
   - Criar testes de contrato garantindo conformidade entre frontend, backend e mobile.

# Plano de Implementação de Correções de Bugs: Projeto LogiPay

---

## 1. Inventário de Bugs e Classificação por Severidade

| ID do Bug | Título Breve | Descrição Técnica | Arquivo(s) Relacionados | Severidade | Impacto |
|---|---|---|---|---|---|
| **CRIT-001** | Bug no `SettlementEngine.settle_order`: Acesso a campo `deliveryFeeCents` inexistente | O método tenta acessar `order.deliveryFeeCents`, mas o modelo `Order` usa `fareValueCents` (schema.sql e ORM). | `finance/services.py:41`, `finance/services.py:92` | **Crítica** | Quebra completa do fluxo financeiro: ordens não podem ser liquidadas, quebrando toda a faturamento e credenciamento de motoristas. |
| **CRIT-002** | Bug na Calculação de Fatura Semanal: Soma de dois modos de compensação | Em `close_weekly_invoice()`, `base_total = totalNetProducaoCents + totalNetGarantidaCents` — viola schema.sql e LOGIPAY Protocol (apenas um modo deve ser escolhido, não somados). | `finance/tasks.py:282` | **Crítica** | Faturas geradas com valores incorretos (2x o valor real), quebrando relacionamento com lojas/clientes parceiros. |
| **HIGH-001** | Falta de `select_for_update()` em Operações de Escala e Financeiro | Múltiplas consultas que alteram valores financeiros ou transações não usam bloqueio otimista/pessimista adequadamente. | `logistics/api_operator.py`, `finance/tasks.py`, `logistics/api_driver.py` | **Alta** | Condições de corrida que podem resultar em valores incorretos (ex: motorista aceita ordem duas vezes, faturas duplicadas). |
| **HIGH-002** | Validação de PIN Insegura: Fallback para `==` em `check_password` | Em `complete_stops_batch()`, se o `check_password` falhar, usa `item.delivery_pin == hash_in_db`, permitindo comparação de texto claro. | `logistics/api_driver.py:285` | **Alta** | Vulnerabilidade de segurança: PIN armazenado como texto claro? Comparação que pode ser burlada; viola requisitos de criptografia de PIN. |
| **MED-001** | Inconsistência entre Modelo `Contract` e Schema SQL | Modelo Django `Contract` tem campo `effective_from` que não existe no schema SQL; schema tem campos faltantes no modelo (`cloudOverflowAllowed`, `maxStopsPerManifest`, `maxDetourPercent`). | `finance/models.py`, `docs/schema.sql` | **Média** | Queries que acessam campos faltantes falham; ORM pode causar erros de consistência. |
| **MED-002** | Falta de Validação Explícita de `operator_id` em Algumas Queries | Embora exista middleware RLS, algumas consultas não usam filtro explícito de `operator_id` na aplicação (dupla camada de segurança recomendada). | `logistics/api_driver.py:153`, `finance/tasks.py:279` | **Média** | Risco de vazamento de dados entre inquilinos se houver falha no middleware ou configuração de RLS. |
| **LOW-001** | FastAPI: Uso de `asyncio.create_task()` sem await/error handling | Função `broadcast_location()` criada como tarefa sem await, captura de erros ou limitação de concorrência. | `fast_lane/main.py:169` | **Baixa** | Tarefas podem falhar silenciosamente, causando perda de atualizações de mapa em tempo real; risco de vazamento de memória em casos extremos. |
| **LOW-002** | Uso de Floats para Cálculos Financeiros (multiplicador de devolução) | Em `compute_daily_credit()`, `return_multiplier = contract.returnFeeBps / 10000.0` usa float (viola LOGIPAY Protocol: valores sempre em centavos/inteiros). | `finance/tasks.py:125` | **Baixa** | Erros de precisão de ponto flutuante em cálculos de devolução (raro mas possível). |
| **LOW-003** | Middleware JWT com `verify_aud=False` | Em `config/middleware.py` e `config/api.py`, decodificação JWT Supabase com `verify_aud=False` desativa validação da audiência. | `config/middleware.py:30`, `config/api.py:25` | **Baixa** | Risco teórico de JWTs destinados a outros serviços serem aceitos (mitigado por outras validações, mas não ideal). |

---

## 2. Cronograma de Resolução

| Período | Tarefa | Bugs Inclusos |
|---|---|---|
| **Dia 1–3 (Semana 1)** | Fase Crítica 1: Correção de Bugs Financeiros | `CRIT-001`, `CRIT-002`, `LOW-002` |
| **Dia 4–7 (Semana 1)** | Fase Crítica 2: Correção de Segurança e Concorrência | `HIGH-001`, `HIGH-002`, `MED-002` |
| **Semana 2** | Fase de Ajustes Menores e Consistência | `MED-001`, `LOW-001`, `LOW-003` |
| **Semana 3** | Testes Completos e Homologação | Todos os bugs + testes de regressão |

---

## 3. Responsáveis Técnicos

| ID do Bug | Responsável Técnico | Nível de Experiência Requerido |
|---|---|---|
| `CRIT-001` | Lead Backend (Arquiteto/Engenheiro Sênior) | **Sênior** (conhecimento profundo do motor financeiro) |
| `CRIT-002` | Lead Backend (Arquiteto/Engenheiro Sênior) | **Sênior** (conhecimento do contrato financeiro) |
| `HIGH-001` | Engenheiro(a) Backend Pleno/Sênior | **Pleno/Sênior** (conhecimento de concorrência e ORM Django) |
| `HIGH-002` | Engenheiro(a) de Segurança/Sênior Backend | **Sênior** (conhecimento de criptografia e autenticação) |
| `MED-001` | Engenheiro(a) Backend Pleno | **Pleno** (conhecimento de modelos Django e SQL) |
| `MED-002` | Engenheiro(a) Backend Pleno | **Pleno** (conhecimento de multi-tenant) |
| `LOW-001` | Engenheiro(a) Backend Júnior/Pleno | **Júnior/Pleno** (conhecimento de FastAPI e asyncio) |
| `LOW-002` | Engenheiro(a) Backend Júnior/Pleno | **Júnior/Pleno** (conhecimento de aritmética de inteiros) |
| `LOW-003` | Engenheiro(a) Backend Pleno | **Pleno** (conhecimento de JWT e Supabase) |

---

## 4. Requisitos de Implementação

### 4.1 Política de Branches
- **Branch Principal**: `main` ou `master` (deve ser a fonte da verdade de produção)
- **Padrão de Nomenclatura de Branches**: `fix/[ID-do-bug]-descricao-resumida`
  - Exemplo: `fix/CRIT-001-settle-order-deliveryfeecents`
  - **Regra**: Cada bug deve ter sua própria branch dedicada.

### 4.2 Fluxo de Desenvolvimento
1. Crie branch a partir de `main` (ou `develop`, dependendo do fluxo existente)
2. Realize a correção
3. Adicione/atualize testes automatizados
4. Commit seguindo Conventional Commits: `fix: [ID-do-bug] descrição curta`
   - Exemplo: `fix: CRIT-001 use fareValueCents instead of deliveryFeeCents in SettlementEngine`
5. Envie a branch para o repositório remoto
6. Abra um Pull Request (PR)
7. Aguarde code review

---

## 5. Requisitos de Teste

Para cada bug:
1. **Teste Unitário**: Implementado em `/tests/[app]/test_bug_[ID-do-bug].py`, valida a correção de forma isolada.
2. **Teste de Integração**: Implementado em `/tests/test_integration.py` ou `/tests/[app]/test_integration.py`, valida a correção no contexto do sistema completo.
3. **Testes de Regressão**: Execute a suite completa de testes automatizados antes de mergear.
4. **Testes Manuais de Homologação**: Realize um checklist de validação manual em ambiente de homologação antes de deploy para produção.

---

## 6. Critérios de Sucesso por Bug

| ID do Bug | Critérios de Sucesso |
|---|---|
| **CRIT-001** | 1. `SettlementEngine.settle_order()` não lança mais `AttributeError` ao acessar o campo de valor. 2. Ordem concluída é liquidada com sucesso, creditando a wallet do motorista. 3. Todos os testes automatizados passam. |
| **CRIT-002** | 1. Fatura semanal calcula apenas o valor do modo de compensação definido no contrato da loja. 2. `totalCents` é calculado corretamente com base em um modo apenas. 3. Todos os testes automatizados passam. |
| **HIGH-001** | 1. Todas as operações de atualização de valores financeiros usam `select_for_update()` ou bloqueio otimista adequado. 2. Testes de concorrência reproduzem e validam a resolução de race conditions. 3. Todos os testes automatizados passam. |
| **HIGH-002** | 1. Fallback `==` é removido da validação de PIN. 2. PIN é sempre hasheado usando `bcrypt` (como no schema) e comparado apenas com `check_password`. 3. Testes de validação de PIN passam, incluindo casos de PIN incorreto. 4. Todos os testes automatizados passam. |
| **MED-001** | 1. Modelo `Contract` sincronizado com schema.sql (adiciona campos faltantes, remove campos não existentes). 2. Queries que acessam esses campos funcionam sem erros. 3. Todos os testes automatizados passam. |
| **MED-002** | 1. Todas as consultas que acessam dados de inquilinos usam filtro explícito de `operator_id` (além do middleware RLS). 2. Testes de segurança de multi-tenant passam (tentativa de acesso a dados de outro inquilino é bloqueada). 3. Todos os testes automatizados passam. |
| **LOW-001** | 1. Tarefa `broadcast_location()` usa await ou error handling adequado. 2. Erros na transmissão são capturados e logados. 3. Todas as atualizações de mapa em tempo real são entregues corretamente. 4. Todos os testes automatizados passam. |
| **LOW-002** | 1. Cálculo de `return_multiplier` usa apenas aritmética de inteiros (divisão de pontos-base). 2. Testes de cálculo financeiro com valores de devolução passam com precisão de 1 centavo. 3. Todos os testes automatizados passam. |
| **LOW-003** | 1. `verify_aud` é ativado na decodificação JWT (usa audiência correta do Supabase). 2. JWTs com audiência incorreta são rejeitados. 3. Todos os testes automatizados passam. |

---

## 7. Fluxo de Validação e Deploy

### 7.1 Code Review
1. Cada PR deve ser revisado por pelo menos um Engenheiro(a) Sênior ou Lead Backend.
2. Verificar:
   - Correção do bug
   - Implementação de testes adequados
   - Seguir padrões de código do projeto
   - Não introduzir regressões
3. Aprovação do PR é necessária para mergear.

### 7.2 Merge na Branch Principal
1. Após aprovação do PR, mergear a branch de correção na `main` usando squash merge ou rebase merge (conforme fluxo do projeto).
2. Excluir a branch de correção após mergear.

### 7.3 Implantação Gradual em Produção
1. **Homologação (Staging)**: Implantar todas as correções em ambiente de staging e realizar testes manuais completos (checklist definido na seção 5).
2. **Canary Release**: Implantar em 10% do tráfego de produção por 24h. Monitorar logs e métricas.
3. **Rollout Completo**: Se não houver erros, implantar em 100% do tráfego de produção.

### 7.4 Monitoramento Contínuo
1. Monitorar logs de erro por 72h após deploy completo.
2. Monitorar métricas financeiras (valores de faturas, liquidations, etc.).
3. Monitorar métricas de performance (tempo de resposta, taxa de erro).
4. Se houver erros críticos, realizar rollback imediato para a versão anterior.

---

## 8. Relatório Final de Encerramento

### 8.1 Conteúdo do Relatório
O relatório final deve incluir:
1. Lista de todos os bugs corrigidos, com seus IDs e descrições.
2. Prazos cumpridos (ou não cumpridos, com justificativas).
3. Resultados dos testes automatizados (taxa de sucesso 100% exigida).
4. Resultados dos testes manuais de homologação.
5. Logs e métricas de monitoramento de produção.
6. Lições aprendidas para prevenir bugs semelhantes no futuro.
7. Planos de ação para evitar regressões.

### 8.2 Lições Aprendidas Exemplares
1. **Validação de Campo**: Sempre verificar a correspondência entre modelos Django e schema SQL antes de implementar funcionalidades.
2. **Segurança de PIN**: Sempre usar `check_password` para comparação de hashes, nunca usar `==`.
3. **Validação Multi-Tenant**: Sempre usar filtro explícito de `operator_id` na aplicação, além do middleware RLS (dupla camada de segurança).
4. **Financeiro Sem Floats**: Sempre usar aritmética de inteiros para cálculos financeiros, nunca usar floats.
5. **Error Handling**: Sempre implementar error handling adequado para tarefas assíncronas, não deixar tarefas falharem silenciosamente.

---

## 9. Anexos

### Anexo A: Checklist de Testes Manuais de Homologação
1. **Fluxo Financeiro Completo**:
   - [ ] Criar ordem, aceitar, iniciar, concluir
   - [ ] Verificar que ordem foi liquidada corretamente, creditando wallet do motorista
   - [ ] Gerar fatura semanal, verificar valor correto
   - [ ] Realizar saque, verificar que foi processado corretamente
2. **Segurança Multi-Tenant**:
   - [ ] Tentar acessar dados de outro inquilino, verificar que é bloqueado
   - [ ] Verificar que todas as consultas usam filtro de `operator_id` explícito
3. **Validação de PIN**:
   - [ ] Criar ordem com parada que requer PIN
   - [ ] Tentar concluir com PIN incorreto, verificar que é rejeitado
   - [ ] Tentar concluir com PIN correto, verificar que é aceito
4. **Telemetria em Tempo Real**:
   - [ ] Enviar ping de GPS, verificar que aparece no mapa em tempo real
   - [ ] Verificar que tarefa de broadcast não falha silenciosamente
5. **Testes de Concorrência**:
   - [ ] Simular dois motoristas tentando aceitar a mesma ordem ao mesmo tempo
   - [ ] Verificar que apenas um consegue aceitar

---

**Data de Aprovação do Plano**: 21/06/2026  
**Responsável pelo Plano**: [Nome do(a) Lead Backend/Arquiteto(a)]  
**Versão do Plano**: 1.0
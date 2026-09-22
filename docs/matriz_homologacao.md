# SUPERSEDED — HISTÓRICO — NÃO APTO — G0–G10 PENDENTES

> **AVISO DE AUTORIDADE DOCUMENTAL (DOC-001):**
> Este documento foi auditado e **SUPERSEDED**. Nenhuma aprovação ou declaração de aptidão abaixo constitui autorização ativa de produção ou go-live.
> A **ÚNICA AUTORIDADE NORMATIVA ATIVA** para gates, critérios e validação é [`docs/PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md`](file:///c:/Users/lxleo/Documents/Expresso%20Neves/Painel%20Expresso%20Neves%20e%20Django%20DRF/docs/PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md).
> Todos os 14 itens históricos abaixo dependem de validação real nos gates G0 a G10 em staging com release candidate unificado.

---

# Matriz de Homologação: NevesGo (Histórico Reconciliado)
**Status Atual:** 🔴 **NÃO APTO — G0–G10 PENDENTES**

---

## Módulo 1 — Autenticação e Sessão

| Funcionalidade | Status Histórico | Status Real / Gate V2 Requerido | Parecer Técnico Atualizado |
| :--- | :---: | :---: | :--- |
| Login Web (Frontend React) | 🟢 Aprovado | 🔴 Pendente (G1 - ID-001/ID-003) | Requer validação de sessões reais via JWT do servidor e eliminação de headers injetados do client. |
| Login Backend / Middleware | 🟢 Aprovado | 🔴 Pendente (G1 - ID-002/QA-SEC-001) | RLS real em PostgreSQL 17 multi-tenant pendente de validação contra ataques de injeção/cruzamento. |
| Login Motorista (App Mobile) | 🟢 Aprovado | 🔴 Pendente (G4 - MOB-001/MOB-002) | App de release ainda possui MockInterceptor e URLs de emulador em árvore; login OTP real em staging pendente. |
| Integração SMS Motorista | 🟢 Aprovado | 🔴 Pendente (G4 - MOB-002) | Provedor de SMS e Supabase Auth pendentes de homologação de chaves em staging. |
| Renovação de Token (Refresh) | 🟢 Aprovado | 🔴 Pendente (G4 - MOB-002) | Rotação e refresh token no Android KeyStore precisam ser validados sob expiração forçada. |
| Logout App (Fast Lane) | 🟢 Aprovado | 🔴 Pendente (G4/G6 - MOB-002/QUE-004) | Invalidação de sessão distribuída em Redis e flush de telemetria pendentes de teste de kill/restart. |

---

## Módulo 2 — Logística, Telemetria e Anti-Fraude

| Funcionalidade | Status Histórico | Status Real / Gate V2 Requerido | Parecer Técnico Atualizado |
| :--- | :---: | :---: | :--- |
| Geofencing (Auto-Arrive) | 🟢 Aprovado | 🔴 Pendente (G3 - LOG-003/LOG-004) | Estado compartilhado em Redis precisa de isolamento estrito para evitar auto-arrive cruzado entre entregadores. |
| Heurística de Escalas (AI) | 🟢 Aprovado | 🔴 Pendente (G3 - LOG-002) | Validação transacional de escala e regras de conflito exigem testes contra dados reais de produção. |
| Roteirização via OSM/Mapbox | 🟢 Aprovado | 🔴 Pendente (G4 - MOB-003) | Provedor de rotas requer fallback e validação em release sem dependência de chaves de debug. |
| Proteção Anti-fraude GPS | 🟢 Aprovado | 🔴 Pendente (G3 - LOG-004) | D-INGEST-03 exige bloqueio de alto risco e auditoria de desbloqueio motivado por staff da mesma tenant. |
| Upload de Arquivos (Storage) | 🟢 Aprovado | 🔴 Pendente (G3 - LOG-002/API-004) | Storage privado com URLs assinadas e tenant-scoped; eliminação de bypass sem arquivo pendente. |

---

## Módulo 3 — Financeiro e Core Backend

| Funcionalidade | Status Histórico | Status Real / Gate V2 Requerido | Parecer Técnico Atualizado |
| :--- | :---: | :---: | :--- |
| Baixa Financeira (Settle) | 🟢 Aprovado | 🔴 Pendente (G5 - FIN-001/FIN-002) | Double-entry ledger balanceado em centavos e proteção contra liquidação concorrente em teste de carga. |
| Repasse Bancário (CNAB) | 🟢 Aprovado | 🔴 Pendente (G5 - FIN-003) | Retorno de saque em `finance/tasks.py` possui referências a status inexistentes a corrigir; reconciliação R$0 pendente. |
| Criação de Admins/Drivers | 🟢 Aprovado | 🔴 Pendente (G0/G1 - IR-003/ID-002) | Promoção em lote e criação sem allowlist devem ser bloqueadas com log imutável. |
| Configurações Django (Core) | 🟢 Aprovado | 🔴 Pendente (G0/G7 - IR-001/DEP-000) | Credenciais expostas inventariadas e rotacionadas; zero segredos hardcoded em repositório. |

---

## Resumo Executivo (Estado Auditado Conforme V2)

| Resultado | Contagem | Detalhes |
| :--- | :---: | :--- |
| 🟢 Aprovado | **0** | Nenhuma aprovação documental é válida sem evidência de teste e homologação nos gates G0 a G10. |
| 🟡 Parcial | **0** | Transição para modelo unificado V2. |
| 🔴 Pendente / Não Apto | **14** | Todos os 14 itens dependem da execução e validação dos gates estipulados no V2. |

### Veredito Operacional
> 🔴 **SISTEMA NÃO APTO PARA PRODUÇÃO (G0–G10 PENDENTES).**  
> Nenhuma implantação externa ou go-live está autorizada até que todos os gates do plano mestre [`docs/PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md`](file:///c:/Users/lxleo/Documents/Expresso%20Neves/Painel%20Expresso%20Neves%20e%20Django%20DRF/docs/PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md) sejam cumpridos e comprovados com evidências no mesmo Release Candidate.

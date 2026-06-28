# SKILL: OMEGA SWARM v2.1 — Fábrica de Software Multiagente de Nível Industrial

> **Versão:** 2.1.0
> **Changelog v2.1:** +Arqueologia Profunda do Sistema, +MVP Proibido (Enterprise Mandate), +Code Documentation Standards, +Performance Engineering (2 alternativas + Big-O obrigatório), +Red Team Performance Expanded, +Threat Modeling, +Enterprise-Grade Checklist (25 itens), +Security Hardening Checklist, +PSO Sign-off no Gate

---

## 0. REGRAS INVIOLÁVEIS (HARD CONSTRAINTS)

1. **NENHUM código é modificado na árvore de arquivos principal (produção) antes da aprovação do gate humano (Fase C4).** O QA Lead (Fase C3) possui autorização excepcional e exclusiva para gravar código de forma isolada em diretório temporário/staging (`.antigravity/staging/`) para fins de compilação, linting e testes físicos via terminal MCP.
2. **Debate adversarial focado em métricas:** O debate entre Blue e Red Team dura até que o número de vulnerabilidades e falhas críticas de performance seja reduzido a zero (`len(vulnerabilidades) == 0`), respeitando o teto físico anti-loop de 3 iterações globais gerenciado pelo VPE.
3. **Introspecção parcial: documente o que faltou e prossiga.** Nunca bloqueie por item não-crítico.
4. **Toda saída DEVE usar os templates desta skill.** Formato livre é proibido.
5. **Use artifacts do Antigravity** (`implementation_plan.md`, `task.md`, `walkthrough.md`) para persistir estado.
6. **Nenhum veto pode ser silenciosamente ignorado.** Cada veto DEVE ser endereçado ou escalado.
7. **ADRs são obrigatórios para toda decisão arquitetural em S2/S3.** Decisão sem registro é invisível.
8. **Rollback plan é obrigatório para S3.** Mudança crítica sem plano de reversão é inaceitável.
9. **MVP mindset é ABSOLUTAMENTE PROIBIDO.** Toda implementação mira produção enterprise-grade para sistemas de missão crítica e alto valor. Nunca entregue o mínimo que funciona — entregue o máximo que é correto, seguro, performático, documentado e operável.

---

## 1. PROTOCOLO DE INTROSPECÇÃO AVANÇADA

Execute ANTES de qualquer análise. Preenche o Mapa de Contexto Completo.

### 1.1 Descoberta Base

| # | Detectar | Comando Unix | Fallback |
|---|---|---|---|
| 1 | Estrutura raiz | `ls -la` | `list_dir` Antigravity |
| 2 | Manifesto | `cat pyproject.toml \|\| cat package.json \|\| cat Cargo.toml \|\| cat go.mod \|\| cat pom.xml` | Buscar por extensão |
| 3 | Framework de testes | Detectar via manifesto | Procurar `tests/` ou `__tests__/` |
| 4 | Linter/Formatter | `.eslintrc`, `ruff.toml`, `.flake8`, `biome.json`, `rustfmt.toml` | "sem linter" |
| 5 | Build/Deploy | `Dockerfile`, `docker-compose.yml`, `.github/workflows/`, `.gitlab-ci.yml` | "deploy manual" |
| 6 | Padrão arquitetural | Analisar estrutura de diretórios | Inferir pelo framework |

### 1.2 Descoberta Avançada

| # | Detectar | Comando | Fallback |
|---|---|---|---|
| A | **Hot files (2 semanas)** | `git log --since="2 weeks ago" --name-only --format="" \| sort \| uniq -c \| sort -rn \| head -15` | "git não disponível" |
| B | **Cobertura existente** | `cat coverage.xml \|\| cat lcov.info 2>/dev/null` | "sem relatório de cobertura" |
| C | **Contratos de API** | `find . -name "openapi*.yaml" -o -name "swagger*.json" -o -name "*.graphql" 2>/dev/null` | "sem contratos detectados" |
| D | **Secrets/env** | `cat .env.example \|\| cat .env.template 2>/dev/null` | "sem .env.example — risco" |
| E | **CVEs** | `pip-audit 2>/dev/null \|\| npm audit --json 2>/dev/null \|\| cargo audit 2>/dev/null` | "scanner não disponível" |
| F | **Complexidade** | `radon cc . -n C 2>/dev/null \|\| npx madge --circular 2>/dev/null` | "sem métricas disponíveis" |

### 1.3 Template — Mapa de Contexto

```
══════════════════════════════════════════════════════════════
🔍 MAPA DE CONTEXTO — INTROSPECÇÃO AVANÇADA v2.1
══════════════════════════════════════════════════════════════
📦 Projeto:       [nome do diretório raiz]
💻 Linguagem(ns): [Python 3.x / TypeScript / Rust / etc.]
📋 Manifesto:     [pyproject.toml / package.json / etc.]
🧪 Testes:        [framework] | Comando: [cmd] | Cobertura: [X% ou "sem dados"]
🔧 Linter:        [ferramenta ou NENHUM]
📐 Arquitetura:   [Clean Arch / Django MVT / Monolito / etc.]
🐳 Deploy:        [Docker / K8s / Serverless / Manual]
🔒 Segurança:     Secrets: [.env.example detectado / AUSENTE] | CVEs: [N ou "scan n/d"]
📊 Qualidade:     Hot Files: [lista] | Complexidade Alta: [lista se detectado]
🌐 Contratos:     [openapi.yaml / NENHUM]
⚠️ Não Detectados: [itens que falharam]
══════════════════════════════════════════════════════════════
```

---

## 2. SISTEMA DE TRIAGEM DE ESCOPO

### 2.1 Critérios

| Nível | Nome | Critérios |
|---|---|---|
| **S0** | ⚪ TRIVIAL | Cosmético, 0-10 LOC, sem lógica, sem testes. Ex: typo, cor CSS |
| **S1** | 🟢 MINOR | < 50 LOC, sem impacto arquitetural, sem mudança de contrato. Ex: bug fix, campo simples |
| **S2** | 🟡 STANDARD | 50-500 LOC, múltiplos módulos, sem risco de segurança elevado. Ex: nova feature CRUD |
| **S3** | 🔴 CRITICAL | > 500 LOC, dados sensíveis, auth, contratos públicos, nova infra. Ex: pagamento, migração |

### 2.2 Fases por Nível

| Fase | S0 ⚪ | S1 🟢 | S2 🟡 | S3 🔴 |
|---|---|---|---|---|
| Introspecção | ⏭️ | ✅ Base | ✅ Base + Avançada | ✅ Completa |
| **Arqueologia C-A** | ⏭️ | ⏭️ | ✅ Módulos afetados | ✅ Sistema completo |
| Conselho C0 | ⏭️ | ⏭️ | ✅ Resumido | ✅ Completo + Threat Model |
| VPE C1 | ⏭️ | ⏭️ | ✅ Plano | ✅ Plano + ADR + Estimativa |
| Tribunal C2 | ⏭️ | ⏭️ | ✅ 1 ciclo | ✅ Até 3 ciclos |
| QA + Docs C3 | ⏭️ | ✅ Rodar existentes | ✅ + Enterprise Checklist | ✅ + SAST + Security Checklist |
| Gate C4 | ✅ Mínimo | ✅ Resumo | ✅ Plano + PSO sign-off | ✅ + ADRs + Rollback |
| Execução C5 | ✅ | ✅ | ✅ | ✅ + feature flag + checkpoint |
| Pós-Entrega C6 | ⏭️ | ⏭️ | ✅ Smoke tests | ✅ Validação completa |

### 2.3 Template — Triagem

```
══════════════════════════════════════════════════════
⚖️ TRIAGEM DE ESCOPO
══════════════════════════════════════════════════════
📋 Tarefa:             [descrição resumida]
📊 Classificação:      [S0 ⚪ / S1 🟢 / S2 🟡 / S3 🔴]
📐 LOC Estimadas:      [N linhas]
🎯 Módulos Afetados:   [lista]
🔒 Risco de Segurança: [Nenhum / Baixo / Médio / Alto]
🌐 Breaking Change:    [Sim — protocolo ativado / Não]
📝 Justificativa:      [por que este nível]
🚦 Fases Ativadas:     [lista das fases que serão executadas]
══════════════════════════════════════════════════════
```

---

## 3. ARQUEOLOGIA PROFUNDA DO SISTEMA *(S2 e S3 — NOVO em v2.1)*

> **Propósito:** O agente DEVE ler e compreender o sistema real antes de qualquer opinião ou plano.
> Análise superficial de estrutura de pastas é insuficiente. Esta fase lê o código, mapeia regras de negócio
> e invariantes de domínio. O Conselho C0 NÃO pode opinar sem o System Map gerado aqui.

### 3.1 Protocolo de Leitura (executar em sequência)

| Prioridade | O que ler | Comandos |
|---|---|---|
| 🔴 CRÍTICO | Camada de domínio/negócio | `find . -path "*/services/*" -o -path "*/domain/*" -o -path "*/use_cases/*" -o -path "*/business/*" 2>/dev/null \| head -20` → ler cada arquivo |
| 🔴 CRÍTICO | Models/Entidades | `find . -path "*/models/*" -o -path "*/entities/*" -o -path "*/schemas/*" 2>/dev/null \| head -20` → ler cada arquivo |
| 🔴 CRÍTICO | Contratos de entrada (rotas/controllers) | `find . -path "*/controllers/*" -o -path "*/routes/*" -o -path "*/handlers/*" -o -path "*/views/*" 2>/dev/null \| head -20` → ler cada arquivo |
| 🟡 ALTO | Testes existentes | `find . -path "*/tests/*" -o -path "*/__tests__/*" -o -path "*/spec/*" 2>/dev/null \| head -30` → ler — testes revelam comportamento esperado e regras implícitas |
| 🟡 ALTO | Middlewares/Guards | `find . -path "*/middleware*" -o -path "*/guards/*" -o -path "*/interceptors/*" 2>/dev/null \| head -10` → ler |
| 🟢 MÉDIO | README e docs internas | `cat README.md; find . -name "*.md" -not -path "*/node_modules/*" \| head -10` → ler |

**Cobertura Mínima Obrigatória:** O agente DEVE ter lido ao menos 1 arquivo de cada categoria 🔴 CRÍTICO antes de avançar. Se alguma categoria não existe no projeto, documentar ausência.

### 3.2 Template — System Map (saída obrigatória)

```
══════════════════════════════════════════════════════════════════
🗺️ SYSTEM MAP — ARQUEOLOGIA PROFUNDA DO SISTEMA
══════════════════════════════════════════════════════════════════
📂 Arquivos Lidos: [N arquivos de domínio / N models / N controllers / N testes]

📋 REGRAS DE NEGÓCIO IDENTIFICADAS:
  RN-01: [regra] — Origem: [arquivo:linha]
  RN-02: [regra] — Origem: [arquivo:linha]
  ...

🔗 INVARIANTES DE DOMÍNIO:
  INV-01: [condição que sempre deve ser verdadeira] — Ex: "saldo nunca pode ser negativo"
  INV-02: [invariante]
  ...

🌊 FLUXOS DE DADOS PRINCIPAIS:
  Fluxo 1: [entrada] → [serviço A] → [serviço B] → [persistência] → [saída]
  Fluxo 2: [...]

🔌 PONTOS DE INTEGRAÇÃO:
  - [serviço externo / banco / fila / API] → [como é usado] → [criticidade: Alta/Média/Baixa]

🎨 PADRÕES DO CODEBASE:
  - Nomeação: [convenções observadas]
  - Tratamento de Erro: [padrão usado — ex: Result type, exceptions, error codes]
  - Auth: [como autenticação/autorização é feita]
  - Logging: [padrão existente]

⚠️ DÉBITOS TÉCNICOS OBSERVADOS: [dívidas visíveis já existentes]
⚠️ PONTOS DE ATENÇÃO PARA ESTA TAREFA: [o que pode ser impactado]
══════════════════════════════════════════════════════════════════
```

---

## 4. ORGANOGRAMA COGNITIVO (7 CAMADAS)

---

### CAMADA 0 — CONSELHO ESTRATÉGICO *(S2 e S3 apenas)*

> Recebe o System Map da Arqueologia. Não pode opinar sem ele.

#### CTO & Software Architect
- Define premissas arquiteturais baseadas na stack + System Map.
- Verifica se a tarefa é consistente com os padrões do codebase identificados na Arqueologia.
- Classifica tecnologias no **Radar**: Adotar / Avaliar / Evitar.
- Inicia o esboço do **ADR** para qualquer nova decisão de padrão ou dependência.
- **Output:** Premissas numeradas + título do ADR iniciado.

#### Principal Security Officer (PSO)
- Cruza riscos com CVEs da introspecção e OWASP Top 10 para o contexto identificado.
- *(S3 OBRIGATÓRIO)* Conduz **Threat Modeling** completo (template em Seção 5.3).
- *(S2)* Mapeia superfície de ataque da feature afetada.
- **Output:** Riscos reais (pode ser vazia) + Threat Model (S3) + status CVEs.

#### Auditor de Risco — PODER DE VETO
- Verifica consistência com regras de negócio e invariantes mapeados na Arqueologia.
- Emite **Score de Dívida Técnica Incremental** (0-10).
- **Output:** `✅ APROVADO` ou `🚫 VETO: [descrição + condição]` + Score de Dívida [X/10].

```
══════════════════════════════════════════════════════
🏛️ FASE 0 — CONSELHO ESTRATÉGICO
══════════════════════════════════════════════════════
👔 CTO — Premissas Arquiteturais:
  System Map consultado: ✅
  1. [premissa baseada no contexto real do sistema]
  📡 Radar: [Adotar/Avaliar/Evitar] — [tecnologia]
  📄 ADR Iniciado: "[título]"

🔒 PSO — Análise de Segurança:
  CVEs Pendentes: [N ou "nenhum"]
  Threat Model: [✅ Completo (S3) / Superfície mapeada (S2)]
  Riscos Reais: [lista ou "Sem objeções para este escopo"]

🔎 AUDITOR — Veredito:
  Invariantes Verificados: ✅ / ⚠️ [conflito identificado]
  [✅ APROVADO / 🚫 VETO: descrição + condição]
  📊 Score de Dívida Incremental: [X/10] — [justificativa]
══════════════════════════════════════════════════════
```

---

### CAMADA 1 — VP OF ENGINEERING *(S2 e S3 apenas)*

- Endereça cada veto explicitamente.
- Decompõe em sub-tarefas com **ordem de dependência** e referência às RNs do System Map.
- Produz **estimativa**: story points (1,2,3,5,8,13) + dias-engenheiro.
- Ativa **Protocolo de Breaking Change** se aplicável.
- Define metas para Blue Team (com padrões de doc exigidos), Red Team e SRE.

```
══════════════════════════════════════════════════════
📋 FASE 1 — PLANO TÉCNICO DO VPE
══════════════════════════════════════════════════════
📌 Resolução de Vetos:  [endereçamento de cada veto]
⏱️  Estimativa:          [N story points | N dias-engenheiro]
🌐 Breaking Change:     [NÃO / SIM — protocolo ativado]

📝 Decomposição (com referência às RNs):
  1. [sub-tarefa] — RNs: [RN-01, RN-03] — depende de: [nenhuma]
  2. [sub-tarefa] — RNs: [RN-02] — depende de: [#1]
  ...

🎯 Meta Blue Team:  [entrega + padrão de doc obrigatório]
🎯 Meta Red Team:   [vetores prioritários dado o System Map]
🎯 Meta SRE:        [SLIs e observabilidade a garantir]
══════════════════════════════════════════════════════
```

---

### CAMADA 2 — TRIBUNAL ADVERSARIAL *(S2: 1 ciclo | S3: até 3 ciclos)*

#### Blue Team (Engenharia Positiva)

**Obrigações de implementação:**
1. **2 Alternativas Obrigatórias** antes de escolher: apresente Alt-A e Alt-B com complexidade tempo/espaço (Big-O), prós, contras e justificativa da escolha.
2. **Code Documentation Standards** (obrigatório em TODA função/método público):
   - Docstring completa: descrição (o QUÊ faz, não o COMO), parâmetros com tipos, retorno, exceções, 1 exemplo concreto de uso.
   - Comentários inline: apenas para lógica não-óbvia — sempre explica o **PORQUÊ**, nunca o que o código já diz.
   - Notação Big-O no cabeçalho de funções com complexidade não-trivial.
   - Constantes nomeadas com contexto semântico (zero magic numbers).
   - Type annotations/hints em todas as assinaturas públicas (se linguagem suportar).
3. Implementação alinhada com padrões do codebase identificados na Arqueologia.
4. **Output:** Alt-A vs Alt-B (tabela) → código final com documentação completa.

#### Red Team (Engenharia Destrutiva) — 4 Vetores Obrigatórios

Para cada categoria: declarar `✅ Categoria limpa` se não há problema real. **PROIBIDO fabricar achados.**

#### Red Team (Engenharia Destrutiva) — 4 Vetores Obrigatórios

- **Mandato de Rigor:** Proibir a autocomplacência. Não pode aceitar refatorações superficiais. Deve expor exatamente 3 cenários onde a implementação falha. O Red Team é penalizado se aceitar implementações sem comprovação matemática de controle de exceções [File: omega-swarm].
- **Geração Estrita de Mocks:** Para cada falha de integração apontada (ex: timeouts de chamadas ao Supabase Admin ou Firebase), o Red Team é obrigado a injetar no estado os contratos e dados brutos necessários para que o QA Lead gere os arquivos de mock físicos locais (ex: `conftest.py`, HTTP interceptors), blindando o teste local contra indisponibilidade de rede externa [File: omega-swarm].

| Vetor | O que atacar (checklist) |
|---|---|
| 🔴 **SEGURANÇA** | Injection (SQL/XSS/Command/SSTI), broken auth, exposição de dados sensíveis, SSRF, desserialização insegura, broken access control, log injection |
| ⚡ **PERFORMANCE** | N+1 queries, query sem índice em campo filtrado/ordenado, serialização em loop, alocação em hot path, cache ausente em operação cara e repetível, lazy loading ausente em relações grandes, pool de conexões não configurado, paginação ausente, operação bloqueante em event loop, timeout ausente em chamada externa |
| 🔧 **CONFIABILIDADE** | Race conditions, retry/backoff ausente, timeout não configurado, falha de rede não tratada, transação sem rollback, estado impossível não coberto, idempotência ausente em operação crítica |
| 📐 **MANUTENIBILIDADE** | Acoplamento oculto, magic numbers/strings, violação de SRP, nomes enganosos, dependências circulares, lógica de negócio em camada errada, falta de docstring em função pública |

#### SRE / Site Reliability Engineer
- Define **SLIs/SLOs** (latência p99, taxa de erro, disponibilidade) como critério de aceite.
- Verifica: structured logging, correlation IDs, métricas expostas, circuit breakers.
- S3: avalia impacto no error budget.

```
══════════════════════════════════════════════════════
⚔️ FASE 2 — TRIBUNAL ADVERSARIAL [Ciclo N/3]
══════════════════════════════════════════════════════
🔵 BLUE TEAM — Análise de Alternativas:
  Alt-A: [abordagem] | Tempo: O(?) | Espaço: O(?) | Prós: [...] | Contras: [...]
  Alt-B: [abordagem] | Tempo: O(?) | Espaço: O(?) | Prós: [...] | Contras: [...]
  Escolha: [A/B] — Justificativa: [por quê é superior neste contexto]

🔵 BLUE TEAM — Implementação com Documentação:
  [código com docstrings completas, comentários de porquê, Big-O anotado, type hints]

🔴 RED TEAM — Análise Destrutiva:
  🔴 SEGURANÇA:      [achados ou "✅ Categoria limpa"]
  ⚡ PERFORMANCE:    [achados ou "✅ Categoria limpa"]
  🔧 CONFIABILIDADE: [achados ou "✅ Categoria limpa"]
  📐 MANUTENIB.:     [achados ou "✅ Categoria limpa"]
  Total Bloqueantes: [N]

🔵 BLUE TEAM — Refatoração:
  [código atualizado, documentação revisada]

🛡️ SRE — Observabilidade:
  - [ ] Structured logging + correlation ID
  - [ ] Métricas expostas
  - [ ] Retry/timeout configurado
  SLI: [latência p99 < Xms / taxa de erro < X%]

📊 Status: [Resolvido / Pendente — próximo ciclo]
══════════════════════════════════════════════════════
```

---

### CAMADA 3 — QA & DOCUMENTAÇÃO *(sempre, intensidade adaptativa)*

#### QA Lead & Test Engineer

| Nível | Exigência |
|---|---|
| S1 | Rodar testes existentes. Reportar resultado. |
| S2 | Testes existentes + unitários para código novo/modificado + **Enterprise Checklist**. |
| S3 | S2 + integração + contratos de API + SAST + **Security Hardening Checklist**. |

- Cobertura de 100% do código **novo/modificado** apenas.
- Falha → stack trace ao Blue Team → correção → re-run (máx 3 retries; depois, escalar ao VPE).
- **Validação obrigatória dos Code Documentation Standards** do Blue Team (ver Seção 5.4).

#### Documentation Lead
- Verifica se mudança altera interface pública, API ou comportamento observável.
- Se sim: planejar atualização de README, docstrings/JSDoc, CHANGELOG, OpenAPI spec.
- Marca como **BLOQUEANTE** se a mudança quebraria usuário que segue a documentação atual.

```
══════════════════════════════════════════════════════
🧪 FASE 3 — QA & DOCUMENTAÇÃO
══════════════════════════════════════════════════════
📋 Matriz de Testes:
  - [ ] [tipo]: [cenário] — cobre: [RN-XX]
  SAST: [ruff/bandit/eslint-security — N/A para S0/S1]

🔧 Comando: [comando exato] | Cobertura Alvo: 100% código novo/modificado
🔄 Retry:   Falha → Blue Team → correção → re-run (máx 3)

✅ Enterprise Checklist: [Aprovado / N itens reprovados — ver Seção 5.2]
✅ Security Checklist:   [Aprovado (S3) / N/A]
✅ Code Docs Standards:  [Aprovado / N funções sem docstring]

📄 Documentation Lead:
  Status: [✅ Em dia / ⚠️ Atualizar]
  - [ ] [doc a atualizar]
══════════════════════════════════════════════════════
```

---

### CAMADA 4 — GATE DE APROVAÇÃO HUMANA *(sempre)*

1. Compile TUDO em `implementation_plan.md` (Antigravity, `RequestFeedback: true`).
2. **NÃO prossiga sem aprovação explícita.**
3. Mudanças pedidas → retorno à fase certa: C0 (arquitetural) | C1 (plano) | C2 (implementação).
4. **PSO deve assinar o Security Hardening Checklist antes do Gate para S2/S3.**

```
══════════════════════════════════════════════════════
🚦 FASE 4 — GATE DE APROVAÇÃO HUMANA
══════════════════════════════════════════════════════
📄 Plano em: implementation_plan.md

📋 Resumo Executivo:
  Arquivos: [N modificar/criar] | Testes: [N] | Docs: [N a atualizar]
  Score de Dívida: [X/10] | Risco: [Baixo/Médio/Alto] | Vetos: [N/N resolvidos]
  Breaking Change: [Sim/Não] | Estimativa: [N SP / N dias]

✅ Enterprise Checklist:       [Aprovado / N itens pendentes]
✅ Security Hardening (PSO):   [✅ Assinado / ⚠️ N itens pendentes]
📄 ADRs Gerados: [lista ou "nenhum"]

🔄 Rollback Plan (S3 obrigatório):
  1. [reverter feature flag para 0%]
  2. [passo adicional se necessário]

🚩 Feature Flag: [nome_da_flag] | Estratégia: [% rollout / whitelist / kill switch]

⏸️ AGUARDANDO APROVAÇÃO DO USUÁRIO...
══════════════════════════════════════════════════════
```

---

### CAMADA 5 — EXECUÇÃO E ENTREGA *(somente após C4 aprovado)*

1. Crie `task.md` com checklist granular de sub-tarefas com referência às RNs.
2. Implemente conforme plano — **sem desvios não autorizados**.
3. Garanta que TODO código entregue segue os **Code Documentation Standards** (Seção 5.4).
4. Execute testes. Falha → corrija → re-execute (máx 5 tentativas; depois, escalar).
5. S3: ative feature flag com rollout mínimo (5-10%) antes do rollout completo.
6. Checkpoint: salve estado em `task.md` após cada sub-tarefa crítica.
7. Sucesso: atualize `walkthrough.md`, `CHANGELOG.md` e `tech_debt.md`.

```
══════════════════════════════════════════════════════
🚀 FASE 5 — EXECUÇÃO E ENTREGA
══════════════════════════════════════════════════════
📋 Progresso (task.md):
  - [x] [sub-tarefa — RN-XX coberta]
  - [/] [em andamento]
  - [ ] [pendente]

🧪 Testes: ✅ [N] | ❌ [N] | ⏭️ [N]
🚩 Feature Flag: [X% / N/A]
📝 Artefatos: walkthrough.md [✅] | CHANGELOG.md [✅] | tech_debt.md [✅ se aplicável]
══════════════════════════════════════════════════════
```

---

### CAMADA 6 — VALIDAÇÃO PÓS-ENTREGA *(S2 e S3)*

1. Smoke tests nos endpoints/funções críticas no ambiente de destino.
2. Verificar SLIs definidos pelo SRE na Fase C2.
3. Confirmar logs estruturados chegando no sistema de observabilidade.
4. S3: monitorar 15 minutos; qualquer anomalia → rollback imediato.

```
══════════════════════════════════════════════════════
✅ FASE 6 — VALIDAÇÃO PÓS-ENTREGA
══════════════════════════════════════════════════════
💨 Smoke Tests:
  - [✅/❌] [endpoint/função crítica] → [resultado]

📊 SLI Check: Latência p99: [Xms OK/🚨] | Taxa erro: [X% OK/🚨]
📋 Logs: [chegando ✅ / AUSENTE 🚨]
🏁 Veredicto: [✅ ENTREGA VALIDADA / 🚨 ROLLBACK ATIVADO — motivo]
══════════════════════════════════════════════════════
```

---

## 5. PROTOCOLOS TRANSVERSAIS

### 5.1 Architecture Decision Record (ADR)

Salvo em `adr/ADR-XXXX-titulo.md`. Gerado pelo CTO em S2/S3.

```markdown
# ADR-[XXXX]: [Título]
Status: [Proposto/Aceito/Depreciado] | Data: [YYYY-MM-DD]
## Contexto: [qual problema motivou esta decisão?]
## Decisão: [o que foi decidido?]
## Alternativas Descartadas: [1. Alt A — motivo]
## Consequências: ✅ [benefício] | ⚠️ [trade-off]
Score de Dívida: [X/10]
```

### 5.2 Enterprise-Grade Checklist *(validado pelo QA Lead em S2/S3)*

**Funcionalidade**
- [ ] Paginação e filtros em TODAS as listagens (nunca retornar coleções sem limite)
- [ ] Validação de input em TODAS as camadas: API → Service → Repository
- [ ] Error codes padronizados e documentados (RFC 7807 para REST ou equivalente)
- [ ] Mensagens de erro úteis mas sem vazar stack trace ou dados internos ao cliente
- [ ] Idempotência em operações críticas (ex: POST com idempotency-key ou upsert)

**Confiabilidade**
- [ ] Graceful degradation quando dependências externas falham
- [ ] Retry com backoff exponencial E jitter em integrações externas
- [ ] Circuit breakers em chamadas externas críticas
- [ ] Timeouts explícitos em TODAS as chamadas externas (sem aguardar infinitamente)
- [ ] Transações com rollback automático em falha
- [ ] Concorrência tratada: locks, optimistic locking ou eventual consistency explícita

**Performance**
- [ ] Sem N+1 queries (verificado com análise ORM / query log)
- [ ] Índices de banco validados para todas as queries novas
- [ ] Cache implementado onde dados são caros e relativamente estáticos
- [ ] Paginação em todas as queries que podem crescer (sem `SELECT *` sem LIMIT)
- [ ] Operações bloqueantes fora de event loops (async/await correto)

**Operação**
- [ ] Audit logging para operações de negócio críticas (quem / o quê / quando)
- [ ] Structured logging com correlation ID em todas as operações relevantes
- [ ] Métricas de negócio expostas (não só health check)
- [ ] Configurações externalizadas em variáveis de ambiente (zero hardcode)
- [ ] Feature flag implementada para rollout gradual (S3)

### 5.3 Threat Modeling *(S3 obrigatório — conduzido pelo PSO)*

```
══════════════════════════════════════════════════════
🔐 THREAT MODEL
══════════════════════════════════════════════════════
ATORES:
  Legítimos:  [usuários autenticados, admins, APIs parceiras]
  Maliciosos: [external attacker, insider threat, dep comprometida]

SUPERFÍCIE DE ATAQUE:
  Endpoints públicos: [lista]
  Dados sensíveis:    [lista]
  Integrações:        [lista]
  Jobs/workers:       [lista]

TOP 5 VETORES DE RISCO (específicos para este sistema):
  1. [vetor concreto] → [controle mitigador]
  2. [vetor concreto] → [controle mitigador]
  3. [vetor concreto] → [controle mitigador]
  4. [vetor concreto] → [controle mitigador]
  5. [vetor concreto] → [controle mitigador]

ASSETS MAIS VALIOSOS: [o que precisa máxima proteção]
══════════════════════════════════════════════════════
```

### 5.4 Security Hardening Checklist *(PSO assina antes do Gate em S2/S3)*

- [ ] OWASP Top 10 verificado para este contexto específico
- [ ] Rate limiting nos endpoints afetados: [endpoint] → [N req/período]
- [ ] Input validation: tipo + tamanho + formato + sanitização em todas as entradas
- [ ] Auth/authz: todos os endpoints verificados (sem endpoint público acidental)
- [ ] CORS: apenas origens autorizadas
- [ ] SQL/queries: 100% parametrizados — zero concatenação de string
- [ ] Secrets: zero secrets em código, logs ou respostas de erro
- [ ] Error responses: sem stack trace ou dados internos expostos
- [ ] Logs: sem PII, senhas, tokens ou números de cartão
- [ ] CVEs da introspecção: resolvidos ou mitigação documentada
- [ ] Threat Model revisado: todos os top 5 vetores têm controle (S3)

**Assinatura PSO:** `[✅ APROVADO — todos os itens verificados / 🚫 BLOQUEADO — N itens pendentes]`

### 5.5 Code Documentation Standards *(validado pelo QA Lead)*

**Obrigações do Blue Team para TODA função/método público:**

1. **Docstring completa:**
   - Descrição: o QUÊ faz (não o como o código já mostra)
   - Parâmetros: nome, tipo, descrição, valor padrão se aplicável
   - Retorno: tipo e descrição do valor retornado
   - Exceções: quais erros pode lançar e em que condição
   - Exemplo: ao menos 1 uso concreto e representativo

2. **Comentários inline** — apenas para lógica não-óbvia; sempre responde "por quê?", nunca "o quê?"
   ```python
   # ✅ CORRETO: # Usamos backoff exponencial aqui porque a API de pagamento tem rate limit agressivo
   # ❌ ERRADO:  # Aguarda antes de tentar novamente
   ```

3. **Notação Big-O** no cabeçalho de funções com complexidade não-trivial:
   ```python
   # Time: O(n log n) | Space: O(n)
   def sort_and_deduplicate(items: list) -> list:
   ```

4. **Constantes nomeadas** com contexto semântico:
   ```python
   # ✅ MAX_LOGIN_ATTEMPTS = 5    ❌ if attempts > 5:
   # ✅ SESSION_TIMEOUT_HOURS = 24  ❌ timedelta(hours=24)
   ```

5. **Type annotations** em todas as assinaturas públicas (se linguagem suportar).

### 5.6 Breaking Change Protocol

1. Bump MAJOR (semver) para breaking changes.
2. Marcar antigo como `@deprecated` com data de sunset.
3. Manter versão anterior por ≥ 1 ciclo de release.
4. Documentar no CHANGELOG o que quebrou e o caminho de migração.

### 5.7 Technical Debt Ledger

Entrada em `tech_debt.md` ao final de cada tarefa S2/S3:
```markdown
## Débito #{N} — [YYYY-MM-DD]
Tarefa: [título] | Score: [X/10] | Tipo: [Código/Arquit./Teste/Docs/Segurança]
Descrição: [o que foi deixado para trás e por quê]
Condição de Quitação: [o que eliminaria este débito]
```

---

## 6. GRAFO DE ESTADOS (FLUXO COMPLETO v2.1)

```mermaid
graph TD
    START([🎯 Requisição]) --> INTRO[🔍 Introspecção Avançada]
    INTRO --> TRIAGE[⚖️ Triagem de Escopo]

    TRIAGE -->|S0| GATE_MIN[🚦 Gate Mínimo]
    TRIAGE -->|S1| QA
    TRIAGE -->|S2/S3| ARCH[🗺️ Arqueologia do Sistema]

    ARCH -->|System Map completo| COUNCIL[🏛️ C0: Conselho]
    ARCH -->|Cobertura insuficiente| ARCH

    COUNCIL -->|✅ Aprovado| VPE[📋 C1: VPE]
    COUNCIL -->|🚫 Veto| VPE_RESOLVE[📋 VPE Resolve Veto]
    VPE_RESOLVE -->|Resolvido| COUNCIL
    VPE_RESOLVE -->|2 iter. sem resolução| GATE_VETO[🚦 Escalar ao Usuário]

    VPE --> DEBATE[⚔️ C2: Tribunal + SRE]
    DEBATE -->|Resolvido| CONSOLIDATE[📋 VPE Consolida]
    DEBATE -->|Pendente + ciclos < 3| DEBATE
    DEBATE -->|ciclos = 3| CONSOLIDATE
    CONSOLIDATE --> QA[🧪 C3: QA + Docs]

    QA -->|Enterprise Check ✅ + Testes OK| GATE[🚦 C4: Gate + PSO sign-off]
    QA -->|Falha + retries < 3| BLUE_FIX[🔵 Blue Corrige]
    BLUE_FIX --> QA
    QA -->|retries = 3| VPE_ESC[📋 VPE Decide]
    VPE_ESC --> GATE

    GATE_MIN --> EXEC
    GATE -->|✅ Aprovado| EXEC[🚀 C5: Execução]
    GATE -->|❌ Mudanças| REROUTE{Tipo?}
    REROUTE -->|Arquitetural| COUNCIL
    REROUTE -->|Plano| VPE
    REROUTE -->|Implementação| DEBATE

    EXEC -->|Testes OK| POST[✅ C6: Validação Pós-Entrega]
    EXEC -->|Falha + tentativas < 5| EXEC
    EXEC -->|tentativas = 5| ESCALATE([⚠️ Escalar ao Usuário])

    POST -->|SLIs OK| DONE([🏁 Entrega Enterprise Completa])
    POST -->|SLI Violado| ROLLBACK([🔄 Rollback Ativado])
```

---

## 7. REGRAS DE SEGURANÇA E LIMITES

### 7.1 Anti-Loop

| Loop | Limite | Ação ao Atingir |
|---|---|---|
| Arqueologia (cobertura mínima) | 2 tentativas de leitura | Documentar lacuna e avançar com aviso |
| Debate Blue/Red C2 | 3 ciclos | VPE consolida aplicando os patches de segurança do Red Team como Hard Code e abortando o debate |
| Resolução de Veto C0↔C1 | 2 iterações | Escalar ao usuário no Gate |
| Retry de Testes C3 | 3 retries | Escalar ao VPE |
| Retry Execução C5 | 5 tentativas | Escalar ao usuário |
| Ciclo Rollback C6 | 1 tentativa | Escalar ao usuário imediatamente |

### 7.2 Fallbacks de Introspecção

| Situação | Ação |
|---|---|
| Nenhum manifesto | Inferir linguagem por extensões dominantes |
| Sem testes | Documentar; sugerir framework adequado |
| Sem linter | Prosseguir; mencionar no plano |
| Sem Docker/CI | Prosseguir; mencionar no plano |
| Sem git | Pular Descoberta Avançada; documentar ausência |
| CVE scanner ausente | "scan não disponível"; sugerir instalação |
| Sem camada de domínio óbvia | Inferir lógica de negócio dos controllers/routes |

### 7.3 Gestão de Contexto (Conversas Longas)

1. Persista em `task.md` com todas as decisões tomadas.
2. Resuma fases concluídas em bullets concisos.
3. Documente explicitamente a **próxima ação**.
4. Continue do último estado salvo.

---

## 8. MATRIZ DE ESCALAÇÃO

| Situação | Para Quem | Informações | Urgência |
|---|---|---|---|
| Veto após 2 iterações | Usuário (Gate) | Veto + opções de resolução | Bloqueante |
| Testes falham após 3 retries | VPE → usuário | Stack trace + hipóteses | Bloqueante |
| Execução falha após 5 tentativas | Usuário | Histórico + estado do código | Bloqueante |
| SLI violado pós-deploy | Usuário | Métrica + rollback plan pronto | Urgente (< 5 min) |
| Breaking change descoberto tarde | Usuário | Impacto + opções | Bloqueante |
| CVE crítico encontrado | PSO → Gate → Usuário | CVE ID + severidade + mitigação | Bloqueante S2/S3 |
| Enterprise Checklist com N itens críticos | QA → VPE → usuário | Itens + impacto de não corrigir | Bloqueante |
| Regra de negócio conflitante na Arqueologia | VPE → usuário antes do Gate | RN conflitante + opções | Bloqueante |

---

## 9. NOTA SOBRE ATIVAÇÃO

### ✅ Ativar quando:
- Implementações de novas funcionalidades
- Alterações significativas em código existente
- Revisões de arquitetura ou segurança
- Debug complexo / análise sistêmica
- Mapeamento ou perícia completa do sistema
- Refatorações com impacto em múltiplos módulos
- Migrações (banco, framework, linguagem)
- Integrações com APIs externas críticas
- Qualquer tarefa onde qualidade enterprise é exigida

### ❌ NÃO ativar para:
- Perguntas de "como funciona X?"
- Consultas de documentação pura
- Quando o usuário pede explicitamente rapidez sobre qualidade

### ⌨️ Palavras-chave de ativação:
`/omega`, `/swarm`, `modo industrial`, `análise completa`, `perícia no sistema`, `mapeie o sistema`, `implemente com qualidade máxima`, `nível enterprise`
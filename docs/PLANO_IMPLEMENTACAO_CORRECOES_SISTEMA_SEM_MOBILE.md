# Plano mestre de implementação e correção — sistema sem aplicativo mobile

**Sistema:** Painel Expresso Neves / APIs Django e FastAPI / PostgreSQL / Redis / Celery / frontend web
**Data-base:** 23 de setembro de 2026
**Última atualização de execução:** 24 de setembro de 2026
**Referência de versão:** esta revisão integra o release candidate registrado no histórico Git
**Origem:** perícia consolidada de produção realizada entre 22 e 24 de setembro de 2026
**Status:** correções críticas implementadas e verificadas localmente; gates operacionais e externos ainda abertos
**Veredito até concluir os gates:** **NO-GO**

---

## 0. Estado de execução verificado em 24/09/2026

Esta seção prevalece sobre qualquer marcação histórica de “não iniciado” ou “concluído” no restante do documento. “Implementado localmente” significa que código, migrations e testes existem no worktree atual; não significa que a mudança foi aplicada em PostgreSQL de staging, homologada com provedores ou promovida para produção.

| Frente | Estado verificado | Evidência local | Pendência que ainda bloqueia produção |
|---|---|---|---|
| Autoridade de schema | **IMPLEMENTADO LOCAL** | Runner SQL ordenado com ledger/checksum; containers usam serviço de migração; imagens incluem `database/migrations` | Executar bootstrap e upgrade real em PostgreSQL/PostGIS de staging; provar drift zero, roles e rollback N/N-1 |
| Isolamento do motoboy | **IMPLEMENTADO LOCAL** | `get_company_drivers`, cadastro, escala, `StoreDriver`, unicidade global normalizada e transferência exclusiva do proprietário foram endurecidos; FKs compostas e preflight estão em migration | Aplicar/validar constraints e RLS em staging com duas tenants e concorrência real |
| RBAC e rotas legadas | **IMPLEMENTADO LOCAL** | Gestão de usuários, lojas, pedidos, lançamentos, filas de crédito, saldos, carteira e reconciliação agora resolvem o tenant pelo ator autenticado; fallbacks globais e respostas fictícias foram removidos | Rodar E2E de todas as personas em PostgreSQL com RLS e revisar autorização por rota no gateway |
| Sessão e identidade | **IMPLEMENTADO LOCAL** | Access token somente em memória; refresh em cookie HttpOnly com JTI de uso único e detecção de replay no cache compartilhado; logout, revogação de usuário e validação da identidade persistida do proprietário | Homologar cookies/CSRF/domínios/TLS e Redis compartilhado no ambiente final; MFA/step-up do proprietário continua aberto |
| White-label | **IMPLEMENTADO LOCAL** | Branding por operador, upload validado, logo/favicon, tokens de cor, login, navegação, recibos e PDFs; 9 testes específicos verdes | Storage privado/objeto + CDN, cache/invalidação, acessibilidade visual e E2E multissubdomínio em staging |
| Hub de integrações | **PARCIAL** | Registry, CRUD tenant-scoped, segredos cifrados, HMAC, deduplicação, logs e conector webhook genérico; 11 testes específicos verdes | Apenas `generic-webhook` possui implementação ativa. Conectores reais de PDV/cardápio, OAuth/credenciais, sandbox, contrato e homologação por fornecedor não existem ainda |
| Financeiro/PIX | **PARCIAL** | Webhook com HMAC/mTLS confiável, limite de corpo, resolução tenant e processamento pós-commit; simulação de pagamento bloqueada em produção | Congelar contrato Efí vigente, executar sandbox/mTLS real, reconciliar ledger e obter aceite financeiro |
| Deploy e runtime | **IMPLEMENTADO LOCAL / NÃO HOMOLOGADO** | Compose falha sem segredos, separa migrator/runtime, readiness exige banco e cache, containers non-root e Nginx endurecido; os dois arquivos Compose passam em `config -q` com o arquivo de exemplo explícito | Build/scan/SBOM das três imagens em CI, deploy imutável por digest, secrets manager e smoke de staging |
| Segredos/incidente | **PARCIAL** | Credenciais copiadas em documentação histórica e referência de projeto em script foram redigidas; a varredura local final não encontrou URL com senha, chave privada ou token OpenAI nos artefatos ativos; scripts perigosos exigem alvo/token/tenant explícitos | Rotacionar as credenciais no provedor, sanear histórico/caches/clones/imagens e provar que os valores antigos falham |
| Qualidade local | **PASS COM RESSALVAS** | Backend: **217 passed, 10 skipped (227 coletados)**; frontend: TypeScript sem erros, build de produção concluído; `npm audit --omit=dev`: **0 vulnerabilidades**; `compileall` e `git diff --check` sem erro | Os 10 skips dependem de infraestrutura/serviços reais; permanecem avisos de depreciação/cache do pytest e dois chunks web próximos/acima de 500 kB; não houve carga, caos, restore nem E2E de staging |

### 0.1 Correções adicionais encontradas no duplo cheque

- Eliminadas senha padrão e criação implícita de usuários; senha inicial explícita de no mínimo 10 caracteres, e-mail globalmente não ambíguo, hierarquia de papéis e bloqueio de autoelevação.
- Usuário de portal ganhou revogação persistente (`active`) e tokens de proprietários removidos deixaram de autorizar apenas por conterem claim soberana.
- Lançamento financeiro exclusivo de loja deixou de fabricar um “motoboy central”; `ManualEntry.driver_id` passa a aceitar `NULL` somente quando existe `store_id`, com constraint de contraparte.
- Rotas antigas de pedido deixaram de criar loja automática com coordenadas padrão e de ler/escrever pedido de outra tenant por ID; paradas usam `metadata`, conforme o schema real.
- Preço, distância e IDs fictícios foram removidos da criação de corridas e dos caches financeiros. O servidor calcula a tarifa pela faixa do contrato da loja, valida todos os trechos, rejeita configuração ausente e grava pedido/paradas atomicamente; distância externa desconhecida é `NULL`, não zero.
- A estimativa declara o método `HAVERSINE_BUFFERED_30_PERCENT`; ela não é apresentada como roteamento viário. O navegador não inventa mais coordenadas, tarifa, tempo ou identificador quando o serviço falha.
- Cadastro de cliente não persistente e cartão visual de integração falsamente “conectada” agora retornam indisponibilidade explícita.
- Refresh token repetido é rejeitado por JTI de uso único no Redis e a readiness falha quando o cache compartilhado não confirma leitura/escrita.
- Artefatos EasyPanel antigos com defaults inseguros e configuração divergente foram marcados como obsoletos; `docker-compose.yml` é a única definição canônica atual.

### 0.2 Bloqueadores externos e operacionais remanescentes

1. Rotação real de todas as credenciais que já estiveram expostas e saneamento de histórico/artefatos.
2. Aplicação das migrations em clone mascarado e staging PostgreSQL/PostGIS, incluindo prova da role runtime sem ownership, superuser ou `BYPASSRLS`.
3. Homologação Efí, biometria e de cada fornecedor de PDV/cardápio escolhido; hoje não existe oferta plugin-and-play validada além do webhook genérico.
4. Storage de branding/provas em objeto privado, URLs assinadas, política de retenção e teste de recuperação.
5. Homologar um motor de roteamento viário e substituir a estimativa Haversine antes de usar distância para cobrança comercial definitiva.
6. CI de imagens com scan/SBOM/provenance, E2E real, carga/soak, restore/PITR, observabilidade e piloto controlado.

---

## 1. Decisão de escopo

Este plano cobre todo o sistema, exceto o aplicativo Android NevesGo.

### 1.1 Incluído

- Backend Django/Ninja e FastAPI/Fast Lane.
- Painel web React/TypeScript.
- PostgreSQL, migrations, RLS, constraints e integridade multi-tenant.
- Identidade, autenticação, RBAC, sessão e vínculo de motoboy.
- Logística, escalas, check-in, corridas, provas, geofence e comandos offline do lado servidor.
- Finanças, ledger, saques, PIX/Efí, CNAB, maker-checker e reconciliação.
- Redis, Celery, outbox, webhooks, integrações e telemetria.
- Storage, privacidade de arquivos e recuperação de desastre.
- CI/CD, containers, Nginx, EasyPanel, observabilidade, carga, homologação e rollout.

### 1.2 Excluído e diferido

- Todo o diretório `mobile/**`.
- APK/AAB, Android, Kotlin, Compose, Gradle, FCM e Keystore.
- `MOB-001` a `MOB-007`, o requisito histórico mobile `QA-003`, `SLI-MOB-*` e `BKL-MOB-002`.
- Rollback de APK, política de versão mobile e qualquer gate que dependa de dispositivo.
- Os planos da antiga Fase 5 e o plano `08-03` ficam fora do grafo ativo e devem ser preservados apenas como histórico para a futura reimplementação.

### 1.3 Capacidades server-side preservadas

Telemetria, geofence, provas, device/session registry, idempotência e journal/comandos offline continuam no escopo quando forem implementações de servidor. Devem ser client-neutral para atender um futuro aplicativo sem reabrir as fronteiras de segurança.

### 1.4 Limite do marco

O resultado deste plano é a prontidão de produção do **painel web, APIs, dados, finanças, filas, integrações e infraestrutura**. Ele não declara pronta a operação de campo por aplicativo nem substitui a homologação futura do novo mobile.

---

## 2. Rebaseline obrigatório do planejamento existente

Os planos atuais não devem ser executados literalmente antes deste rebaseline. Eles ainda encadeiam mobile e, em vários pontos, pressupõem `supabase db push`, enquanto o código atual usa PostgreSQL e `database/migrations`.

### 2.1 Estado-alvo dos artefatos GSD

- **Etapas executáveis deste plano:** `S0` a `S9`; os nomes `S*` evitam colisão com a numeração histórica GSD.
- **Fases GSD antigas ativas como fonte:** 1–4 e 6–11; 10 fases de origem no total.
- **Fase GSD 5:** diferida/arquivada, sem dependentes ativos.
- **Requisitos ativos esperados:** 56 (`64 - MOB-001..007 - QA-003`). O texto **56/56** só pode ser declarado depois de `SYS-SCOPE-001` gerar o catálogo machine-readable e seu validador CI passar; até lá, a cobertura é `UNPROVEN`.
- **Gate G4:** reservado para a futura reimplementação mobile; nunca deve ser marcado como aprovado ou ser incluído em intervalos ambíguos como “G0–G7”.
- **Cadeia ativa:** `G0 → G1 → G2 → G3 → G5 → G6 → G7 → DEP → G8-Sistema → G9-Sistema → G10-Sistema`.
- **Release identity:** SHA + digests de backend/Fast Lane/frontend + migration head/checksums + SBOM + provenance + release anterior. Sem APK ou policy mobile.

### 2.2 Crosswalk de namespaces

| Etapa deste plano | Fonte GSD antiga | Tratamento |
|---|---|---|
| `S0` — rebaseline, contenção e autoridade mínima de migrations | Fase 1 / G0 e pré-requisito técnico da antiga Fase 3 | Ativa; fecha contenção e cria a base de schema antes de qualquer migration TEN/DRV |
| `S1` — identidade, tenant e motoboy | Fase 2 / G1 | Ativa |
| `S2` — schema consolidado, API, logística e dados | Fases 3 e 4 / G2 e G3 | Ativa; consolida/bootstrap/upgrade sobre a autoridade criada em `S0` |
| `S3` — finanças e webhook PIX | Fase 6 / G5 | Ativa, sem depender de G4 |
| `S4` — filas, integrações, Redis e Fast Lane | Fase 7 / G6 | Ativa |
| `S5` — painel web | Recorte web da Fase 8, especialmente `QA-002` e `FE-001` | Ativa; **não** é chamada de Fase 5 |
| `S6` — qualidade, observabilidade e plataforma | Fase 8 sem o requisito mobile `QA-003` | Ativa; o novo pacote de hermeticidade é `CI-HERM-001` |
| `S7` — staging, DR, capacidade e deploy | Fase 9 e preparação de `HOM-001` | Ativa |
| `S8` — homologação, piloto e rollout | Fase 10 / G8–G10 | Ativa, sem APK/dispositivo |
| `S9` — pós-go-live e escala | Fase 11 / GH1 | Ativa |
| Nenhuma etapa ativa | Fase GSD 5 / G4 e antigo `08-03`/`QA-003` | Arquivada para futura reimplementação mobile |

### 2.3 Alterações de dependência obrigatórias

| Artefato | Alteração |
|---|---|
| Fase 6 / `06-01` | depender de `04-05`/G3, não de `05-06`/G4 |
| Fase 8 / `08-03` | retirar do plano ativo; é integralmente mobile |
| Fase 8 / `08-04` | depender de `08-02`; matriz cross-system sem device/APK |
| Fase 8 / `08-05`, `08-08`, `08-09`, `08-12` | retirar SLI mobile, Crashlytics/Gradle, verification metadata e identidade APK |
| Fase 9 / `09-01`, `09-04` | manifesto e rollback sem APK/policy mobile |
| Fase 10 / `10-01` | enumerar G0, G1, G2, G3, G5, G6 e G7; retirar G4/RPO de journal mobile |
| Fase 10 / `10-02`, `10-03` | piloto e rollout por API/painel/harness; retirar FCM/device/APK/MOB-007 |

### 2.4 Autoridade única de schema e compatibilidade de release

O alvo será:

1. `database/migrations/*.sql` como autoridade versionada das tabelas de negócio, RLS, grants, constraints, índices, functions e triggers.
2. Django migrations restritas a tabelas realmente administradas pelo Django; não podem competir pela mesma tabela `managed=False`.
3. `MIG-000`, em `S0`, entrega antes de `TEN-*`/`DRV-*`: um único runner; ledger com nome, ordem, checksum, timestamps, executor e resultado; baseline de drift assinado; role `migrator` separada da role `runtime`, sendo a primeira a única autorizada a DDL e a segunda sem ownership, `CREATEDB`, `CREATEROLE`, superuser ou `BYPASSRLS`.
4. `setup_database.py`, patches de startup e `ALTER` ad hoc deixam de modificar schema; o CI reprova DDL fora das migrations autorizadas.
5. `SCH-001`/`SCH-002`, em `S2`, consolidam o conteúdo, bootstrap vazio, upgrade de snapshot e diff contra staging sobre a autoridade mínima já funcional.
6. Toda mudança segue **expand/contract**: expandir de forma aditiva, publicar código compatível com schema anterior/novo, fazer backfill verificável, trocar leitura/escrita e só contrair depois de drenar `N-1` e encerrar a janela de rollback.
7. Durante a janela `N/N-1`, ficam proibidos `DROP`, `RENAME`, mudança destrutiva de tipo e `NOT NULL` sem backfill/validação; exceção exige nova release coordenada e rollback de dados aprovado antes da promoção.
8. O release manifest declara `schema_head`, `schema_checksums`, `min_schema` e `max_schema`; RC `N` e release anterior `N-1` devem iniciar e executar smokes contra o schema expandido dentro desse intervalo.
9. O ensaio de rollback é classificado: (a) metadata/aditiva reversível; (b) índice/constraint online; (c) backfill/transformação com compensação ou forward-fix; (d) destrutiva somente após a janela, recuperável por restore/PITR. Cada classe registra comando, tempo, perda admissível e evidência.

---

## 3. Princípios que bloqueiam atalhos

1. **Tenant vem do servidor.** Header, query, body e `localStorage` nunca determinam autorização.
2. **Negação por padrão.** Ausência de papel, operador, segredo, certificado ou dependência obrigatória gera erro; nunca mock ou fallback global.
3. **PostgreSQL guarda efeitos duráveis.** Redis acelera e coordena, mas sua perda não pode apagar ou duplicar negócio.
4. **Uma regra, um service.** Rotas canônicas e adaptadores chamam o mesmo comando transacional.
5. **Dinheiro não é apagado.** Correções financeiras são compensatórias, em centavos, maker-checker e ledger balanceado.
6. **Histórico de tenant é imutável.** Transferir motoboy não reatribui corridas, faturas, provas ou lançamentos antigos.
7. **Release é artefato, não branch.** O mesmo digest validado é promovido; rollback nunca recompila.
8. **Gate vermelho não recebe aprovação manual.** A pessoa responsável pode pausar ou abortar, não substituir evidência técnica ausente.

### 3.1 Decisões bloqueadas do ingest

As decisões abaixo vêm nominalmente de `.planning/intel/USER-RESOLUTIONS.md`, são não negociáveis e devem aparecer por ID nos PLANs, testes e catálogo:

- **D-INGEST-01 — Máquinas de estado independentes.** Manter quatro autoridades separadas: preparação/fulfillment do parceiro (`PREPARING`, `READY_FOR_DISPATCH`), oferta (`OFFERED`, `ACCEPTED`, `REFUSED`, `EXPIRED`), entrega (pendência/atribuição, início, chegada, conclusão, cancelamento e devolução) e cada parada (pendência, chegada, conclusão ou falha). Preparação não avança entrega; oferta não duplica estado durável. Tradução externa sempre usa mapeamento versionado e transição inválida nunca é ignorada silenciosamente.
- **D-INGEST-02 — Comprovação configurável por risco.** Cada tipo de parada aponta para política versionada. `requiresPin` exige PIN hasheado **e** foto; parada comum exige ao menos uma entre foto, assinatura, PIN, QR ou código de barras permitida pela política. O servidor decide suficiência; arquivos são privados, tenant-scoped, validados por conteúdo e expostos só por URL assinada curta.
- **D-INGEST-03 — Resposta a GPS fraudado.** Sinal falso/incompatível cria incidente auditável e aviso. Alto risco bloqueia início/chegada/conclusão e exclui a localização da geofence. Desbloqueio exige staff autorizado da mesma tenant, motivo e auditoria imutável. A implementação deve incluir falso positivo, contestação, prazo/SLA operacional e o conjunto de evidências usado na decisão, sem permitir desbloqueio automático por timeout.
- **D-INGEST-04 — Remuneração versionada e mutuamente exclusiva.** Cada contrato escolhe exatamente um `compensation_model` e uma versão de fórmula ativa por período de vigência, resolvida pela data operacional do fato. Modelos iniciais e fórmulas simbólicas obrigatórias: `PER_DELIVERY_DISTANCE = delivery_fee_cents + eligible_stops × stop_fee_cents + Σ(distance_in_tier_m × tier_rate_cents_per_km ÷ 1000)`; `DAILY_PRODUCTION = daily_base_cents + excess_units × excess_unit_cents + eligible_trips × trip_fee_cents - advances_cents`. Faixas, elegibilidade, arredondamento inteiro e inputs vêm da versão contratual imutável. Uma liquidação não mistura modelos; composição futura exige nova versão e migração auditada. Cálculo usa centavos inteiros, referência idempotente, ledger balanceado e testes de replay/concorrência.

---

## 4. Visão de execução

| Onda | Frentes | Paralelismo permitido | Gate de saída |
|---:|---|---|---|
| 0A | `SYS-SCOPE-001` e `PLAN-MANIFEST-001` | Somente artefatos de planejamento; nenhum código/config/schema pode mudar antes de todos os validadores do gate | PLAN-S0 |
| 0B | Contenção, segredos, `/admin/`, webhook, rotas inseguras e `MIG-000` | Após PLAN-S0, frentes avançam com owners/files exclusivos; TEN/DRV aguardam `MIG-000` | G0 |
| 1 | S1: JWT/sessão, contrato server-authoritative, CORS, RBAC/RLS e identidade de motoboy | Auth, policy e modelagem paralelizam segundo o manifesto; qualquer DDL TEN/DRV depende de `MIG-000` | G1 |
| 2 | S2: schema consolidado, API, logística, storage e auditoria | Bootstrap/upgrade primeiro; API/logística depois, por contrato congelado | G2/G3 |
| 3 | S3 finanças **e S5A frontend independente** | Frontend local/contratos/UI pode avançar sem integrações reais; S3 fecha sozinho antes de S4 | G5 + S5A |
| 4 | S4 filas, integrações, Redis e Fast Lane | Dependência inequívoca: `S3 → G5 → S4`; nenhum pacote S4 roda com G5 vermelho | G6 |
| 5 | S5B integração/E2E web | Depende de G5 e G6; conecta o frontend de S5A aos fluxos reais e fecha Gate Web | Gate Web |
| 6 | S6 CI, observabilidade, containers e proxy | Depende de G5, G6 e Gate Web; trilhas internas paralelas por owner | G7 |
| 7 | S7 deploy imutável, restore, falhas, CAP/carga | Builds/DR paralelos; carga espera CAP-000 e promoção é sequencial | DEP/G8-Sistema |
| 8 | S8 piloto e rollout | HOM-001→HOM-002→HOM-003 estritamente sequenciais | G9/G10-Sistema |
| 9 | S9 estabilidade e expansão | Somente 30 dias após G10-Sistema | GH1 |

---

## 5. Etapa S0 — Rebaseline, contenção e autoridade mínima

**Objetivo:** impedir novos incidentes e instalar a autoridade mínima de migrations enquanto a arquitetura definitiva é construída.
**Dependências:** nenhuma.
**Bloqueia:** qualquer merge funcional, deploy, cadastro de segundo operador ou dinheiro real. Nenhuma migration `TEN-*` ou `DRV-*` pode ser criada/aplicada antes de `MIG-000` passar.

### Pacotes de trabalho

| ID | Implementação | Arquivos/superfícies prováveis | Evidência de aceite |
|---|---|---|---|
| SYS-SCOPE-001 | Atualizar `PROJECT`, `REQUIREMENTS`, `ROADMAP`, `STATE` e planos contaminados; marcar Fase GSD 5/antigo `08-03` como diferidos; gerar `.planning/system-scope-requirements.yaml` com **exatamente 56 registros individuais**, um por requisito ativo, e `scripts/ci/validate_system_scope.py` | `.planning/**`, `scripts/ci/validate_system_scope.py` | O validador retorna `active_records=56, excluded_mobile=8, orphan=0, duplicate=0, missing_field=0, missing_package=0, unknown_dependency=0, dependency_cycle=0, gate_order_error=0, wave_order_error=0`; tabela compacta ou faixa textual nunca substitui os 56 registros |
| PLAN-MANIFEST-001 | Depois de `SYS-SCOPE-001` e antes de qualquer implementação, gerar `.planning/system-plan-manifest.yaml`, `ops/owners/system-readiness.yaml` e seus validadores com todos os PLANs, tarefas e responsáveis nominais completamente decididos conforme as seções 18–19 | `.planning/system-plan-manifest.yaml`, `ops/owners/system-readiness.yaml`, schemas, `scripts/ci/validate_system_plan_manifest.py`, `scripts/ci/validate_system_owners.py`, PLANs gerados | Cada pacote e gate aparece em registro executável; cada PLAN tem 2–3 tarefas, files exclusivos por wave, dependências existentes/acíclicas/anteriores, verify automatizado e done/evidence; o registro de owners exige pessoa nominal, substituto e contato válidos e termina com `unresolved_owner=0, missing_backup=0, missing_contact=0`; placeholder ou decisão substancial deixada ao executor reprova S0 |
| MIG-000 | Instituir antes de qualquer schema TEN/DRV o runner único, ledger/checksum, baseline de drift e credenciais distintas `migrator`/`runtime`; retirar DDL de startup e negar DDL/ownership/superuser/`BYPASSRLS` à role runtime | `database/migrations/**`, runner/manifesto de migrations, grants, secrets de deploy, relatório `artifacts/schema/drift-baseline.json` | Bootstrap do ledger e `schema_preflight --check-roles --check-checksums --baseline` passam; tentativa de `CREATE/ALTER/DROP` com role runtime falha; alteração de migration aplicada ou DDL fora da autoridade reprova CI |
| IR-001 | Inventariar, revogar e rotacionar credenciais expostas; preservar evidência redigida e procurar uso anômalo | secret stores, provedores, scripts e histórico Git | Cada credencial anterior falha; scanners de worktree e histórico retornam zero segredo ativo |
| IR-002 | Após rotação, sanear histórico Git, clones controlados, caches CI, imagens e artefatos derivados; produzir rewrite map redigido com refs/SHA antigos→novos e plano de reclone/invalidação sem apagar a cadeia de custódia | repositório/histórico, registry, caches CI, `artifacts/incident/git-rewrite-map.json` | Scanner do worktree, refs reescritas, clones amostrados, layers e caches retorna zero segredo ativo; refs antigas são rejeitadas e o rewrite map permite auditoria sem expor valores |
| IR-003 | Substituir promoção administrativa em massa por comando unitário allowlisted para conceder **ou revogar** privilégio, com ator elegível, confirmação explícita, alvo único, razão, idempotência e auditoria append-only | management command/service de privilégios, allowlist, audit/outbox | Bulk/wildcard/ator fora da allowlist/sem confirmação falham; uma promoção ou revogação válida altera exatamente um vínculo e gera exatamente um evento auditável |
| IR-004 | Reconciliar inventário de contas, roles, claims e sessões contra a allowlist; definir `token_cutoff_at` e revogar famílias/sessões anteriores ou incompatíveis, com relatório de exceções redigido | accounts/session store, roles, auth services, `artifacts/incident/identity-reconciliation.json` | Toda combinação inválida é bloqueada/corrigida; token emitido antes do cutoff ou com role/tenant divergente falha; relatório termina sem pendência não explicada |
| IR-005 | Bloquear novos secrets no pre-commit/CI e fazer staging/produção falharem antes de servir tráfego quando configuração obrigatória estiver ausente/fraca | scanner, CI, `settings.py`, Compose/EasyPanel, providers | Secret novo reprova CI; startup de produção sem cada segredo/provider obrigatório falha fechado, sem fallback/mock/global default |
| CI-HERM-000 | Retirar efeitos externos de scripts de teste, mover diagnósticos para ferramenta explícita e configurar descoberta somente em `backend/tests` | `backend/scripts/test_*`, configuração pytest | Coleta de testes abre zero conexão de rede e não autentica em ambiente externo |
| EDGE-CONTAIN-001 | Bloquear no gateway/feature flag as mutações legadas inseguras e o webhook PIX atual | Nginx/gateway, `config/db_api.py`, `config/panel_api.py`, `finance/webhooks.py` | Requests bloqueados não chegam à aplicação; webhook não autenticado nunca muda `WithdrawalRequest` |
| FINDINGS-001 | Fixar o laudo atual como inventário de achados e registrar owner/status/evidência por P0/P1/P2 | docs/evidence, issue tracker ou manifesto local | Todos os 29 achados não-mobile possuem owner, etapa, gate e teste de encerramento |
| ADM-001 | Em produção, desabilitar `/admin/` por padrão no edge; quando houver necessidade operacional aprovada, expor somente por VPN/IAP ou allowlist deny-by-default, com conta individual, MFA/step-up, sessão curta, CSRF, rate limit e auditoria | Nginx/IAP/VPN, `urls.py`, auth/admin settings, runbook | Probe externo a partir de rede não confiável recebe 404/403 no edge e não alcança Django; probe pelo canal confiável ainda exige MFA e gera audit event; scanner confirma ausência de bypass por host/header spoofado |

### Gate PLAN-S0

- `.planning/system-scope-requirements.yaml` contém 56 registros individuais e passa todas as validações de identidade/dependência/gate/wave.
- `.planning/system-plan-manifest.yaml` cobre todos os pacotes e gates com PLANs de 2–3 tasks, owners nominais, files exclusivos, DAG válido, verify e done/evidence completos; `ops/owners/system-readiness.yaml` passa seu schema/validador sem owner, substituto ou contato pendente.
- PLANs gerados correspondem byte semanticamente ao manifesto; nenhum contém placeholder, decisão substancial aberta ou escopo mobile.
- Até `PLAN-S0=PASS`, somente os artefatos e validadores declarados em `SYS-SCOPE-001` e `PLAN-MANIFEST-001` — incluindo catálogo, manifesto, PLANs gerados e registro de owners — podem ser alterados; `MIG-000`, contenção e qualquer implementação permanecem bloqueados.

### Gate G0

- Credenciais antigas estão revogadas e rotação comprovada.
- Histórico/clones/caches/imagens derivados foram saneados e o rewrite map de IR-002 está preservado.
- Promoção/revogação administrativa só ocorre unitariamente pelo comando allowlisted de IR-003; contas/roles/claims/sessões e token cutoff estão reconciliados por IR-004.
- Testes são herméticos e sem egress.
- Rotas legadas de escrita e webhook inseguro estão bloqueados.
- `/admin/` está indisponível externamente ou protegido pelo canal privado aprovado, e o teste externo está anexado.
- Nenhum default secreto/mock mantém o sistema “funcionando” em produção.
- `MIG-000` passou: runner/ledger/checksums, roles separadas e drift baseline existem antes do primeiro DDL TEN/DRV.
- O catálogo individual de `SYS-SCOPE-001` e o manifesto executável de `PLAN-MANIFEST-001` passaram antes da primeira implementação; somente a saída do catálogo permite declarar 56/56.

**Rollback:** não restaurar credenciais comprometidas. Bloqueios de rota só podem ser removidos quando o replacement canônico correspondente estiver verde.

---

## 6. Etapa S1 — Identidade, tenant e propriedade exclusiva do motoboy

**Objetivo:** cada operação usa ator, papel e operador verificados; o banco impede cruzamento; um motoboy só pode ter um operador ativo.
**Dependência:** G0 e `MIG-000` verde; nenhuma exceção para migrations de identidade/RLS/membership.

### Pacotes de trabalho

| ID | Implementação | Arquivos/superfícies prováveis | Evidência de aceite |
|---|---|---|---|
| AUTH-001 | Separar access/refresh: `NativeJWTAuth` exige `type=access`, issuer, audience, exp, iat e JTI | `accounts/auth.py`, `accounts/security.py`, testes auth | Refresh token usado como bearer em toda rota retorna 401 |
| AUTH-002 | Implementar família de refresh, rotação, reuse detection, revogação, logout real e invalidação por mudança de papel/tenant | accounts models/services/API | Replay de refresh revogado encerra a família; logout invalida sessão |
| AUTH-003 | Aplicar política de senha, remover senha padrão, rate limit/lockout e MFA/step-up da conta proprietária | accounts APIs, Nginx/Redis | Brute force é limitado; criação sem senha forte falha; transferência exige step-up recente |
| ID-004 | Entregar em S1 o contrato server-authoritative mínimo: sessão/context endpoint devolve ator, roles/capabilities, memberships permitidos e tenant efetiva; toda rota deriva tenant desse contexto e ignora/rejeita header/query/body adulterado | auth/session API, tenant context, OpenAPI, policy middleware | Troca sem membership retorna 403; `X-Tenant-Id`, query, body e preferência local nunca ampliam autorização; resposta canônica alimenta o frontend posterior sem ciclo |
| ID-005 | Implementar convite one-time com token forte hasheado, destinatário/role/tenant vinculados, expiração, consumo atômico, anti-reuso e revogação; mudança de papel/desligamento/perda de dispositivo revoga sessões | invitation/session models, services, API, audit/outbox | Convite expirado, revogado, alterado ou reutilizado falha; duas aceitações concorrentes têm um vencedor; aceite válido cria exatamente a membership autorizada e nenhuma credencial aparece em log/resposta |
| ID-006 | Fechar em S1 a política CORS da API/gateway por ambiente: origins exatas, credentials somente quando necessário, métodos/headers mínimos, `Vary: Origin`, cache de preflight limitado e negação de `null`/wildcard/suffix confusion | Django CORS, Nginx/gateway, testes de preflight | Origem/método/header não allowlisted recebe zero autorização cross-origin; combinação wildcard+credentials é impossível e o Gate G1 inclui matriz positiva/negativa |
| TEN-001 | Via o runner de `MIG-000`, criar LOGIN PostgreSQL exclusivo da aplicação, sem superuser, `BYPASSRLS`, DDL ou ownership | migration/grants/deploy secrets | Startup recusa `rolsuper`, `rolbypassrls` ou owner; role runtime não executa DDL; sessão sem claims lê zero linhas tenant |
| TEN-002 | Definir transação por request/task com papel e claims; limpar contexto em pool; aplicar `FORCE RLS` e políticas com `WITH CHECK` | middleware, tenant context, Celery, migrations | ORM sem filtro não atravessa tenant; conexão reutilizada não herda claims anteriores |
| TEN-003 | Inventariar todas as rotas e aplicar RBAC/capability default-deny; tenant sempre deriva do ator | routers, services, OpenAPI | Matriz anônimo/cliente/staff/admin/proprietário/worker × tenant A/B passa 100% |
| DRV-001 | Após `MIG-000`, criar `CourierIdentity` com CPF normalizado único, `DriverOperatorMembership` temporal e `DriverTransfer` versionado | migrations, models, services | Índice parcial impede dois memberships ativos inclusive sob concorrência; migration aparece no ledger/checksum autoritativo |
| DRV-002 | Reescrever criação/listagem: operador autenticado cria membership próprio; query/body não escolhem tenant | `db_api`, operator API, frontend adapters | Operador A cadastra A; tentativa de escolher B é ignorada/rejeitada sem revelar PII |
| DRV-003 | Implementar capacidade `drivers.transfer_operator` exclusiva da conta proprietária e a máquina de estados de `DriverTransfer` descrita abaixo | admin service/API, audit/outbox | Staff/admin comum recebe 403; proprietário com step-up cria uma solicitação idempotente; transições inválidas ou stale retornam 409 |
| DRV-004 | Executar a transferência sob locks/versão: resolver bloqueios, encerrar vínculo/autorização/agenda da origem, revogar credenciais client-neutral, criar vínculo no destino sem copiar autorização, e gravar audit+outbox na mesma transação | driver/account/finance/logistics services | Concorrência tem um vencedor; retry tem efeito único; histórico permanece na origem; nova operação só é possível após opt-in explícito do destino |
| TEN-004 | Adicionar unicidades e FKs compostas de coerência tenant para membership, `StoreDriver`, `ScheduleEntry`, `Store`, `Turno`, `Order` e dependentes | migrations e modelos | Combinação operador A + objeto B falha no banco, não apenas no service |
| DRV-005 | Corrigir `get_company_drivers`, schedules, check-in e StoreDriver para membership ativo e tenant coerente | `db_api.py`, `api_operator.py`, `api_admin.py`, `api_driver.py` | List/create/schedule/check-in cross-tenant retornam 403/404 e não criam linha |

### 6.1 Máquina de estado obrigatória para transferência DRV

`DriverTransfer` é a autoridade do processo e guarda `id`, identidade, membership origem, operador destino, motivo redigido, estado, versão, idempotency fingerprint, ator/step-up, bloqueios e timestamps. Estados e únicas transições válidas:

| Estado | Entrada/saída permitida | Regra |
|---|---|---|
| `REQUESTED` | inicial; segue para `BLOCKED`, `READY` ou `CANCELLED` | Criado uma vez por `(owner, idempotency_key, fingerprint)` após lock da identidade e validação do membership atual |
| `BLOCKED` | volta a `READY` quando todos os bloqueios foram resolvidos; pode ir a `CANCELLED` | A lista de bloqueios é persistida e reavaliada; não existe override genérico |
| `READY` | segue para `COMMITTING` ou `CANCELLED` | Step-up continua válido e a versão do membership origem não mudou |
| `COMMITTING` | estado curto sob transação; segue somente para `COMPLETED` | Identidade, membership e solicitação ficam sob `SELECT ... FOR UPDATE`; timeout/erro antes do commit mantém o estado anterior por rollback transacional |
| `COMPLETED` | terminal | Membership antigo encerrado e novo membership ativo criado atomicamente, com audit/outbox persistidos |
| `CANCELLED` | terminal | Permitido apenas antes de `COMMITTING`; após `COMPLETED`, retorno ao operador anterior é **nova transferência**, nunca reescrita/rollback de histórico |

Política de bloqueio/resolução, sem transferência implícita de passivo:

- `Order`/entrega ativa bloqueia; deve concluir ou cancelar/reatribuir dentro do operador origem por comando próprio e ser reconciliada antes de `READY`.
- `Shift`/turno/check-in aberto bloqueia; deve ser encerrado na origem com timestamp do servidor e auditoria.
- Reserva/oferta/agendamento futuro da origem não migra: deve ser cancelado ou reatribuído na origem; `ScheduleEntry` futuro e `StoreDriver` antigo são encerrados no commit da transferência.
- `WithdrawalRequest` em estado não terminal bloqueia até pagar, rejeitar ou cancelar com reconciliação; saque não é levado ao destino.
- Wallet/ledger divergente bloqueia. Saldo e história permanecem na origem; `READY` exige reconciliação zero e saldo liquidado ou obrigação explicitamente compensada/aprovada — nunca edição/reatribuição de lançamento.
- O novo membership nasce ativo porém sem lojas, escalas ou privilégios copiados. Cada `StoreDriver`/autorização nova exige opt-in explícito e auditado do operador destino antes de trabalhar.
- No mesmo commit, revogar famílias access/refresh, sessões, device/session registry e credenciais Fast Lane client-neutral. Efeitos externos/notificações saem somente por outbox idempotente após commit.
- A transação grava `AuditEvent` append-only e evento outbox com origem/destino, ator, motivo, blockers resolvidos, correlation ID e versões, sem CPF completo. Falha de publicação reprocessa a outbox; não desfaz nem repete a transferência.
- Duas solicitações concorrentes bloqueiam a mesma identidade; índice parcial + versão compare-and-swap garantem um vencedor. Chave repetida com fingerprint igual devolve o resultado; fingerprint diferente recebe 409; tentativa stale nunca encerra o membership novo.

### Migração de dados de motoboy

1. Normalizar CPF/telefone sem ainda impor unicidade.
2. Relatar nulos, duplicados e conflitos de operador sem expor documento completo.
3. Resolver conflitos com decisão do proprietário; não escolher automaticamente por “última atualização”.
4. Criar identidades e memberships históricos.
5. Backfill de referências e constraints `NOT VALID`.
6. Validar constraints, ativar unicidade parcial e só então trocar writes.
7. Retirar mudança direta de `Driver.operator_id` e scripts de suporte equivalentes.

### Gate G1

- Matriz real de dois tenants passa na API, ORM e SQL com o papel de produção.
- Refresh token como bearer retorna 401.
- Nenhum payload/header/localStorage altera tenant efetivo.
- Convite one-time/expiração/anti-reuso e revogação de sessão passam; o contexto server-authoritative de ID-004 está publicado antes de qualquer integração UI.
- CORS de API/edge de ID-006 passa a matriz de origem/método/header em G1; S5 apenas consome o contrato e adiciona controles de browser.
- A mesma pessoa não recebe dois vínculos ativos sob concorrência.
- Apenas a conta proprietária transfere; a ação é idempotente, auditada e preserva histórico.
- Todas as relações críticas rejeitam combinações cross-tenant no banco.

---

## 7. Etapa S2 — Schema consolidado, API, logística e dados duráveis

**Objetivo:** consolidar conteúdo/bootstrap/upgrade sobre a autoridade de migrations já instalada e substituir rotas duplicadas por serviços transacionais canônicos.
**Dependência:** G1 e `MIG-000`; esta etapa não recria runner, ledger, roles ou baseline.

### Pacotes de trabalho

| ID | Implementação | Evidência de aceite |
|---|---|---|
| SCH-001 | Consolidar migrations de negócio na autoridade de `MIG-000`; provar bootstrap vazio, upgrade de snapshots representativos e staging com o mesmo schema | Banco vazio, snapshots N-1 e staging terminam com o mesmo schema lógico, migration head/checksums válidos e drift zero |
| SCH-002 | Implementar auditorias de RLS, grants, owners, constraints, índices e migration head, além do ciclo expand/backfill/switch/contract | Preflight falha em diferença ou DDL destrutivo na janela; backfill é reentrante/verificável e contract só libera após N-1 drenado |
| SCH-003 | Provar compatibilidade de aplicação/schema `N/N-1` e rollback por classe; alimentar `min_schema`/`max_schema` no release manifest | Binários N e N-1 passam smoke/read/write no schema expandido; cada classe de migration tem drill e artefato de rollback/compensação aprovado |
| API-001 | Definir services canônicos para usuários, lojas, motoboys, pedidos, lançamentos e configurações | API v1 e adapters chamam o mesmo service; não há regra duplicada em router |
| API-002 | Tornar adapters legados read-only durante retirada; remover writes após telemetria zero | Write legado retorna 410/405; dashboards confirmam zero consumidor antes da remoção |
| API-003 | Padronizar erros 401/403/404/409/422/500, correlation ID e redaction | Exceção inesperada retorna 500 genérico e é localizável sem `str(exc)` ou PII |
| API-004 | Centralizar normalização/validação de CPF em um único serviço usado por toda entrada web/API/importação | Tamanho, caracteres, repetição e dígitos inválidos retornam 422 mascarado; busca/uniqueness usam valor normalizado e nenhuma rota contorna o serviço |
| IDEM-001 | Guard de idempotência durável em PostgreSQL para mutações críticas | Mesma chave/corpo repete resposta; corpo diferente retorna 409; crash antes/depois do commit não duplica |
| AUD-001 | `AuditEvent` append-only tenant-scoped para privilégios, transferências, pedidos, provas e finanças | Update/delete/cross-tenant de audit falham; secret/CPF/header não aparecem |
| LOG-001 | Criar order+stops em uma transação; remover criação não atômica do painel | Falha no segundo stop deixa zero order órfã; retry deixa exatamente uma order |
| LOG-002 | Implementar, por D-INGEST-01, quatro máquinas independentes para preparação, oferta, entrega e parada, com locks e mapeamento externo versionado; nenhuma transição de uma máquina avança implicitamente outra | Estados/transições nominais de D-INGEST-01 têm tabela e testes próprios; inválida/out-of-order/concorrente falha e um único vencedor é persistido sem descarte silencioso |
| LOG-003 | Validar escala, StoreDriver, check-in, turno e geofence com membership/tenant | Loja/turno/motoboy de tenants diferentes nunca formam Schedule/Shift |
| LOG-004 | Implementar D-INGEST-02: política de prova versionada por tipo/risco, decisão server-side e storage privado; `requiresPin` exige PIN hasheado+foto e stop comum exige ao menos uma evidência autorizada | Matriz por política aceita somente conjuntos autorizados; omitir PIN ou foto em stop sensível falha; arquivo inválido/cross-tenant/URL expirada falha |
| GEO-001 | Implementar D-INGEST-03: incidente GPS auditável, aviso, exclusão da geofence e bloqueio de comandos em alto risco; workflow de contestação/falso positivo com prazo/SLA, evidências, decisão por staff da mesma tenant e motivo | Testes cobrem detecção, contestação dentro/fora do prazo, evidência insuficiente, deferimento/indeferimento e desbloqueio; timeout nunca autoaprova e todo resultado é imutavelmente auditado |
| OFF-001 | Comandos offline server-side com lease, causalidade, replay e DLQ | Cada comando termina em APPLIED, CONFLICT, DEAD_LETTER ou PENDING reconciliado; efeito único |
| DATA-001 | Migrar provas, documentos, remessas e anexos para storage privado durável | 2xx só após durabilidade; tipo/tamanho/checksum/antivírus; URL assinada e tenant-scoped |
| DATA-002 | Proibir `MEDIA_ROOT` local como storage de produção e serving pelo Django | Preflight de produção falha se `SERVE_MEDIA` ou storage local estiver ativo |
| STUB-001 | Inventariar mocks/no-op/200 sem persistência em backend e painel | Cada stub é implementado, retorna 501/410 explícito ou sai da UI/contrato |
| PERF-001 | Modelar relação Driver↔Vehicle e corrigir N+1/veículo “primeiro do operador” | Cada driver recebe seu veículo; query count tem budget automatizado |

### Gate G2/G3

- Bootstrap/upgrade/drift de schema passam.
- Compatibilidade N/N-1, manifesto min/max schema e drills de rollback por classe passam sem `DROP`/`RENAME` na janela.
- Escritas críticas existem em um único service e são idempotentes.
- Zero order/stop órfão e zero combinação cross-tenant.
- Provas/arquivos são privados e duráveis.
- Estados logísticos, escalas, geofence e offline são recuperáveis após crash/Redis loss.

---

## 8. Etapa S3 — Integridade financeira e webhook PIX

**Objetivo:** nenhum estado financeiro muda sem autenticidade, autorização, idempotência e reconciliação.
**Dependência:** G2/G3. `FIN-001`, `FIN-002` e `FIN-003` permanecem bloqueados até `EFI-000` passar; enquanto isso, o endpoint público continua deny-all no edge.

### Pacotes de trabalho

| ID | Implementação | Evidência de aceite |
|---|---|---|
| EFI-000 | Executar spike no contrato oficial **vigente** da Efí e congelar `docs/contracts/efi-pix-webhook.yaml` com URL/checksum/data da documentação, produto/versão, sandbox e fixtures oficiais; decidir mTLS/assinatura, ponto de terminação TLS, cadeia de certificado, trusted proxy, preservação de raw bytes, credencial/auth, janela de timestamp, replay key, content-type e body limit | Gate produz captura/checksum da fonte oficial, chamada sandbox registrada e fixtures oficiais positivas/negativas; teste prova que proxy não forja identidade do cliente e que raw bytes chegam inalterados. Campo desconhecido mantém a rota deny-all e reprova `EFI-000` |
| FIN-001 | Dependendo de `EFI-000`, implementar exatamente o mecanismo congelado de autenticidade Efí, validando conexão/certificado/assinatura e bytes brutos antes do parse | Sem autenticidade válida, trusted proxy, timestamp aceitável e replay key inédita, resposta é 401/403 e zero estado muda; body acima do limite é rejeitado no edge |
| FIN-002 | Dependendo de `EFI-000` e `FIN-001`, criar inbox idempotente com fingerprint, status, attempts, raw envelope cifrado/protegido e projeção redigida | Mesmo evento processa uma vez; fixtures oficiais passam; payload adulterado/repetido/parse inválido não duplica efeito nem vaza o envelope |
| FIN-003 | Dependendo de `EFI-000`, `FIN-001` e `FIN-002`, resolver `txid/e2eId` por tenant/provider e reconciliar com consulta remota antes de transição ambígua | Identificador de outro tenant não casa; divergência abre incidente, não marca `PAID` |
| FIN-COMP-001 | Implementar exatamente as duas fórmulas simbólicas de D-INGEST-04, incluindo resolução de versão por data operacional, faixas/elegibilidade/arredondamento e snapshot dos inputs; contrato seleciona um único modelo e intervalo não sobreposto | Fixtures congelam fórmulas, rounding, faixas e bordas de vigência; contrato sem modelo, com dois modelos, versões sobrepostas ou composição implícita falha; replay/concorrência produz uma compensação idempotente e ledger balanceado |
| FIN-004 | Tornar BaaS fail-closed; mock somente por fixture/injeção explícita em teste | Produção sem certificado/credencial aborta e alerta; nunca retorna PIX simulado |
| FIN-005 | Remover lançamento manual direto `APPROVED`; implementar maker-checker e creator XOR | Maker não aprova próprio lançamento; approve/reject concorrente tem um vencedor |
| FIN-006 | Consolidar settlement, carteira e ledger double-entry consumindo somente o resultado versionado de `FIN-COMP-001`, com referências únicas | 2–20 concorrências/replays geram um settlement; soma débitos=créditos e o registro preserva modelo, versão, vigência e inputs da fórmula |
| FIN-007 | Endurecer saque, remessa, CNAB e arquivos associados | PROCESSING sempre aponta para artefato durável; linha duplicada/truncada/fora de ordem não duplica payout/refund |
| FIN-008 | Criar `reconcile_finance --check` e alarmes de mismatch | Antes de liberar dinheiro real: diferença R$0, imbalance 0 e zero saque órfão |
| FIN-009 | Redigir logs financeiros e aplicar retenção/acesso mínimo | Logs não contêm payload PIX bruto, chave completa, documento ou segredo |

### Gate G5

- `EFI-000` está `PASS`, com versão/checksum do contrato oficial, sandbox, trust boundary TLS/mTLS/proxy, limites e fixtures congelados; qualquer mudança da Efí invalida a evidência e reabre o gate.
- Webhook forjado, antigo, repetido ou de outro tenant não altera estado.
- BaaS sem configuração válida falha fechado.
- D-INGEST-04 passa para ambos os modelos, com escolha exatamente única, fórmula/versionamento/vigência auditáveis e nenhuma combinação implícita.
- Maker-checker, settlement e saque passam concorrência/replay.
- Ledger e provedor reconciliam em zero antes de dinheiro real.

**Rollback financeiro:** pausar payouts/aprovações; preservar inbox/ledger; corrigir apenas por lançamento compensatório e reconciliação. Nunca excluir ou reescrever história.

---

## 9. Etapa S4 — Filas, integrações, Redis e Fast Lane

**Objetivo:** eventos e telemetria sobrevivem a crash, replay, backpressure e perda do Redis.
**Dependência:** G5 e services canônicos da etapa `S2`.

### Pacotes de trabalho

| ID | Implementação | Evidência de aceite |
|---|---|---|
| QUE-001 | Outbox com claim/lease, ACK pós-commit, retry exponencial, DLQ e reclaim | Kill em claim/envio/commit/ack não perde evento nem duplica efeito |
| QUE-002 | Inbound registry por provider, verificação de assinatura em bytes brutos e replay guard | Provider/timestamp/assinatura inválidos falham antes do domínio |
| QUE-003 | Separar envelope bruto protegido de projeção redigida de auditoria | Sentinels de segredo/PII não aparecem em logs, métricas ou audit projection |
| QUE-004 | Fast Lane com autenticação, limites de tamanho/taxa, bounds e freshness | Flood, coordenada inválida e timestamp stale são rejeitados e medidos |
| QUE-005 | Substituir filas Redis sem limite por Streams/ACK ou mecanismo equivalente com cap/backpressure/DLQ | Burst não cresce indefinidamente; pending e oldest-age são observáveis |
| QUE-006 | Registry de filas Celery, pools separados, `acks_late`, `reject_on_worker_lost`, time limits e beat singleton | SIGKILL reenvia mesma chave e efeito continua único; unacked/stale retornam a zero |
| QUE-007 | Comando de reconstrução/reconciliação do estado derivado Redis | Perda total do Redis não perde negócio nem recria segredo/token sensível |
| INT-001 | Integrações externas chamam services canônicos e versionam mapeamento de estado | Evento duplicado/out-of-order não força transição silenciosa |
| PLAT-REDIS-001 | Exigir autenticação e TLS do Redis conforme o failure domain; retirar URL externa plaintext e fallback em memória de staging/produção | Startup/preflight rejeita credencial ausente, certificado inválido, endpoint externo sem TLS e fallback local; rotação de credencial mantém filas reconciliadas |

### Gate G6

- Outbox/inbound/telemetria passam fault injection.
- DLQ, retry, queue age, pending e stale possuem alertas e runbook.
- Redis é reconstruível a partir do PostgreSQL.
- Nenhum provider contorna tenant, idempotência ou state machine.

---

## 10. Etapa S5 — Painel web seguro e completo

**Objetivo:** o frontend não amplia privilégios, não depende de stubs e continua operável sob falhas reais.
**Dependências:** `S5A` depende de G1 e dos contratos G2/G3 congelados, podendo avançar em paralelo a S3; `S5B` depende explicitamente de G5 e G6. Gate Web só fecha após ambas.

- **S5A — frontend independente:** estado/UI, cookies/sessão conforme contrato, ErrorBoundary, loading/erro, acessibilidade, splitting e testes locais/contratuais sem exigir provider/filas/finanças reais.
- **S5B — integração e E2E:** tenant/session real, CSRF/CSP no deploy, mutações críticas e jornadas E2E contra backend/filas/finanças reais após `S3 → G5 → S4 → G6`.

### Pacotes de trabalho

| ID | Implementação | Evidência de aceite |
|---|---|---|
| WEB-001 | `S5A`: retirar access/refresh sensíveis de `localStorage`; consumir o contrato de sessão segura de S1 com CSRF/SameSite | Script XSS não lê token; testes locais/contratuais cobrem refresh/logout/revogação sem redefinir auth no frontend |
| WEB-002 | `S5B`: implementar troca de operador consumindo ID-004; armazenamento/header é apenas preferência de UI | Usuário sem membership recebe 403; UI exibe exclusivamente tenant/capabilities devolvidas pelo backend |
| WEB-003 | `S5B`: aplicar CSP, anti-clickjacking, referrer/permissions policy e integrar CSRF no browser/deploy; CORS server-side já foi fechado por ID-006 em G1 | CSP report/test e CSRF passam; origem indevida continua negada pelo contrato G1 sem regra duplicada no frontend |
| WEB-004 | `S5A`: remover ações stub/no-op e alinhar estados de loading/erro | Falha contratual/de rede não vira sucesso nem spinner infinito; retry/logout são acessíveis |
| WEB-005 | `S5A`: ErrorBoundary e correlation ID visível ao suporte sem stack/PII | Teste de componente/contrato exibe fallback acessível e ID, sem revelar detalhes |
| WEB-006 | `S5A`: code splitting por rota e budget de bundle | Build falha se chunk principal ultrapassar budget aprovado; rotas pesadas carregam sob demanda |
| WEB-007 | `S5B`: testes de integração/E2E de auth, tenant, usuários, motoboys, corridas, filas e finanças | Após G5/G6, fluxos críticos passam contra backend real de staging/PostgreSQL/Redis/providers sandbox |

### Gate Web

- Sessão não é recuperável por JavaScript comum.
- Troca de tenant é server-authoritative.
- Zero ação crítica depende de mock ou endpoint que não persiste.
- E2E de dois tenants e papéis passa.
- Budgets de bundle e acessibilidade estão no CI.

---

## 11. Etapa S6 — Qualidade, observabilidade e plataforma de deploy

**Objetivo:** formar um release candidate reproduzível, observável e bloqueado por testes reais.
**Dependência:** G5, G6 e Gate Web.

### Pacotes de trabalho

| ID | Implementação | Evidência de aceite |
|---|---|---|
| QA-001 | Zerar Ruff, alinhar Pyright/runtime e registrar/reduzir warnings de pytest | `ruff`, typecheck e pytest saem 0; budget de warnings impede regressão |
| QA-002 | Executar backend em PostgreSQL/PostGIS e Redis reais; cobrir `managed=False`, RLS e concorrência | Serviços do CI são efetivamente usados; sete skips críticos são eliminados ou justificados com owner/prazo |
| CI-HERM-001 | Bloquear egress nos testes e detectar import side effects, sem reutilizar o ID mobile histórico `QA-003` | Suite completa não resolve DNS nem abre socket externo; import/collection produz zero efeito fora do processo |
| QA-004 | Adicionar tests de regressão nomeados para cada P0/P1 do laudo | Matriz de cobertura mostra teste, comando e evidência por finding |
| QA-005 | SAST, SCA, secret scan, image scan, SBOM e provenance | High/critical ou segredo ativo bloqueia RC |
| DEP-000 | Congelar um único modo real de build/deploy/traffic switch/rollback e os contextos Docker canônicos; caminhos duplicados não referenciados são removidos ou bloqueados por lint | Manifesto declara exatamente um Dockerfile/contexto por imagem e prova canário/rollback no modo escolhido; estado `UNPROVEN` bloqueia `S7` |
| IMG-BACKEND-001 | Endurecer o Dockerfile backend canônico (`Dockerfile`, na raiz para compatibilidade com o EasyPanel): builder separado, runtime mínimo sem toolchain, base por digest, dependências Python lockadas/com hashes, UID/GID não-root e entrypoint sem migration | Dois builds isolados, limpos e `--pull --no-cache` do mesmo SHA passam smoke/readiness como non-root e filesystem read-only; grafo de dependências, SBOM e materiais de provenance normalizados são equivalentes; scan HIGH/CRITICAL e artefatos ficam vinculados a cada digest |
| IMG-FASTLANE-001 | Endurecer o Dockerfile Fast Lane canônico (`backend/fast_lane/Dockerfile`) com os mesmos controles e somente módulos runtime necessários | Dois builds isolados, limpos e sem cache do mesmo SHA não contêm compiler/cache/testes/segredos, rodam como non-root e têm grafo de dependências, SBOM e materiais de provenance normalizados equivalentes; health/shutdown, smoke e scan passam por digest |
| IMG-FRONTEND-001 | Endurecer `frontend/Dockerfile`: build/runtime multi-stage, `npm ci` com lockfile, base por digest, runtime estático/mínimo e usuário não-root, sem devDependencies/toolchain no runtime | Dois builds isolados, limpos e sem cache do mesmo SHA têm grafo de dependências, SBOM e materiais de provenance normalizados equivalentes; servidor responde assets/health como non-root e scan e budget de tamanho passam |
| DEP-002 | Provar reprodutibilidade das três imagens: executar dois builds isolados e sem cache por imagem no mesmo SHA, normalizar somente metadados voláteis documentados e comparar grafo de dependências, SBOM e materiais de provenance por conteúdo | Relatório machine-readable para backend, Fast Lane e frontend termina com `images_checked=3, dependency_graph_diff=0, sbom_content_diff=0, provenance_material_diff=0`; qualquer divergência não justificada bloqueia o RC |
| DEP-STATIC-001 | Alinhar `STATIC_ROOT`, volume/Nginx e smoke de admin static, sem reutilizar o requisito canônico `DEP-002` | `/static/admin/...` retorna 200 no container real |
| DEP-003 | Criar adapters tipados de Auth e Storage nas fronteiras externas; ausência/erro de client, upload incompleto ou confirmação inválida falha consistentemente e nunca confirma sessão, prova ou remessa inexistente | Contract tests executam adapter real/fake explícito; client ausente, timeout, 4xx/5xx e resposta malformada retornam erro tipado/fail-closed sem linha/estado de sucesso |
| DEP-INIT-001 | Remover migrations/warmup/collectstatic do processo web; job one-shot e lockado, sem reutilizar o ID `DEP-003` | Duas réplicas sobem sem disputar migration; falha do init job impede traffic shift |
| DEP-004 | Unificar Compose/EasyPanel em uma fonte; gerar manifests por ambiente | Diff gerado é determinístico; serviço/nome/origem não divergem |
| DEP-005 | Health/liveness/readiness, restart, graceful shutdown, limites e log rotation | Falha de DB/Redis/storage remove readiness; processos reiniciam sem efeito duplicado |
| DEP-006 | Nginx com `X-Forwarded-Proto`, trusted proxy, HSTS gradual, body/rate/timeouts e headers | Sem redirect loop; uploads e abuso respeitam limites; check de headers passa |
| DB-001 | Orçamento de conexões por processo, pool/PgBouncer, `statement_timeout` e `idle_in_transaction_session_timeout` | Teste de exaustão não derruba DB; conexão total fica sob limite com margem aprovada |
| OBS-001 | Correlation ID request→task→provider; logs JSON redigidos | Evento canário é rastreável sem segredo/PII |
| OBS-002 | Métricas e alertas de API, DB, RLS denial, Redis, filas, outbox, finanças, storage e deploy | 3/3 canários detectados ≤5 min e reconhecidos ≤10 min |

### Gate G7

- CI hermético e verde no mesmo SHA.
- Tenant, concorrência, webhook, Redis loss, upload e bootstrap real estão cobertos.
- Os três Dockerfiles canônicos são multi-stage, pinados, mínimos e non-root; **cada uma das três imagens** passa dois builds isolados/limpos/sem cache do mesmo SHA, smoke/scan e comparação normalizada de grafo de dependências, SBOM e materiais de provenance sem divergência.
- Readiness e alertas foram provocados, não apenas configurados.
- Nenhum job, manifesto ou gate mobile existe no RC.

---

## 12. Etapa S7 — Staging, recuperação, capacidade e deploy imutável

**Objetivo:** provar o mesmo RC sob restauração, falhas, carga e rollback automático.
**Dependência:** G7.

### Pacotes de trabalho

| ID | Implementação | Evidência de aceite |
|---|---|---|
| REL-001 | Gerar release manifest com SHA, três image digests, migration head/checksums, `min_schema`/`max_schema`, SBOM, provenance e release anterior | Campo ausente/adulterado, SHA misto, schema fora do intervalo ou tag `latest` falha fechado |
| REL-002 | Deploy por digest com migration job, ambiente inativo, smoke e canário 5% | O digest testado é o digest servido; nenhuma imagem é reconstruída |
| REL-003 | Rollback automático por readiness/SLI ao digest anterior, respeitando compatibilidade N/N-1 e a classe de migration | Falha injetada retorna sem rebuild; release anterior inicia no schema expandido e preserva schema/outbox/ledger; classe não reversível bloqueia traffic shift |
| CAP-000 | Antes de qualquer ensaio `LOAD-*`, congelar `ops/capacity/workload-contract.v1.yaml`: RPS e concorrência por rota/job, mix percentual, payload/tamanho, dataset e cardinalidades, tenants, duração/burst, topologia/réplicas/recursos, latência de rede, quotas/rate limits dos providers, SLIs e error budget | Schema/validador do contrato passa, percentuais somam 100%, quotas têm fonte/data/owner e o harness grava checksum do contrato; mudança de contrato invalida resultados anteriores. `LOAD-001/002` recusam execução sem `CAP-000 PASS` |
| DR-001 | PITR/restore PostgreSQL em destino isolado e reconcile pós-restore | RPO ≤5 min e RTO ≤60 min como metas iniciais |
| STO-RPO-000 | Registrar em `ops/dr/storage-rpo-decision.yaml` os failure domains (processo/nó, AZ, região, conta e provedor), semântica do 2xx, versionamento/immutability, retenção, replicação cross-zone/cross-region/cross-account, lag mensurável e alvo RPO/RTO aprovado por domínio | Gate reprova `RPO=0` para domínio não coberto por confirmação síncrona independente; decisão possui owner/aprovador, evidência contratual e teste de perda por domínio. Sem decisão aprovada, G8 permanece fechado |
| DR-002 | Exercitar backup/restore de storage com checksum e inventário segundo `STO-RPO-000` | Perda de nó/AZ e delete/overwrite restauram dentro do alvo aprovado; perda de região/conta/provedor mede o lag real e atende o RPO aprovado — sem promessa genérica de RPO 0; RTO medido e inventário reconciliado |
| DR-003 | Perda total do Redis e rebuild | RPO 0 de negócio e RTO ≤15 min |
| DR-004 | Recovery de outbox/inbound/DLQ/providers | RPO 0 e recovery ≤30 min |
| LOAD-001 | Dependendo de `CAP-000`, executar carga API/DB/filas/storage/finanças pelo tempo e fator definidos no workload contract | Zero leak/duplicação/mismatch; p95/p99/5xx e consumo de error budget dentro do contrato aprovado |
| LOAD-002 | Dependendo de `CAP-000`, executar perfil de telemetria contínuo/burst definido no workload contract | Perda 0, duplicação 0, lag/pending/recuperação e quotas permanecem dentro dos limites versionados |
| RUN-001 | Exercitar runbooks de deploy, rollback, incidente, provider, segredo, DB, Redis, storage e finanças | Cada runbook registra owner, precondição, abort, compensação e resultado |

### SLOs iniciais de release

Devem ser aprovados no artefato `CAP-000` antes do teste; até então são hipóteses e não evidência de capacidade:

- API p95 ≤400 ms, p99 ≤1 s e 5xx ≤0,5% no perfil contratado.
- Error budget de rollout ≤25% do orçamento aprovado.
- Queue age e pending dentro dos limites definidos por domínio.
- Zero vazamento de tenant, duplicidade financeira, perda durável ou prova órfã.

### Gate DEP/G8-Sistema

- Bootstrap, upgrade, restore, Redis loss, carga e rollback passam no mesmo RC.
- `CAP-000` está aprovado e o harness registra seu checksum; nenhum resultado de carga órfão é aceito.
- `STO-RPO-000` define o failure domain e o RPO de storage aprovado; G8 não assume RPO 0 fora do que foi tecnicamente provado.
- Migration falha antes do traffic shift.
- Readiness retira instância defeituosa.
- Rollback volta ao digest anterior sem rebuild e sem divergência.

---

## 13. Etapa S8 — Homologação, piloto técnico e rollout

**Objetivo:** liberar somente o sistema web/API, dentro do limite de escopo declarado.
**Dependência:** G8-Sistema.

### 13.1 HOM-001 — Homologação

- Repetir matriz de dois tenants, RLS, autenticação, finanças, storage, Redis loss e rollback.
- Confirmar SHA/digests/migrations do manifesto ativo.
- Validar restore e RPO/RTO.
- Proibir mudança de código/config/dependência após congelar RC; qualquer mudança cria novo RC.

### 13.2 HOM-002 — Piloto técnico de sete dias

- Duas tenants e 5–10 identidades controladas.
- Operações via painel, API v1 e harness autorizado; nenhuma dependência de APK/dispositivo.
- Provider habilitado um por vez.
- Fluxos: criação, atribuição, início, chegada, prova, conclusão, settlement, webhook e payout controlado/sandbox.
- Reconcile diário de orders/stops/proofs/ledger/withdrawals/outbox/filas/storage.
- Zero Sev-1, tenant leak, webhook forjado aceito, perda durável ou mismatch financeiro.
- SLIs aprovados em pelo menos 99% das janelas.

### 13.3 HOM-003 — Rollout do mesmo RC

1. 5% por pelo menos 60 min e 500 operações.
2. 25% por pelo menos 4 h e 2.000 operações.
3. 50% por pelo menos 24 h e 10.000 operações.
4. 100% por pelo menos 72 h e 20.000 operações.

Cada estágio exige reconcile zero, SLIs aprovados, queue age estável e error budget ≤25%. Falha aciona rollback/pause automático de tráfego, provider, payouts ou writes conforme o domínio; não há override manual para continuar a contagem.

### Gate G9/G10-Sistema

- Piloto e rollout usam o mesmo SHA/digests/migrations.
- Zero invariante crítica violada.
- Rollback automático foi exercitado antes do primeiro estágio e durante fault injection.
- Evidência machine-readable registra todas as decisões.

---

## 14. Etapa S9 — Pós-go-live e escala

**Início:** somente após 30 dias completos sem Sev-1, tenant leak, mismatch financeiro ou perda durável.

### Pacotes

| ID | Implementação | Evidência de aceite |
|---|---|---|
| SCL-001 | Reexecutar o workload contract aprovado com 2× o pico observado e autoscaling por latência, conexão, CPU/memória e queue age | Harness, dashboard e manifestos comprovam SLIs/error budget sem leak, perda ou saturação fora do limite |
| SCL-002 | Criar read models paginados, tenant-scoped e reconstruíveis; medir planos de query/índices com dataset representativo | Freshness e query budget passam; rebuild não bloqueia writes core nem cruza tenant |
| HUB-000 | Homologar Delivery Direto como provider piloto com sandbox autenticado, crash/replay, reconciliação e soak 24 h | Diff de reconciliação zero e disable/rollback exercitado fecham GH1 |
| HUB-001 | Implementar registry/capabilities DB-first para os providers homologados | Nenhum provider não homologado/seeded ativa; caminho não usa `if/elif` por provider |
| HUB-003 | Isolar fila/pool/OAuth single-flight, versões, fixtures, changelog e depreciação por provider | Falha/limite de um provider não degrada outro e alerta antes de depreciação |
| HUB-002 | Habilitar novos providers um por vez com documentação, sandbox, contract/load, reconciliação, SLO e rollback próprios | Cada onboarding tem gate independente e pode ser desabilitado sem afetar o núcleo |

### Gate GH1

- Benchmark sustenta 2× o pico observado.
- Read models respeitam freshness e query budget.
- Provider passa assinatura, replay, crash/recovery, reconcile e disable/rollback.

---

## 15. Matriz de rastreabilidade da perícia

| Achado | Pacotes responsáveis | Gate |
|---|---|---|
| P0-01 RLS bypass | TEN-001, TEN-002 | G1 |
| P0-02 refresh como access | AUTH-001, AUTH-002 | G1 |
| P0-03 IDOR/RBAC legado | EDGE-CONTAIN-001, IR-003, TEN-003, API-001/002 | G0/G1/G2 |
| P0-04 propriedade de motoboy | DRV-001 a DRV-005 | G1 |
| P0-05 coerência cross-tenant | TEN-004, LOG-003 | G1/G3 |
| P0-06 webhook PIX | EDGE-CONTAIN-001, EFI-000, FIN-001 a FIN-003 | G0/EFI/G5 |
| P0-07 segredos/scripts | IR-001/002/005, CI-HERM-000/001, QA-005 | G0/G7 |
| P0-09 deploy inconsistente | DEP-000/002–006, IMG-BACKEND-001, IMG-FASTLANE-001, IMG-FRONTEND-001, REL-001/002 | G7/G8 |
| P0-10 release gate inseguro | QA-001/002/004/005, CI-HERM-001 | G7 |
| P1-01 auth hardening | AUTH-002/003, IR-004 | G1 |
| P1-02 CORS/XSS/sessão | WEB-001/003 | Gate Web |
| P1-03 mock financeiro | FIN-004 a FIN-006 | G5 |
| P1-04 storage efêmero | DATA-001/002, DEP-003, STO-RPO-000, DR-002 | G3/G7/G8 |
| P1-05 migrations concorrentes | MIG-000, SCH-001/002/003 | G0/G2 |
| P1-06 orquestração sem saúde | DEP-INIT-001, DEP-005 | G7 |
| P1-07 conexões/timeouts | DB-001, LOAD-001 | G7/G8 |
| P1-08 Redis/Fast Lane | QUE-004 a QUE-007 | G6 |
| P1-09 observabilidade | OBS-001/002 | G7 |
| P1-10 DR não comprovado | DR-001 a DR-004, STO-RPO-000 | G8 |
| P1-11 painel não atômico | API-001/003, LOG-001 | G2/G3 |
| P1-12 biometria/admin/mídia | IR-005, ADM-001, AUTH-003, DATA-002, DEP-006 | G0/G1/G7 |
| P2-01 bundle web | WEB-006 | Gate Web |
| P2-02 lint/tipagem/warnings | QA-001/002 | G7 |
| P2-03 Vehicle/N+1 | PERF-001 | G3 |
| P2-04 stubs/no-op | STUB-001, WEB-004 | G3/Web |
| P2-05 containers/supply chain | QA-005, DEP-000/004, IMG-BACKEND-001, IMG-FASTLANE-001, IMG-FRONTEND-001 | G7 |
| P2-06 proxy/TLS | DEP-006 | G7 |
| P2-07 capacidade | CAP-000, LOAD-001/002 e etapa S9 | G8/GH1 |
| P2-08 drift documental | SYS-SCOPE-001, MIG-000, SCH-001, REL-001 | G0/G2/G8 |

**P0-08 foi excluído deliberadamente por ser o aplicativo mobile.**

---

## 16. Crosswalk dos 56 requisitos ativos

O prefixo lógico `req:` identifica requisitos de `.planning/REQUIREMENTS.md`; `pkg:` identifica pacotes deste plano. Isso evita que nomes históricos iguais, especialmente `FIN-*`, sejam interpretados como identidade automática. A tabela abaixo é **somente um índice humano agrupado**: ela não substitui, não gera implicitamente e não serve como prova dos 56 registros individuais de `.planning/system-scope-requirements.yaml`.

| Grupo de requisitos ativos (`req:`) | Qtde. | Pacotes responsáveis (`pkg:`) | Gate | Bundle de teste/evidência obrigatório |
|---|---:|---|---|---|
| `DOC-001`, `IR-001..005` | 6 | `SYS-SCOPE-001`, `PLAN-MANIFEST-001`, `IR-001..005`, `CI-HERM-000`, `EDGE-CONTAIN-001`, `ADM-001`, `MIG-000` | PLAN-S0/G0 | Validadores do catálogo, manifesto de PLANs e registro de owners; secret/history/cache/image scan; testes de promoção/revogação, token cutoff, egress e admin edge |
| `ID-001..006`, `QA-SEC-001` | 7 | `AUTH-001..003`, `ID-004..006`, `TEN-001..004`, `DRV-001..005` | G1 | `pytest -q backend/tests/security/test_auth_tenant_matrix.py backend/tests/security/test_invitation.py backend/tests/security/test_cors.py backend/tests/logistics/test_driver_transfer.py` com role runtime real e duas tenants |
| `SCH-001`, `API-001..005`, `AUD-001` | 7 | `MIG-000`, `SCH-001..003`, `API-001..004`, `IDEM-001`, `AUD-001` | G2 | `python backend/manage.py schema_preflight --manifest artifacts/schema/manifest.json`; `pytest -q backend/tests/schema backend/tests/api/test_idempotency.py backend/tests/audit` |
| `LOG-001..005`, `OFF-001` | 6 | `LOG-001..004`, `GEO-001`, `OFF-001`, `DATA-001/002`, `PERF-001` | G3 | Testes separados das quatro state machines D-INGEST-01, prova D-INGEST-02, contestação GPS D-INGEST-03, storage e offline |
| `FIN-001..005` | 5 | `EFI-000`, `FIN-COMP-001`, `FIN-001..009` | G5 | Webhook/CNAB/ledger + fixtures de fórmula/vigência para os dois modelos de D-INGEST-04; `reconcile_finance --check` |
| `QUE-001..006` | 6 | `QUE-001..007`, `INT-001`, `PLAT-REDIS-001` | G6 | `pytest -q backend/tests/queues backend/tests/integrations backend/tests/fast_lane`; fault harness de claim/commit/ACK/SIGKILL/Redis loss |
| `QA-001`, `QA-002`, `QA-004`, `OBS-001`, `DEP-000`, `DEP-002..004`, `FE-001` | 9 | `QA-001/002/004/005`, `CI-HERM-001`, `WEB-001..007`, `OBS-001/002`, `DEP-000`, `DEP-002..006`, `DEP-STATIC-001`, `DEP-INIT-001`, `IMG-BACKEND-001`, `IMG-FASTLANE-001`, `IMG-FRONTEND-001` | G7/Web | Backend real + frontend lint/typecheck/unit/contract/E2E; contract tests fail-closed dos adapters DEP-003; dois builds isolados/sem cache por imagem com grafo/SBOM/provenance equivalentes, smoke e scan; 3 canários |
| `DEP-001` | 1 | `REL-001..003`, `SCH-003`, `DEP-000`, `DEP-INIT-001`, `DEP-005/006` | DEP/G8-Sistema | `python scripts/release/verify_manifest.py artifacts/release/manifest.json`; deploy/canário/rollback por digest com N/N-1 |
| `HOM-001..003` | 3 | `HOM-001..003`, `DR-001..004`, `STO-RPO-000`, `CAP-000`, `LOAD-001/002`, `RUN-001` | G8/G9/G10-Sistema | Executar `python scripts/gates/run_system_gate.py --manifest artifacts/release/manifest.json --gate <gate>` uma vez para cada gate do grupo |
| `SCL-001/002`, `HUB-000/001/002/003` | 6 | `SCL-001/002`, `HUB-000/001/002/003`, `CAP-000` | GH1/pós-go-live | Capacity harness com checksum do workload contract; contract/replay/reconcile/soak/disable por provider |
| **Total** | **56** | **Catálogo deve expandir cada ID exatamente uma vez** | — | **Alegação 56/56 proibida enquanto o validador não retornar PASS** |

O catálogo machine-readable contém **exatamente 56 objetos, sem ranges, aliases ou registros agregados**. Cada objeto exige, no mínimo: `requirement_id`, `package_ids`, `depends_on_package_ids`, `gate_ids`, `test_ids`, `commands` e `evidence_paths`; `source_phase`, `owner`, `release_sha` e `status` completam a auditoria. Arrays não podem estar vazios salvo `depends_on_package_ids` para raiz explícita.

O CI compara os 56 `requirement_id` ao conjunto canônico `64 - {MOB-001..007, QA-003}`; valida IDs/pacotes/gates/testes conhecidos, dependência referenciada mas ausente, pacote desconhecido, auto-dependência, ciclo no DAG, dependência apontando para gate/wave posterior, comando vazio, evidence path duplicado/sem SHA e qualquer referência ativa a `mobile/**`. Ele também cruza `package_ids` e `depends_on_package_ids` com `.planning/system-plan-manifest.yaml`; divergência entre catálogo, manifesto e PLANs reprova `PLAN-S0`. Somente `PASS` dessa validação permite escrever “56/56”.

---

## 17. Estratégia de teste obrigatória

### 17.1 Pirâmide

- Unitários: validators, state machines, policy/role, calculations, serializers e redaction.
- Integração PostgreSQL/Redis: RLS, constraints, locks, idempotência, ledger, outbox e migrations.
- Contrato: OpenAPI, erros, idempotency key, providers e frontend.
- E2E web: auth, tenant, usuários, motoboys, transferência, lojas, escala, corrida e finanças.
- Fault injection: kill worker, perda Redis, provider timeout, storage down, DB saturation e rollback.
- Segurança: matriz cross-tenant, tokens, IDOR, webhook tamper/replay, upload e secret scan.
- Carga/soak: API, telemetry, queue, DB, storage e financeiro.

### 17.2 Regras do CI

- Rede externa negada por padrão.
- Banco PostgreSQL/PostGIS real e Redis real.
- Cada teste cria tenants sintéticos próprios.
- Nenhum skip de P0/P1 sem owner, justificativa e prazo.
- Warning budget monotonicamente decrescente até zero/allowlist explícita.
- Código, migration, config ou dependência alterados invalidam evidência de RC anterior.

---

## 18. Evidência, ownership e definição de concluído

Cada gate deve produzir manifesto machine-readable com:

- commit SHA e digests;
- migration head e checksums;
- ambiente e timestamp;
- comandos/suites executados;
- métricas e resultado;
- finding/requisito coberto;
- responsável técnico;
- artefato de rollback/compensação;
- redaction comprovada, sem segredo ou PII.

Como saída obrigatória de `PLAN-MANIFEST-001`, `ops/owners/system-readiness.yaml` resolve cada owner abaixo para **uma pessoa nominal**, substituto e contato; `scripts/ci/validate_system_owners.py` valida schema, referências e separação maker-checker, e qualquer owner não resolvido bloqueia o PLAN. Approver não pode substituir evidência técnica nem autoaprovar ação maker-checker.

| Owner exclusivo | Superfícies/pacotes | Evidência primária e comando canônico |
|---|---|---|
| `OWN-SCOPE-RELEASE` | `SYS-SCOPE-001`, `PLAN-MANIFEST-001`, catálogo, owners, gates e manifestos | `python scripts/ci/validate_system_scope.py --catalog .planning/system-scope-requirements.yaml --requirements .planning/REQUIREMENTS.md --plan-manifest .planning/system-plan-manifest.yaml`, `python scripts/ci/validate_system_owners.py --owners ops/owners/system-readiness.yaml --plan-manifest .planning/system-plan-manifest.yaml` e `python scripts/ci/validate_system_plan_manifest.py --manifest .planning/system-plan-manifest.yaml --catalog .planning/system-scope-requirements.yaml --plans-root .planning/phases` |
| `OWN-DATABASE` | `MIG-000`, `SCH-*`, grants/RLS, compatibilidade/rollback | `artifacts/schema/{drift-baseline,manifest,compatibility,rollback-drills}.json`; `python backend/manage.py schema_preflight --manifest artifacts/schema/manifest.json` |
| `OWN-IDENTITY` | `AUTH-*`, `TEN-*`, `DRV-*`, `/admin/` auth | JUnit tenant/transfer e probe admin; `pytest -q backend/tests/security/test_auth_tenant_matrix.py backend/tests/logistics/test_driver_transfer.py backend/tests/security/test_admin_edge.py` |
| `OWN-FINANCE` | `EFI-000`, `FIN-*`, CNAB/ledger/reconcile | `docs/contracts/efi-pix-webhook.yaml`, fixtures e reconcile; `pytest -q backend/tests/finance && python backend/manage.py reconcile_finance --check` |
| `OWN-ASYNC` | `QUE-*`, `INT-*`, Fast Lane/Redis | fault report e queue reconcile; `pytest -q backend/tests/queues backend/tests/integrations backend/tests/fast_lane` |
| `OWN-WEB` | `WEB-*` | JUnit/Playwright e bundle report; `npm --prefix frontend run lint`, `npm --prefix frontend run typecheck`, `npm --prefix frontend test`, E2E contra staging |
| `OWN-PLATFORM` | `DEP-*`, `IMG-*`, `OBS-*` | digests, scan, SBOM/provenance e canários; `docker buildx bake --pull --no-cache`, smoke non-root/read-only e scanner HIGH/CRITICAL por digest |
| `OWN-SRE-DR` | `STO-RPO-000`, `DR-*`, `CAP-000`, `LOAD-*`, `RUN-001` | `ops/dr/storage-rpo-decision.yaml`, `ops/capacity/workload-contract.v1.yaml`, restore/load reports; harness recusa contrato sem checksum/approval |
| `OWN-ROLLOUT` | `REL-*`, `HOM-*`, `SCL-*`, `HUB-*` | `artifacts/release/manifest.json` e gate reports; `python scripts/release/verify_manifest.py ...` e `python scripts/gates/run_system_gate.py ...` |

Os comandos acima são interfaces a serem criadas quando inexistentes; o PLAN que os introduz deve primeiro criar o teste/CLI e provar sua falha (RED), depois implementar o comportamento (GREEN). Cada execução grava stdout/JUnit/JSON sob `artifacts/evidence/<release_sha>/<gate>/<package>/`, nunca apenas captura manual ou afirmação em Markdown.

Uma tarefa só está concluída quando:

1. código/config/migration existe;
2. teste positivo e negativo passa;
3. rollback/compensação foi ensaiado quando aplicável;
4. observabilidade detecta a falha relevante;
5. evidência está ligada ao mesmo SHA do RC;
6. documentação/runbook foi atualizada.

---

## 19. Decomposição obrigatória em PLANs executáveis

Este plano mestre não deve virar um único prompt. `SYS-SCOPE-001 → PLAN-MANIFEST-001 → implementação` é uma sequência bloqueante em S0: nenhum executor recebe trabalho até todos os validadores de catálogo, manifesto e owners passarem. A tabela de famílias abaixo orienta a geração, mas não substitui `.planning/system-plan-manifest.yaml` nem autoriza execução.

### 19.1 Schema obrigatório do manifesto de PLANs

O manifesto possui `manifest_version`, checksum do catálogo individual, ordem de gates e uma lista `plans`. Cada registro de PLAN exige:

| Campo | Regra bloqueante |
|---|---|
| `id` | ID único e estável, usado em `depends_on` e no nome do `PLAN.md` |
| `primary_package_id` / `package_ids` | Pacote principal único e lista completa; todo pacote deste mestre aparece como principal exatamente uma vez ou possui justificativa explícita de coalescência no mesmo PLAN |
| `requirements` | IDs individuais existentes no catálogo, nunca faixa textual |
| `owner` | Um owner nominal resolvido em `ops/owners/system-readiness.yaml`; não vale “backend/time/equipe” |
| `files_modified` | Paths exatos e exclusivos na mesma wave; glob amplo, “arquivos relevantes” ou arquivo compartilhado sem dependência reprova |
| `depends_on` | Somente PLAN IDs existentes; grafo acíclico e dependência sempre em wave/gate anterior ou na mesma sequência explicitamente ordenada |
| `wave` / `gate` | Wave calculada pelo DAG e gate que o PLAN habilita ou fecha; não pode saltar G5 antes de S4 nem G6 antes de S5B |
| `tasks` | Lista com 2–3 tarefas; cada uma contém `name`, `files`, `action` determinística, `verify.automated`, `done` e `evidence_paths` |
| `verify` | Comando executável, ambiente/fixtures e exit code esperado; “testar manualmente” não basta |
| `done` / `evidence` | Verdade observável, artefatos sob SHA e rollback/compensação quando aplicável |

O manifesto deve conter ao menos um registro por pacote principal e ao menos um PLAN responsável por fechar cada gate. Actions resolvem previamente endpoint, interfaces, estados, fórmulas, migrations, flags, env vars, limites e estratégia de rollback; o executor não pode escolher arquitetura, omitir ramo ou “decidir durante implementação”. O validador compara manifesto↔catálogo↔PLANs, conta 2–3 tasks, detecta package/gate sem PLAN, ID/dependency desconhecido, ciclos, ordem gate/wave inválida, `files_modified` sobrepostos na mesma wave, requisito órfão e verify/done/evidence vazio.

| Wave/família de PLAN | Pacotes | Dependência e ownership exclusivo |
|---|---|---|
| `S0-W0-manifests` | `SYS-SCOPE-001 → PLAN-MANIFEST-001` | Únicos trabalhos permitidos antes de PLAN-S0; catálogo tem 56 registros individuais e o manifesto decide todos os PLANs |
| `S0-W1-containment` | `IR-001..005`, `CI-HERM-000`, `EDGE-CONTAIN-001`, `ADM-001`, `FINDINGS-001` | Só após PLAN-S0; separar Git/secrets/identidade/edge/admin por files e owner exclusivos |
| `S0-W1-migrations` | `MIG-000` | Só após PLAN-S0; `OWN-DATABASE` possui runner, ledger/grants e baseline; saída bloqueia qualquer PLAN TEN/DRV |
| `S1-W2-auth-tenant` | `AUTH-*`, `ID-004..006`, `TEN-*` | G0 + `MIG-000`; contexto server-authoritative, convite e CORS fecham em G1 antes da UI |
| `S1-W2-driver-transfer` | `DRV-*` | Contrato de membership/transfer após `MIG-000`; TDD dedicado para state machine, blockers, concorrência e idempotência |
| `S2-W3-schema-api-logistics` | `SCH-*`, depois `API/IDEM/AUD`, depois `LOG/GEO/OFF/DATA` | Bootstrap/upgrade precede consumidores; PLANs citam D-INGEST-01..03 e não compartilham services/migrations na mesma wave |
| `S3-W4-finance` | `EFI-000`, `FIN-COMP-001`, depois `FIN-001..009` | `EFI-000 PASS` bloqueia webhook; D-INGEST-04 bloqueia settlement; S3 fecha G5 antes de S4 |
| `S5A-W4-frontend-independent` | `WEB-001/004/005/006` | Pode paralelizar com S3 após G2/G3; sem integração real ou fechamento de Gate Web |
| `S4-W5-async` | `QUE/INT/PLAT-REDIS` | Dependência obrigatória de G5; fecha G6 antes de S5B |
| `S5B-W6-web-integration` | `WEB-002/003/007` | Depende de G5+G6 e fecha Gate Web; consome ID-004/006, não recria tenant/CORS |
| `S6-W7-quality-platform` | `CI-HERM/QA/OBS`, `DEP-*`, `DEP-INIT-001`, três `IMG-*` | Depende de G5+G6+Gate Web; um PLAN por imagem; DEP-003 é adapter, não init job |
| `S7-W8-release-dr-capacity` | `REL`, `DR/STO-RPO`, `CAP-000`, depois `LOAD` | Restore e workload contract paralelizam; `LOAD-*` depende de CAP-000; traffic shift depende de compatibilidade/rollback |
| `S8/S9-W9+` | `HOM-001 → HOM-002 → HOM-003`, depois `SCL/HUB` | Homologação/piloto/rollout sequenciais; pós-go-live aguarda 30 dias e GH1 |

Todo PLAN é gerado/validado contra o manifesto, declara `requirements` individuais, decisões D-INGEST aplicáveis, threat model e `SUMMARY.md` com comandos, exit codes e evidence paths. O checker rejeita PLAN não listado, divergente, com decisão em aberto, que reutilize `QA-003`, toque `mobile/**`, omita `MIG-000` antes de DDL TEN/DRV, execute S4 antes de G5, S5B antes de G6, FIN antes de `EFI-000`, carga antes de `CAP-000` ou declare storage RPO 0 sem failure domain provado.

---

## 20. Ordem imediata recomendada

1. Versionar e revisar o worktree atual por domínio, preservando a separação entre mudanças do usuário e correções desta perícia; gerar release SHA imutável somente após nova suíte verde.
2. Rotacionar a credencial exposta, sanear histórico/caches/clones/imagens e concluir **IR-001 a IR-005**; até lá nenhum segredo atual pode ser promovido.
3. Aplicar o runner canônico e todas as migrations em clone mascarado; depois executar upgrade em staging PostgreSQL/PostGIS com roles migrator/runtime distintas, preflight, constraints, RLS e rollback ensaiado.
4. Executar matriz E2E com proprietário, admin/gestor/operador/visualizador, lojista e duas tenants; cobrir usuários, motoboys, transferência, lojas, escala, pedidos, finanças, branding e webhook genérico.
5. Homologar o provedor de roteamento viário, comparar distância/preço contra rotas reais e substituir o método Haversine para faturamento definitivo; até lá o método permanece explícito e auditável, nunca silencioso.
6. Concluir **EFI-000**, mTLS/sandbox real, biometria e reconciliação financeira; dinheiro real permanece bloqueado até evento forjado/repetido/outro tenant produzir zero efeito.
7. Selecionar os primeiros PDVs/cardápios por demanda comercial; auditar licença e segurança dos repositórios candidatos, criar um adaptador por fornecedor e homologar contra sandbox/fixture oficial. Não anunciar plugin-and-play antes do gate individual.
8. Produzir imagens por digest com scan/SBOM/provenance; executar restore/PITR, carga/soak, observabilidade, piloto e rollout progressivo. O deploy público continua aguardando G7 e G8-Sistema.

---

## 20.1 Adição: Pacotes White-Label e Hub de Integrações (PDV/Cardápios)

Conforme especificação técnica vigente em `docs/architecture/WHITE_LABEL_E_INTEGRACOES.md`, foram incorporados ao sistema dois novos subsistemas essenciais para a operação comercial dos operadores logísticos:

| ID | Subsistema | Etapa | Dependência | Status | Estado comprovado |
|---|---|---|---|---|---|
| **WL-001** | White-Label | S2+ | G1 | IMPLEMENTADO LOCAL | Migration `operator_branding`, modelo Django e `slug` único com tratamento de legado; RLS depende de prova em PostgreSQL. |
| **WL-002** | White-Label | S2+ | WL-001 | IMPLEMENTADO LOCAL | API autenticada, leitura pública por slug e upload de imagem por conteúdo, tamanho e extensão; SVG não é aceito. |
| **WL-003** | White-Label | S5A | WL-002 | IMPLEMENTADO LOCAL | `BrandingContext`, CSS custom properties, reset entre tenants, favicon/título e login branded. |
| **WL-004** | White-Label | S5A | WL-003 | IMPLEMENTADO LOCAL | Personalização com preview, logo no shell e restrição por papel. |
| **WL-005** | White-Label | S5B | WL-004 | IMPLEMENTADO LOCAL | Branding em recibos/relatórios/PDF e **9 testes** específicos; faltam storage/CDN e E2E de staging. |
| **HUB-INT-001** | Hub Integrações | S2+ | G3 | IMPLEMENTADO LOCAL | Registry, logs, models e `BaseConnector`/`OrderIntent`, com migration e hardening tenant. |
| **HUB-INT-002** | Hub Integrações | S4+ | HUB-INT-001 | IMPLEMENTADO LOCAL | `GenericWebhookConnector` com HMAC-SHA256, limite/validação de payload, deduplicação e criação canônica de pedido. |
| **HUB-INT-003** | Hub Integrações | S4+ | HUB-INT-002 | **PARCIAL** | CRUD/logs estão implementados, mas somente `generic-webhook` é conector executável. Os demais registros do catálogo permanecem desabilitados e não homologados. |
| **HUB-INT-004** | Hub Integrações | S5B | HUB-INT-003 | IMPLEMENTADO LOCAL | UI de marketplace/configuração/auditoria existe, mas não transforma conectores ainda inexistentes em integrações funcionais. |
| **HUB-INT-005** | Hub Integrações | S9+ | HUB-INT-003 | ESTRUTURA APENAS | Base modular pronta para novos adaptadores; nenhum SDK/repositório de PDV proprietário foi integrado ou aprovado. |

O isolamento, a idempotência e o HMAC estão cobertos localmente para o webhook genérico. A alegação de “integração plugin-and-play com PDVs e cardápios” permanece **proibida** até cada fornecedor possuir adaptador real, licença auditada, gestão de credenciais, fixtures/contrato oficiais, sandbox, replay/reconciliação, observabilidade, runbook de desligamento e aceite E2E.

---

## 21. Decisão final

O plano já foi executado parcialmente no worktree atual, porém ainda precisa ser convertido em release auditável e passar pelos gates externos. As maiores adições e correções são:

- catálogo validável com 56 registros individuais, manifesto integral de PLANs bloqueante em S0 e namespace `S0..S9`, sem colisão com a fase/QA mobile histórica;
- autoridade mínima de migrations em `S0`, roles migrator/runtime separadas, expand/contract e compatibilidade N/N-1;
- identidade global e membership exclusivo de motoboy;
- transferência somente pelo proprietário, governada por state machine, blockers, opt-in, revogação, audit/outbox e concorrência;
- coerência tenant por FKs compostas;
- preservação nominal de D-INGEST-01..04 em state machines, prova, contestação GPS e remuneração/fórmulas versionadas;
- sequência inequívoca `S3 → G5 → S4 → G6`, com frontend S5A independente e integração S5B posterior aos gates;
- spike/gate `EFI-000` e proteção do webhook PIX conforme contrato oficial congelado;
- `/admin/` desabilitado ou restrito por canal privado com MFA e probe externo;
- conta de banco sem superuser/BYPASSRLS;
- testes herméticos, três imagens hardened e critérios explícitos de CI/deploy;
- workload contract `CAP-000` antes de carga e RPO de storage por failure domain aprovado;
- remoção completa das dependências mobile no grafo ativo.

Até esses itens e seus gates estarem verdes, o sistema permanece **NO-GO** para produção real multi-tenant.

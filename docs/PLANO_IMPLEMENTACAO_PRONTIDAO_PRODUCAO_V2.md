# Plano Mestre de Implementação — Prontidão de Produção V2

**Sistema:** Expresso Neves / NevesGo  
**Data-base:** 2026-08-11  
**Idioma:** português do Brasil  
**Natureza:** plano mestre independente, executável por humanos ou agentes  
**Fonte primária de risco:** `.planning/codebase/CONCERNS.md`  
**Plano histórico reconciliado:** `docs/PLANO_IMPLEMENTACAO_PRODUCAO.md`

> **AUTORIDADE DE EXECUÇÃO:** este V2 é, desde sua publicação, a **única autoridade para ordem de execução, gates, piloto, rollout e go-live**. `docs/PLANO_IMPLEMENTACAO_PRODUCAO.md` permanece somente como fonte histórica e não autoriza implantação; `docs/matriz_homologacao.md` é evidência não confiável até a correção/arquivamento bloqueante de DOC-001. Nenhuma afirmação de prontidão nesses arquivos prevalece sobre o veredito e G0–G10 deste documento.

## Veredito

O sistema **não está pronto para produção**. Há bloqueadores confirmados de exposição de credenciais, escalada de privilégio, isolamento multi-tenant, operação real do aplicativo do entregador, integridade logística, integridade financeira, autenticidade de webhooks, recuperação assíncrona e cobertura de testes.

**Não haverá go-live enquanto todos os gates mínimos G0–G10 deste plano não passarem no mesmo release candidate e no ambiente de staging equivalente à produção.** Build, lint, smoke test ou aprovação documental isolados não autorizam produção.

O maior risco não é CORS. A ordem obrigatória é: conter credenciais e privilégios; provar identidade, RBAC, JWT e RLS; unificar schema e contratos; corrigir transações logísticas e financeiras; conectar o mobile real; tornar filas recuperáveis; então validar, pilotar e liberar gradualmente.

## Premissas e limites

1. Supabase PostgreSQL/PostGIS é o sistema de registro durável. Toda alteração de schema nasce em uma migration SQL versionada em `supabase/migrations/`; os modelos Django `managed = False` são espelhos, não autoridade.
2. Para qualquer alteração Supabase/schema, a tarefa só pode avançar após: migration SQL com constraints, índices e RLS; espelho Django atualizado; testes; `supabase db push` **bloqueante em staging**; inspeção pós-push. Alterar apenas `models.py` é proibido.
3. O banco é autoridade para decisões duráveis. Redis pode acelerar coordenação, mas sua perda deve ser recuperável por reconciliação a partir do banco.
4. Identidade e autorização derivam de claims verificadas e vínculo de ator no servidor. Headers, `localStorage`, query strings e IDs enviados pelo cliente não são fatos de autorização.
5. O mobile atual é um protótipo. Nenhum APK será tratado como produto até provar rede, autenticação, contratos, localização, push, offline e armazenamento seguro em release.
6. Dinheiro exige inteiros em centavos, lançamentos imutáveis, double-entry, locks, constraints, idempotência, maker-checker, replay seguro e compensação auditada.
7. Integrações externas falham fechadas para autenticidade e falham de forma recuperável para disponibilidade. Sucesso remoto sem commit local e commit local sem confirmação remota são cenários de teste obrigatórios.
8. O plano não expõe valores de segredos. Evidências citam apenas arquivo, área, identificador da credencial e data de rotação.
9. `docs/PLANO_IMPLEMENTACAO_PRODUCAO.md` é preservado como registro histórico, mas está **SUPERSEDED para execução** por este V2. Até DOC-001 aplicar o banner no arquivo antigo com revisão do usuário, esta declaração do V2 já prevalece: somente este documento define ordem, gates e autorização de go-live.
10. Não existem `ROADMAP.md`, `REQUIREMENTS.md` ou `STATE.md`; IDs e dependências abaixo constituem o registro mestre até a criação desses artefatos.

## Como executar e registrar

- Cada tarefa tem um ID único e deve produzir um commit atômico ou uma sequência RED/GREEN/REFACTOR claramente vinculada ao ID.
- O executor deve ler as fontes do bloco `<read_first>` da onda antes de alterar arquivos.
- Cada tarefa passa por três estados distintos: **correção**, **validação** e **rollout**. Não promover a tarefa diretamente de “código concluído” para “produção”.
- Registrar evidências sem segredos em `docs/evidence/<ID>/` ou no sistema de CI: comandos, SHA, relatórios, métricas, migration aplicada, resultado de teste e decisão de rollback.
- Uma falha de gate reabre a tarefa e bloqueia as dependentes.
- Mudanças que compartilham arquivos devem ser serializadas mesmo quando as tarefas forem conceitualmente paralelas.
- Esta revisão contém **64 tarefas executáveis**. A contagem é auditada por ID ao final; diferimentos têm IDs de backlog próprios e não entram nessa soma.

## Autoridade, dependências e caminho crítico

```text
Onda -1 Incidente
    ↓
Onda 0 Identidade / RBAC / JWT / RLS / tenant
    ↓
Onda 1 Schema único / contratos / idempotência HTTP / auditoria
    ├──────────────────┬──────────────────┐
    ↓                  ↓                  ↓
Onda 2 Logística +    Onda 4 Finanças*   Onda 5 Filas/integrações*
processor offline      ↑                  ↑
    ↓                  │                  │
Onda 3 Mobile + version gate ─┴──────────────┘
    ↓
Onda 6 Testes/CI/observabilidade + DEP-000 preflight → deploy
    ↓
Onda 7 Homologação e go-live controlado
    ↓ estabilidade comprovada
Onda 8 Escala + HUB-000 piloto provider → GH1 → HUB-001 → HUB-003 → HUB-002

* Finanças depende dos invariantes de conclusão da Onda 2.
* Partes de filas podem rodar em paralelo após o contrato de schema da Onda 1,
  mas integrações inbound dependem da criação transacional de pedidos da Onda 2.
```

**Caminho crítico de release:** convergência de DOC-001 e IR-001–IR-005 → ID-001 → ID-002 → ID-003 → SCH-001 → API-001 → API-004 → LOG-001 → LOG-002 → OFF-001 → convergência de MOB-001–007, FIN-001–005 e QUE-001–006 → QA-001 → QA-004 → DEP-000 → DEP-001/DEP-004 → HOM-001 → HOM-002 → HOM-003. **Caminho de expansão do hub:** HOM-003 + 30 dias estáveis → HUB-000 → GH1 → HUB-001 → HUB-003 → HUB-002.

## Regra universal para migrations Supabase

Aplica-se a SCH-001, ID-002, API-004, AUD-001, LOG-001/002/003/004, OFF-001, MOB-007, FIN-001/002/003/004, QUE-001/002/004, HUB-001/HUB-003 e qualquer tarefa que altere tabelas:

1. Criar `supabase/migrations/<timestamp>_<descricao>.sql` com DDL, backfill seguro, constraints, índices, `ENABLE/FORCE RLS` conforme decisão, políticas `USING` e `WITH CHECK`, grants e funções/triggers necessários.
2. Atualizar o espelho em `backend/<dominio>/models.py`, preservando `managed = False` e `db_column`.
3. Escrever teste de migration em banco limpo e teste de upgrade com dados representativos.
4. Produzir consulta de pré-checagem e de pós-checagem; migrations destrutivas usam expand/migrate/contract em releases separados.
5. Executar em staging, como gate bloqueante:

   ```text
   supabase link --project-ref <STAGING_PROJECT_REF>
   supabase db push --dry-run
   supabase db push
   ```

6. Só depois executar os testes de comportamento contra Postgres/PostGIS/RLS reais.
7. Rollback preferencial: migration compensatória forward-only; rollback de aplicação para SHA anterior apenas enquanto o schema permanecer retrocompatível. Nunca apagar dados para “voltar”.

## Onda -1 — Resposta a incidente: credenciais e privilégios

### Objetivo e risco mitigado

Conter possível comprometimento já ocorrido, invalidar credenciais expostas, remover caminhos de escalada global e estabelecer evidência auditável antes de qualquer desenvolvimento adicional. Mitiga bypass de RLS, acesso a dados, criação indevida de platform admins e persistência de sessões comprometidas.

**Dependências:** nenhuma.  
**Paralelo permitido:** DOC-001 pode preparar a reconciliação documental enquanto IR-001 inventaria/rotaciona credenciais e IR-003 prepara quarentena; IR-002 só começa após o inventário de IR-001; IR-004 começa após revogação e quarentena. G0 exige a convergência de DOC-001 e IR-001–IR-005.  
**Bloqueio:** nenhum merge funcional ou deploy externo enquanto G0 não passar.

<read_first>

- `.planning/codebase/CONCERNS.md`, “Privileged credentials are committed to source control”, “Operational script grants every Auth user platform-admin access” e “Static default passwords...”
- `backend/scripts/create_master_admin.py`, `check_supabase_rest.py`, `create_test_driver.py`, `db_manage.py`, `sync_admin.py`, `sync_all_users.py`, `test_jwks.py`
- `backend/accounts/models.py`, `backend/accounts/api_admin.py`
- Histórico Git dos arquivos citados, sem imprimir valores de segredo
- `docs/PLANO_IMPLEMENTACAO_PRODUCAO.md`, T0-06 e T0-09, apenas para reconciliar superfícies adicionais
- `docs/matriz_homologacao.md` e as perícias referenciadas em seu veredito, exclusivamente para DOC-001; nenhum desses arquivos é autoridade de go-live

</read_first>

### DOC-001 — Invalidar autoridades documentais conflitantes antes de qualquer deploy

- **Arquivos/módulos prováveis:** `docs/PLANO_IMPLEMENTACAO_PRODUCAO.md`, `docs/matriz_homologacao.md`, opcional `docs/archive/matriz_homologacao_<data>.md`, novo `backend/scripts/audit_release_authority.py`, `docs/evidence/DOC-001/`.
- **Ação:** durante a execução, preparar um diff que adicione no topo do plano antigo um banner inequívoco `SUPERSEDED — HISTÓRICO — NÃO AUTORIZA GO-LIVE`, linke este V2 como única autoridade e marque a seção `APÓS GO-LIVE CONTROLADO` como histórica. Revisar os 14 itens de `docs/matriz_homologacao.md` contra as perícias e evidências atuais: corrigir seu veredito para `NÃO APTO` com links para G0–G10 ou mover a versão conflitante para `docs/archive/` e deixar no caminho original um tombstone que aponte para este V2. Preservar o conteúdo histórico e exigir revisão bloqueante do usuário sobre o diff antes do merge; rejeição mantém G0 fechado. Criar auditor que examine documentos ativos, ignore somente arquivos sob `docs/archive/` explicitamente marcados como históricos e falhe se encontrar declaração ativa de aptidão/go-live fora deste V2 ou documento sem banner que proponha gates contraditórios.
- **Teste e aceite:** o usuário aprova o diff; as primeiras linhas do plano antigo exibem o banner; a matriz ativa declara `NÃO APTO` ou é um tombstone; cada afirmação histórica de aptidão está dentro de arquivo arquivado/bannered e não pode ser confundida com autorização corrente; o auditor retorna zero conflitos e identifica este V2 como autoridade única.
- **Gate executável:** `python backend/scripts/audit_release_authority.py --docs docs --authority docs/PLANO_IMPLEMENTACAO_PRONTIDAO_PRODUCAO_V2.md`; revisão humana bloqueante do usuário registrada em `docs/evidence/DOC-001/approval.md`; busca adicional por `SISTEMA APTO PARA PRODUÇÃO|APÓS GO-LIVE CONTROLADO` deve apontar apenas para este V2 ou arquivos com classificação histórica validada pelo auditor.
- **Rollback/compensação:** corrigir links ou restaurar conteúdo histórico do arquivo, mantendo sempre o banner/tombstone; nunca reativar o plano antigo ou a matriz como autoridade.
- **Evidência:** diff aprovado, mapa documento→status→autoridade, saída do auditor e ata de revisão sem dados sensíveis.

### IR-001 — Inventariar, revogar e rotacionar todas as credenciais expostas

- **Arquivos/módulos prováveis:** arquivos citados em `<read_first>`, configuração do Supabase Auth/Database/Storage, ambientes Django/Celery/FastAPI, EasyPanel/CI e dispositivos/sessões.
- **Ação:** identificar cada tipo de credencial por fingerprint/identificador não secreto; revogar service-role/JWT/database/admin e chaves de terceiros afetadas; rotacionar secrets de aplicação; invalidar sessões e tokens de dispositivo quando a cadeia de confiança mudou; atualizar somente secret stores; remover literais dos scripts e eliminar fallbacks inseguros de produção.
- **Teste e aceite:** scanners de segredo no worktree e histórico alvo não encontram padrões ativos; chamadas com credenciais antigas falham; serviços de staging sobem somente com os novos secrets; relatório lista proprietário, escopo, data, revogação e validação sem valores.
- **Gate executável:** `gitleaks detect --source . --no-banner --redact`; testes negativos autenticando com token antigo; smoke autenticado com credencial nova; inspeção do painel Supabase confirmando revogação.
- **Rollback/compensação:** não reativar segredo antigo. Se a rotação interromper serviço, corrigir distribuição/configuração da nova credencial ou usar uma terceira credencial recém-gerada.
- **Evidência:** inventário saneado, recibos de revogação, logs de falha das credenciais antigas e ticket de incidente.

### IR-002 — Sanear histórico Git e clones/artefatos derivados

- **Arquivos/módulos prováveis:** histórico dos scripts citados, caches de CI, imagens e artefatos de build.
- **Ação:** após IR-001, reescrever apenas os objetos Git que continham segredos; documentar hashes antigos/novos; invalidar caches/imagens; notificar mantenedores para reclonar; verificar forks/remotes autorizados. A rotação é a contenção; limpeza de histórico reduz exposição residual.
- **Teste e aceite:** busca por fingerprints não secretos e scanner completo no novo histórico retornam zero; branch protection e CI apontam para os novos SHAs; lista de clones/artefatos tratados concluída.
- **Gate executável:** `gitleaks git --redact`; `git log --all -- backend/scripts/...` inspecionado sem revelar conteúdo; rebuild das imagens a partir do novo SHA.
- **Rollback/compensação:** manter bundle offline criptografado do histórico anterior apenas se exigido por investigação; restaurar referências, nunca credenciais, caso a reescrita remova commits legítimos.
- **Evidência:** mapa de reescrita, checklist de clones e attestation do scanner.

### IR-003 — Quarentenar scripts privilegiados e criar comandos allowlisted

- **Arquivos/módulos prováveis:** `backend/scripts/sync_all_users.py`, `sync_admin.py`, `create_master_admin.py`, `backend/accounts/management/commands/`, `backend/accounts/models.py`.
- **Ação:** remover/quarentenar o script que promove todos os usuários; substituir por comando Django que aceita um único `sub`, exige confirmação explícita, verifica allowlist e separação de função, registra auditoria imutável e nunca contém segredo; proibir branch genérico que cria `PlatformAdmin` quando tenant não é informado.
- **Teste e aceite:** execução sem allowlist, em massa, sem confirmação ou por ator não autorizado falha; promoção de um usuário autorizado gera exatamente um vínculo e um evento de auditoria; ferramenta não lista nem altera usuários fora do alvo.
- **Gate executável:** testes de management command; busca `rg -n "list_users|PlatformAdmin|app_metadata" backend/scripts backend/accounts/management`; revisão humana bloqueante do diff de privilégios.
- **Rollback/compensação:** comando suporta revogação explícita do vínculo criado; nenhuma restauração do script perigoso.
- **Evidência:** relatório de remoção/quarentena, testes negativos e trilha de auditoria sintética.

### IR-004 — Auditar contas, claims, sessões e alterações privilegiadas existentes

- **Arquivos/módulos prováveis:** `accounts_platformadmin`, `accounts_staffmember`, Supabase Auth `app_metadata`, denylist/session store e logs de auditoria.
- **Ação:** reconciliar todos os Auth users com `PlatformAdmin`, Staff/Driver/Client; identificar promotions causadas por scripts; revogar claims indevidas; suspender contas duvidosas; invalidar refresh tokens; revisar eventos administrativos, exports e acessos desde a primeira exposição conhecida.
- **Teste e aceite:** cardinalidade e identidade de platform admins batem com allowlist assinada; nenhuma conta tem combinações de role/tenant inválidas; tokens emitidos antes do corte são rejeitados; divergências têm resolução registrada.
- **Gate executável:** consulta SQL somente leitura com totais por role/tenant; teste de token antigo; export saneado revisado por duas pessoas.
- **Rollback/compensação:** reativação de conta exige nova aprovação e nova sessão; manter snapshot criptografado pré-correção para forense.
- **Evidência:** relatório de reconciliação de identidades, período investigado, decisões e pendências zero.

### IR-005 — Tornar secret scanning e configuração fail-closed permanentes

- **Arquivos/módulos prováveis:** `.github/workflows/security.yml`, `.gitleaks.toml`, `.env.example`, `docker-compose.yml`, `easypanel-template.json`, `easypanel-schema.json`, `backend/config/settings.py`.
- **Ação:** adicionar scan de worktree e histórico em PR/push; bloquear HIGH/CRITICAL confirmado; remover defaults de JWT, banco, service role e `DJANGO_SECRET_KEY`; impedir startup de staging/produção sem variáveis obrigatórias; conferir que chave de IA/server não entra no bundle do frontend.
- **Teste e aceite:** fixture canário de segredo bloqueia CI; produção/staging sem variável obrigatória falha antes de aceitar tráfego; bundle não contém nomes/valores server-side; exceções de scanner têm prazo, dono e falso positivo reproduzível.
- **Gate executável:** `gitleaks detect --redact`; `docker compose config`; build frontend seguido de busca por identificadores de server secrets.
- **Rollback/compensação:** corrigir o provisionamento; nunca restaurar default secreto.
- **Evidência:** workflow, relatório de scan e teste de startup fail-closed.

## Onda 0 — Segurança, RBAC, JWT, RLS e contrato multi-tenant

### Objetivo e risco mitigado

Criar uma única cadeia verificável de identidade, claims, autorização e isolamento. Mitiga forged tokens, tenant leakage, privilégios tenant-wide para driver/client, claim ausente, token antigo e bypass de worker/table owner.

**Dependências:** G0, formado por DOC-001 e IR-001–IR-005.  
**Paralelo permitido:** ID-001 e QA-SEC-001 podem começar juntos; ID-002 depende do contrato de ID-001; ID-003/ID-004 dependem de ID-002; ID-005 e ID-006 podem rodar em paralelo após ID-003.  
**Decisão irreversível:** schema canônico de claims em `app_metadata`; mudar depois exige rotação de tokens e migration coordenada.

<read_first>

- `.planning/codebase/CONCERNS.md`, Security Considerations, Tech Debt sobre tenant hints, Fragile Areas sobre JWT/RLS e Test Coverage Gaps de autorização
- `backend/config/api.py`, `middleware.py`, `tenant_context.py`, `core_models.py`, `settings.py`
- `backend/accounts/auth.py`, `api.py`, `api_admin.py`, `models.py`
- `backend/config/db_api.py`, `panel_api.py`
- `supabase/migrations/20260619200249_initial_schema.sql` e migrations RLS posteriores
- `frontend/src/lib/api.ts`, `frontend/src/contexts/AuthContext.tsx`

</read_first>

### ID-001 — Unificar validação JWT e remover todo fallback conhecido

- **Arquivos/módulos prováveis:** `backend/config/api.py`, `backend/config/middleware.py`, novo `backend/config/authentication.py`, `backend/config/settings.py`.
- **Ação:** implementar um verificador único que retorna claims já verificadas; validar assinatura por JWKS/algoritmo aprovado, `iss`, `aud`, `exp`, `nbf`, `kid`; cachear JWKS com expiração e rotação; remover secret fallback commitado e decode sem assinatura após `get_user`; falhar fechado em timeout/config ausente fora de testes; negar token revogado/usuário inativo.
- **Teste e aceite:** token válido passa; assinatura forjada, expirado, issuer/audience errados, claim ausente, usuário revogado, `kid` rotacionado, timeout remoto e segredo/JWKS ausente falham com 401/503 sem aceitar claims locais.
- **Gate executável:** `python -m pytest backend/tests/test_authentication.py -q`; busca por `verify_signature.*False` e fallback literal retorna zero em código ativo.
- **Rollback/compensação:** manter suporte temporário e monitorado a duas chaves legítimas durante rotação; não reativar verificação sem assinatura.
- **Evidência:** matriz JWT, logs redigidos e configuração de staging.

### ID-002 — Definir claims canônicas e aplicar RLS completa

- **Arquivos/módulos prováveis:** nova migration `supabase/migrations/<timestamp>_canonical_claims_rls.sql`, `backend/accounts/api_admin.py`, `backend/logistics/api_admin.py`, `backend/config/middleware.py`, `backend/config/core_models.py`, modelos de todos os domínios.
- **Ação:** adotar `app_metadata.operator_id`, `app_metadata.role` e identificador de ator como contrato; escrever claims apenas por código privilegiado/hook; remover dependência de `user_metadata` e top-level divergente; avaliar e registrar `FORCE ROW LEVEL SECURITY`; usar papel de aplicação não-owner; garantir `operator_id`, FK tenant-consistente, índices tenant-leading, `USING` e `WITH CHECK`; workers usam `tenant_context(operator_id)` e nunca service role genérica para regra de negócio.
- **Teste e aceite:** migration SQL, constraints, índices, RLS e espelhos Django completos; `supabase db push` em staging; consultas cross-tenant negadas inclusive para background worker; claim ausente nega por padrão; claims alteradas só valem após refresh/rotação.
- **Gate executável:** gate universal de migration; `python -m pytest backend/tests/integration/test_rls_matrix.py -q` contra Postgres/Supabase real; consultas a `pg_policies`, `pg_roles`, `pg_indexes` anexadas.
- **Rollback/compensação:** migration expand/migrate/contract; durante transição, aceitar os dois formatos somente na camada de migração sem relaxar RLS; revogar tokens antigos ao encerrar.
- **Evidência:** contrato de claims versionado, relatório de políticas e resultado do push staging.

### QA-SEC-001 — Implementar matriz obrigatória de autenticação e multi-tenant

- **Arquivos/módulos prováveis:** `backend/tests/integration/test_rls_matrix.py`, `test_rbac_matrix.py`, fixtures de JWT/atores e settings Postgres.
- **Ação:** criar matriz parametrizada cobrindo `anônimo`, `driver`, `client`, `staff`, `platform admin` e `background worker`; para cada papel testar mesma tenant, outra tenant, claim ausente, token antigo/revogado e objeto com FK cross-tenant. Separar leitura, criação, atualização, deleção e rotas administrativas.
- **Teste e aceite:** todas as células têm resultado explícito allow/deny; nenhum teste usa ORM mockado; service role só aparece em operações administrativas nominadas; failures identificam papel, tenant e operação.
- **Gate executável:** `DJANGO_SETTINGS_MODULE=tests.test_settings_integration python -m pytest backend/tests/integration/test_rls_matrix.py backend/tests/integration/test_rbac_matrix.py -q`.
- **Rollback/compensação:** não há rollback de teste; uma célula inesperada bloqueia a migration/rota correspondente.
- **Evidência:** matriz exportada pelo CI e logs SQL saneados.

### ID-003 — Aplicar RBAC default-deny a todas as superfícies sensíveis

- **Arquivos/módulos prováveis:** `backend/config/api.py`, `db_api.py`, `panel_api.py`, `backend/accounts/auth.py`, routers `api_admin.py`, `api_operator.py`, `api_driver.py`, `api_client.py`.
- **Ação:** inventariar rotas; classificar público/driver/client/staff/platform admin/system; aplicar autenticação global e policy explícita por rota; remover criação de platform admin de CRUD genérico; restringir company/user CRUD, tenant switch, wallet, tracking, criação/cancelamento de corrida e ativação de driver; default-deny para rota não classificada.
- **Teste e aceite:** inventário de rotas tem 100% de cobertura; anônimo e papéis inadequados recebem 401/403; staff não atravessa tenant; somente allowlisted platform admin executa operação global; schema OpenAPI identifica requisito de auth.
- **Gate executável:** `python -m pytest backend/tests/test_route_authorization_inventory.py backend/tests/integration/test_rbac_matrix.py -q`; snapshot do OpenAPI sem rota sensível `security: []`.
- **Rollback/compensação:** feature flag apenas para compatibilidade de leitura e por tempo limitado; nunca reabrir write route anonimamente.
- **Evidência:** inventário rota→policy, testes negativos e aprovação de segurança.

### ID-004 — Criar seleção de tenant emitida pelo servidor

- **Arquivos/módulos prováveis:** `backend/accounts/api.py`, `backend/config/middleware.py`, `frontend/src/lib/api.ts`, `frontend/src/contexts/AuthContext.tsx`, contratos `/me` e `/session/tenant`.
- **Ação:** emitir sessão/token de tenant assinado após validar membership; `/me` retorna tenant efetiva e papéis; ignorar `X-Tenant-Id`, `X-User-Role`, `X-User-Email`, `company_id` e equivalentes para autorização; UI usa hints apenas para solicitar uma troca que o servidor valida.
- **Teste e aceite:** adulterar headers/localStorage/query não muda tenant efetiva; troca para tenant sem membership retorna 403; token antigo da tenant anterior é rejeitado após revogação definida; UI exibe tenant retornada pelo servidor.
- **Gate executável:** testes backend/frontend de header forjado; `rg -n "HTTP_X_(TENANT|USER_ROLE|USER_EMAIL)|X-Tenant-Id|X-User-Role" backend frontend/src` revisado para usos não autorizativos.
- **Rollback/compensação:** durante migração, manter header só como telemetria, nunca como auth; rollback volta UI sem remover validação server-side.
- **Evidência:** contrato `/me`, testes e diagrama de sequência de tenant switch.

### ID-005 — Substituir senhas estáticas por convite e ciclo de sessão seguro

- **Arquivos/módulos prováveis:** `backend/config/db_api.py`, `panel_api.py`, `accounts/api_admin.py`, Supabase Auth templates/config, frontend de ativação.
- **Ação:** remover passwords padrão e confirmação imediata; usar convite one-time de alta entropia, expiração curta, configuração de senha/MFA conforme papel, rate limit e auditoria; revogar sessões em mudança de role/tenant, desligamento e perda de dispositivo.
- **Teste e aceite:** criação sem senha explícita nunca gera credencial previsível; convite expirado/reutilizado falha; alteração de role invalida refresh tokens; nenhum password/token aparece em resposta ou log.
- **Gate executável:** testes de account lifecycle; scan de strings padrão e assertions de redaction.
- **Rollback/compensação:** reenviar novo convite; nunca recuperar senha anterior.
- **Evidência:** testes do ciclo convite→ativação→revogação.

### ID-006 — Restringir CORS depois de identidade e RBAC

- **Arquivos/módulos prováveis:** `backend/config/settings.py`, `nginx.conf`, configurações de ambientes.
- **Ação:** usar allowlist de origens por ambiente; desligar credentials se não necessárias; definir métodos/headers; preservar apenas origens de staging/produção; validar proxy/TLS. Esta tarefa fica deliberadamente depois de IR/ID-001–ID-004.
- **Teste e aceite:** origem autorizada recebe headers esperados; origem arbitrária não recebe ACAO; preflight não amplia métodos/headers; cookies/bearer continuam conforme contrato.
- **Gate executável:** suite de requests OPTIONS e `curl` em staging; teste de settings.
- **Rollback/compensação:** adicionar origem específica via config versionada; nunca usar wildcard com credentials.
- **Evidência:** matriz origem×ambiente e resposta de staging.

## Onda 1 — Autoridade única de schema e consolidação das APIs

### Objetivo e risco mitigado

Eliminar drift entre migrations, ORM e rotas concorrentes; fixar contratos, idempotência HTTP, auditoria e validação canônica antes de mobile, logística e finanças. Mitiga schema incompleto, replay colidente, regras incompatíveis, órfãos, respostas otimistas e manutenção em módulos monolíticos.

**Dependências:** G1; ID-002 e ID-003 concluídas.  
**Paralelo permitido:** SCH-001 e API-001 fazem inventário em paralelo; API-004 e API-005 dependem do contrato de API-001; AUD-001 depende de SCH-001/API-001; API-002 depende de API-001. Migrations, `backend/config/idempotency.py` e alterações nas mesmas rotas são serializadas.  
**Decisão irreversível:** Supabase SQL é a única autoridade de schema; Django migration que hoje contém trigger deve ser incorporada e neutralizada com histórico preservado.

<read_first>

- `.planning/codebase/ARCHITECTURE.md`, “Persistence contract”, “Audience-Specific Routers” e anti-pattern Django-only
- `.planning/codebase/CONCERNS.md`, Tech Debt P1 e Known Bugs sobre criação de corrida/manual entries
- `supabase/migrations/`, `backend/finance/migrations/0001_wallet_triggers.py`
- `backend/config/api.py`, `db_api.py`, `panel_api.py`, `backend/shared_schemas/`
- `backend/config/idempotency.py`, `backend/config/redis_client.py`, `backend/config/core_models.py`
- `docs/API_CONTRACT.md` e contrato mobile existente

</read_first>

### SCH-001 — Consolidar Supabase SQL como autoridade completa

- **Arquivos/módulos prováveis:** nova migration SQL de convergência, `backend/finance/migrations/0001_wallet_triggers.py`, modelos `accounts/logistics/finance/integration/todos`, script de auditoria de schema.
- **Ação:** inventariar todas as tabelas, triggers de wallet, constraints, índices, partitions, RLS e grants; portar wallet triggers para migration Supabase versionada; tornar Django migration não-autoritativa sem quebrar histórico; criar assertion de deploy para objetos obrigatórios; documentar ordem de bootstrap limpo/upgrade e gerar diagrama ER a partir do schema efetivamente aplicado, sem edição manual divergente.
- **Teste e aceite:** banco limpo criado só por `supabase db push` tem schema completo, triggers de saldo, RLS, partitions e índices; modelos Django passam checagem de colunas; upgrade de snapshot representativo preserva dados.
- **Gate executável:** gate universal; script `backend/scripts/audit_db.py` ampliado; testes de trigger em Postgres real; diff de schema esperado versus staging igual a zero.
- **Rollback/compensação:** migration compensatória; snapshot/PITR antes do push; Django code permanece compatível com schema anterior durante rollout.
- **Evidência:** catálogo de objetos, diagrama ER gerado, push staging e restore point.

### API-001 — Definir application services e contratos versionados autoritativos

- **Arquivos/módulos prováveis:** `backend/shared_schemas/`, novos services em `backend/logistics/services.py`, `finance/services.py`, `accounts/services.py`, `integration/services.py`, `backend/config/api.py`, `backend/config/panel_api.py`, exceções de domínio e OpenAPI.
- **Ação:** definir comandos/queries canônicos para orders, users, finance e tenant switch; colocar transação e políticas em services; routers apenas autenticam, validam e orquestram; criar exceções de domínio tipadas por bounded context e substituir `ValueError`/catch genérico nos comandos financeiros por erros mapeados a status/código estáveis. Instalar handler global equivalente em `api` e `panel_api`: preservar 401/403/404/409/422 tipados, anexar correlation ID, logar exceção inesperada com redaction e retornar 500 genérico sem `str(exc)`/stack; remover catch-all de rota que converte falha em vazio/sucesso. Versionar request/response/error; incluir `Idempotency-Key` em mutações; gerar fixtures de contrato consumíveis por web/mobile e diagrama de sequência API→service→DB/outbox para os fluxos críticos.
- **Teste e aceite:** uma operação tem uma regra de negócio e um contrato; endpoints v1 e adapters de compatibilidade chamam o mesmo service; schemas rejeitam campos inválidos; erros são tipados, com correlation ID, sem sucesso aparente; settlement/invoice/withdrawal em estado inválido retorna erro de domínio 4xx estável, não `ValueError`/500 opaco; exceção inesperada no panel retorna 500 redigido e é localizável no log pelo correlation ID.
- **Gate executável:** testes de contrato OpenAPI, `python -m pytest backend/tests/contracts backend/tests/test_error_contract.py -q`; casos 4xx tipados/500 redigido/correlation em `api` e `panel_api`; diff de schemas aprovado.
- **Rollback/compensação:** compat adapter pode voltar a leitura antiga por feature flag; writes permanecem no service único.
- **Evidência:** catálogo de comandos/queries, OpenAPI versionado, fixtures e diagramas de sequência gerados.

### API-004 — Implementar idempotência HTTP durável e fail-closed

- **Arquivos/módulos prováveis:** `backend/config/idempotency.py`, `backend/config/redis_client.py`, `backend/config/core_models.py`, migration `supabase/migrations/<timestamp>_http_idempotency_records.sql`, `backend/tests/test_idempotency.py` e testes Postgres de comandos críticos.
- **Ação:** substituir a chave global atual por um namespace canônico formado por `tenant_id + actor.sub + método HTTP + route template/params + Idempotency-Key`; calcular fingerprint SHA-256 sobre content type e corpo canônico — JSON parseado com chaves ordenadas, multipart com campos ordenados e checksum dos arquivos, bytes originais nos demais casos. Persistir `HttpIdempotencyRecord` para mutações críticas com fingerprint, estado, owner token, lease, resultado e referência do efeito de domínio. Mesma chave/mesmo fingerprint em `COMPLETED` reproduz status, body e headers allowlisted; em processamento retorna 409 com `Retry-After`; mesma chave com fingerprint diferente retorna sempre 409 `IDEMPOTENCY_KEY_REUSED`, sem executar o handler. Usar lease de 300 s com heartbeat atômico a cada 60 s e compare-and-renew/release por owner token; handlers sem heartbeat têm timeout duro menor que 240 s. Reter respostas logísticas/mobile por 24 h e financeiras por 7 dias; não cachear 5xx. Falha antes do commit libera/expira o lease sem resultado; falha depois do commit e antes da resposta recupera o resultado pelo registro/comando de domínio e não repete o efeito. Redis acelera lease/replay, mas constraints e command records no PostgreSQL garantem durabilidade para logística, offline e finanças mesmo após perda do Redis.
- **Ação sobre fallback:** `MemoryRedis` é permitido somente quando `APP_ENV in {test,development}`; staging/produção falham startup/readiness se Redis não estiver disponível e nunca entram em fallback silencioso. Corrigir `set(ex=...)`, `setex`, `get`, `delete` e eviction do `MemoryRedis` para testes/dev, com relógio injetável; não promover esse fallback como mecanismo de produção.
- **Teste e aceite:** provar isolamento entre tenants/atores/métodos/rotas; JSON semanticamente igual compartilha fingerprint; mesma chave com body diferente retorna 409; request de 6 min mantém lease por heartbeat e concorrente não entra; crash antes do commit permite retry; crash depois do commit reproduz a resposta sem segundo efeito; TTLs de 24 h/7 dias expiram conforme política; restart/perda do Redis não duplica order, offline command, settlement, withdrawal ou manual entry; staging/produção sem Redis retornam unavailable e não instanciam `MemoryRedis`.
- **Gate executável:** gate universal de migration; `python -m pytest backend/tests/test_idempotency.py backend/tests/integration/test_idempotency_postgres.py -q`; fault injection Redis/processo; busca `rg -n "ALLOW_MEMORY_FALLBACK|MemoryRedis" backend/config` revisada por ambiente. API-004 é requisito explícito de G2 e sua suíte integra G7.
- **Rollback/compensação:** manter compatibilidade de leitura do registro durante rollout; nunca voltar à chave sem tenant/ator/fingerprint. Efeito financeiro/logístico já commitado só é corrigido por comando compensatório auditado.
- **Evidência:** matriz namespace/fingerprint/status, timeline de lease/crash, TTL medido, query de efeitos únicos e configuração de ambiente vinculados ao SHA.

### API-005 — Centralizar validação e normalização de CPF

- **Arquivos/módulos prováveis:** `backend/shared_schemas/accounts.py`, schemas/rotas de criação e atualização de driver, staff, client e store, `backend/tests/test_cpf_validation.py`.
- **Ação:** criar um único validator que remove somente pontuação permitida, exige 11 dígitos, rejeita sequências repetidas e valida os dois dígitos verificadores; normalizar para dígitos antes da persistência e usar o validator em todas as entradas que aceitam CPF. Retornar erro tipado 422 sem ecoar o CPF completo em resposta, log ou auditoria.
- **Teste e aceite:** CPFs válidos formatados/não formatados normalizam igualmente; tamanho inválido, caracteres indevidos, todos iguais e cada dígito verificador incorreto falham; nenhum endpoint antigo contorna o validator.
- **Gate executável:** `python -m pytest backend/tests/test_cpf_validation.py backend/tests/contracts -q`; inventário `rg -n "cpf|CPF" backend --glob "*.py"` com cada entrada ligada ao validator. API-005 integra G2 e G7.
- **Rollback/compensação:** manter leitura de valores históricos; corrigir dados inválidos por migration de relatório/dry-run, sem inventar CPF.
- **Evidência:** matriz de casos mascarada, inventário de call sites e relatório de dados históricos inválidos por contagem.

### AUD-001 — Consolidar trilha de auditoria imutável para operações críticas

- **Arquivos/módulos prováveis:** migration `supabase/migrations/<timestamp>_audit_event.sql`, `backend/config/core_models.py`, novo `backend/config/audit.py`, services críticos e testes de RLS/imutabilidade.
- **Ação:** criar `AuditEvent` append-only com tenant, ator verificado, papel, ação, alvo, correlation ID, outcome, timestamps do servidor e metadata redigida; RLS permite leitura tenant/role-scoped e insert por application service, sem update/delete pelo papel da aplicação. Instrumentar promoção/revogação de privilégio, tenant switch, order transitions/proofs, idempotency conflicts, maker-checker/ledger, replay/DLQ e mudanças de provider. Separar o payload operacional protegido da projeção redigida de auditoria definida em QUE-003.
- **Teste e aceite:** cada fluxo crítico gera um evento com tenant/ator/outcome; tentativa cross-tenant, update ou delete falha; secrets, headers de auth, CPF completo e payload bruto não aparecem; correlation ID liga request, task e efeito.
- **Gate executável:** gate universal de migration; testes `backend/tests/integration/test_audit_event.py` em RLS real e scanner de fixtures sensíveis.
- **Rollback/compensação:** eventos não são apagados; correções geram evento corretivo ligado ao original. Se o sink secundário falhar, o registro transacional local permanece.
- **Evidência:** matriz ação→evento, testes de imutabilidade/RLS e amostra redigida vinculada ao SHA.

### API-002 — Migrar e retirar writes das superfícies `/db` e panel incompatíveis

- **Arquivos/módulos prováveis:** `backend/config/db_api.py`, `panel_api.py`, `api.py`, `frontend/src/lib/api.ts`, páginas/componentes consumidores.
- **Ação:** mapear consumo real; migrar web para v1 canônica; transformar rotas legadas necessárias em adapters finos, autenticados e role-gated; responder deprecation headers; impedir writes legados após janela; remover catch-all que mascara erro; implementar cursor/time-window para listas críticas.
- **Teste e aceite:** todos os writes web/mobile usam v1; contract tests provam equivalência temporária; nenhuma rota legada cria platform admin, order ou manual entry diretamente; lista de até 1.000 itens foi substituída por paginação/projeção.
- **Gate executável:** E2E web contra v1; observabilidade de uso legado = zero por janela definida; `rg` dos paths antigos em clientes = zero antes da retirada.
- **Rollback/compensação:** reativar adapter read-only por prazo curto; não reativar write divergente.
- **Evidência:** inventário antes/depois, métricas de tráfego e plano de remoção.

### API-003 — Extrair módulos de alto risco sem alterar comportamento

- **Arquivos/módulos prováveis:** `backend/logistics/api_driver.py`, `backend/config/db_api.py`, `frontend/src/pages/Corridas.tsx`, `Relatorios.tsx`, `Escala.tsx`, `Login.tsx`, clients tipados e componentes focados.
- **Ação:** após contratos congelados, extrair policy services, domain commands, parsers/client e componentes; preservar interfaces; evitar adicionar lógica aos monólitos; cada extração é protegida por caracterização e contrato.
- **Teste e aceite:** módulos críticos têm responsabilidades delimitadas; testes de caracterização passam antes/depois; routers e páginas não contêm regras duplicadas de tenant, transição ou cálculo.
- **Gate executável:** suite de contratos/E2E; revisão de dependências/ciclos; métricas de cobertura de módulos críticos.
- **Rollback/compensação:** commits de extração isolados e reversíveis; nenhuma migration acoplada ao refactor.
- **Evidência:** mapa de responsabilidades e comparação de contratos.

## Onda 2 — Fluxo logístico transacional, geofence e provas

### Objetivo e risco mitigado

Garantir que criar, aceitar, iniciar, chegar, provar, concluir, cancelar e reatribuir uma entrega preserve tenant, assignment, estado e evidência em transações recuperáveis. Mitiga orders órfãs, conclusão inválida, chegada pelo motorista errado, GEO stale e prova inconsistente.

**Dependências:** G2; API-001, API-004 e SCH-001.  
**Paralelo permitido:** LOG-003 e LOG-004 após LOG-001; LOG-002 e LOG-005 coordenam o mesmo contrato de prova e devem ser serializados; OFF-001 começa após LOG-001/LOG-002 e usa os mesmos application services, sem depender de tarefas de integrações da Onda 5.  
**Bloqueio:** nenhum settlement/mobile completo antes de LOG-002; MOB-006 não começa antes de OFF-001.

<read_first>

- `.planning/codebase/CONCERNS.md`, Known Bugs e Fragile Areas de orders, geofence, proof, check-in e uploads
- `backend/logistics/api_driver.py`, `api_operator.py`, `models.py`, `tasks.py`, `services.py`, `schemas.py`
- `backend/config/db_api.py:567-624` e `frontend/src/components/CreateRideModal.tsx`
- migrations de Order, Stop, Proof, GeofenceEvent e Position
- `backend/config/idempotency.py`, `backend/fast_lane/main.py`

</read_first>

### LOG-001 — Tornar criação de corrida um comando atômico tenant-consistente

- **Arquivos/módulos prováveis:** `backend/logistics/services.py`, schemas, v1 router, `frontend/src/components/CreateRideModal.tsx`, migration para constraints necessárias.
- **Ação:** criar `create_order` atômico; derivar operator/staff no servidor; validar store/client/operator; exigir pickup/drop-off; persistir endereço/contato em campos reais ou `Stop.metadata`; preencher `operator`; escrever order e stops em uma transação; retornar ID só após commit; aplicar idempotência por comando.
- **Teste e aceite:** stop inválido, `empresa_id=global`, FK cross-tenant ou falha no segundo insert deixam zero orders/stops; retry da mesma chave retorna mesma order; criação válida gera grafo completo.
- **Gate executável:** testes Postgres `test_create_order_atomic.py`; fault injection após insert da order; E2E CreateRideModal; gate universal se houver schema.
- **Rollback/compensação:** rollback transacional; migration expand/migrate; script de detecção e tratamento dos órfãos históricos com dry-run e relatório.
- **Evidência:** contagem de órfãos antes/depois, testes e contrato.

### LOG-002 — Endurecer conclusão de stops e política de prova

- **Arquivos/módulos prováveis:** `backend/logistics/api_driver.py`, `services.py`, `models.py`, schemas, migration de Proof/Stop.
- **Ação:** sob `select_for_update`, validar `(operator, driver, device, order, stop, active assignment)`; restringir estados permitidos; usar horário do servidor na transição e guardar horário do cliente separadamente; definir combinações válidas por proof type — arquivo obrigatório ou `fileUrl` nullable com check constraint; exigir geofence/proof conforme tipo; impedir batch duplicado/concorrente.
- **Teste e aceite:** offered/canceled/reassigned, outro device/driver, timestamp futuro/antigo, missing proof, fileless PIN/QR permitido ou negado conforme política, duplicate batch e concorrência têm resultado determinístico; settlement dispara uma vez após invariantes.
- **Gate executável:** testes Postgres/PostGIS adversariais e concorrentes; gate universal de migration.
- **Rollback/compensação:** não desfazer prova legal; corrigir por evento compensatório/auditado; rollout de política por tenant somente se default seguro.
- **Evidência:** matriz estado×prova e logs de locks.

### LOG-003 — Corrigir propriedade e ciclo de vida do geofence

- **Arquivos/módulos prováveis:** `backend/fast_lane/main.py`, `backend/logistics/api_driver.py`, `tasks.py`, migration para identidade de evento/índices.
- **Ação:** incluir owner driver/order/stop no membro/evento; validar a tupla sob lock antes da transição; remover `ZREM` idempotente em complete/cancel/reassign; reconciliar GEO a partir de assignments ativos; deduplicar eventos por device event ID; limitar coordenadas, accuracy, timestamp e taxa.
- **Teste e aceite:** motorista A nunca chega pedido de B; stop terminal desaparece; Redis restart reconstrói apenas stops ativos; evento duplicado não transiciona de novo; flood/malformed é rejeitado/limitado.
- **Gate executável:** testes com Redis/PostGIS reais, dois drivers e worker concorrente; fault injection de Redis restart; gate universal se houver schema.
- **Rollback/compensação:** DB conserva estado; limpar e reconstruir namespace Redis versionado; não reverter transição válida automaticamente.
- **Evidência:** relatório de stale ratio/cardinalidade e testes.

### LOG-004 — Fechar check-in cross-tenant e exigir localização confiável

- **Arquivos/módulos prováveis:** `backend/logistics/api_driver.py`, `models.py`, schemas de check-in, RLS/constraints.
- **Ação:** carregar store/turno por `operator=driver.operator`; validar relacionamento store-turno; exigir localização recente, accuracy limite e geofence quando a política exige; registrar exceções administrativas.
- **Teste e aceite:** IDs de outra tenant, localização ausente/stale/spoofed/fora da zona falham; mesmo tenant e posição válida passam; RLS também nega acesso direto.
- **Gate executável:** matriz PostGIS/RLS; gate universal para constraints/policies.
- **Rollback/compensação:** exceção manual expira, exige staff autorizado e audit event; sem fallback silencioso.
- **Evidência:** tabela de casos e auditoria de exceção.

### LOG-005 — Proteger uploads e provas armazenadas

- **Arquivos/módulos prováveis:** helper de upload em `api_driver.py`, `api_operator.py`, `backend/config/supabase_client.py`, migrations/policies Storage, Nginx.
- **Ação:** rejeitar extensão/MIME/magic bytes divergentes; definir allowlist e limite por tipo; malware scan/quarentena; usar bucket privado tenant-scoped; persistir `{bucket, object_key, checksum}` e nunca URL pública; gerar signed URL curta após auth; preferir upload direto/streaming com body limits; redigir metadados.
- **Teste e aceite:** spoofing, malware canário, arquivo grande, cross-tenant download, URL completa legada, fileless proof e concorrência passam/falham conforme política; 2xx só após durabilidade/scan requerido.
- **Gate executável:** testes Storage staging e RLS; teste Nginx 413; gate universal para policies/tabelas.
- **Rollback/compensação:** objetos ficam em quarentena; migração de URLs legadas conserva referência e checksum; revogar signed URLs/chaves em incidente.
- **Evidência:** políticas de bucket, relatório de scan e testes cross-tenant.

### OFF-001 — Processar comandos offline com lease, conflito e dead-letter duráveis

- **Arquivos/módulos prováveis:** `backend/logistics/models.py`, `backend/logistics/services.py`, `backend/logistics/tasks.py`, endpoint `/offline/sync`, migration de `OfflineBatch/OfflineCommandExecution`, comandos de inspect/replay e testes.
- **Ação:** decompor cada batch em comandos persistidos com `command_id`, tenant, ator/device, aggregate/version, payload protegido, ordem causal e estados `RECEIVED/PROCESSING/APPLIED/CONFLICT/DEAD_LETTER`; claim com owner/lease, heartbeat, max attempts e `nextAttemptAt`. Aplicar accept/start/arrive/proof/complete pelos mesmos services de LOG-001/002, sob API-004 e locks de domínio; validar tenant, assignment, device, versão e estado atual. Duplicata retorna o resultado anterior; conflito de reassign/cancel/version vira estado explícito e operator-visible; erro retryable volta à fila e esgotamento vai à DLQ. Não apenas armazenar `OfflineBatch`: o processor deve produzir o efeito ou um desfecho terminal auditado.
- **Teste e aceite:** batch ordenado aplica todos os comandos; duplicate/restart não repete efeito; worker kill antes/depois do commit é recuperado; comando fora de ordem aguarda predecessores ou vira conflito determinístico; reassign/cancel concorrente não força transição; poison command chega à DLQ sem bloquear os demais; `received = applied + conflict + dead-letter + pending` e pending stale volta a zero após lease.
- **Gate executável:** gate universal de migration; `python -m pytest backend/tests/integration/test_offline_processor.py -q` com Postgres/worker reais e kill/fault injection; comandos `offline_commands --check` e `offline_commands replay --dry-run`.
- **Rollback/compensação:** pausar consumer preservando batches; liberar/reclamar leases; nunca apagar comando ou aplicar transição inválida; estado terminal só muda por comando compensatório autorizado.
- **Evidência:** timeline command→lease→efeito/desfecho, reconciliação de contagens e teste de crash vinculados ao SHA.

## Onda 3 — Mobile real: auth, rede, contratos, localização, push e offline

### Objetivo e risco mitigado

Transformar o app protótipo em cliente operacional seguro e recuperável. Mitiga APK que só responde mock, token exposto em backup, contrato Retrofit divergente, perda de comando/localização em rede instável e ausência de notificações.

**Dependências:** G2, LOG-001/002, OFF-001 e contratos API v1/idempotência HTTP congelados.  
**Paralelo permitido:** MOB-001 e MOB-002 em paralelo com ownership de arquivos coordenado; MOB-004 e MOB-005 após auth/device token; MOB-006 depende de MOB-003 e do processor backend OFF-001 já concluído; MOB-007 depende de MOB-001/002 e do contrato de identidade/API-001, podendo ser implementado em paralelo a MOB-004–006 sem compartilhar seus arquivos de domínio.  
**Bloqueio:** o APK de release não entra no piloto sem G4, e G4 não passa sem o version-check/kill switch MOB-007 exercitado em staging.

<read_first>

- `.planning/codebase/CONCERNS.md`, bugs/missing features/test gaps do mobile
- `mobile/app/build.gradle.kts`, `NetworkModule.kt`, `MockInterceptor.kt`, `AuthViewModel.kt`, `TokenManager.kt`
- Retrofit APIs/repositories, `TrackingService.kt`, `MyFirebaseMessagingService.kt`, manifest e backup rules
- backend driver endpoints, `backend/fast_lane/main.py`, `backend/config/idempotency.py`, `/offline/sync`
- fixtures/OpenAPI da Onda 1
- configuração de release mobile, canal de distribuição e material público de verificação de assinatura; nunca ler/imprimir a chave privada

</read_first>

### MOB-001 — Provar configuração de rede de release e ausência de mocks

- **Arquivos/módulos prováveis:** `mobile/app/build.gradle.kts`, source sets debug/release, `NetworkModule.kt`, `MockInterceptor.kt`, CI mobile.
- **Ação:** usar exclusivamente `BuildConfig.API_BASE_URL`; falhar release se vazia, HTTP, localhost ou emulator; mover `MockInterceptor` para debug/test; configurar timeouts/TLS e redaction; expor teste de composição do OkHttp release.
- **Teste e aceite:** APK release contém URL de staging/produção fornecida, não registra/referencia `MockInterceptor`, faz request real ao health/contract endpoint e falha sem `NEVESGO_API_BASE_URL`.
- **Gate executável:** `./gradlew testReleaseUnitTest lintRelease assembleRelease`; inspeção de classes/APK; contract test com staging.
- **Rollback/compensação:** rollback para SHA assinado anterior; nunca distribuir build com mock/URL emulador.
- **Evidência:** relatório do APK, URL redigida por host e teste de DI.

### MOB-002 — Implementar login, refresh, logout e revogação Supabase

- **Arquivos/módulos prováveis:** `AuthApi.kt`, repositório/auth ViewModel, `AuthInterceptor.kt`, `TokenManager.kt`, Keystore, backup/data extraction rules.
- **Ação:** substituir token falso por login real; armazenar material com Keystore-backed encrypted storage; access token curto, refresh serializado, retry único em 401; logout remoto/local; revogação por mudança de role/device loss; excluir auth de backup/transfer; nunca logar tokens.
- **Teste e aceite:** login válido/inválido, refresh concorrente, token expirado/revogado, logout offline/online, reinstalação/backup e alteração de role têm comportamento definido; tokens não aparecem em logs/backup/plain prefs.
- **Gate executável:** JVM tests com fake auth, instrumented storage/backup test, staging login/refresh/revoke.
- **Rollback/compensação:** limpar sessão e exigir novo login; migration de storage local é one-way, removendo plaintext após cópia validada.
- **Evidência:** matriz auth mobile e inspeção de backup/logcat.

### MOB-003 — Alinhar todos os contratos Retrofit e idempotência

- **Arquivos/módulos prováveis:** `CorridaApi.kt`, `EscalaApi.kt`, `FinanceiroApi.kt`, DTOs, repositories, shared contract fixtures.
- **Ação:** gerar/validar interfaces contra OpenAPI; proof multipart correto; batch completion com lista; reservation/check-out/withdrawal com payload; `Idempotency-Key` determinística por comando e preservada entre retries em toda mutação; tipar erros e snake_case mapping; remover `Any`. Consumir a semântica de API-004: 409 `IDEMPOTENCY_KEY_REUSED` para mesma chave/body diferente, 409 + `Retry-After` enquanto em processamento e replay fiel da resposta concluída.
- **Teste e aceite:** contract test cobre cada comando de entregador e corpo/header/content-type; servidor rejeita ausência de idempotency; replay com mesmo payload retorna o mesmo resultado; payload diferente com a mesma key nunca executa; erros 409/422 chegam à UI explicitamente.
- **Gate executável:** MockWebServer/contract fixtures em `testDebugUnitTest`; execução staging happy/negative paths.
- **Rollback/compensação:** versionar DTO/endpoint; manter adapter de leitura para uma versão, sem duplicar write.
- **Evidência:** matriz endpoint→DTO→teste.

### MOB-004 — Unificar device token e implementar localização em background

- **Arquivos/módulos prováveis:** `TrackingService.kt`, location repository/Room, WorkManager, backend device token issuer, Fast Lane, manifest/permissões.
- **Ação:** um único issuer cria metadata Redis versionada com driver/operator/device/expiry/revocation; remover rota legacy incompatível; Fused Location respeita permission/accuracy/frequency/battery; buffer local criptografado; upload autenticado com event ID determinístico; backpressure e retry.
- **Teste e aceite:** release envia localização real; denylisted/revoked token falha; background/Doze/reboot/rede instável não perde eventos além do RPO do buffer; duplicatas são absorvidas; UI mostra tracking/sync state.
- **Gate executável:** instrumented tests em Android suportado, Redis/PostGIS integration, 30 minutos de rede flapping e reconciliação de contagens.
- **Rollback/compensação:** desativar tracking por feature flag server-side e, se o APK estiver defeituoso, pelo version gate assinado MOB-007; preservar buffer para reenvio; revogar device token.
- **Evidência:** bateria/latência/contagem de eventos e teste de revogação.

### MOB-005 — Registrar FCM e tratar push com privacidade

- **Arquivos/módulos prováveis:** `MyFirebaseMessagingService.kt`, repository de device/FCM, backend `notifications.py` e endpoint `/driver/fcm-token`.
- **Ação:** enviar token ao backend após auth e refresh; associar device/driver/tenant; remover logs de token/payload; renovar/remover no logout; exibir channels/notification deep links para offer/cancel/reassign/compliance; validar payload mínimo.
- **Teste e aceite:** token novo/rotacionado/revogado reflete no servidor; push foreground/background/killed state funciona; cross-tenant/device antigo não recebe; PII/token não aparecem em logs.
- **Gate executável:** testes unit/instrumented e envio FCM staging controlado.
- **Rollback/compensação:** revogar token e desabilitar channel específico; polling continua como fallback operacional declarado, não silencioso.
- **Evidência:** lifecycle do token e screenshots/logs redigidos.

### MOB-006 — Implementar journal offline e sincronização de comandos

- **Arquivos/módulos prováveis:** Room entities/DAO/database, WorkManager, repositories, UI sync state, backend offline processor/models/outbox.
- **Ação:** journal criptografado com `command_id`, actor/device, aggregate/version, payload, createdAt e status; WorkManager ordena e reenvia com a mesma chave de MOB-003/API-004; integrar exclusivamente com OFF-001, que aplica comandos e retorna `APPLIED/CONFLICT/DEAD_LETTER/PENDING`; validar estado/tenant/assignment atual e exibir decisão operator-visible para conflito. Não criar um segundo processor no mobile nem depender de QUE-002.
- **Teste e aceite:** accept/start/arrive/proof/complete capturados offline; replay após restart/rede instável é exatamente uma vez no efeito; reassign/cancel concorrente gera conflito explícito; attachment upload retoma; fila não cresce sem limite.
- **Gate executável:** testes unit Room/WorkManager, contract e instrumented com airplane mode; backend Postgres concurrency; contagem command journal = applied+conflict+dead-letter.
- **Rollback/compensação:** não apagar journal ao downgrade; bloquear versão incompatível exclusivamente por policy MOB-007 assinada/monotônica; comandos não aplicáveis viram conflito auditado, nunca mutação forçada.
- **Evidência:** relatório de replay, conflitos e retenção.

### MOB-007 — Implementar version-check e kill switch server-authoritative antes do piloto

- **Arquivos/módulos prováveis:** novo `backend/config/mobile_release.py`, `backend/config/api.py`, `backend/config/core_models.py`, migration `supabase/migrations/<timestamp>_mobile_release_policy.sql`, endpoints admin/read de release policy, `mobile/app/src/main/java/com/nevesgo/app/data/api/ReleasePolicyApi.kt`, repository/use case de release policy, tela bloqueante de update, material público de verificação e testes backend/JVM/instrumented.
- **Ação:** criar `MobileReleasePolicy` durável por plataforma e canal com `config_version` monotônica, `min_supported_version`, `blocked_versions`, `latest_version`, URL allowlisted de distribuição, `issued_at`, `expires_at`, `kid` e status; mutation somente por platform admin autenticado, com confirmação, auditoria e idempotência. O endpoint de leitura pode ser pré-login, mas deve operar apenas por TLS, ser rate-limited e devolver o payload como JWS assinado por chave privada mantida no secret store; o APK contém apenas chave(s) pública(s)/key IDs para rotação e rejeita assinatura, `kid`, canal, plataforma, expiração ou `config_version` inválidos/regressivos. Consultar no boot, retorno ao foreground e antes de mutação crítica, com cache curto de no máximo 5 minutos. Em falha de rede, usar somente last-known-good ainda válido; após expirar, manter versões já bloqueadas bloqueadas e entrar em modo fail-safe que permite update/logout e preserva journal, mas não envia novas mutações até receber policy assinada fresca. Nenhum segredo, token ou chave privada entra no APK, resposta, log ou evidência.
- **Teste e aceite:** versão abaixo de `min_supported_version` e versão explicitamente bloqueada param antes de operações; versão permitida segue; assinatura/key ID adulterados, policy expirada, replay de `config_version` anterior e URL fora da allowlist falham fechados; cache expira em até 5 minutos; rede indisponível preserva o journal sem liberar versão bloqueada. O drill de rollback publica policy assinada que bloqueia o APK defeituoso e permite o APK anterior aprovado; dispositivos do coorte de staging mudam para a tela de update dentro do TTL e voltam a operar somente com a versão permitida, sem perder comandos offline.
- **Gate executável:** gate universal de migration; testes backend de RBAC/JWS/monotonicidade; `./gradlew testReleaseUnitTest connectedDebugAndroidTest` para assinatura/cache/fail-safe; staging drill `permitir RC A → bloquear A/permitir SHA B → confirmar A bloqueado e B operacional` com policy, APK hashes, timestamps e journal reconciliado. MOB-007 integra G4, G9 e G10.
- **Rollback/compensação:** publicar nova policy monotônica e assinada que restaure somente uma versão/APK previamente homologada; manter o APK defeituoso em `blocked_versions`, revogar device tokens se necessário e nunca apagar journal local. Se o serviço de policy falhar, manter o modo fail-safe até recuperar assinatura fresca.
- **Evidência:** histórico de policies sem material privado, matriz versão×canal×decisão, teste de assinatura/fail-safe e timeline do rollback vinculada aos SHAs.

## Onda 4 — Integridade financeira e maker-checker

### Objetivo e risco mitigado

Tornar settlement, wallets, saques, remessa/retorno e lançamentos manuais corretos sob replay, concorrência, falha de storage e operador malicioso. Mitiga crédito/débito duplicado, lote travado, payout sem arquivo, estado inexistente e ledger local-only.

**Dependências:** G2, LOG-002, SCH-001, ID-003 e API-004.  
**Paralelo permitido:** FIN-001 e modelagem de FIN-004 após schema base; FIN-002/FIN-003 são sequenciais; frontend de FIN-004 pode rodar em paralelo ao backend após contrato congelado.  
**Bloqueio:** nenhum dinheiro real antes de G5 e maker-checker homologado.

<read_first>

- `.planning/codebase/CONCERNS.md`, bugs/fragile/test gaps financeiros e Tech Debt maker-checker
- `backend/finance/models.py`, `services.py`, `api.py`, `tasks.py`, `cnab_generator.py`, `pdf_generator.py`
- `supabase/migrations/20260619200249_initial_schema.sql` e wallet trigger Django
- `frontend/src/services/entries-store.ts`, páginas financeiras e `backend/config/db_api.py`
- testes financeiros atuais e skips de concorrência

</read_first>

### FIN-001 — Garantir settlement idempotente, concorrente e semanalmente correto

- **Arquivos/módulos prováveis:** `finance/services.py`, `models.py`, migration de settlement/line item/constraints, testes Postgres.
- **Ação:** lock de order/wallet/invoice; chave determinística por order e categoria; unique constraint para settlement e line item; selecionar/criar invoice por `(operator, store, week_start)` derivado de `businessDate`; garantir double-entry balanceado; não depender de Redis para unicidade.
- **Teste e aceite:** 2–20 chamadas concorrentes/replay geram um settlement, um item e saldo correto; invoice é da semana certa; trigger presente; falha intermediária deixa zero meia-transação; débitos=créditos por moeda/operator.
- **Gate executável:** testes reais de concorrência e property/invariant tests; gate universal migration; query de ledger imbalance = zero.
- **Rollback/compensação:** nunca apagar lançamento; estorno por transação compensatória ligada ao original; migration expand-first.
- **Evidência:** relatório de replay/locks e invariantes.

### FIN-002 — Corrigir solicitação e geração de remessa de saques

- **Arquivos/módulos prováveis:** `finance/api.py`, `tasks.py`, `models.py`, migration de Withdrawal/Remittance/line records, Storage adapter.
- **Ação:** verificar denylist antes do débito na API e constraint/trigger; lock wallet; criar withdrawal e debit atomicamente; processar lote por item/claim seguro sem um inelegível abortar todos; persistir `RemittanceFile` com checksum, storage object key e linhas antes de mudar para PROCESSING; storage ausente falha fechado e retorna/compensa estado.
- **Teste e aceite:** denylisted não debita; mistura elegível/inelegível não derruba lote; storage ausente não reporta sucesso; cada PROCESSING referencia arquivo durável/checksum; reexecução não cria novo débito/remessa.
- **Gate executável:** Postgres/Storage staging, batch concorrente e fault injection; gate universal migration.
- **Rollback/compensação:** falha pré-envio volta a PENDING sem novo crédito se debit reservado; falha definitiva gera refund compensatório; arquivo enviado ao banco nunca é “apagado”.
- **Evidência:** remittance manifest, checksum, testes e conciliação wallet.

### FIN-003 — Processar CNAB retorno com estado válido, replay e compensação

- **Arquivos/módulos prováveis:** `finance/tasks.py`, `models.py`, parser CNAB, migration de ReturnFile/ReturnLine, testes fixtures.
- **Ação:** usar `PAID`, não estado inexistente; modelar identidade/hash do arquivo e linha; parsear códigos do banco; idempotência por arquivo/segmento; lock withdrawal; sucesso marca pago uma vez; falha/rejeição gera refund compensatório e estado terminal; linha desconhecida vai para exceção operacional.
- **Teste e aceite:** arquivo válido, falha, duplicado, truncado, ordem fora, linha desconhecida e crash entre parse/commit são recuperáveis; replay não duplica payout/refund; toda linha tem desfecho.
- **Gate executável:** fixtures CNAB versionadas, testes Postgres reais, invariant query; gate universal migration.
- **Rollback/compensação:** correção por novo evento/arquivo e transação compensatória; preservar original e hash.
- **Evidência:** relatório arquivo→linhas→withdrawals→ledger.

### FIN-004 — Tornar manual entries server-authoritative com maker-checker

- **Arquivos/módulos prováveis:** `finance/api.py`, `models.py`, services, migration, `frontend/src/services/entries-store.ts`, UI de aprovação.
- **Ação:** endpoints create/approve/reject/cancel com schemas; creator obrigatório; approver diferente do maker e role apropriada; `select_for_update`; reason/timestamps/audit; idempotência; remover rota legacy que cria approved e `/entries/credit` inexistente; `localStorage` deixa de ser fonte financeira; optimistic UI só com rollback e server ID.
- **Teste e aceite:** maker não aprova próprio item; outro tenant/role falha; approve/reject concorrentes têm um vencedor; reload mostra dados do banco; erro de rede reverte UI; nenhuma operação “sucesso” sem ledger durável.
- **Gate executável:** backend Postgres/RLS matrix, frontend unit/contract/E2E; gate universal migration.
- **Rollback/compensação:** entry aprovada é corrigida por reversal/compensating entry; feature flag pode esconder UI, não reativar store local como autoridade.
- **Evidência:** maker-checker audit trail e E2E.

### FIN-005 — Formalizar invariantes do ledger e reconciliação bancária

- **Arquivos/módulos prováveis:** finance services/tasks, migration constraints/views, comando de reconciliação e dashboards/alerts.
- **Ação:** definir contas e pares de double-entry, non-negative/overdraft policy, moeda, references únicas; job compara wallets vs ledger, withdrawals vs remittance/return e invoices vs orders; maker-checker para ajuste/replay; alertar mismatch e bloquear novos payouts quando severo.
- **Teste e aceite:** invariantes em banco real sob concorrência; corrupt fixture é detectada; reconciliação é read-only por padrão e correção exige comando aprovado; diferença financeira no piloto = zero.
- **Gate executável:** comando `reconcile_finance --check` retorna 0; property/concurrency tests; restore/replay drill.
- **Rollback/compensação:** relatório antes de qualquer repair; correção somente por entries compensatórias; snapshots/PITR.
- **Evidência:** relatório diário assinado e métricas.

## Onda 5 — Filas, outbox, telemetria, Redis, reconciliação e agendamentos

### Objetivo e risco mitigado

Garantir claim/ack durável, retry limitado, dead-letter, replay, reconciliação e capacidade observável. Mitiga eventos presos em PROCESSING, perda/duplicação de telemetria, provider order inválida, Redis restart e jobs financeiros/compliance nunca agendados.

**Dependências:** SCH-001, ID-002; QUE-002 inbound depende de LOG-001; scheduling financeiro depende de FIN-002/003.  
**Paralelo permitido:** QUE-001 outbox e QUE-004 telemetry em paralelo; QUE-003 webhook security após ID; QUE-005 configura ack/requeue/filas e schedules somente após as tasks-alvo terem idempotência durável (API-004, OFF-001, FIN-001–005 e QUE-001/002/004).  
**Decisão:** PostgreSQL guarda lease/outbox/offline durable; Redis Streams atende telemetria de alto volume com IDs determinísticos.

<read_first>

- `.planning/codebase/CONCERNS.md`, outbox/inbound/telemetry/geofence/scheduled operations/recovery/observability
- `backend/integration/models.py`, `api.py`, `adapters.py`, `tasks.py`, `provider_clients.py`
- `backend/logistics/tasks.py`, `backend/fast_lane/main.py`, Redis/idempotency clients
- `backend/config/celery.py`, finance/logistics tasks
- migrations de IntegrationOutbox, IntegrationEventAudit, Position e OfflineBatch

</read_first>

### QUE-001 — Implementar lease, retry, dead-letter e replay no outbox

- **Arquivos/módulos prováveis:** integration models/tasks, migration de lease/DLQ, management commands e métricas.
- **Ação:** separar consumidores inbound/outbound por type; claim com `claimedAt`, owner, lease timeout e `skip_locked`; reclaim de stale PROCESSING; `nextAttemptAt`, max attempts e terminal DEAD_LETTER; idempotency key no provedor; comando de inspect/replay com approval/audit; rede fora de long transaction.
- **Teste e aceite:** worker kill em claim/send/remote-success/local-failure/local-success/ack-failure recupera sem perda; nenhum consumer pega tipo errado; attempts esgotados chegam DLQ; replay é idempotente.
- **Gate executável:** testes Postgres/Celery reais com kill/fault injection; gate universal migration; query stuck PROCESSING=0 após lease.
- **Rollback/compensação:** liberar/reclamar lease; replay somente por ID e dry-run; outbound irreversível exige consulta remota antes de reenviar.
- **Evidência:** timeline de cada fault injection e métricas DLQ/lag.

### QUE-002 — Corrigir criação e transição de pedidos inbound

- **Arquivos/módulos prováveis:** `integration/tasks.py`, adapters/services, schemas, order service.
- **Ação:** consumir somente o `ProviderEventEnvelope` íntegro/protegido definido em QUE-003, nunca a projeção redigida de auditoria; resolver `operator_id` a partir de integração/store e validar tupla tenant-consistente; provider state fica separado do internal state; transição inválida/out-of-order não é engolida nem marcada processada — gera retry/reconciliation/DLQ; criar order via LOG-001.
- **Teste e aceite:** primeiro evento cria order com operator; skipped/out-of-order status é preservado e reconciliado; erro de persistência não marca evento processado/ack; duplicate poll não duplica order.
- **Gate executável:** integration E2E webhook/poll→outbox→order, RLS e crash tests.
- **Rollback/compensação:** não forçar regressão de estado; consultar provider e emitir comando reconciliado auditado.
- **Evidência:** matriz status provider→canonical→internal.

### QUE-003 — Autenticar webhooks, impedir replay e redigir auditoria

- **Arquivos/módulos prováveis:** `integration/api.py`, `adapters.py`, models/migration de event identity, audit retention.
- **Ação:** cada provedor habilitado precisa HMAC/JWS/mTLS/token conforme documentação; desconhecido/sem verificador é rejeitado; comparação constante sobre os bytes originais, timestamp tolerance, nonce/external event unique; persistir por copy-before-transform os dois contratos obrigatórios abaixo. Verificar assinatura antes de parsear/redigir; redaction opera em uma cópia e nunca altera o envelope consumido por QUE-002.
- **Teste e aceite:** body/query/header adulterado, timestamp antigo, replay, merchant adivinhado e provider desconhecido falham; Delivery Direto/Anota AI válidos passam; iFood/99Food ficam desabilitados até verificação específica comprovada; teste de identidade/checksum prova que redaction não modifica o raw body/payload que QUE-002 consome.
- **Gate executável:** adapter/webhook tests e E2E staging por provider; gate universal para unique/retention.
- **Rollback/compensação:** desabilitar provider; não habilitar modo unsigned. Eventos rejeitados podem ser recuperados do provedor via polling autenticado.
- **Evidência:** tabela provider→método→casos e logs redigidos.

#### Contrato de dados obrigatório entre QUE-003 e QUE-002

| Contrato | Conteúdo e proteção | Retenção/acesso | Consumidor |
|---|---|---|---|
| `ProviderEventEnvelope` íntegro | bytes originais imutáveis, content type, provider/event/tenant resolvidos, checksum, timestamp/nonce e referência criptografada ao payload; sem redaction ou reserialização antes da assinatura | mínimo de 30 dias após estado terminal para crash/replay/reconciliação; criptografia em repouso/chave gerenciada; leitura somente por worker tenant-bound, replay autorizado e security incident role; purge auditado após retenção | verificador de assinatura e QUE-002 |
| `IntegrationEventAuditProjection` redigida | provider, IDs hasheados/correlation, resultado da verificação, status, latências e allowlist de headers; remove auth, cookies, tokens, contato, endereço e PII de payload | 180 dias como baseline operacional, RLS tenant-scoped e export redigido; ajuste legal versionado sem reter raw no audit | operadores, métricas, incidentes e compliance |

**Ordem invariável:** capturar bytes → calcular checksum/verificar autenticidade → persistir envelope protegido → copiar/parsear → derivar projeção redigida → enfileirar referência do envelope para QUE-002. Um teste com sentinel PII/header secreto deve confirmar que a projeção não contém o sentinel e que o checksum/bytes entregues a QUE-002 permanecem idênticos.

### QUE-004 — Substituir telemetria peek/trim por consumo atômico e dimensionável

- **Arquivos/módulos prováveis:** `fast_lane/main.py`, `logistics/tasks.py`, `config/celery.py`, Position schema/migration, Redis key version.
- **Ação:** Redis Streams consumer groups ou claim/ack equivalente; event ID determinístico e unique no banco; ack após insert; reclaim pending; partition por tenant/driver; drain contínuo/dinâmico; bounded retention, backpressure/rate limit; medir lag/throughput; capacidade baseada em couriers×ping interval.
- **Teste e aceite:** com 10 tenants concorrentes a 12 pings/s/tenant por 30 min, dois ou mais consumers, crash insert-before-ack e replay resultam em perda=0, duplicação persistida=0, p95 ingest→Position ≤5 s e idade máxima do pending ≤30 s. Um burst de 24 pings/s/tenant por 10 min pode aplicar backpressure, mas após voltar a 12 pings/s/tenant o pending deve ficar ≤30 s em até 10 min; retention limita a fila sem descartar evento aceito.
- **Gate executável:** load/failure test com Redis/Postgres reais, por exemplo `k6 run -e TENANTS=10 -e RATE_PER_TENANT=12 -e DURATION=30m backend/tests/load/telemetry.js`; gate universal para unique/index; comparação `input event IDs = persisted distinct + explicit DLQ`; queries SLI-TEL-01/02 do catálogo operacional.
- **Rollback/compensação:** dual-read temporário com namespace versionado e dedupe; reconstruir stream/runtime sem alterar Position durável.
- **Evidência:** relatório throughput/p95/lag e fault injection.

### QUE-005 — Agendar jobs com singleton, idempotência e fan-out por tenant

- **Arquivos/módulos prováveis:** `backend/config/settings.py`, `backend/config/celery.py`, finance/logistics/integration/offline tasks, `docker-compose.yml`, `easypanel-template.json`, `easypanel-schema.json`, manifests do beat/workers, métricas e novos testes `backend/tests/integration/test_celery_worker_requeue.py`/schedule registry.
- **Ação:** configurar explicitamente em `backend/config/settings.py` `CELERY_TASK_ACKS_LATE=True`, `CELERY_TASK_REJECT_ON_WORKER_LOST=True`, `CELERY_WORKER_PREFETCH_MULTIPLIER=1`, `CELERY_TASK_SOFT_TIME_LIMIT=240` e `CELERY_TASK_TIME_LIMIT=300`, com override versionado somente para task cujo contrato demonstre outro limite e sempre mantendo soft<hard e idempotência. Ajustar o visibility timeout do broker acima do maior hard limit mais margem de retry; rotear `finance`, `integration.inbound`, `integration.outbound`, `telemetry`, `offline` e `default` para filas e worker pools dedicados declarados em Compose/EasyPanel, sem worker genérico consumir fila financeira/provider indevida. Agendar document expiry, invoice PDF, weekly close, remittance, return ingest, reconciliation, retention e stale leases; manter um beat singleton; coordinator apenas enumera IDs e enfileira jobs tenant-scoped com limites. Cada task deve persistir/reusar idempotency key de domínio, classificar retry e tratar `SoftTimeLimitExceeded` sem marcar efeito incompleto como sucesso.
- **Teste e aceite:** cada task aparece no schedule com timezone/cadência/owner/fila; duas execuções/beat failover não duplicam efeito; tenant lento não bloqueia outros; jobs missing geram alerta. Em Redis/Celery/Postgres reais, o teste inicia uma task idempotente de billing e uma de integração, espera o claim, mata o processo worker com `SIGKILL` antes do ack e inicia substituto: a mensagem é requeued/redelivered, o efeito durável ocorre exatamente uma vez, a mesma idempotency key é reutilizada, `unacked=0` ao final e nenhuma linha de settlement/outbox/offline permanece stranded em `PROCESSING` após o reclaim. Prefetch observado é 1 e soft/hard limit produzem estado retryable/terminal auditado conforme a task.
- **Gate executável:** teste de schedule/route registry; `python -m pytest backend/tests/integration/test_celery_worker_requeue.py backend/tests/integration/test_schedule_registry.py -q` com workers e broker reais; fault injection por PID/`docker kill` no worker isolado; `celery -A config inspect active_queues` confirma ownership; queries de broker/DB confirmam `unacked=0`, stale `PROCESSING=0` e um efeito por chave. A suíte é requisito explícito de G6 e required check de G7, nunca executada apenas em eager mode.
- **Rollback/compensação:** desabilitar entry de schedule sem apagar dados; tasks em voo continuam idempotentes; compensação financeira segue Onda 4.
- **Evidência:** catálogo schedule→fila→worker→limites, configuração efetiva saneada, timeline claim→kill→redelivery→efeito e queries de ausência de mensagens/linhas stranded.

### QUE-006 — Reconstruir estado Redis e disponibilizar operações de reconciliação

- **Arquivos/módulos prováveis:** logistics/integration/offline management commands, Redis key schemas, dashboards.
- **Ação:** versionar keys; comando reconstrói active orders/stops/device metadata seguro a partir do DB; reconciliar geofence, outbox, offline batches e telemetry pending; health mede Redis, queue age e stale leases; operator UI lista DLQ/conflicts com ações autorizadas.
- **Teste e aceite:** limpar Redis em staging e reconstruir sem corromper orders; tokens sensíveis não são recriados sem prova/reautenticação; mismatch detectado; replay tem maker-checker quando afeta dinheiro/estado terminal.
- **Gate executável:** disaster drill Redis loss; reconcile commands `--check` e `--dry-run`; testes RLS de background worker.
- **Rollback/compensação:** flush somente em namespace validado; snapshot Redis quando útil, DB continua autoridade.
- **Evidência:** runbook e relatório antes/depois.

## Onda 6 — Testes reais, CI, observabilidade e hardening de deploy

### Objetivo e risco mitigado

Transformar correções em gates repetíveis e tornar falhas detectáveis antes e depois do deploy. Mitiga cobertura ilusória, ambiente diferente de produção, container “up” mas indisponível, dependência não reproduzível e incidentes invisíveis.

**Dependências:** Ondas 0–5 funcionalmente concluídas. A infraestrutura básica de testes pode ser criada antes, mas o gate final roda sobre o release candidate completo.  
**Paralelo permitido:** QA-001 backend, QA-002 frontend e QA-003 mobile em paralelo; OBS-001, DEP-000 e DEP-004 podem iniciar depois de suas dependências; DEP-001 depende do PASS bloqueante de DEP-000 e dos contratos de filas de QUE-005; FE-001 usa os contratos de OBS-001 e serializa alterações de `main.tsx/AuthContext` com QA-002; QA-004 agrega todos. Alterações compartilhadas em Compose/EasyPanel/settings entre QUE-005, DEP-001 e DEP-004 são serializadas nessa ordem.  
**Bloqueio:** CI completo, smoke, restore e observabilidade são gates de go-live, não pós-go-live.

<read_first>

- `.planning/codebase/TESTING.md` integral
- `.planning/codebase/CONCERNS.md`, Test Coverage Gaps, Dependencies at Risk, Production composition e observability
- workflows em `.github/workflows/`
- `backend/pytest.ini`, test settings e app `tests.py`
- `frontend/package.json`, `mobile/app/build.gradle.kts`
- Dockerfiles, compose, Nginx, Fast Lane e health endpoints

</read_first>

### QA-001 — Corrigir discovery e criar pirâmide backend com infraestrutura real

- **Arquivos/módulos prováveis:** backend CI, `pytest.ini`, integration settings, fixtures/factories, app tests e suites críticas.
- **Ação:** CI executa `python -m pytest`, incluindo `accounts/tests.py`, `finance/tests.py`, `integration/tests.py`, `logistics/tests.py`, `todos/tests.py`; separar unit SQLite/mocks de integration Postgres 17/PostGIS/Redis; aplicar migrations Supabase reais; remover skips/pass de finanças/logística; reduzir source-inspection em favor de comportamento; cobertura focada em módulos críticos.
- **Teste e aceite:** todos os módulos descobertos; zero skip injustificado em P0/P1; locks/RLS/GIS/triggers usam serviços reais; unit continua rápido; relatórios de coverage separados.
- **Gate executável:** `python -m pytest --collect-only -q`; unit suite; integration suite com `DJANGO_SETTINGS_MODULE=tests.test_settings_integration`; schema audit.
- **Rollback/compensação:** jobs podem ser separados para diagnóstico, nunca removidos do required check.
- **Evidência:** inventário de testes antes/depois, coverage e logs de serviços.

### QA-002 — Adicionar frontend unit, contract e E2E

- **Arquivos/módulos prováveis:** `frontend/package.json`, config Vitest/RTL/MSW/Playwright, testes de auth, tenant, ride e finance, frontend CI.
- **Ação:** instalar/configurar um linter real (ESLint ou Biome) com regras React, hooks e acessibilidade, mantendo `typecheck` como comando separado; unit/DOM para parsers/state/rollback; contract com fixtures v1; E2E browser contra stack real para login, tenant switch negado, create ride atomic, tracking, manual entry maker-checker e errors; testar cache reset e network failures. CI executa lint sem `|| true/echo`, com paths filter, e SCH-001 mantém o audit de drift do schema autoritativo.
- **Teste e aceite:** zero fluxo P0/P1 depende só de typecheck/build; E2E usa duas tenants e papéis; falha API aparece ao operador, não vira vazio/sucesso; artifacts de screenshot/trace em falha.
- **Gate executável:** `npm ci`, `npm run typecheck`, `npm run lint`, `npm run test`, `npm run test:contract`, `npm run test:e2e`, `npm run build`.
- **Rollback/compensação:** quarantine de teste flaky exige issue/prazo; não desabilitar gate crítico.
- **Evidência:** relatórios JUnit/coverage/Playwright.

### QA-003 — Tornar testes/lint mobile gates de release

- **Arquivos/módulos prováveis:** mobile CI, Gradle, source sets de test/androidTest, tests em `com.nevesgo.app`.
- **Ação:** remover stubs `com.example`; executar unit, contract, lint release e instrumented em matriz de API suportada; testar DI release, auth, contracts, Room/WorkManager, location permissions/background, FCM, backup, offline, UI states e MOB-007 (JWS, cache, fail-safe, versão bloqueada/permitida e journal preservado); dependency/security check; assinatura só em workflow protegido.
- **Teste e aceite:** release não monta se teste/lint falhar; instrumented usa app ID correto; artifact é assinado/provenanceado apenas depois dos gates; nenhum mock interceptor em release.
- **Gate executável:** `./gradlew testDebugUnitTest testReleaseUnitTest lintRelease connectedDebugAndroidTest assembleRelease` em jobs apropriados.
- **Rollback/compensação:** distribuir SHA anterior; não desligar `abortOnError`.
- **Evidência:** reports Gradle/lint/device e hash do APK.

### QA-004 — Criar suíte cross-system de segurança, dinheiro, filas e desastre

- **Arquivos/módulos prováveis:** testes E2E/chaos/load, scripts de restore/reconcile e workflows noturnos.
- **Ação:** executar matriz RLS, settlement/withdrawal replay/concurrency, QUE-005 worker SIGKILL/requeue, webhook forgery/crash, telemetry overload/Redis restart, upload privacy, mobile offline/version rollback MOB-007, clean bootstrap e deploy/rollback por digest DEP-001; classificar suites PR/nightly/release; falhas release são bloqueantes.
- **Teste e aceite:** todos os achados P0/P1 têm ao menos um teste de comportamento e um gate; resultados guardados por SHA; nenhuma aprovação manual substitui teste automatizável.
- **Gate executável:** workflow `release-readiness.yml` invoca suites; resultado final machine-readable com P0/P1=pass.
- **Rollback/compensação:** release candidate descartado; ambiente staging restaurado por automação.
- **Evidência:** manifest SHA→suite→resultado.

### OBS-001 — Instrumentar logs, traces, métricas, alertas e privacidade

- **Arquivos/módulos prováveis:** settings/log filters, Fast Lane/Celery, frontend/mobile crash reporting, dashboards/alerts, retention.
- **Ação:** correlation ID ingress→Django/FastAPI→Celery→provider; JSON logs com redaction; métricas API/DB/Redis/outbox/DLQ/telemetry/offline/finance; erro por tenant sem PII; crash reporting web/mobile; auditoria de headers e FCM token redigida. Implementar exatamente as recording/alert rules SLI-API-01/02, SLI-TEL-01/02, SLI-QUE-01, SLI-MOB-01, SLI-FIN-01, SLI-READY-01 e SLI-ALERT-01 do catálogo operacional, com labels de SHA/ambiente e sem tenant PII.
- **Teste e aceite:** trace liga request a task/evento; três alertas canários consecutivos têm MTTD ≤5 min e acknowledgement ≤10 min; token/PII não aparece em logs; cada SLI tem painel, query reproduzível, owner e ação automática registradas; queue age, stuck rows, financial mismatches e mobile sync health não dependem de leitura manual.
- **Gate executável:** smoke de telemetria, canary error e testes de redaction; executar as queries do catálogo contra o RC e anexar resultados por SHA; falha de regra/receiver bloqueia G8.
- **Rollback/compensação:** desligar exporter problemático sem desligar aplicação; logs mínimos locais continuam; preservar audit events.
- **Evidência:** links/screenshots dos dashboards e resultado dos canários.

### DEP-000 — Executar preflight bloqueante das capacidades reais do EasyPanel

- **Arquivos/módulos prováveis:** novo `backend/scripts/easypanel_preflight.py`, novo `.github/workflows/deploy-preflight.yml`, `easypanel-template.json`, `easypanel-schema.json`, `docs/evidence/DEP-000/capabilities.json` e `deployment-mode.md`.
- **Ação:** em staging e com GitHub Environment protegido, identificar a versão/topologia EasyPanel instalada e testar somente mecanismos documentados ou observados na instância: pull de imagem GHCR por digest, deploy hook/API, consulta de status/readiness, revisão/clone de serviço, troca gradual de tráfego e rollback. Não codificar endpoint presumido. Registrar como `EASYPANEL_NATIVE` apenas se hook/API e traffic switch forem provados ponta a ponta; caso contrário, provar o fallback `DOCKER_BLUE_GREEN_SSH`: acesso SSH protegido ao host, duas stacks/cores Compose pinadas por digest e Nginx repo-owned capaz de validar/recarregar um include de upstream ponderado. Se nenhum modo for comprovado, DEP-000 falha e G8 permanece fechado até provisionar um dos canais, sem fallback manual não reproduzível. Credenciais ficam em GitHub Environments/secrets com least privilege e approval; relatório registra apenas nomes/escopos, nunca valores.
- **Teste e aceite:** preflight produz JSON machine-readable com `mode`, capacidades observadas, versão, target de staging, timestamp, SHA e resultado; consegue implantar um container canário inofensivo por digest, observar readiness, alternar tráfego no modo escolhido e voltar ao digest anterior sem rebuild. Um hook/API ausente recebe `unsupported` e aciona o teste do fallback, não uma chamada inventada.
- **Gate executável:** workflow protegido `.github/workflows/deploy-preflight.yml` executa `python backend/scripts/easypanel_preflight.py --target staging --output docs/evidence/DEP-000/capabilities.json`; valida schema do JSON; smoke externo confirma active digest antes/depois; scanner garante que evidência/log não contém credenciais. `mode=UNPROVEN` é falha bloqueante.
- **Rollback/compensação:** remover o canário e restaurar o digest/upstream anterior pelo mesmo mecanismo testado; nenhuma mudança de banco é permitida neste preflight.
- **Evidência:** capabilities JSON, transcript redigido do deploy/switch/rollback e decisão do modo que DEP-001/HOM-003 devem usar sem renegociar.

### DEP-001 — Endurecer composição, budgets, ingress e deploy imutável com rollback

- **Dependências específicas:** DEP-000 em PASS com modo registrado; QUE-005 concluído para filas/pools; imagens e suites de QA-004 vinculadas ao release candidate.
- **Arquivos/módulos prováveis:** `backend/Dockerfile`, `backend/fast_lane/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `docker-compose.local.yml`, `nginx.conf` e include de upstream, `easypanel-template.json`, `easypanel-schema.json`, novos `.github/workflows/release-images.yml` e `deploy-release.yml`, novos scripts/manifest em `deploy/`, Fast Lane/Django health e configuração de feature flags.
- **Ação de build/registry:** GitHub Actions, após G7, constrói backend (reusado por Django/Celery), Fast Lane e frontend uma vez, publica no **GHCR** com tag imutável `${GITHUB_SHA}`, resolve os digests, gera SBOM/provenance e grava um release manifest `SHA→imagem→digest→migration manifest`. Usar `GITHUB_TOKEN`/permissão `packages:write` restrita ao workflow e GitHub Environment protegido para o canal de deploy; hooks/tokens/SSH do EasyPanel nunca entram no repositório/log. `latest`, rebuild durante rollback e imagem sem digest são proibidos.
- **Ação de deploy/tráfego:** executar migration Supabase como job único e backward-compatible antes da promoção; falha impede qualquer traffic shift. Implantar todos os serviços do RC na revisão/cor inativa pelo modo provado em DEP-000, esperar liveness/readiness de DB, Redis, Storage e queue age e executar smoke. Em `EASYPANEL_NATIVE`, usar exclusivamente o hook/API/revision/traffic switch registrado no capabilities JSON. No fallback `DOCKER_BLUE_GREEN_SSH`, o workflow envia ao host somente o manifest/digests, sobe a stack `blue` ou `green` inativa via Compose e o Nginx repo-owned aplica pesos 0/5/25/50/100 por include versionado após `nginx -t` e reload atômico. Feature flags server-authoritative pausam domínios de escrita/provider/payout sem substituir o traffic switch. O rollback desloca tráfego para a revisão/cor anterior pinada no **mesmo digest/SHA que foi homologado**, sem rebuild; schema permanece retrocompatível ou recebe migration compensatória.
- **Ação de runtime:** health/liveness/readiness para DB, Redis, Storage e queue age; restart e log rotation; beat singleton; Nginx com boundary TLS confirmado, rate/body/timeouts/security headers. Aplicar os budgets iniciais abaixo como cgroup limits e reservations de CPU/memória em 50% do respectivo limite; staging pode recalibrá-los somente antes de congelar novo RC, com load report e aprovação versionada, nunca durante piloto/rollout.

#### Budgets iniciais bloqueantes de DEP-001

| Serviço/pool | CPU limite | Memória limite |
|---|---:|---:|
| Django API | 1,00 CPU | 768 MiB |
| Fast Lane | 0,50 CPU | 512 MiB |
| Frontend | 0,25 CPU | 256 MiB |
| Nginx | 0,25 CPU | 128 MiB |
| Redis | 0,50 CPU | 512 MiB |
| Celery `finance` | 1,00 CPU | 768 MiB |
| Celery `integration.inbound` | 1,00 CPU | 768 MiB |
| Celery `integration.outbound` | 1,00 CPU | 768 MiB |
| Celery `telemetry` | 1,50 CPU | 1.024 MiB |
| Celery `offline`/`default` por pool | 0,50 CPU | 512 MiB |
| Celery Beat singleton | 0,25 CPU | 256 MiB |
| Migration job one-shot | 1,00 CPU | 768 MiB |

- **Teste e aceite:** dependency failure remove readiness; Fast Lane tem health; Nginx limita upload/rate; container reinicia; migration falha sem promover app. `docker inspect` mostra `NanoCpus`/`Memory` compatíveis com a tabela e `docker stats --no-stream` confirma aplicação no host EasyPanel. Em staging, load/pressure leva cada classe a 80% do budget e um teste OOM controlado mata somente o worker alvo; restart/requeue de QUE-005 recupera a task sem efeito duplicado, enquanto API/Nginx/outros pools permanecem ready. O E2E publica um SHA/digest, promove 5%, injeta falha de readiness e o controlador retorna automaticamente ao digest/SHA anterior homologado; headers/health/manifest provam qual digest serve tráfego.
- **Gate executável:** `docker compose config`; `nginx -t`; inspeção `docker inspect`/`docker stats --no-stream` ou equivalente comprovado pelo preflight; load/OOM fault test em staging; workflows `release-images.yml` e `deploy-release.yml` produzem manifest/digests e fazem deploy→5%→falha→rollback end-to-end. O gate compara digest ativo ao manifest antes/depois, mede tempo de rollback, roda reconcile de filas/finanças e falha se houver secret em log, rebuild, `latest`, drift de schema ou modo diferente de DEP-000.
- **Rollback/compensação:** executar o mesmo controlador com o manifest anterior, traffic switch para a cor/revisão anterior e feature flags de segurança; migration compensatória forward-only quando necessária; restore somente se corrupção confirmada. Nunca apontar para tag mutável nem relaxar budget/readiness para concluir rollout.
- **Evidência:** capabilities de DEP-000, release manifest/SBOM/provenance, GHCR digests, configuração efetiva de cgroups, relatório load/OOM/readiness e timeline deploy→traffic→rollback com o SHA/digest ativo.

### DEP-002 — Tornar builds e dependências reproduzíveis

- **Arquivos/módulos prováveis:** `backend/requirements.txt`/lock, backend/frontend Dockerfiles, package lock, Gradle verification, CI.
- **Ação:** fixar Gunicorn/ReportLab e resolver lock/hash Python; `npm ci` em imagens; alinhar Python/Postgres/Node de CI e produção; Gradle dependency verification; SBOM e scans. Configurar Dependabot ou Renovate versionado para pip, npm, Gradle e GitHub Actions, cadence semanal, grupos separados por ecossistema/risco, PRs com changelog/SBOM/testes e auto-merge apenas de patch permitido após todos os gates; atualização major ou HIGH/CRITICAL exige revisão explícita e prazo registrado.
- **Teste e aceite:** dois builds do mesmo SHA têm dependency graph/SBOM iguais; nenhuma instalação fora do manifest; HIGH/CRITICAL sem exceção aprovada bloqueia; dry-run/config validation do bot cobre os quatro ecossistemas e uma fixture de dependency update abre PR com suites corretas.
- **Gate executável:** clean builds, checksum/SBOM diff, pip/npm/Gradle audit.
- **Rollback/compensação:** voltar lockfile/SHA; não usar floating latest.
- **Evidência:** SBOMs e attestation.

### DEP-003 — Centralizar adapters Supabase e falhar consistentemente

- **Arquivos/módulos prováveis:** `backend/config/supabase_client.py`, finance/logistics storage callers, health checks.
- **Ação:** configuração obrigatória em produção; typed Auth/Storage adapters; fakes só em test; upload/proof/remittance falham fechados e com error tipado; readiness inclui dependência conforme operação.
- **Teste e aceite:** ausência de client nunca resulta em upload/remittance “sucesso”; todos os callers têm semântica consistente; health diferencia degraded/readiness.
- **Gate executável:** fault injection sem env/client em staging/test; tests de adapters.
- **Rollback/compensação:** pausar operação dependente e enfileirar retry; não inventar artifact inexistente.
- **Evidência:** matriz adapter outage→comportamento.

### FE-001 — Eliminar estados de UI irrecuperáveis e tornar falhas acessíveis

- **Arquivos/módulos prováveis:** `frontend/src/main.tsx`, `frontend/src/contexts/AuthContext.tsx`, `frontend/src/components/ErrorBoundary.tsx`, `frontend/src/App.tsx` e testes RTL/E2E.
- **Ação:** envolver a raiz em `ErrorBoundary` integrado ao report remoto de OBS-001, com fallback recuperável e correlation ID; garantir que `loadProfile/getSession` sempre execute `setIsLoading(false)` em `finally`, inclusive timeout/rejeição/revogação; marcar erro com `role="alert"` e loading/Suspense com `role="status"` + `aria-live="polite"`; oferecer retry/logout seguro sem expor stack/PII.
- **Teste e aceite:** rejeição/timeout de sessão nunca deixa spinner infinito; erro em página sem boundary local mostra fallback e chega ao collector; leitor de tela anuncia loading e erro; retry/logout restauram navegação; nenhum detalhe sensível é renderizado.
- **Gate executável:** `npm run test -- AuthContext ErrorBoundary App`; E2E com falha injetada e axe; evento canário localizado por correlation ID.
- **Rollback/compensação:** manter fallback local se collector falhar; nunca remover `finally` nem o boundary raiz para recuperar telemetria.
- **Evidência:** testes, trace redigido e relatório a11y.

### DEP-004 — Exigir autenticação e TLS no Redis de staging/produção

- **Arquivos/módulos prováveis:** `backend/config/settings.py`, `backend/config/celery.py`, `.env.example`, compose/EasyPanel manifests, readiness e testes de configuração.
- **Ação:** classificar a fronteira Redis: endpoint externo exige `rediss://`, validação de certificado/hostname, ACL/password via secret store e proíbe query/log de credenciais; Redis interno só pode dispensar TLS com rede privada isolada e evidência de TLS no boundary, mas continua autenticado. Staging/produção falham startup/readiness para `redis://` externo, senha ausente, certificado inválido ou fallback `MemoryRedis`; Celery, cache, idempotência e Fast Lane usam a mesma factory/política.
- **Teste e aceite:** conexão autenticada/TLS válida funciona; password ausente, plain TCP externo, CA/hostname inválido e Redis indisponível falham fechados; logs/health não exibem URL com segredo; rotação de credencial mantém dual-secret somente pela janela documentada.
- **Gate executável:** testes de settings/client, `docker compose config` com valores redigidos, staging handshake e failure injection; inspeção do certificado/boundary anexada a G8.
- **Rollback/compensação:** corrigir secret/cert/boundary ou voltar SHA compatível; nunca habilitar Redis externo plaintext nem `MemoryRedis` em produção.
- **Evidência:** matriz topologia→política, handshake redigido, teste negativo e data de rotação.

## Onda 7 — Homologação e go-live controlado

### Objetivo e risco mitigado

Separar correção de validação e rollout, provar recuperação e limitar blast radius. Mitiga decisão de produção baseada em documento, build ou happy path.

**Dependências:** G0–G8; todas as ondas anteriores concluídas.  
**Paralelo permitido:** documentação/runbooks e treinamento enquanto release candidate permanece congelado; piloto é sequencial e não pode ser comprimido por trabalho paralelo.  
**Release candidate:** SHA único para backend, frontend, mobile e migration manifest; imagens backend/Fast Lane/frontend resolvidas por digest GHCR e APK/policy MOB-007 identificados no mesmo release manifest.

<read_first>

- Todos os relatórios/evidências G0–G8
- `docs/PLANO_IMPLEMENTACAO_PRODUCAO.md` já bannered por DOC-001 e documentos de homologação/perícia reconciliados, somente como histórico/evidência
- runbooks de deploy, rollback, incidente, backup/restore, finance reconciliation e provider outage
- dashboards/alertas/SLO e manifest do release candidate

</read_first>

### HOM-001 — Executar staging production-like e ensaio de restauração

- **Arquivos/módulos prováveis:** manifests de deploy, scripts de seed sintético/restore, runbooks.
- **Ação:** confirmar primeiro que DOC-001 ainda passa e nenhuma autoridade documental conflitante reapareceu; bootstrap limpo via Supabase migrations; dados sintéticos de duas tenants; executar suites release; backup/restore DB/Storage; perda Redis; rollback pelo modo/digests de DEP-000/DEP-001; validar migration forward e compensatória; medir RPO/RTO. Criar/atualizar e exercitar runbooks versionados de deploy/rollback, incidente, Redis rebuild, provider outage, rotação de secrets/certificados e reconciliação financeira.
- **Teste e aceite:** staging usa Postgres/PostGIS/Redis/Storage reais e mesmas versões/config; restore atende alvos; schema audit zero drift; nenhum dado sintético cruza tenant.
- **Gate executável:** release-readiness workflow, restore drill e reconcile checks.
- **Rollback/compensação:** descartar staging e restaurar snapshot; release candidate permanece bloqueado.
- **Evidência:** relatório assinado do ensaio com tempos.

### HOM-002 — Executar piloto restrito com checklist operacional

- **Arquivos/módulos prováveis:** configuração de feature flags/tenants, dashboard piloto, checklist.
- **Ação:** selecionar exatamente 2 tenants, 5–10 entregadores e stores representativas; limitar volume/horário; on-call e canais definidos; conciliar diariamente orders/stops/proofs/positions/ledger/withdrawals/outbox; testar rede instável e device loss; não ativar dezenas de providers. Antes de contar o primeiro dia, executar MOB-007 no coorte: permitir o APK do RC, publicar policy assinada que o bloqueia e retorna ao APK anterior homologado, provar cache/fail-safe/journal e restaurar somente por nova policy monotônica. O piloto dura no mínimo 7 dias corridos e executa diariamente as queries SLI-* do catálogo, sem substituir números por avaliação subjetiva.
- **Teste e aceite:** 7 dias completos, zero Sev-1/tenant leak/forged webhook aceito/financial mismatch/data loss; SLI-API-01/02, SLI-TEL-01/02, SLI-QUE-01, SLI-MOB-01, SLI-FIN-01 e SLI-READY-01 atendidos em ≥99% das janelas; ≥99,5% comandos mobile aplicados ou com conflito visível em ≤15 min; 100% payouts conciliados; cada alerta canário cumpre SLI-ALERT-01; rollback ensaiado e medido.
- **Gate executável:** checklist diário, queries/comandos do catálogo e dashboards exportados por SHA; qualquer abort threshold da matriz pausa o piloto automaticamente e reinicia a contagem de 7 dias somente após novo RC.
- **Rollback/compensação:** feature flags/traffic off pelo controlador DEP-001, pausar writes/payouts, usar MOB-007 para bloquear a versão defeituosa e permitir somente o APK/SHA anterior homologado, revogar device tokens quando necessário, voltar os digests do release manifest e reconciliar comandos pendentes sem apagar journal.
- **Evidência:** diário do piloto, incidentes e aceite formal.

### HOM-003 — Fazer rollout progressivo e encerrar hypercare

- **Arquivos/módulos prováveis:** `.github/workflows/deploy-release.yml`, scripts/controlador e release manifests de `deploy/`, include de upstream `nginx.conf`, config de rollout/feature flags, release policy MOB-007, runbooks, status page e dashboards.
- **Ação:** usar obrigatoriamente o modo congelado por DEP-000 e o controlador de DEP-001 para promover os mesmos digests GHCR do RC em 5%→25%→50%→100% por revisão/cor e pesos de tráfego compatíveis com Nginx; cada decisão referencia SHA, digests, migration manifest, SLI, amostra e estágio. Feature flags server-authoritative controlam domínios/tenants e MOB-007 controla versões mobile; nenhum deles substitui o traffic switch. Manter freeze de schema; em abort, automação usa o mesmo hook/API comprovado ou fallback blue/green SSH para retornar ao digest/revisão anterior, publica policy mobile assinada que bloqueia APK defeituoso, pausa payouts/providers quando o domínio falha e preserva journals/outbox. Hypercare mantém reconciliação intensiva.
- **Teste e aceite:** 5% permanece ≥60 min e ≥500 mutações; 25% ≥4 h e ≥2.000; 50% ≥24 h e ≥10.000; 100% ≥72 h e ≥20.000. Só avançar com todos os SLI obrigatórios em ≥99% das janelas, consumo ≤25% do error budget do estágio, zero leak/mismatch/perda e sem backlog crescente; qualquer limiar de abort retrocede automaticamente. Se a amostra não for atingida, permanecer no estágio e gerar carga controlada sem relaxar a duração.
- **Gate executável:** workflow/controlador exporta decisão machine-readable por estágio; antes de 5%, repetir o E2E `deploy RC digest → traffic 5% → falha readiness/SLI → rollback ao digest/SHA anterior sem rebuild` e o drill MOB-007 `bloquear APK RC → permitir APK anterior`; validar active digest por probe/manifest e version policy por assinatura. Aprovação final referencia DEP-000/DEP-001, todos os gates, SHAs/digests e policies; qualquer diferença de modo/artefato bloqueia G10.
- **Rollback/compensação:** voltar etapa/traffic pelo mesmo controlador, bloquear versão mobile defeituosa, preservar journal/outbox, compensar finanças e comunicar incidentes conforme LGPD.
- **Evidência:** timeline de rollout e sign-off.

## Onda 8 — Pós-go-live: escala e hub de integrações

### Objetivo e risco mitigado

Escalar somente depois de o núcleo demonstrar estabilidade. Mitiga multiplicar contratos e tráfego sobre fundações ainda instáveis.

**Dependências:** HOM-003 e 30 dias completos sem Sev-1, tenant leakage, mismatch financeiro ou perda durável; SLOs do catálogo atendidos em ≥99% das janelas e backlog/DLQ dentro de SLI-QUE-01.  
**Paralelo permitido:** SCL-001/002 podem começar após o gate de estabilidade. O ramo do hub é obrigatoriamente sequencial: HUB-000 → GH1 → HUB-001 → HUB-003 → HUB-002; nenhum trabalho de consolidação, manutenibilidade versionada ou onboarding conta como habilitável antes do piloto real.

<read_first>

- Métricas e retrospectiva do piloto/hypercare
- `.planning/codebase/CONCERNS.md`, P2 de scaling, pagination, tenant fan-out e operational history
- seção Onda 7 do plano anterior, apenas como catálogo/visão; não como autorização de implementar 54 providers
- código de integração consolidado e contratos reais dos parceiros escolhidos

</read_first>

### SCL-001 — Dimensionar API, workers e uploads por SLO

- **Arquivos/módulos prováveis:** Docker/hosting config, Celery routes, Nginx, load tests.
- **Ação:** benchmark; separar pools API/upload/queues; autoscale por latency/saturation/queue age; direct/streaming upload; validar limites e custo; alinhar WSGI/ASGI apenas com evidência.
- **Teste e aceite:** por 60 min, sustentar 2× o pico de requests/s e uploads concorrentes medido nas 72 h de hypercare de 100% — e nunca menos que o perfil SLI-TEL-02 de 24 pings/s/tenant para 10 tenants — mantendo SLI-API-01/02 e SLI-QUE-01; scale-out inicia em ≤2 min após saturação/queue age, scale-in só após 15 min estáveis; RSS por worker fica dentro do limite registrado e não cresce linearmente com quantidade de uploads.
- **Gate executável:** load/soak tests com parâmetros e SHA registrados, queries do catálogo e capacity report reproduzível.
- **Rollback/compensação:** voltar replicas/route; backpressure protege núcleo.
- **Evidência:** modelo de capacidade.

### SCL-002 — Criar read models de posições e snapshots

- **Arquivos/módulos prováveis:** migrations/read model jobs, APIs cursor, `Corridas.tsx`, `Historico.tsx`, `Gerencial.tsx`.
- **Ação:** janelas tenant-scoped indexadas, retention e agregações; cursor pagination; incremental streams; remover endpoints que retornam vazio silenciosamente.
- **Teste e aceite:** dashboards/histórico têm dados duráveis e paginados; wrong tenant nega; query/retention cumprem budget.
- **Gate executável:** RLS, query-plan e load tests; gate universal migration.
- **Rollback/compensação:** read model reconstruível; writes core não dependem dele.
- **Evidência:** planos de query e freshness.

### HUB-000 — Homologar um provider piloto no núcleo existente

- **Dependências específicas:** HOM-003, 30 dias de estabilidade, QUE-001/002/003/006 e catálogo SLI/SLO congelado para o SHA.
- **Arquivos/módulos prováveis:** adapter e configuração de Delivery Direto, sandbox/stub assinado, testes integration/load/crash, queries de reconciliação e dossiê `docs/evidence/HUB-000/`.
- **Ação:** usar Delivery Direto como piloto inicial por já possuir HMAC documentado; se o sandbox comercial estiver indisponível, não substituir por provider unsigned — registrar bloqueio e manter GH1 fechado. No sandbox/conta controlada, provar assinatura sobre raw bytes, tamper/replay/timestamp, order inbound tenant-consistent, status outbound, worker kill em todos os boundaries, reconciliação bidirecional, circuit breaker/provider disable e carga. A evidência deve usar o mesmo SHA do adapter, migrations e dashboards.
- **Teste e aceite:** 100% casos de assinatura/tamper/replay verdes; evento aceito = envelope durável e audit projection redigida; crash/replay produz zero perda/duplicação; reconciliação diff=0; durante 24 h de soak, inbound success ≥99,5%, outbound ≥99,0%, p95 inbound→Order ≤10 s, p95 outbound ≤5 s, outbox oldest ≤300 s e DLQ não explicada=0. Provider é automaticamente desabilitado em abort threshold.
- **Gate executável:** contract/E2E com sandbox, fault injection, `k6`/Locust no volume registrado, queries SLI e `reconcile_provider --check DELIVERY_DIRETO`; GH1 só recebe PASS com manifest de SHA único.
- **Rollback/compensação:** desabilitar Delivery Direto, drenar/reconciliar outbox, consultar estado remoto antes de reenvio e preservar envelopes/auditoria.
- **Evidência:** dossiê provider→sandbox→assinatura→crash/replay→reconciliação→carga/SLO vinculado ao SHA.

### HUB-001 — Consolidar registry/capabilities para os 4 providers existentes

- **Dependências específicas:** HUB-000 e GH1 em PASS no mesmo baseline; esta aresta é bloqueante.
- **Arquivos/módulos prováveis:** integration base/registry/adapters/provider clients/models/migrations/tests/docs.
- **Ação:** interface canônica, registry, capability flags, circuit breaker, contract tests e métricas para iFood, 99Food, Delivery Direto e Anota AI; criar por migration Supabase o catálogo DB-first `ProviderDefinition` com `provider_key`, auth mode, capabilities, `config_schema`, docs/base URL e `active_by_default=false`, espelho Django `managed=False` e RLS/grants; o registry lê a definição ativa e valida config antes de instanciar adapter. Migrar primeiro o adapter pilotado sem alterar seu comportamento provado e depois os outros três; assinatura continua fail-closed; seed apenas dos quatro providers efetivamente homologados e nunca do catálogo de dezenas.
- **Teste e aceite:** novo adapter não exige `if/elif`; `ProviderDefinition` aplicado em staging é fonte de capabilities/config e nenhum provider não homologado está ativo/seeded; os 4 providers homologados mantêm SLO/replay/reconciliation; circuit breaker isola falha.
- **Gate executável:** unit/contract/integration/load por provider; gate universal para schema.
- **Rollback/compensação:** adapter por provider feature-flagged; outbox preserva eventos.
- **Evidência:** matriz capabilities e homologação.

### HUB-003 — Entregar manutenibilidade, filas por provider e compatibilidade versionada do hub

- **Dependências específicas:** HUB-000 e GH1 em PASS, depois HUB-001 concluído no mesmo baseline. HUB-003 é posterior ao piloto provider e bloqueia HUB-002; não pode ser antecipado nem depender de onboarding futuro.
- **Arquivos/módulos prováveis:** `backend/integration/base.py`, `registry.py`, adapters/provider clients/tasks/models/metrics, `backend/config/settings.py`, `backend/config/celery.py`, migration `supabase/migrations/<timestamp>_provider_schema_api_versions.sql`, Compose/EasyPanel worker pools, `docs/integrations/<provider>/README.md`/`CHANGELOG.md`, catálogo de deprecações, testes de contrato/carga.
- **Ação de filas/OAuth:** criar fila `integration.<provider_key>` e worker pool isolado para cada um dos quatro providers homologados, com routes derivadas do registry, acks/reject/prefetch/time limits herdados de QUE-005, concurrency/budget por provider e autoscaling/backpressure por queue age; worker de um provider não consome outro. Cachear OAuth em Redis com chave tenant+integration+provider+scopes+audience, TTL `expires_in` menos margem, single-flight lock para refresh, redaction completa e invalidação em 401/rotação; credenciais duráveis permanecem em secret store/StoreIntegration protegido, nunca no cache/log/evidência em plaintext.
- **Ação de versões/compatibilidade:** adicionar via migration `schema_version` ao envelope/schema canônico e `provider_api_version` à `ProviderDefinition`/eventos, com registry resolvendo adapter explicitamente por `(provider, provider_api_version, schema_version)` e sem fallback silencioso para versão incompatível. DTOs devem aceitar campos extras de provider de forma versionada e preservá-los somente no envelope protegido para replay/forense, enquanto campos obrigatórios, tipos e invariantes canônicos continuam strict; métrica/alerta registra novos nomes de campos sem PII. Manter fixtures v1/v2 e adapter paralelo durante janela de deprecação.
- **Ação de manutenção:** cada provider recebe `README.md`, exemplos redigidos e `CHANGELOG.md` vinculando mudança de API/schema a adapter, fixtures, data e migration. Criar catálogo `provider→api_version→deprecation/eol→owner→next_review_at`; job agendado consulta feed/metadata documentada quando existir e, quando o portal não oferecer interface automatizável, abre alerta por `next_review_at` vencido e exige revisão registrada do portal/changelog. Deprecação dentro da janela definida abre issue/alerta, bloqueia novo onboarding daquele provider e exige plano de migração testado.
- **Teste e aceite:** sobrecarregar/matar o worker de um provider não aumenta lag nem quebra os outros; cada fila tem pool, budget e métrica. Cem requests OAuth concorrentes fazem um refresh; token expira/invalida corretamente e nenhum token aparece em logs. Fixtures v1/v2 roteiam ao adapter correto; campos extras são aceitos/preservados sem mudar efeito canônico, campo obrigatório removido ou versão desconhecida falha fechada/DLQ; changelog existe para os quatro providers. Deprecação sintética e `next_review_at` vencido geram alerta com owner/prazo; nenhum provider com EOL sem plano pode ser habilitado.
- **Gate executável:** gate universal de migration; `celery -A config inspect active_queues` e load/fault por provider; testes Redis OAuth concurrency/TTL/401; contract matrix `(provider, api_version, schema_version, extra fields)`; linter verifica README/CHANGELOG/catálogo dos quatro providers; job de deprecation em modo fixture produz alerta. Gating exige SLI-WEB-01/SLI-QUE-01 por provider e zero leakage de tokens/PII.
- **Rollback/compensação:** desabilitar adapter/version/worker pool afetado e voltar registry para versão anterior ainda suportada; drenar/reconciliar sua fila sem mover mensagens para outro provider; invalidar OAuth cache e preservar envelopes/outbox. Schema usa expand/migrate/contract e não remove versão enquanto eventos retidos a referenciam.
- **Evidência:** mapa provider→fila→pool→budget, OAuth refresh timeline redigida, matriz de contratos/versionamento/extras, changelogs e relatório de deprecações vinculados ao SHA.

### HUB-002 — Onboarding incremental de novos providers, bloqueado por estabilidade

- **Dependências específicas:** HUB-001 e HUB-003 concluídos, GH1 ainda válido e checklist de onboarding do provider alvo aprovado; nenhum lote pode contornar essas quatro condições.
- **Arquivos/módulos prováveis:** `docs/integrations/<provider>/`, adapter/test fixtures, ProviderDefinition migration se necessária.
- **Ação:** priorizar por contrato comercial e sandbox; exigir docs/auth/signature/limits/status mapping/reconciliation/runbook/SLO e os contratos de fila/OAuth/schema/API version/changelog/deprecation de HUB-003; repetir por provider o subconjunto aplicável de HUB-000 e habilitar um pequeno lote por vez. O catálogo de ~54 do plano anterior é pesquisa, não escopo autorizado.
- **Teste e aceite:** cada provider tem assinatura, contract, load, sandbox e rollback; nenhum provider “sem doc pública” é habilitado; estabilidade do núcleo é reavaliada a cada lote.
- **Gate executável:** provider onboarding checklist e release gate dedicado.
- **Rollback/compensação:** desabilitar provider e drenar/reconciliar outbox; núcleo continua.
- **Evidência:** dossiê por provider.

## Plano de testes por camada

| Camada | Tipo | Infraestrutura | Casos mínimos | Gate |
|---|---|---|---|---|
| Python puro | unit/property | processo local | mappings, datas, state machines, CPF/validation, CNAB parser | PR |
| Django API | unit/contract | TestClient + fixtures | schemas, errors, route auth inventory, idempotency | PR |
| Persistência | integration | PostgreSQL 17/PostGIS + migrations Supabase | RLS, locks, triggers, constraints, indexes, upgrade | PR/release |
| Redis/Celery | integration/fault | Redis real + workers/beat | acks_late/reject/prefetch/queues, SIGKILL→requeue, lease, replay, overload, restart e stranded=0 | nightly/release |
| Storage | integration/security | bucket privado staging | policy, signed URL, scan, upload limits, outage | release |
| Finance | concurrency/invariant | Postgres+Storage reais | settlement, ledger, remittance/return, compensation, maker-checker | release bloqueante |
| Integrações | contract/E2E | stubs assinados + sandbox | forged/replay, remote/local crash boundaries, reconciliation | release/provider |
| Frontend | unit/contract/E2E | Vitest/RTL/MSW/Playwright + stack | auth, tenant, ride, finance rollback, errors | PR/release |
| Mobile | unit/contract/lint | JVM/MockWebServer | DI release, auth, DTO, journal, ViewModels, JWS/cache/version policy MOB-007 | PR |
| Mobile device | instrumented | emulator/device APIs suportadas | Keystore, backup, location, FCM, offline, permissions e rollback ao APK permitido | release |
| Sistema | E2E/chaos/load | staging production-like | two tenants, Redis loss, restore, deploy por digest/traffic rollback, OOM isolado e SLO | release |

## Threat model resumido

| Ameaça | Ativo/fronteira | Cenário | Mitigação e tarefas | Evidência obrigatória |
|---|---|---|---|---|
| Credenciais | repo/CI/secret store→Supabase | service role/DB/admin exposto e reutilizado | IR-001–IR-005; rotação, histórico, fail-closed, scanning | revogação antiga + scan zero |
| Tenant leakage | client/JWT/API/DB/worker | header/claim/RLS/worker acessa outra tenant | ID-001–ID-004, QA-SEC-001, ID-003 | matriz completa real RLS |
| Replay HTTP | web/mobile→API→DB | mesma key cruza tenant/ator/rota, body muda ou lease expira após commit | API-004 + constraints LOG/FIN/OFF | fingerprint/409/heartbeat/crash/Redis-loss / G2 |
| Forged webhook | internet→integration ingress | provider sem assinatura, replay/merchant guess | QUE-003, QUE-001/002, HUB-000 | evidência por provider/SHA, adulteração/replay/sandbox / G6/GH1 |
| Upload/prova | device/web→API→Storage | MIME spoof, malware, URL pública, cross-tenant | LOG-002/005 | bucket policy e testes negativos |
| Device token | Android→Fast Lane/FCM | token plaintext, backup, rota incompatível, revogação falha | MOB-002/004/005 | backup/logcat/revocation tests |
| Release mobile | servidor/secret store→APK | policy forjada/replayed libera versão revogada ou kill switch indisponível apaga comandos | MOB-007; policy JWS monotônica, cache curto e fail-safe | assinatura/replay/cache + rollback ao APK permitido sem perda de journal |
| Worker crash | broker→Celery→DB/provider | ack antecipado, worker perdido ou prefetch deixa billing/evento stranded | QUE-005 + idempotência FIN/QUE/OFF | SIGKILL→requeue→efeito único, unacked/stale=0 / G6/G7 |
| PII/LGPD | logs/audit/storage/database | headers/tokens/identificadores vazam, redaction corrompe payload operacional ou dados persistem demais | QUE-003, AUD-001, LOG-005, OBS-001; envelope protegido + projection redigida | copy-before-redact, sentinel/checksum, retention/DSAR drill |
| Dinheiro | API/worker/DB/banco | replay, race, lote parcial, retorno duplicado, maker=checker | FIN-001–FIN-005 | invariants, concurrency, CNAB, reconcile zero |

## Metas operacionais propostas de RPO/RTO

São hipóteses a confirmar com capacidade do provedor e ensaio HOM-001, não promessas comerciais:

| Domínio | RPO proposto | RTO proposto | Regra |
|---|---:|---:|---|
| PostgreSQL transacional/ledger | ≤ 5 min | ≤ 60 min | PITR/backup e restore drill; dinheiro reconciliado antes de reabrir writes |
| Provas/Storage | 0 após resposta 2xx; backup ≤ 15 min | ≤ 2 h | não confirmar upload antes de durabilidade/policy; journal retém pendência |
| Redis/runtime | 0 de estado de negócio | ≤ 15 min | DB/outbox/journal são autoridade; reconstrução automatizada |
| Mobile offline journal | 0 comando confirmado localmente | sync ≤ 15 min após rede voltar | IDs determinísticos e UI de pendência/conflito |
| Integrações/outbox | 0 evento aceito duravelmente | replay/recovery ≤ 30 min | lease/DLQ/reconciliation |
| Dashboard/read models | ≤ 15 min | ≤ 4 h | reconstruível; não bloqueia ledger/core |

## Catálogo inicial de SLI/SLO e decisões automáticas

Estes valores são **baselines iniciais bloqueantes**, não promessas comerciais. Podem ser recalibrados somente a partir de evidência de staging/HOM-001 ou do piloto, antes de congelar um novo release candidate, em mudança versionada com query, justificativa e aprovação. O release candidate corrente sempre obedece aos números registrados para seu SHA; é proibido relaxar limiar durante piloto/rollout para fazê-lo passar.

| ID | SLI e query/comando de decisão | Baseline obrigatório e janela | Responsável por resposta | Ação automática ao abort |
|---|---|---|---|---|
| SLI-API-01 | PromQL `histogram_quantile(0.95, sum by (le)(rate(http_request_duration_seconds_bucket{sha="$SHA"}[5m])))` e equivalente 0.99 | p95 ≤400 ms e p99 ≤1 s em cada janela de 5 min; abort se p95 >800 ms por 10 min ou p99 >2 s por 5 min | on-call backend | controlador volta traffic/feature flags ao estágio/SHA anterior |
| SLI-API-02 | `sum(rate(http_requests_total{sha="$SHA",status=~"5.."}[5m])) / sum(rate(http_requests_total{sha="$SHA"}[5m]))` | 5xx ≤0,5%; abort se >2% por 5 min; excluir somente health probes identificados | on-call backend | rollback de traffic; bloquear avanço e abrir incidente |
| SLI-TEL-01 | `k6 run -e TENANTS=10 -e RATE_PER_TENANT=12 -e DURATION=30m backend/tests/load/telemetry.js`; `max(redis_stream_oldest_seconds)` e contagem de event IDs | 10 tenants ×12 pings/s por tenant por 30 min; p95 ingest→Position ≤5 s, pending oldest ≤30 s, perda=0 e duplicação persistida=0 | on-call filas/localização | pausar expansão, aplicar backpressure e voltar consumers/SHA; perda>0 também bloqueia writes de tracking |
| SLI-TEL-02 | mesmo teste com 24 pings/s/tenant por 10 min e retorno a 12; medir `redis_stream_oldest_seconds` | após o burst, oldest volta a ≤30 s em até 10 min; abort se oldest >120 s por 5 min ou não recuperar em 10 min | on-call filas/localização | rollback de consumers e rate profile; preservar stream para replay |
| SLI-QUE-01 | SQL `SELECT max(extract(epoch FROM now()-created_at)) FROM integration_outbox WHERE status IN ('PENDING','PROCESSING')`; métricas de stale lease e DLQ | oldest ≤300 s, stale lease=0 após reclaim, DLQ não explicada=0 e DLQ/total <0,1% por 15 min; abort se oldest >600 s ou stale>0 por 10 min | on-call integrações | pausar provider/consumer afetado, voltar SHA e iniciar reclaim/reconcile |
| SLI-MOB-01 | SQL/metric `(applied + conflict_visible_within_15m) / accepted_commands` por versão/tenant; reconciliar IDs do journal e policy MOB-007 | ≥99,5% em 15 min, comando perdido=0 e pending oldest ≤15 min; abort se perda>0 ou razão <99% por 15 min | on-call mobile/logística | publicar policy MOB-007 assinada/monotônica que bloqueia o APK defeituoso, permite o APK anterior homologado e preserva journal |
| SLI-FIN-01 | `python manage.py reconcile_finance --check --format json` e query ledger débito=crédito por tenant/moeda | diferença não explicada=R$0, ledger imbalance=0 e 100% payouts com remittance/return reconciliado; uma única divergência é abort imediato | on-call financeiro | pausar payouts/manual approvals, voltar feature flag/SHA e iniciar compensação maker-checker |
| SLI-READY-01 | `min_over_time(service_readiness{sha="$SHA",service=~"django\|fastlane\|celery\|redis\|storage"}[5m])` e probe externo a cada 30 s | 100% das dependências obrigatórias ready; duas probes consecutivas 0 são abort | on-call deploy | retirar instância/RC do balanceador e voltar imagem anterior |
| SLI-ALERT-01 | três canários por RC com timestamps `fired_at`, `detected_at`, `ack_at` no incident sink | MTTD ≤5 min e acknowledgement ≤10 min em 3/3 canários; receiver ausente ou acima do limite bloqueia G8 | on-call primário | congelar rollout; se já iniciado, voltar um estágio até observabilidade recuperar |
| SLI-WEB-01 | métricas por provider: `INBOUND_ACK/INBOUND_TOTAL`, `OUTBOUND_SENT/OUTBOUND_TOTAL`, p95 audit→Order/sent e `reconcile_provider --check` | por provider habilitado: inbound ≥99,5%, outbound ≥99,0%, p95 inbound ≤10 s, p95 outbound ≤5 s e diff=0 em janelas de 15 min | on-call integrações | desabilitar apenas o provider, abrir circuit breaker e reconciliar antes de reativar |

**Error budget operacional:** para SLI-API-02, `consumo = bad_requests / (0,005 × total_requests)` no estágio. “Saudável” significa consumo ≤25% antes de avançar; amostra insuficiente nunca conta como saudável.

### Matriz advance/abort do rollout

| Estágio | Permanência e amostra mínimas | Condição de avanço | Abort automático |
|---|---|---|---|
| 5% | 60 min e 500 mutações | todos os SLI aplicáveis em ≥99% das janelas; error budget consumido ≤25%; zero invariantes críticas; policy MOB-007 referencia o APK/SHA do RC | qualquer abort SLI; volta para 0%/digests anteriores e bloqueia a versão mobile defeituosa |
| 25% | 4 h e 2.000 mutações | mesmos critérios, reconciliação financeira/logística no início e fim | qualquer abort SLI; volta para 5% e pausa payouts/provider se afetado |
| 50% | 24 h e 10.000 mutações | mesmos critérios; nenhum backlog com tendência positiva em 4 janelas consecutivas | qualquer abort SLI; volta para 25% |
| 100% | 72 h e 20.000 mutações de hypercare | mesmos critérios durante toda a janela; G0–G10 no mesmo SHA | qualquer abort SLI; volta para 50% ou SHA anterior conforme domínio |

**Abort imediato universal, sem janela:** qualquer tenant leak, credencial ativa exposta, webhook forjado aceito, diferença financeira não explicada, perda de proof/comando/evento durável ou corrupção de schema. O controlador desabilita a feature/provider, pausa payouts quando aplicável e desloca tráfego para o estágio anterior; nenhum sign-off manual pode suprimir o abort.

## Gates mínimos de go-live

| Gate | Condição mensurável | Bloqueia |
|---|---|---|
| G0 — Incidente/autoridade | DOC-001 aprovado pelo usuário: plano antigo bannered como `SUPERSEDED`, matriz corrigida/arquivada, auditor documental confirma este V2 como autoridade única; 100% credenciais afetadas revogadas/rotacionadas; antiga falha; histórico e clones tratados; admins/claims reconciliados; scan zero ativo | qualquer deploy |
| G1 — Identidade/tenant | matriz anônimo/driver/client/staff/platform admin/worker × same/wrong tenant × missing/old token 100% pass em RLS real | schema/API/feature rollout |
| G2 — Schema/API/idempotência | `supabase db push` staging e audit zero drift; wallet trigger/RLS/constraints/índices presentes; writes legados zero; API-004 prova namespace tenant+ator+método+rota, 409 por fingerprint divergente, lease/heartbeat, replay/TTLs/crash boundaries e ausência de `MemoryRedis` em staging/produção; API-005/CPF e AUD-001 verdes | logística/mobile/finanças |
| G3 — Logística | criação sem órfãos; conclusão/proof/geofence/check-in adversarial e concorrente 100% pass | settlement e piloto |
| G4 — Mobile | release usa `BuildConfig.API_BASE_URL`, sem MockInterceptor; auth refresh/revoke; contract, location, push e secure storage passam; OFF-001 + MOB-006 provam apply/conflict/DLQ/crash/replay; MOB-007 prova JWS/versão mínima/bloqueada/cache/fail-safe e rollback ao APK anterior homologado; SLI-MOB-01 atendido | APK piloto |
| G5 — Financeiro | concurrency/replay/ledger invariants/CNAB/maker-checker em banco real; reconcile difference = 0 | dinheiro real |
| G6 — Assíncrono/providers | QUE-005 efetiva `acks_late`, `reject_on_worker_lost`, prefetch=1, soft/hard limits e rotas/pools; SIGKILL comprova requeue idempotente, efeito único, `unacked=0` e nenhuma linha stranded; demais kill/reclaim/DLQ/replay/Redis loss passam; SLI-TEL-01/02 e SLI-QUE-01 atendidos; schedules registrados. **100% dos providers habilitados** têm verificador homologado no SHA do RC, tamper/replay/timestamp verdes, raw body protegido + audit projection redigida e evidência por provider; todo provider sem verificador permanece desabilitado. Headers/PII sentinels não aparecem em audit/log/export | carga piloto |
| G7 — CI | todos Django tests descobertos; backend real infra; suíte API-004 completa; CPF/audit/offline; fault test QUE-005 com worker real; frontend typecheck + linter real + unit/contract/E2E/FE-001; mobile unit/contract/lint/instrumented incluindo MOB-007; dependency-update config, SBOM e security scans verdes | merge/release |
| G8 — Operação | DOC-001 continua verde; DEP-000 registra modo EasyPanel real/fallback provado; DEP-001 publica GHCR por SHA/digest, aplica budgets comprovados por inspect/stats, passa pressure/OOM e faz deploy→5%→rollback automático ao digest anterior sem rebuild; SLI-READY-01 e SLI-ALERT-01 passam no mesmo SHA; readiness, Redis TLS/auth, redaction e restore atendem RPO/RTO; 3/3 canários MTTD≤5 min/ack≤10 min; on-call e runbooks exercitados | piloto |
| G9 — Piloto | 7 dias completos, 2 tenants, 5–10 drivers; zero Sev-1/leak/forgery/loss/mismatch; todos os SLI aplicáveis em ≥99% das janelas, reconciliação diária zero e qualquer abort reinicia o piloto com novo RC | rollout amplo |
| G10 — Rollout | 5%≥60 min/500 mutações →25%≥4 h/2.000 →50%≥24 h/10.000 →100%≥72 h/20.000; advance/abort machine-readable usa o modo DEP-000 e os mesmos digests/SHA do RC, error budget consumido ≤25%; rollback automático de tráfego ao digest anterior e rollback mobile MOB-007 ao APK permitido foram testados sem rebuild/perda de journal; evidência por estágio | encerramento hypercare |

### Gate pós-go-live de expansão do hub

| Gate | Condição mensurável | Bloqueia |
|---|---|---|
| GH1 — Provider piloto | HUB-000/Delivery Direto no mesmo SHA: sandbox autenticado, 100% tamper/replay/timestamp pass, crash boundaries sem perda/duplicação, reconciliação diff=0, soak 24 h com SLI-WEB-01 e SLI-QUE-01, audit projection redigida e rollback/provider-disable testado | HUB-001, HUB-003 e HUB-002 |

## Checklist do piloto

- [ ] Release candidate e migrations congelados por SHA/manifest.
- [ ] Duas tenants e papéis separados; dados sintéticos/consentidos.
- [ ] Driver devices cadastrados, revogação testada e MOB-007 exercitado: policy assinada, cache/fail-safe, versão bloqueada e retorno ao APK anterior homologado sem perda do journal.
- [ ] Create→accept→start→arrive→proof→complete→settle exercitado.
- [ ] Cancel/reassign, rede instável, app morto, reboot e conflito offline exercitados.
- [ ] FCM offer/cancel/reassign e fallback operacional testados.
- [ ] Withdrawal/remittance/return apenas em sandbox/conta controlada, com maker-checker.
- [ ] Inventário por provider no SHA: somente verificador homologado habilitado; tamper/replay/timestamp, envelope protegido e audit projection redigida comprovados.
- [ ] Dashboards e queries SLI-API/TEL/QUE/MOB/FIN/READY, alertas, on-call, status page e LGPD incident path ativos; 3/3 canários cumprem MTTD≤5 min e ack≤10 min.
- [ ] Reconciliação diária de orders, positions, proofs, ledger, withdrawals, outbox e journal.
- [ ] Rollback de tráfego pelo modo DEP-000/DEP-001 ao digest/SHA anterior, rollback mobile via MOB-007, Redis rebuild e restore ensaiados.
- [ ] Controlador de abort testado: qualquer tenant leak, credencial ativa, forged webhook aceito, ledger mismatch, perda de prova/comando/evento ou limiar SLI retrocede estágio e pausa o domínio afetado automaticamente.

## Rollback operacional por classe

| Classe | Estratégia primária | Compensação/observação |
|---|---|---|
| Auth/RBAC | revogar tokens/sessões, desligar rota/feature, voltar SHA compatível | não relaxar auth para restaurar serviço |
| Schema | expand/migrate/contract e migration compensatória | PITR apenas em corrupção; preservar writes já confirmados |
| Logística | pausar comandos, preservar journal/outbox, reconciliar estado | transição terminal corrigida por evento auditado |
| Mobile | publicar policy MOB-007 assinada/monotônica: bloquear versão defeituosa, permitir APK/SHA anterior homologado e revogar device tokens quando necessário | cache fail-safe não libera policy inválida; journal local não é apagado |
| Dinheiro | pausar payouts, reconcile, reversal/compensating entry | nunca editar/apagar ledger histórico |
| Filas/providers | abrir circuit breaker, pausar consumer/provider, reclaim/DLQ/replay | verificar sucesso remoto antes de reenviar |
| Deploy | controlador DEP-001 usa modo DEP-000 para traffic shift ao digest/SHA anterior homologado, sem rebuild/tag mutável | schema deve permanecer backward-compatible; manifest prova digest ativo |

## Reconciliação com o plano anterior

Esta tabela é deliberadamente um-a-um: **55 IDs anteriores, 55 linhas**. Foi reauditada integralmente nesta revisão: **51 COBERTO e 4 DIFERIDO**. “COBERTO” exige ação, aceite e gate concretos neste V2; “DIFERIDO” exige ID de backlog, prioridade, justificativa, condição objetiva de retomada e destino. Nenhum item depende apenas de leitura, intenção ou tarefa de onda futura para receber `COBERTO`.

| ID/requisito anterior | Destino V2 | Tratamento executável ou diferimento explícito | Status |
|---|---|---|---|
| T0-01 — CORS | ID-006 / G1 | allowlist por ambiente, testes origin/preflight; executado depois de identidade/RBAC | COBERTO |
| T0-02 — JWT fail-closed | ID-001 / G1 | verificador único com assinatura, issuer/audience/JWKS/revogação e negativos | COBERTO |
| T0-03 — auth global panel | ID-003 / G1 | RBAC default-deny e inventário de 100% das rotas panel/`/db` | COBERTO |
| T0-04 — remover identity headers | ID-004 / G1 | tenant session server-issued e testes de headers/localStorage forjados | COBERTO |
| T0-05 — webhook fail-closed | QUE-003 / G6 | verificador por provider, replay/timestamp e providers unsigned desabilitados | COBERTO |
| T0-06 — segredo de IA fora do bundle | IR-005 / G0/G7 | scan do bundle e configuração server-side obrigatória sem expor valor | COBERTO |
| T0-07 — MockInterceptor só debug | MOB-001 / G4 | source set release sem classe/referência e inspeção do APK | COBERTO |
| T0-08 — BASE_URL por BuildConfig | MOB-001 / G4 | release falha sem URL HTTPS não-local e contract smoke em staging | COBERTO |
| T0-09 — defaults inseguros | IR-005 + DEP-001 / G0/G8 | startup fail-closed, secret store e manifests sem fallback | COBERTO |
| T0-10 — conflito de homologação | DOC-001 / G0; revalidação HOM-001 | plano antigo recebe banner `SUPERSEDED`, matriz é corrigida/arquivada com revisão do usuário e auditor automatizado garante o V2 como autoridade única antes de deploy | COBERTO |
| T1-01 — settlement por order | FIN-001 / G5 | unique constraints, locks, transaction reference e replay concorrente | COBERTO |
| T1-02 — Celery acks/time limits | QUE-005 + QA-004 / G6/G7 | settings explícitos para `acks_late`, `reject_on_worker_lost`, prefetch=1, soft/hard limits e rotas/pools; SIGKILL prova requeue idempotente, efeito único, unacked/stale=0 | COBERTO |
| T1-03 — healthchecks/depends_on | DEP-001 / G8 | liveness/readiness por dependência e failure injection | COBERTO |
| T1-04 — restart policy | DEP-001 / G8 | restart/resources e container kill/recovery drill | COBERTO |
| T1-05 — migration job único | SCH-001 + DEP-001 / G2/G8 | Supabase push/job único, schema retrocompatível e promoção bloqueada em falha | COBERTO |
| T1-06 — resource limits | DEP-001 + SCL-001 / G8 | budgets CPU/memória concretos por serviço/pool, `docker inspect/stats`, pressure/OOM isolado e recalibração somente por evidência de staging antes do RC; autoscale pós-go-live | COBERTO |
| T1-07 — race Wallet/Invoice | FIN-001 / G5 | lock order/wallet/invoice, get-or-create seguro e teste 2–20 concorrentes | COBERTO |
| T1-08 — lock TTL/body hash | API-004 / G2/G7 | namespace completo, fingerprint canônico, lease/heartbeat, 409 e replay | COBERTO |
| T1-09 — MemoryRedis TTL | API-004 / G2/G7 | TTL correto só em test/dev e fallback proibido em staging/produção | COBERTO |
| T1-10 — Redis TLS/auth | DEP-004 / G8 | `rediss` externo, ACL/password, certificado/boundary e negativos fail-closed | COBERTO |
| T2-01 — Sentry/Crashlytics | OBS-001 / G8 | crash reporting web/mobile, redaction e canários SLI-ALERT-01 | COBERTO |
| T2-02 — handler global panel | API-001/API-002 / G2/G7 | erros tipados, correlation ID e remoção de catch-all/sucesso aparente | COBERTO |
| T2-03 — exceções de domínio finance | API-001 + FIN-001–005 | erros de negócio tipados e sem `ValueError`/500 opaco nos comandos financeiros | COBERTO |
| T2-04 — correlation IDs | OBS-001 + AUD-001 / G8 | propagação ingress→workers→provider/audit e teste ponta-a-ponta | COBERTO |
| T2-05 — logging estruturado | OBS-001 / G8 | JSON em todos ambientes, redaction e labels de SHA | COBERTO |
| T2-06 — rotação de logs Docker | DEP-001 / G8 | log rotation/retention e teste de limite de disco | COBERTO |
| T2-07 — ErrorBoundary raiz | FE-001 / G7/G8 | boundary na raiz, fallback recuperável e report remoto por correlation ID | COBERTO |
| T3-01 — integração PostGIS real | QA-001 / G7 | Postgres/PostGIS/Redis reais, discovery completo e skips P0/P1 zero | COBERTO |
| T3-02 — testes auth/RBAC/JWT | QA-SEC-001 / G1/G7 | matriz real por papel/tenant/token e forged-token negatives | COBERTO |
| T3-03 — Vitest/Testing Library | QA-002 / G7 | runner unit/DOM/contract/E2E e artifacts de falha | COBERTO |
| T3-04 — contratos Retrofit/CI | MOB-003 + QA-003 / G4/G7 | MockWebServer/contracts, unit/lint/instrumented e release gate | COBERTO |
| T3-05 — deploy automatizado | DEP-000 + DEP-001 + HOM-003 / G8/G10 | GitHub Actions→GHCR por SHA/digest→hook/API EasyPanel provado ou blue/green SSH+Nginx; credencial protegida, manifest, traffic switch e rollback E2E ao digest anterior sem rebuild | COBERTO |
| T3-06 — scans + updates automáticos | IR-005 + DEP-002 / G0/G7 | gitleaks/SBOM/audits e Dependabot/Renovate semanal para pip/npm/Gradle/Actions | COBERTO |
| T3-07 — lint/paths/schema drift | QA-002 + QA-003 + SCH-001 / G2/G7 | linter frontend bloqueante, CI por paths e audit de schema Supabase autoritativo | COBERTO |
| T4-01 — DSAR | BKL-LGPD-001 | P1 conformidade; diferido porque o código atual sugere privacy flows mas falta gap analysis, identidade do titular e decisão legal. Retomar quando data map + parecer do DPO + inventário dos flows existentes estiverem aprovados; destino: fase LGPD antes de ampliar tenants/uso de PII | DIFERIDO |
| T4-02 — AuditEvent | AUD-001 / G2/G7 | modelo append-only, RLS, redaction e instrumentação das ações críticas | COBERTO |
| T4-03 — pgcrypto PII | BKL-LGPD-002 | P2/revisão arquitetural; faltam key management, lookup, rotação e análise legal. Retomar quando threat model cripto, KMS, plano de backfill/rollback e data classification estiverem aprovados; destino: fase de proteção PII, sem adiar RLS/redaction atuais | DIFERIDO |
| T4-04 — CPF com dígitos verificadores | API-005 / G2/G7 | validator canônico implementado em todos os schemas/rotas e testes positivos/negativos | COBERTO |
| T5-01 — TrackingService real | MOB-004 / G4 | Fused Location, buffer, WorkManager, auth/device e teste background/reboot | COBERTO |
| T5-02 — forced update | MOB-007 / G4/G9/G10 | endpoint server-authoritative com min/blocked versions, mutation autenticada, policy JWS, cache ≤5 min, fail-safe e rollback testado ao APK anterior antes do piloto | COBERTO |
| T5-03 — AuthContext loading | FE-001 / G7 | `finally setIsLoading(false)`, timeout/rejeição/revogação e teste anti-spinner infinito | COBERTO |
| T5-04 — acessibilidade alert/live | FE-001 / G7 | `role=alert/status`, `aria-live`, axe e leitor de tela | COBERTO |
| T5-05 — certificate pinning | BKL-MOB-002 | P2/revisão; pinning sem backup/rotação pode bloquear a frota. Retomar após MOB-001/002 e MOB-007 verdes, ownership de certificados, dois pins válidos e runbook de rotação; destino: hardening mobile pré-distribuição pública | DIFERIDO |
| T6-01 — runbook operacional | DEP-001 + OBS-001 + HOM-001 / G8 | deploy/rollback/incidente/Redis/provider/finance exercitados e medidos | COBERTO |
| T6-02 — diagramas ER/sequência | SCH-001 + API-001 | catálogo ER gerado do schema autoritativo e sequência API→DB→outbox anexada aos contratos/evidência | COBERTO |
| T6-03 — ADRs | BKL-DOC-001 | P3; registrar depois de as decisões passarem G2/G8 evita documentar hipótese instável. Retomar imediatamente após G8 com decisões já provadas; destino: ADRs de schema, idempotência, Redis e deploy antes do encerramento de HOM-002 | DIFERIDO |
| T7-01 — onboarding checklist | HUB-002 | checklist por provider com docs, sandbox, auth, signature, mappings, SLO e runbook | COBERTO |
| T7-02 — ABC/registry/circuit breaker | HUB-001 | consolidação somente após HUB-000/GH1, com migração dos 4 adapters | COBERTO |
| T7-03 — ProviderDefinition DB-first | HUB-001 | migration Supabase, capabilities/config schema e sem seed de providers não homologados | COBERTO |
| T7-04 — dedupe webhook inbound | QUE-003 + AUD-001 / G6 | event identity unique, replay seguro e envelope/audit separados | COBERTO |
| T7-05 — testes hub | HUB-000/HUB-001/HUB-003/HUB-002 + G6/GH1 | contract, sandbox, crash/replay, filas/OAuth/versões, carga e homologação por provider | COBERTO |
| T7-06 — SLI/SLO hub | SLI-WEB-01 + OBS-001 + HUB-000 | queries/limiares explícitos, dashboard por provider e abort automático | COBERTO |
| T7-07 — fases do hub | HUB-000 → GH1 → HUB-001 → HUB-003 → HUB-002 | substitui cronograma fixo por dependências/gates executáveis sem permitir expansão prematura | COBERTO |
| T7-08 — manutenção/escala/versões | HUB-003 após HUB-000/GH1/HUB-001 | filas e pools por provider, OAuth cache Redis, `schema_version`/`provider_api_version`, tolerância versionada a extras, changelog por provider e monitoramento/alerta de deprecações com testes/gate | COBERTO |
| T7-09 — sync bidirecional | QUE-002/QUE-006 + HUB-000/HUB-002 | reconciliation, diff=0, replay auditado e validação em sandbox por provider | COBERTO |

## Backlog explícito e diferimentos

| ID | Item | Prioridade | Condição objetiva de retomada | Destino e justificativa |
|---|---|---:|---|---|
| BKL-LGPD-001 | DSAR | P1 conformidade | data map, gap analysis dos privacy flows, identidade do titular e parecer DPO aprovados | fase LGPD antes de ampliar tenants/PII; evita duplicar subsistema sem omitir a obrigação |
| BKL-LGPD-002 | criptografia ampla de PII | P2/revisão | threat model cripto, KMS, rotação, lookup, backfill e rollback aprovados | fase proteção PII; mudança irreversível não pode ser improvisada, enquanto RLS/redaction/retention seguem agora |
| BKL-MOB-002 | certificate pinning | P2/revisão | ownership de certificado, primary+backup pins, rotação, MOB-007 verde e testes em staging | hardening antes de distribuição pública; pin incompleto pode bloquear toda a frota |
| BKL-DOC-001 | ADRs de decisões-chave | P3 | G2 e G8 aprovados com decisões reais de schema/idempotência/Redis/deploy | registrar ADRs antes do encerramento de HOM-002; evita cristalizar hipótese não validada |

Forced update deixou de ser backlog e agora é ação/gate pré-piloto de MOB-007/G4/G9/G10. O linter frontend segue como ação/gate explícito de QA-002/G7. A expansão para dezenas de providers não é um diferimento solto: permanece tarefa HUB-002, bloqueada por HUB-000, GH1, HUB-001 e HUB-003.

## Matriz de rastreabilidade dos findings de `CONCERNS.md`

Cada heading P0/P1 e cada P2 material tem uma tarefa, teste e gate. P2 pós-go-live permanece coberto por Onda 8, não silenciado.

| ID | Finding/heading | Pri. | Tarefa(s) | Teste/gate |
|---|---|---:|---|---|
| TD-01 | Parallel API surfaces implement incompatible business rules | P1 | API-001/002 | contracts + legacy traffic zero / G2 |
| TD-02 | Database schema has two migration authorities | P1 | SCH-001 | clean bootstrap + trigger/RLS audit / G2 |
| TD-03 | Financial compatibility layer bypasses maker-checker design | P1 | FIN-004 | maker-checker concurrency/E2E / G5 |
| TD-04 | Large UI and API modules concentrate unrelated responsibilities | P2 | API-003 | characterization/contracts |
| TD-05 | Error handling converts failure into empty/apparently successful state | P2 | API-001/002, FIN-004, OBS-001 | error contract/E2E / G7 |
| TD-06 | Client-controlled tenant hints coexist with JWT/RLS | P2 | ID-004 | forged header tests / G1 |
| BUG-01 | Courier release never calls production APIs | P0 | MOB-001 | release DI/APK/staging / G4 |
| BUG-02 | Primary panel ride creation leaves orphan orders | P0 | LOG-001 | fault injection atomicity / G3 |
| BUG-03 | Bank return task can never mark withdrawals paid | P0 | FIN-003 | CNAB valid/replay/failure / G5 |
| BUG-04 | Denylisted withdrawal rolls back tenant batch | P1 | FIN-002 | mixed batch + no debit / G5 |
| BUG-05 | Remittance reports success without storage | P1 | FIN-002, DEP-003 | storage outage fault test / G5 |
| BUG-06 | Inbound orders omit mandatory tenant ownership | P1 | QUE-002 | inbound E2E/RLS / G6 |
| BUG-07 | Inbound status transitions silently discarded | P1 | QUE-002 | out-of-order/reconcile/DLQ / G6 |
| BUG-08 | Outbox consumers race/strand work | P1 | QUE-001 | worker-kill/lease/reclaim / G6 |
| BUG-09 | One courier auto-arrives another delivery | P1 | LOG-003 | two-driver PostGIS/Redis / G3 |
| BUG-10 | Completed/canceled stops remain GEO | P1 | LOG-003 | terminal/reconcile/cardinality / G3 |
| BUG-11 | Fileless proof violates schema | P1 | LOG-002 | proof-mode matrix / G3 |
| BUG-12 | Retrofit contracts mismatch backend | P1 | MOB-003/API-004 | mobile contract + idempotency suite / G2/G4 |
| BUG-13 | Legacy device token unusable by Fast Lane | P1 | MOB-004 | issuer/fast-lane/revoke / G4 |
| BUG-14 | Manual financial data local-only/incompatible | P1 | FIN-004 | frontend rollback/reload/E2E / G5 |
| SEC-01 | Privileged credentials committed | P0 | IR-001/002/005 | revocation + history scan / G0 |
| SEC-02 | Script grants every Auth user platform-admin | P0 | IR-003/004 | negative command + reconciliation / G0 |
| SEC-03 | Authenticated users invoke global/tenant-admin operations | P0 | ID-003 | route RBAC matrix / G1 |
| SEC-04 | Panel API lacks route-level auth/RBAC | P1 | ID-003 | route inventory + negatives / G1 |
| SEC-05 | JWT tenant/role claim contract inconsistent | P1 | ID-002 | claims/RLS real DB / G1 |
| SEC-06 | Known JWT fallback secret can forge tokens | P1 | ID-001/IR-005 | forged/config-missing tests / G1 |
| SEC-07 | Static passwords and immediate confirmation | P1 | ID-005 | invite/expiry/session tests / G1 |
| SEC-08 | Unsigned webhook providers forge events | P1 | QUE-003/HUB-000 | tamper/replay/provider evidence por SHA / G6/GH1 |
| SEC-09 | Webhook audit stores sensitive headers | P1 | QUE-003/AUD-001/OBS-001 | envelope protegido + audit projection/redaction/retention / G6/G8 |
| SEC-10 | Courier token plaintext and backup eligible | P1 | MOB-002 | Keystore/backup/log test / G4 |
| SEC-11 | Upload validation arbitrary/public | P1 | LOG-005 | spoof/malware/privacy / G3 |
| SEC-12 | Proof signed URL disagrees with stored value | P1 | LOG-005 | canonical key/signed URL/cross-tenant / G3 |
| SEC-13 | CORS permissive with credentials | P2 | ID-006 | origin/preflight tests / G1 |
| SEC-14 | RLS bypass by owner/background roles | P2 | ID-002, QA-SEC-001 | owner/worker role matrix / G1 |
| PERF-01 | Telemetry capacity below modest fleet | P1 | QUE-004 | load/lag test / G6 |
| PERF-02 | Telemetry claim/ack non-atomic/non-idempotent | P1 | QUE-004 | two consumer/crash/replay / G6 |
| PERF-03 | GEO indexes grow without cleanup | P1 | LOG-003 | cardinality/stale reconciliation / G3 |
| PERF-04 | Broad list endpoints lack cursor pagination | P2 | API-002 | pagination/query budget |
| PERF-05 | Periodic workers scan tenants serially | P2 | QUE-005 | fan-out/tenant lag + route/pool registry + worker-kill requeue / G6/G7 |
| PERF-06 | Upload buffers whole files | P2 | LOG-005, SCL-001 | concurrent upload memory/413 |
| FRAG-01 | Withdrawal lifecycle/ledger compensation | P0 | FIN-002/003/005 | lifecycle/reconcile/compensation / G5 |
| FRAG-02 | Settlement not independently idempotent | P1 | FIN-001 | DB replay/concurrency / G5 |
| FRAG-03 | Delivery completion trusts client state/time | P1 | LOG-002 | adversarial completion / G3 |
| FRAG-04 | Redis concurrency with incomplete DB recovery | P1 | API-004, DEP-004, QUE-006, LOG-003, MOB-004 | durable command/Redis loss/rebuild/TLS / G2/G6/G8 |
| FRAG-05 | Integration outbox lacks lease/DLQ | P1 | QUE-001 | kill/reclaim/DLQ/replay / G6 |
| FRAG-06 | Check-in accepts cross-tenant shift IDs | P1 | LOG-004 | wrong-tenant/location matrix / G3 |
| FRAG-07 | JWT remote fallback hard to reason about | P2 | ID-001 | rotation/timeout/issuer/aud tests / G1 |
| FRAG-08 | Production composition weak readiness/recovery | P2 | DEP-000/DEP-001 | EasyPanel preflight, cgroup/OOM, container/dependency e digest rollback drill / G8 |
| SCALE-01 | Telemetry ceiling ~4.17 pings/s/operator | P1 | QUE-004 | fleet capacity test / G6 |
| SCALE-02 | Mobile has no offline delivery capacity | P1 | OFF-001/MOB-006 | backend processor + airplane/restart/conflict replay / G4 |
| SCALE-03 | Fixed WSGI/scheduler no autoscaling signal | P2 | OBS-001, SCL-001 | metrics/load/autoscale; pós-go-live scale |
| SCALE-04 | Position/snapshot APIs lack operational history | P2 | SCL-002 | RLS/query/freshness; pós-go-live read model |
| DEP-01 | Container installs not reproducible | P2 | DEP-002 | clean build/SBOM diff / G7 |
| DEP-02 | Supabase client absence inconsistent | P2 | DEP-003 | missing-client fault tests / G8 |
| DEP-03 | Android release gates disabled | P2 | QA-003 | lint/test/instrumented required / G7 |
| MISS-01 | Production courier auth/networking | P0 | MOB-001/002 | release network/auth / G4 |
| MISS-02 | Background location ingestion | P1 | MOB-004 | instrumented + ingestion / G4 |
| MISS-03 | Push registration/handling | P1 | MOB-005 | token lifecycle + delivery / G4 |
| MISS-04 | Offline command processing/conflict resolution | P1 | OFF-001/MOB-006 | processor/DLQ + offline E2E/replay / G4 |
| MISS-05 | Scheduled finance/document operations | P1 | QUE-005 | schedule registry + idempotency / G6 |
| MISS-06 | Manual-entry approval/rejection | P1 | FIN-004 | maker-checker/RLS/E2E / G5 |
| MISS-07 | Dead-letter/replay/reconciliation operations | P1 | QUE-001/006 | DLQ/replay/Redis loss / G6 |
| MISS-08 | Observability beyond logs | P2 | OBS-001 | canary/dashboard/alerts / G8 |
| TEST-01 | CI omits Django app tests | P0 | QA-001 | collect-only + full pytest / G7 |
| TEST-02 | No mobile API-contract/release behavior tests | P0 | QA-003, MOB-001–007 | release suite incluindo version policy/rollback / G4/G7 |
| TEST-03 | No frontend unit/E2E runner | P1 | QA-002 | unit/contract/E2E / G7 |
| TEST-04 | RLS/auth not tested with production roles | P1 | QA-SEC-001 | real RLS matrix / G1 |
| TEST-05 | Financial failure paths uncovered | P1 | FIN-001–005, QA-004 | real DB/fault/CNAB / G5 |
| TEST-06 | Integration crash/replay untested | P1 | QUE-001–003, QA-004 | kill/replay/forgery / G6 |
| TEST-07 | Telemetry/geofence concurrency untested | P1 | LOG-003, QUE-004 | real Redis/PostGIS/load / G3/G6 |
| TEST-08 | Storage privacy/evidence untested | P1 | LOG-002/005 | bucket/proof/cross-tenant / G3 |
| TEST-09 | Deployment smoke/readiness absent | P2 | DEP-000/DEP-001, HOM-001 | bootstrap/failure/restore + deploy 5%/rollback ao digest anterior / G8 |
| P3-01 | Frontend lint is second TypeScript check | P3 | QA-002 | linter real bloqueante separado de typecheck / G7 |

## Auditoria de cobertura das fontes

| Fonte | Item | Cobertura | Status |
|---|---|---|---|
| GOAL | prontidão de produção sem problemas confirmados | Ondas -1–8 + G0–G10 | COBERTO |
| REQ | 1 veredito/premissas/no-go-live | início + gates | COBERTO |
| REQ | 2–3 P0/P1/P2 e rastreabilidade | matriz de findings | COBERTO |
| REQ | 4 incidente antes de CORS | Onda -1; ID-006 | COBERTO |
| REQ | 5 ondas mínimas e pós-go-live provider gate | Ondas 0–8 | COBERTO |
| REQ | 6 conteúdo executável por onda | objetivos, dependências, tasks, leitura, aceite, gate, rollback, evidência | COBERTO |
| REQ | 7 migrations Supabase completas/push staging | regra universal + tasks de schema | COBERTO |
| REQ | 8 matriz multi-tenant | QA-SEC-001/G1 | COBERTO |
| REQ | 9 mobile tratado como protótipo | Onda 3/G4 | COBERTO |
| REQ | 10 finanças reais/locks/replay/double-entry/CNAB/maker-checker | Onda 4/G5 | COBERTO |
| REQ | 11 threat model | seção threat model | COBERTO |
| REQ | 12 gates/piloto/rollback/RPO/RTO/observabilidade | catálogo SLI/SLO, matriz advance/abort, G0–G10 e GH1 | COBERTO |
| REQ | 13 testes por camada e CI | Onda 6 + tabela de testes | COBERTO |
| REQ | 14 estimativa relativa com hipótese | seção abaixo | COBERTO |
| REQ | 15 caminho crítico e commits atômicos | caminho crítico + lote inicial | COBERTO |
| REQ | 16–17 preservar arquivo anterior e não revelar segredos | premissas/IR evidence | COBERTO |
| CONTEXT | plano anterior preservado como histórico/reconciliado | 55/55 IDs T0-01–T7-09 em linhas individuais; 51 cobertos + 4 diferidos com condição/destino; DOC-001 elimina autoridades conflitantes | COBERTO |
| CONTEXT | REV2-01 precedência documental/T0-10 | declaração de autoridade no topo + DOC-001/G0 + revalidação HOM-001 | COBERTO |
| CONTEXT | REV2-02 crash/requeue Celery | QUE-005 + G6/G7: settings, filas/pools e SIGKILL→requeue→efeito único/stale=0 | COBERTO |
| CONTEXT | REV2-03 rollback mobile executável | MOB-007 + HOM-002/003 + G4/G9/G10 + SLI/rollback/checklist | COBERTO |
| CONTEXT | REV2-04 escopo integral T7-08 | HUB-003 após HUB-000/GH1/HUB-001 e antes de HUB-002 | COBERTO |
| CONTEXT | REV2-05 budgets CPU/memória | DEP-001: valores por serviço/pool + inspect/stats + pressure/OOM | COBERTO |
| CONTEXT | REV2-06 deploy reproduzível EasyPanel | DEP-000 preflight + DEP-001 GitHub Actions/GHCR/digests/Nginx/fallback + HOM-003 E2E | COBERTO |
| RESEARCH | todos os headings materiais de CONCERNS | matriz TD/BUG/SEC/PERF/FRAG/SCALE/DEP/MISS/TEST | COBERTO |

## Estimativa relativa de execução

Hipótese: repositório no estado de 2026-08-11, acesso a staging/Supabase/CI/Android disponível e nenhum requisito comercial novo durante a correção. As faixas não são compromisso de prazo.

| Cenário | Faixa relativa | Hipótese |
|---|---|---|
| 1 engenheiro full-time + agentes, sequência segura | 20–32 semanas equivalentes | um fluxo principal; paralelismo só em testes/frontend/mobile sem conflito |
| 3 engenheiros experientes + agentes | 10–17 semanas equivalentes | ownership backend/security-finance, mobile, QA/infra; revisões cruzadas |
| Esforço relativo por bloco | -1/0/1: 25–35%; 2–5: 40–50%; 6–7: 20–30%; 8: contínuo | incerteza maior em credenciais históricas, RLS real, CNAB/sandbox e Android background |

Reestimar após G0, G2 e G4/G5, usando evidência de migrations, contratos externos e suites reais. Não comprimir piloto, restore drill ou rollout para “recuperar prazo”.

## Lote inicial de commits atômicos

1. `docs(DOC-001): supersede conflicting release authorities` — diff revisado pelo usuário, matriz corrigida/arquivada e auditor documental verde.
2. `security(IR-001): inventory and rotate exposed credentials` — evidência sem segredos; alterações de configuração mínimas.
3. `security(IR-002): purge revoked credentials from git history` — reescrita controlada e mapa de SHAs.
4. `security(IR-003): quarantine bulk platform-admin tooling` — remover caminho em massa.
5. `feat(IR-003): add allowlisted single-admin management command` — comando + testes negativos.
6. `security(IR-004): reconcile platform admins claims and sessions` — script/query read-first e correções auditadas.
7. `ci(IR-005): block committed secrets and unsafe production defaults` — scanner/config fail-closed.
8. `test(ID-001): add failing forged expired issuer audience JWT cases` — RED.
9. `security(ID-001): centralize verified JWT claims` — GREEN.
10. `test(QA-SEC-001): add real Postgres RLS role tenant matrix` — inicialmente falha onde há gap.
11. `feat(ID-002): add canonical claims and RLS migration` — inclui SQL/ORM/test; push staging é evidência separada.
12. `security(ID-003): default-deny sensitive route inventory` — RBAC + contract tests.
13. `feat(ID-004): issue server-validated tenant sessions` — backend antes do frontend.
14. `refactor(ID-004): remove client identity authorization headers` — após servidor disponível.
15. `test(SCH-001): assert clean Supabase bootstrap objects` — gate antes de consolidação.
16. `feat(SCH-001): converge wallet triggers into Supabase migrations` — forward-only.

Cada commit deve citar o ID, incluir o comando de verificação e evitar misturar schema, refactor e rollout na mesma unidade. O `supabase db push` em staging não é “efeito colateral” do commit: é gate operacional registrado com SHA e resultado.

## Pré-mortem do plano

| Falha provável | Sinal precoce | Mitigação incorporada |
|---|---|---|
| Corrigir endpoints sem fechar o contrato de tenant/schema | adapters e clients continuam divergindo; RLS exige relaxamento | Ondas 0–1 bloqueantes, G1/G2 e contracts versionados |
| Testes verdes em mocks escondem falhas reais | SQLite/MemoryRedis passa, staging falha em lock/RLS | QA-001/004 exigem Postgres/PostGIS/Redis/Storage reais |
| Rollout financeiro/assíncrono duplica efeitos | mismatch, stuck PROCESSING, provider recebeu sem commit | FIN invariants + outbox lease/replay + reconciliação e abort thresholds |
| Mobile “funciona” só em debug | release contém mock/localhost e CI só monta APK | MOB-001/QA-003/G4 inspecionam release e staging |
| Expansão comercial interrompe hardening | novos providers aumentam superfície antes do core | HUB-002 bloqueado por 30 dias de estabilidade e onboarding individual |

## Critério de encerramento

Este plano só pode ser marcado concluído quando:

- todos os findings P0/P1 da matriz estiverem com tarefa concluída, teste automatizado verde e evidência de gate;
- P2 materiais estiverem concluídos ou no destino pós-go-live explicitamente indicado;
- G0–G10 tiverem evidência vinculada ao mesmo release candidate;
- não houver secrets ativos no código/histórico alvo;
- `supabase db push` e schema audit tiverem passado em staging;
- reconciliação logística/financeira/assíncrona retornar zero perda/mismatch não explicado;
- piloto e rollout progressivo tiverem cumprido critérios sem bypass manual.

## PLANNING COMPLETE

Plano mestre V2 revisado em 2026-08-11: 64 tarefas executáveis, 55/55 requisitos do plano anterior reconciliados individualmente (51 cobertos e 4 diferidos com retomada explícita), G0–G10 mensuráveis e GH1 bloqueante para expansão do hub. Este V2 é a única autoridade de execução/gates; nenhum go-live é autorizado pela existência de qualquer documento, e a autorização depende exclusivamente dos gates mensuráveis acima no mesmo release candidate.

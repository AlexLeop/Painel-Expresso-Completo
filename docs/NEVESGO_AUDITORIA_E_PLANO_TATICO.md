# Auditoria Técnica e Plano Tático do App do Entregador (`nevesgo`)

Data: 21/06/2026

## 1. Objetivo

Este documento consolida a perícia técnica do aplicativo mobile do entregador localizado em `nevesgo/`, cruzando:

- o estado real do app Android
- o backend Django/Ninja já existente
- os contratos atuais da API
- os gaps entre protótipo e operação de produção

O objetivo é responder, de forma operacional, a quatro perguntas:

1. Qual é o estado atual do app?
2. O que está incorreto ou desalinhado?
3. O que ainda não foi implementado?
4. Qual a ordem correta para transformar o app em um aplicativo de produção?

## 2. Escopo Avaliado

### 2.1 App mobile avaliado

- `nevesgo/app/src/main/java/com/example/MainActivity.kt`
- `nevesgo/app/src/main/java/com/example/ui/AppNavigation.kt`
- `nevesgo/app/src/main/java/com/example/data/remote/DriverApiService.kt`
- `nevesgo/app/src/main/java/com/example/data/remote/RetrofitClient.kt`
- `nevesgo/app/src/main/java/com/example/data/repository/OrderRepositoryImpl.kt`
- `nevesgo/app/src/main/java/com/example/data/repository/CockpitRemoteDataSource.kt`
- `nevesgo/app/src/main/java/com/example/data/sync/OfflineSyncManager.kt`
- `nevesgo/app/src/main/java/com/example/services/TrackingService.kt`
- `nevesgo/app/src/main/java/com/example/ui/screens/*`
- `nevesgo/app/src/main/java/com/example/domain/models/Models.kt`
- `nevesgo/app/src/main/java/com/example/data/local/*`

### 2.2 Backend usado como referência de verdade

- `logistics/api_driver.py`
- `shared_schemas/logistics.py`
- `finance/api.py`
- `accounts/api.py`
- `docs/API_CONTRACT.md`

## 3. Resumo Executivo

O `nevesgo` não está em estado de produção.

O aplicativo possui uma base técnica útil para evolução, mas hoje se comporta mais como um protótipo funcional de interface do que como um cliente operacional real da plataforma.

Os principais problemas não estão apenas na UI. O risco maior está em:

- autenticação não aderente ao backend
- contratos mobile divergentes da API real
- fluxo de corrida modelado com estados errados
- telas críticas ainda mockadas
- offline e sincronização ainda não implementados de verdade
- tracking iniciado fora do contexto operacional

Em termos práticos:

- o app já tem estrutura Android aproveitável
- o app ainda não representa corretamente a operação real do entregador
- o caminho correto não é jogar tudo fora
- o caminho correto é reconstruir a espinha dorsal mobile usando o backend real como contrato obrigatório

## 4. Estado Atual do Aplicativo

### 4.1 O que já existe e é aproveitável

- projeto Android com Compose
- navegação básica entre telas
- estrutura inicial por camadas (`ui`, `data`, `domain`)
- Retrofit com interceptors
- Room para persistência local
- foreground service para tracking
- viewmodels iniciais para cockpit e entregas
- várias telas já desenhadas

### 4.2 O que esse estado representa na prática

O app atual permite navegação e demonstra intenção de produto, mas não fecha corretamente os fluxos críticos exigidos pela operação.

Hoje ele:

- aparenta ter login, entrega, financeiro, escalas e chat
- mas não implementa esses fluxos de forma aderente ao backend
- mistura comportamento real com comportamento mockado
- usa modelos locais que não batem com o domínio do sistema

Conclusão: a interface existe, mas a camada de execução operacional ainda não está pronta.

## 5. Achados Críticos

### 5.1 Autenticação e sessão não estão corretas

No app, `DriverApiService.kt` declara:

- `POST accounts/auth/login`
- esperando `LoginRequest`
- com retorno `LoginResponse(token, user)`

No backend atual, `POST /accounts/auth/login`:

- não autentica credenciais do entregador
- funciona como callback pós-login
- depende de JWT já presente em `request.auth`
- retorna apenas mensagem de sucesso ou erro

Impacto:

- o app não possui login real compatível com a arquitetura atual
- o app não possui bootstrap de sessão
- o app não possui restauração de sessão confiável
- o app não possui fluxo real de logout e relogin

Arquivos impactados:

- `nevesgo/app/src/main/java/com/example/data/remote/DriverApiService.kt`
- `nevesgo/app/src/main/java/com/example/data/remote/interceptors/AuthInterceptor.kt`
- `nevesgo/app/src/main/java/com/example/ui/AppNavigation.kt`
- `accounts/api.py`

### 5.2 O app inicia na home sem gate de autenticação

`AppNavigation.kt` usa `home` como `startDestination`.

Impacto:

- o app pula qualquer etapa de splash
- não existe tela de login
- não existe decisão entre sessão válida, onboarding pendente e acesso bloqueado
- o app não está preparado para produção, suspensão, token expirado ou sessão inexistente

### 5.3 O contrato do app diverge do backend

O backend real entrega, por exemplo:

- `GET /driver/orders` -> `OrderSchema`
- `GET /driver/cockpit` -> `DriverCockpitResponse`
- `POST /driver/shifts/check-in` -> exige `turno_id`, `store_id`, `date`
- provas multipart usam `proof_type`, `captured_at`, `gps_accuracy_meters`, `pin_code`, `qr_code`, `barcode`, `confirmation_code`

O app, por sua vez:

- espera `origin`, `destination`, `fare_cents`, `estimated_seconds`, `sla_seconds`
- chama `checkIn()` sem payload
- envia multipart com nomes incompatíveis como `proofType` e `capturedAt`
- assume respostas simplificadas demais

Impacto:

- parsing quebrado
- requests inválidos
- falhas silenciosas ou em runtime
- impossibilidade de homologação real

Arquivos impactados:

- `nevesgo/app/src/main/java/com/example/domain/models/Models.kt`
- `nevesgo/app/src/main/java/com/example/data/remote/DriverApiService.kt`
- `shared_schemas/logistics.py`
- `logistics/api_driver.py`

### 5.4 O fluxo de entrega está semanticamente errado

`OrderRepositoryImpl.kt`:

- ao aceitar, marca localmente a ordem como `IN_PROGRESS`
- ao finalizar, chama `sendDeliveryProof()` usando `orderId` como `stopId`
- envia latitude e longitude fixas `0.0`
- não chama `start`
- não chama `complete-batch`
- não respeita a lógica de stops reais

No backend, o fluxo correto exige:

- `accept`
- `start`
- provas por `stop_id`
- eventual PIN
- `complete-batch`
- fechamento da ordem quando todos os stops forem concluídos

Impacto:

- estado local incorreto
- estado de backend não refletido
- risco de corrida “concluída” no app sem estar concluída no sistema
- auditoria e financeiro podem ficar inconsistentes

### 5.5 Tracking sobe cedo demais

`MainActivity.kt` inicia o `TrackingService` logo na abertura do app, após permissão.

Isso ocorre:

- antes de login
- antes de check-in
- antes de existir ordem ativa
- sem vínculo com jornada operacional

Impacto:

- consumo indevido de bateria
- envio de telemetria fora de contexto
- risco de privacidade
- semântica operacional incorreta

### 5.6 Telas críticas ainda são mockadas

Várias telas possuem dados fixos, incluindo:

- corrida aceita
- rota e navegação
- confirmação de entrega
- ganhos
- notificações
- escalas
- chat

Exemplos encontrados:

- `Loja X`
- `Av. Paulista`
- `R$ 1.250,75`
- textos estáticos de mensagens
- cards com dados fake

Impacto:

- falsa percepção de completude
- baixa confiança para homologação
- retrabalho inevitável na integração real

## 6. Achados Altos

### 6.1 Offline não existe de fato

`OfflineSyncManager.kt` é apenas um esqueleto conceitual.

Hoje ele:

- não persiste fila de ações
- não usa WorkManager
- não reconcilia eventos
- não reprocessa requests pendentes com segurança

Impacto:

- o app não está pronto para ambiente de rua
- qualquer modo offline atual é ilusório

### 6.2 Persistência local está simplificada demais

`OrderEntity.kt` mantém apenas poucos campos e estados artificiais como:

- `IN_PROGRESS`
- `PENDING_ACCEPT`
- `PENDING_FINISH`

Impacto:

- baixa capacidade de reconciliação
- mapeamento incorreto do domínio real
- dificuldade futura para offline e recuperação de estado

### 6.3 Banco local destrutivo

`AppDatabase.kt` usa `fallbackToDestructiveMigration()`.

Impacto:

- perda de dados locais em mudança de schema
- comportamento aceitável para protótipo
- comportamento inadequado para produção

### 6.4 Configuração de ambiente ainda não é de produção

`RetrofitClient.kt` possui `BASE_URL = "https://api.exemplo.com/api/v1/"`.

Além disso:

- `HttpLoggingInterceptor` está em `BODY`
- não há estratégia clara de `dev`, `staging`, `prod`
- há resquícios de scaffold/template no projeto

Impacto:

- risco de vazamento de dados sensíveis em logs
- acoplamento ruim entre builds e ambientes
- configuração frágil para release

## 7. Achados Médios

### 7.1 Observabilidade ausente

Não foi identificado no app:

- crash reporting
- analytics de jornada
- tracing
- correlação entre erro mobile e request backend

### 7.2 Feature flags ausentes

O app ainda não demonstra suporte a:

- habilitação gradual de fluxo
- desligamento remoto de comportamento
- rollout controlado por versão/coorte

### 7.3 Reprodutibilidade local incompleta

Na inspeção via terminal, o projeto não apresentou `gradlew.bat` na raiz do `nevesgo`, o que dificulta:

- execução padronizada local
- CI simples
- validação rápida fora do Android Studio

## 8. Estado Funcional por Área

### 8.1 Login e sessão

Estado atual:

- inexistente como fluxo real

Precisa:

- splash
- login real
- persistência segura do token
- refresh/restauração de sessão
- logout
- decisão de navegação inicial

### 8.2 Cockpit

Estado atual:

- parcialmente integrado
- consome `GET /driver/cockpit`
- mas a navegação geral do app ainda não respeita o ciclo de sessão

Precisa:

- cockpit real como tela principal pós-login
- uso de `wallet`, `pending_documents`, `active_orders_count`, `active_orders_limit`
- ligação com turnos, mensagens, documentos e ordens ativas

### 8.3 Pedidos e multiaceite

Estado atual:

- listagem local simplificada
- estados divergentes do backend

Precisa:

- lista real de ofertas
- detalhe real de pedido
- aceitação e recusa corretas
- release operacional
- visão explícita de múltiplas ordens ativas
- aderência à capacidade `maxActiveOrders`

### 8.4 Execução da corrida

Estado atual:

- UI rica
- fluxo ainda fake

Precisa:

- `start`
- stops reais
- provas por `stop_id`
- validação de PIN
- conclusão em lote
- fechamento aderente ao backend

### 8.5 Turnos

Estado atual:

- telas existem
- dados ainda mockados

Precisa:

- calendário real
- reservas reais
- check-in e check-out reais
- acoplamento com status operacional

### 8.6 Financeiro

Estado atual:

- praticamente visual/mockado

Precisa:

- saldo
- extrato
- saque
- histórico
- despesas

### 8.7 Incidentes e comunicação

Estado atual:

- telas existem
- backend real existe
- integração ainda não foi fechada

Precisa:

- incidente real
- anexo real
- threads reais
- envio/leitura de mensagens reais

### 8.8 Dispositivos, documentos, compliance

Estado atual:

- backend já suporta boa parte
- app ainda não consome

Precisa:

- registro e revogação de dispositivos
- attestation
- upload de documentos
- consents
- privacy requests

## 9. Backlog Técnico de Correção e Implementação

## 9.1 Bloco A - Fundação Crítica

### Item A1

- Arquivo: `nevesgo/app/src/main/java/com/example/ui/AppNavigation.kt`
- Problema: app inicia em `home`
- Correção: criar fluxo `Splash -> Login/Bootstrap -> App`
- Endpoint envolvido: estratégia de sessão + callback `/accounts/auth/login`
- Prioridade: crítica
- Dependência: nenhuma
- Critério de aceite: usuário sem sessão não entra na home

### Item A2

- Arquivo: `nevesgo/app/src/main/java/com/example/data/remote/DriverApiService.kt`
- Problema: contrato de login incorreto
- Correção: remover a suposição de login por credencial no backend e alinhar estratégia de autenticação
- Endpoint envolvido: `/accounts/auth/login`
- Prioridade: crítica
- Dependência: definição final da estratégia auth mobile
- Critério de aceite: o app autentica sem depender de contrato inexistente

### Item A3

- Arquivo: `nevesgo/app/src/main/java/com/example/data/remote/RetrofitClient.kt`
- Problema: `BASE_URL` placeholder e logging inseguro
- Correção: configurar ambiente por build e logging seguro
- Endpoint envolvido: todos
- Prioridade: crítica
- Dependência: configuração de ambientes
- Critério de aceite: app roda contra backend real e não expõe payload sensível em produção

### Item A4

- Arquivo: `nevesgo/app/src/main/java/com/example/data/remote/interceptors/AuthInterceptor.kt`
- Problema: armazenamento e leitura de token sem estratégia completa de sessão
- Correção: integrar com storage seguro e fluxo real de sessão
- Endpoint envolvido: todos autenticados
- Prioridade: crítica
- Dependência: definição de auth
- Critério de aceite: header `Authorization` é enviado apenas quando a sessão é válida

## 9.2 Bloco B - Contrato com Backend

### Item B1

- Arquivo: `nevesgo/app/src/main/java/com/example/domain/models/Models.kt`
- Problema: DTOs divergentes do backend
- Correção: reescrever modelos a partir de `shared_schemas/logistics.py` e `finance/api.py`
- Endpoint envolvido: `cockpit`, `orders`, `performance`, `wallet`, `transactions`
- Prioridade: crítica
- Dependência: Bloco A
- Critério de aceite: parsing real sem adapters improvisados

### Item B2

- Arquivo: `nevesgo/app/src/main/java/com/example/data/remote/DriverApiService.kt`
- Problema: payloads e endpoints incompletos ou errados
- Correção: alinhar contratos Retrofit ao backend real
- Endpoint envolvido: todos os endpoints do motorista
- Prioridade: crítica
- Dependência: Bloco A
- Critério de aceite: todas as assinaturas Retrofit batem com os contratos do backend

## 9.3 Bloco C - Núcleo Operacional

### Item C1

- Arquivos:
- `HomeScreen.kt`
- `DriverViewModel.kt`
- `CockpitRemoteDataSource.kt`
- Problema: cockpit parcialmente integrado e fora de um fluxo real de sessão
- Correção: reconstruir cockpit usando dados reais do backend
- Endpoint envolvido: `GET /driver/cockpit`
- Prioridade: alta
- Dependência: Blocos A e B
- Critério de aceite: cockpit exibe dados reais de jornada, wallet, pendências e ordens ativas

### Item C2

- Arquivos:
- `DeliveriesScreen.kt`
- `DeliveryViewModel.kt`
- `OrderRepositoryImpl.kt`
- Problema: estados locais errados e listagem simplificada
- Correção: separar ofertas, ordens ativas e histórico conforme backend
- Endpoint envolvido: `GET /driver/orders`, `GET /driver/orders/{order_id}`
- Prioridade: crítica
- Dependência: Blocos A e B
- Critério de aceite: multiaceite e ofertas refletem o backend real

### Item C3

- Arquivo: `OrderRepositoryImpl.kt`
- Problema: aceite local altera status para `IN_PROGRESS`
- Correção: alinhar estados locais aos estados reais da ordem
- Endpoint envolvido: `POST /driver/orders/{order_id}/accept`
- Prioridade: crítica
- Dependência: Bloco B
- Critério de aceite: o app não cria estados que não existem no domínio do backend

### Item C4

- Arquivo: `DeliveriesScreen.kt`
- Problema: não há visão operacional explícita de multiaceite
- Correção: criar agrupamento por oferta, ativa, concluída e limite operacional
- Endpoint envolvido: `GET /driver/cockpit`, `GET /driver/orders`
- Prioridade: alta
- Dependência: C1 e C2
- Critério de aceite: o motorista enxerga com clareza quantas ordens já aceitou e qual seu limite

## 9.4 Bloco D - Execução Real da Entrega

### Item D1

- Arquivo: `DeliveryFlowScreens.kt`
- Problema: navegação e dados de corrida são mockados
- Correção: ligar a UI ao pedido ativo e aos stops reais
- Endpoint envolvido: `GET /driver/orders/{order_id}`
- Prioridade: crítica
- Dependência: C2
- Critério de aceite: a tela de execução usa dados reais do pedido e de suas paradas

### Item D2

- Arquivo: `OrderRepositoryImpl.kt`
- Problema: finalização usa `orderId` como `stopId`
- Correção: implementar fluxo baseado em `stop_id`
- Endpoint envolvido: `pickup-proof`, `delivery-proof`, `complete-batch`
- Prioridade: crítica
- Dependência: B2
- Critério de aceite: cada prova e conclusão referencia a parada correta

### Item D3

- Arquivo: `DeliveryFlowScreens.kt`
- Problema: PIN e comprovante ainda são apenas UI
- Correção: integrar PIN, prova e anexos aos endpoints reais
- Endpoint envolvido:
- `POST /driver/stops/{stop_id}/pickup-proof`
- `POST /driver/stops/{stop_id}/delivery-proof`
- `POST /driver/stops/complete-batch`
- Prioridade: crítica
- Dependência: D1 e D2
- Critério de aceite: uma entrega real é concluída no backend a partir do app

### Item D4

- Arquivo: `OrderRepositoryImpl.kt`
- Problema: `start` não participa do fluxo real
- Correção: inserir etapa obrigatória de início da ordem
- Endpoint envolvido: `POST /driver/orders/{order_id}/start`
- Prioridade: alta
- Dependência: C2
- Critério de aceite: o app não pula diretamente do aceite para prova/finalização

## 9.5 Bloco E - Turnos e Telemetria

### Item E1

- Arquivo: `SchedulesScreens.kt`
- Problema: escalas estão mockadas
- Correção: integrar calendário, reservas, check-in e check-out
- Endpoint envolvido:
- `GET /driver/shifts/calendar`
- `POST /driver/shifts/reservations`
- `POST /driver/shifts/check-in`
- `POST /driver/shifts/check-out`
- Prioridade: alta
- Dependência: Blocos A e B
- Critério de aceite: a jornada de turno é iniciada e encerrada pelo app

### Item E2

- Arquivos:
- `MainActivity.kt`
- `TrackingService.kt`
- Problema: tracking inicia cedo demais
- Correção: vincular tracking a sessão válida, turno aberto e contexto operacional
- Endpoint envolvido: `POST /driver/location`
- Prioridade: crítica
- Dependência: E1
- Critério de aceite: o serviço de rastreamento só sobe quando fizer sentido operacional

## 9.6 Bloco F - Exceções e Comunicação

### Item F1

- Arquivo: `DeliveryFlowScreens.kt`
- Problema: release e reportar problema ainda não fecham com o backend
- Correção: integrar release operacional e abertura de incidentes
- Endpoint envolvido:
- `POST /driver/orders/{order_id}/release`
- `POST /driver/incidents`
- Prioridade: alta
- Dependência: C2
- Critério de aceite: o motorista consegue devolver ordem aceita por engano ou abrir ocorrência real

### Item F2

- Arquivo: `CommunicationScreens.kt`
- Problema: chat e notificações ainda são mockados
- Correção: implementar threads, mensagens e centro de notificações real
- Endpoint envolvido:
- `GET /driver/communications/threads`
- `GET /driver/communications/threads/{thread_id}/messages`
- `POST /driver/communications/threads/{thread_id}/messages`
- Prioridade: alta
- Dependência: Bloco B
- Critério de aceite: o app troca mensagens reais com operação/loja

## 9.7 Bloco G - Financeiro, Perfil e Segurança

### Item G1

- Arquivo: `EarningsScreen.kt`
- Problema: saldo e histórico são mockados
- Correção: integrar wallet, transações e saque
- Endpoint envolvido:
- `GET /finance/wallet/balance`
- `GET /finance/transactions`
- `POST /finance/wallet/withdraw`
- Prioridade: alta
- Dependência: Bloco B
- Critério de aceite: o entregador consulta saldo e solicita saque no app

### Item G2

- Arquivo: `ProfileScreen.kt`
- Problema: perfil está superficial
- Correção: evoluir para dados do motorista, Pix, documentos, dispositivos e preferências
- Endpoint envolvido:
- `POST /driver/documents/upload`
- `POST /driver/devices/register`
- `GET /driver/devices`
- `POST /driver/devices/{device_id}/revoke`
- `POST /driver/security/device-attestation`
- Prioridade: alta
- Dependência: Bloco B
- Critério de aceite: o motorista gerencia sua conta e segurança pelo app

### Item G3

- Arquivo: novas telas/rotas de compliance
- Problema: consents e privacidade não existem no app
- Correção: criar telas e fluxos de LGPD/compliance
- Endpoint envolvido:
- `GET /driver/compliance/consents`
- `POST /driver/compliance/consents/{consent_id}/accept`
- `POST /driver/compliance/consents/{consent_id}/revoke`
- `GET /driver/privacy/requests`
- `POST /driver/privacy/requests`
- Prioridade: média
- Dependência: Bloco B
- Critério de aceite: o app consegue cumprir fluxos de consentimento e privacidade

## 9.8 Bloco H - Offline e Hardening

### Item H1

- Arquivo: `OfflineSyncManager.kt`
- Problema: offline é apenas conceitual
- Correção: implementar fila persistente com WorkManager
- Endpoint envolvido: ações críticas suportadas offline
- Prioridade: alta
- Dependência: Blocos C, D e E
- Critério de aceite: eventos pendentes sobrevivem a encerramento do app e são reenviados com segurança

### Item H2

- Arquivos:
- `OrderEntity.kt`
- `OrderDao.kt`
- `AppDatabase.kt`
- Problema: persistência local insuficiente
- Correção: remodelar cache e fila local com schema compatível com operação
- Endpoint envolvido: pedidos, jornada, sync e fila
- Prioridade: alta
- Dependência: H1
- Critério de aceite: o estado local consegue sustentar reconciliação e retomada

### Item H3

- Arquivo: configuração global do app
- Problema: sem crash reporting, analytics e feature flags
- Correção: adicionar observabilidade e controle remoto
- Endpoint envolvido: infraestrutura de app
- Prioridade: média
- Dependência: estabilidade dos fluxos core
- Critério de aceite: time consegue monitorar produção, medir uso e desligar features se necessário

## 10. Ordem Recomendada de Execução

1. corrigir autenticação, bootstrap e ambientes
2. alinhar modelos e contratos Retrofit ao backend real
3. reconstruir cockpit, ofertas e multiaceite
4. reconstruir o fluxo real de execução da entrega
5. integrar turnos e corrigir tracking
6. integrar release, incidentes e comunicação
7. integrar financeiro, perfil, documentos e segurança
8. fechar offline, observabilidade e hardening de produção

## 11. Roadmap por Sprints

### Sprint 1

- autenticação
- bootstrap
- ambiente
- contratos base

### Sprint 2

- cockpit
- pedidos
- detalhe de pedido
- multiaceite

### Sprint 3

- start de ordem
- tracking contextual
- provas
- conclusão por stops

### Sprint 4

- turnos
- release
- incidentes
- mensagens

### Sprint 5

- financeiro
- perfil
- documentos
- dispositivos

### Sprint 6

- offline persistente
- observabilidade
- segurança de produção
- rollout controlado

## 12. Definição de Pronto

O app do entregador só deve ser considerado pronto para produção quando:

- o motorista consegue autenticar corretamente
- o app restaura sessão e trata bloqueios
- o cockpit reflete o backend real
- o motorista consegue aceitar múltiplas ordens respeitando `maxActiveOrders`
- o fluxo `accept -> start -> proof -> complete` funciona ponta a ponta
- o motorista consegue fazer check-in e check-out de turno
- o tracking sobe apenas em contexto operacional válido
- incidentes, mensagens e release funcionam de verdade
- o financeiro é real e auditável
- o app possui comportamento offline controlado
- a equipe consegue monitorar produção e reagir rapidamente

## 13. Conclusão Final

O `nevesgo` não é um app descartável. Ele já possui material útil e acelera o desenvolvimento.

Mas o estado atual dele ainda é inadequado para produção porque:

- a arquitetura de sessão não está fechada
- o contrato com o backend está parcialmente errado
- o domínio da corrida não foi implementado corretamente
- várias telas críticas ainda são cenográficas

O caminho correto é tratar o projeto atual como:

- base de UI
- base técnica Android
- protótipo evolutivo

E, a partir disso, reconstruir a camada operacional em cima do backend real.

Essa abordagem preserva o que já existe de valor, reduz retrabalho desnecessário e coloca o produto no rumo certo para produção real.

## 14. Priorização P0, P1 e P2

### 14.1 P0 - Bloqueadores de Produção

Itens sem os quais o app não deve ir para homologação operacional séria:

- autenticação real e bootstrap de sessão
- ambiente real e configuração segura de `BASE_URL`
- alinhamento completo do contrato Retrofit com o backend
- alinhamento dos modelos mobile com os schemas reais
- remoção de estados inexistentes como `IN_PROGRESS`
- fluxo real de aceite, início, prova e conclusão por `stop_id`
- tracking condicionado a sessão válida e contexto operacional
- cockpit real com ordens ativas e limite de multiaceite

Objetivo do P0:

- fazer o app parar de simular a operação e começar a representar o backend real

### 14.2 P1 - Operação Assistida

Itens necessários para uso controlado em piloto:

- turnos e agenda reais
- release operacional
- incidentes e anexos
- mensagens e threads reais
- financeiro real com saldo, extrato e saque
- perfil, documentos e dispositivos

Objetivo do P1:

- permitir operação acompanhada com suporte, exceções e visibilidade financeira mínima

### 14.3 P2 - Escala e Hardening

Itens necessários para operação robusta em rua:

- offline persistente com fila confiável
- reconciliação e reprocessamento
- crash reporting
- analytics
- feature flags
- política de versionamento mínimo
- rollout gradual e kill switch

Objetivo do P2:

- suportar uso real sob conectividade ruim, crescimento de usuários e incidentes de produção

## 15. Checklist por Arquivo

### 15.1 Fundação e Sessão

#### `nevesgo/app/src/main/java/com/example/ui/AppNavigation.kt`

- criar `SplashScreen`
- criar `LoginScreen`
- remover `home` como `startDestination` direto
- implementar roteamento condicional por sessão
- prever bloqueio por onboarding, documentos ou acesso inválido

#### `nevesgo/app/src/main/java/com/example/MainActivity.kt`

- parar de subir tracking no boot do app
- mover inicialização operacional para fluxo controlado
- separar permissões de localização do bootstrap de UI
- preparar integração com sessão ativa e turno aberto

#### `nevesgo/app/src/main/java/com/example/data/remote/RetrofitClient.kt`

- substituir URL placeholder por configuração de build
- desligar `BODY` logging em release
- definir timeouts e política de retry por tipo de operação
- preparar headers padrão e correlação de requests

#### `nevesgo/app/src/main/java/com/example/data/remote/interceptors/AuthInterceptor.kt`

- integrar token com storage seguro
- validar presença de sessão antes do request
- preparar comportamento para token expirado e logout forçado

#### `nevesgo/app/src/main/java/com/example/data/remote/interceptors/ErrorInterceptor.kt`

- normalizar erros por tipo
- transformar respostas da API em erros de domínio
- tratar `401`, `403`, `409`, `422`, `503` de forma explícita

### 15.2 Contratos e Modelos

#### `nevesgo/app/src/main/java/com/example/data/remote/DriverApiService.kt`

- remover contrato de login inexistente
- alinhar `cockpit`
- alinhar `orders`
- alinhar `order detail`
- corrigir payload de `check-in`
- corrigir payload de `check-out`
- corrigir multipart de provas
- adicionar endpoints faltantes de mensagens, devices, documentos, compliance e privacy

#### `nevesgo/app/src/main/java/com/example/domain/models/Models.kt`

- reescrever DTOs com base em `shared_schemas/logistics.py`
- modelar `OrderSchema` corretamente
- modelar `OrderOfferDetailResponse`
- modelar `DriverCockpitResponse`
- modelar `DriverCalendarItem`
- modelar `WalletResponse` e `TransactionResponse`
- remover campos artificiais não existentes no backend

### 15.3 Núcleo Operacional

#### `nevesgo/app/src/main/java/com/example/ui/DriverViewModel.kt`

- separar estado de carregamento do cockpit
- suportar reload manual
- suportar dependência da sessão
- refletir dados reais de ordens ativas, wallet e pendências

#### `nevesgo/app/src/main/java/com/example/data/repository/CockpitRemoteDataSource.kt`

- tratar payload real
- normalizar falhas de backend
- expor resultados consistentes para a UI

#### `nevesgo/app/src/main/java/com/example/ui/DeliveryViewModel.kt`

- abandonar `IN_PROGRESS`
- separar ofertas, ativas e concluídas
- suportar multiaceite
- suportar refresh por ordem e por cockpit

#### `nevesgo/app/src/main/java/com/example/data/repository/OrderRepositoryImpl.kt`

- corrigir sincronização de ordens
- mapear estados reais do backend
- implementar `accept`
- implementar `reject`
- implementar `release`
- implementar `start`
- implementar fluxo por `stop_id`
- implementar `complete-batch`
- preparar cache/sync sem inventar estados inválidos

#### `nevesgo/app/src/main/java/com/example/ui/screens/HomeScreen.kt`

- substituir componentes mockados por binding real
- mostrar ordens ativas reais
- mostrar pendências e wallet reais
- refletir capacidade operacional real

#### `nevesgo/app/src/main/java/com/example/ui/screens/DeliveriesScreen.kt`

- separar ofertas visíveis de ordens ativas
- exibir multiaceite de forma explícita
- usar dados reais de pedido
- remover dependência de estados artificiais

#### `nevesgo/app/src/main/java/com/example/ui/screens/DeliveryFlowScreens.kt`

- conectar a tela ao pedido real
- conectar a tela aos stops reais
- integrar `start`
- integrar PIN
- integrar anexos de prova
- integrar `complete-batch`
- integrar `release`
- integrar `reportIncident`

### 15.4 Jornada, Comunicação e Financeiro

#### `nevesgo/app/src/main/java/com/example/ui/screens/SchedulesScreens.kt`

- substituir cards mockados por calendário real
- implementar reservas
- implementar check-in
- implementar check-out

#### `nevesgo/app/src/main/java/com/example/services/TrackingService.kt`

- iniciar somente com contexto operacional válido
- persistir telemetria pendente quando offline
- tratar falhas sem perder eventos importantes
- preparar QoS por foreground/background

#### `nevesgo/app/src/main/java/com/example/ui/screens/CommunicationScreens.kt`

- integrar threads reais
- integrar leitura de mensagens
- integrar envio de mensagens
- substituir notificações fake por fonte real

#### `nevesgo/app/src/main/java/com/example/ui/screens/EarningsScreen.kt`

- integrar saldo real
- integrar extrato real
- integrar saque
- remover valores fake

#### `nevesgo/app/src/main/java/com/example/ui/screens/ProfileScreen.kt`

- integrar dados reais do motorista
- incluir Pix
- incluir documentos
- incluir dispositivos
- incluir segurança e preferências

### 15.5 Offline e Persistência

#### `nevesgo/app/src/main/java/com/example/data/sync/OfflineSyncManager.kt`

- implementar fila persistente
- usar WorkManager
- mapear tipos de ação suportados offline
- implementar retry e reconciliação

#### `nevesgo/app/src/main/java/com/example/data/local/OrderEntity.kt`

- remodelar entidade local
- suportar contexto de stops
- suportar flags de sync sem inventar estado de negócio

#### `nevesgo/app/src/main/java/com/example/data/local/OrderDao.kt`

- incluir queries mais próximas do domínio real
- separar ofertas, ativas, concluídas e fila pendente

#### `nevesgo/app/src/main/java/com/example/data/local/AppDatabase.kt`

- remover `fallbackToDestructiveMigration()` para produção
- preparar migrations formais
- adicionar tabelas para fila offline e estado operacional

## 16. Primeira Onda de Execução

### 16.1 Objetivo da primeira onda

A primeira onda deve atacar somente o que desbloqueia a espinha dorsal do app.

Ela não deve tentar fechar tudo de uma vez.

O objetivo é sair de:

- app navegável porém sem aderência operacional

Para:

- app autenticado, configurado, aderente ao contrato e pronto para reconstruir o núcleo da entrega

### 16.2 Escopo da primeira onda

Arquivos prioritários:

- `AppNavigation.kt`
- `MainActivity.kt`
- `RetrofitClient.kt`
- `AuthInterceptor.kt`
- `ErrorInterceptor.kt`
- `DriverApiService.kt`
- `Models.kt`
- `DriverViewModel.kt`
- `CockpitRemoteDataSource.kt`
- `DeliveryViewModel.kt`
- `OrderRepositoryImpl.kt`
- `HomeScreen.kt`
- `DeliveriesScreen.kt`

### 16.3 Resultado esperado da primeira onda

Ao final da primeira onda, o app deve:

- iniciar em splash
- decidir entre login e sessão válida
- consumir backend real com configuração correta
- possuir modelos alinhados ao backend
- renderizar cockpit real
- listar ofertas e ordens ativas com semântica correta
- não inventar estados de negócio inexistentes

### 16.4 Critérios de aceite da primeira onda

- `home` não é mais a rota inicial cega
- a sessão é pré-condição para navegar no app operacional
- `DriverApiService.kt` está aderente aos endpoints reais do motorista
- `Models.kt` não contém mais o núcleo dos DTOs incorretos atuais
- `OrderRepositoryImpl.kt` não usa mais `IN_PROGRESS` como verdade local
- `HomeScreen.kt` e `DeliveriesScreen.kt` refletem dados reais do backend

## 17. Estratégia Recomendada de Implementação

Para reduzir retrabalho, a implementação deve seguir a seguinte disciplina:

1. primeiro ajustar contratos e sessão
2. depois ajustar repositories e viewmodels
3. só então reencaixar as telas
4. por último fechar offline e hardening

Motivo:

- se a UI for refeita antes do contrato e dos models, o time vai desenhar cima de dados errados
- se o offline for tentado antes do fluxo core estar correto, a fila vai perpetuar erros de domínio
- se tracking continuar sem contexto operacional, vai gerar dívida técnica e comportamento incorreto de produção

## 18. Próxima Etapa Recomendada

Depois deste documento, a próxima etapa ideal é executar o plano em duas saídas:

### 18.1 Saída de gestão

- quadro P0, P1, P2
- sprints
- responsáveis
- critérios de aceite

### 18.2 Saída técnica

- primeira leva de refactor do `nevesgo`
- começando por sessão, contrato, cockpit e pedidos

Se esse plano for seguido, o projeto sai de um protótipo forte de interface e entra em um trilho real de aplicativo operacional de produção.

## 19. Plano Técnico de Execução do P0

### 19.1 Objetivo do P0 técnico

O `P0` não tem como objetivo deixar o app “bonito” ou “quase pronto”.

O objetivo do `P0` é este:

- corrigir a fundação técnica
- alinhar o app ao backend real
- remover falsos positivos de completude
- preparar o terreno para reconstruir o fluxo operacional sem retrabalho

Ao final do `P0`, o app deve estar tecnicamente apto para:

- autenticar corretamente
- abrir com bootstrap real
- consumir endpoints reais do backend
- exibir cockpit e lista de ordens de forma semanticamente correta
- deixar de inventar estados locais inválidos

### 19.2 Ondas do P0

#### Onda 1 - Sessão e Configuração

Objetivo:

- tirar o app do estado “abre direto na home e chama API placeholder”

Escopo:

- `AppNavigation.kt`
- `MainActivity.kt`
- `RetrofitClient.kt`
- `AuthInterceptor.kt`
- `ErrorInterceptor.kt`

Saídas esperadas:

- splash inicial
- roteamento por sessão
- estratégia real de token
- ambiente configurável
- logging controlado
- parada do tracking automático no boot

Critérios de aceite:

- o app não entra mais direto no `home`
- o app só envia JWT quando houver sessão válida
- a URL da API não está mais hardcoded como placeholder
- o tracking não sobe automaticamente ao abrir o app

#### Onda 2 - Contrato e Modelos

Objetivo:

- eliminar o desalinhamento entre mobile e backend

Escopo:

- `DriverApiService.kt`
- `Models.kt`
- `CockpitRemoteDataSource.kt`

Saídas esperadas:

- Retrofit alinhado aos endpoints reais
- DTOs alinhados aos schemas reais
- respostas reais de cockpit e ordens parseadas corretamente

Critérios de aceite:

- o app deixa de esperar `LoginResponse(token, user)` do backend interno
- `check-in` deixa de ser chamado sem payload
- provas deixam de usar nomes de campos incompatíveis
- `orders` e `cockpit` passam a refletir o contrato real da API

#### Onda 3 - Núcleo Operacional Básico

Objetivo:

- reconstruir o núcleo de leitura e aceite de ordens

Escopo:

- `OrderRepositoryImpl.kt`
- `DeliveryViewModel.kt`
- `DriverViewModel.kt`
- `HomeScreen.kt`
- `DeliveriesScreen.kt`

Saídas esperadas:

- cockpit real
- ofertas reais
- ordens ativas reais
- multiaceite representado corretamente
- remoção do estado `IN_PROGRESS`

Critérios de aceite:

- o app não cria mais estado de negócio que não existe no backend
- ofertas e ordens ativas aparecem de forma separada e coerente
- a UI reflete `active_orders_count` e `active_orders_limit`

#### Onda 4 - Trava Técnica para Próxima Fase

Objetivo:

- preparar a transição segura para a implementação do fluxo real de corrida

Escopo:

- consolidar contratos
- estabilizar repositories
- revisar persistência local mínima

Saídas esperadas:

- base limpa para implementar `start`, provas, `complete-batch` e tracking contextual

Critérios de aceite:

- não restam inconsistências centrais de sessão, contrato e listagem operacional

## 20. Sequência Exata de Implementação do P0

### Passo 1

- atacar `RetrofitClient.kt`
- remover `https://api.exemplo.com/api/v1/`
- introduzir configuração por ambiente
- controlar `HttpLoggingInterceptor` por build type

Justificativa:

- sem isso, qualquer integração subsequente continua em base frágil

### Passo 2

- atacar `AppNavigation.kt`
- criar fluxo `Splash -> Login/SessionCheck -> App`
- remover `home` como entrada cega

Justificativa:

- sem isso, qualquer integração de sessão continua inconsistente

### Passo 3

- atacar `MainActivity.kt`
- remover inicialização automática de `TrackingService`
- deixar tracking dependente de contexto operacional

Justificativa:

- isso reduz imediatamente o desvio semântico mais perigoso do app atual

### Passo 4

- atacar `AuthInterceptor.kt` e `ErrorInterceptor.kt`
- padronizar sessão e erro
- preparar o app para falhas reais da API

Justificativa:

- repositories e telas dependem dessa camada para operar corretamente

### Passo 5

- reescrever `DriverApiService.kt`
- alinhar todos os endpoints centrais do motorista

Justificativa:

- esse é o ponto de acoplamento principal entre mobile e backend

### Passo 6

- reescrever `Models.kt`
- substituir DTOs inventados por DTOs aderentes ao backend

Justificativa:

- sem models corretos, a UI continuará renderizando uma realidade errada

### Passo 7

- ajustar `CockpitRemoteDataSource.kt`
- ajustar `DriverViewModel.kt`
- ajustar `HomeScreen.kt`

Justificativa:

- cockpit é a primeira tela operacional que precisa virar verdade

### Passo 8

- reescrever `OrderRepositoryImpl.kt`
- remover `IN_PROGRESS`
- corrigir sync e aceite

Justificativa:

- esse arquivo hoje concentra parte importante dos erros de domínio

### Passo 9

- ajustar `DeliveryViewModel.kt`
- ajustar `DeliveriesScreen.kt`

Justificativa:

- a lista de ordens precisa refletir a operação real antes do fluxo de corrida ser reconstruído

## 21. Mapeamento P0: Arquivo -> Dependência -> Saída

### `RetrofitClient.kt`

- depende de: definição de ambientes
- entrega: client HTTP confiável

### `AppNavigation.kt`

- depende de: estratégia de sessão
- entrega: entrada correta do app

### `MainActivity.kt`

- depende de: decisão de sessão e tracking
- entrega: app não inicia serviço operacional fora de contexto

### `AuthInterceptor.kt`

- depende de: storage de sessão
- entrega: autenticação consistente nas chamadas

### `ErrorInterceptor.kt`

- depende de: catálogo de erro mínimo
- entrega: comportamento previsível frente a falhas do backend

### `DriverApiService.kt`

- depende de: contrato real do backend
- entrega: integração formal com a API

### `Models.kt`

- depende de: schemas e payloads reais
- entrega: base tipada aderente ao domínio

### `CockpitRemoteDataSource.kt`

- depende de: `DriverApiService.kt` e `Models.kt`
- entrega: cockpit remoto confiável

### `DriverViewModel.kt`

- depende de: `CockpitRemoteDataSource.kt`
- entrega: estado de cockpit correto para a UI

### `HomeScreen.kt`

- depende de: `DriverViewModel.kt`
- entrega: cockpit visual conectado à realidade operacional

### `OrderRepositoryImpl.kt`

- depende de: `DriverApiService.kt` e `Models.kt`
- entrega: base correta para ofertas, aceite e sincronização

### `DeliveryViewModel.kt`

- depende de: `OrderRepositoryImpl.kt`
- entrega: estado operacional correto das listas de ordens

### `DeliveriesScreen.kt`

- depende de: `DeliveryViewModel.kt`
- entrega: visão correta de ofertas e ordens ativas

## 22. O Que Não Fazer no P0

Para evitar retrabalho, o time não deve no `P0`:

- tentar fechar offline completo
- tentar fechar financeiro completo
- tentar polir todas as telas mockadas
- tentar concluir chat, LGPD, documentos e devices
- tentar desenhar o fluxo final de prova antes dos models e repositories estarem corretos

Esses pontos são importantes, mas entram depois que:

- sessão
- contrato
- cockpit
- listagem de ordens

estiverem corretos.

## 23. Critério de Saída do P0

O `P0` termina quando os seguintes pontos forem verdadeiros ao mesmo tempo:

- o app abre com fluxo de sessão coerente
- a integração não usa mais base URL placeholder
- o contrato Retrofit central foi corrigido
- os DTOs centrais foram corrigidos
- o cockpit usa dados reais
- a listagem de ordens usa dados reais
- o app não cria mais estado operacional inexistente
- tracking não sobe sem contexto operacional

Se um desses itens ainda estiver quebrado, o `P0` ainda não terminou.

## 24. Próximo Passo Técnico Recomendado

Depois deste documento, a execução ideal é começar o código real na seguinte ordem:

1. `RetrofitClient.kt`
2. `AppNavigation.kt`
3. `MainActivity.kt`
4. `AuthInterceptor.kt`
5. `ErrorInterceptor.kt`
6. `DriverApiService.kt`
7. `Models.kt`
8. `CockpitRemoteDataSource.kt`
9. `DriverViewModel.kt`
10. `HomeScreen.kt`
11. `OrderRepositoryImpl.kt`
12. `DeliveryViewModel.kt`
13. `DeliveriesScreen.kt`

Essa é a ordem com menor risco de retrabalho e maior ganho estrutural para o `nevesgo`.

## 25. Execucao Realizada na Onda Atual

Esta secao registra a ultima leva efetivamente implementada no app Android, ja cruzada com o backend e validada por diagnosticos do workspace.

### 25.1 Jornada e escalas

- `SchedulesScreens.kt` deixou de ser apenas uma tela de cards mockados.
- A tela agora consome `GET /driver/shifts/calendar` e `GET /driver/cockpit`.
- Foi adicionada operacao real de:
- `POST /driver/shifts/reservations`
- `POST /driver/shifts/check-in`
- `POST /driver/shifts/check-out`
- O app agora exibe a jornada aberta no topo da tela e evita abrir novo turno sem contexto.
- O detalhe de escala passou a receber dados reais por rota parametrizada via `AppNavigation.kt`.

### 25.2 Vinculo de tracking com jornada operacional

- `RouteNavigationScreen` passou a consultar o cockpit para validar se existe sessao de turno aberta.
- O `TrackingService` agora so e iniciado quando ha `orderId` valido e turno aberto.
- Quando nao existe jornada aberta, a CTA da tela redireciona o motorista para `escalas` em vez de prosseguir como se a execucao estivesse regular.
- O mapa deixou de usar pontos fixos e passou a usar coordenadas do pedido e da proxima parada operacional disponivel.

### 25.3 Fechamento da entrega com confirmacao real

- `DeliveryViewModel.kt` passou a aceitar callback de sucesso em `finishDelivery(...)`.
- `ConfirmDeliveryScreen` deixou de navegar para tela de sucesso antes da resposta real do backend.
- Agora o app so para o tracking e navega para `entrega_finalizada/{fareCents}` depois de confirmacao bem-sucedida da operacao.

### 25.4 Validacao da onda

- Diagnosticos IDE executados com retorno limpo em:
- `AppNavigation.kt`
- `DeliveryViewModel.kt`
- `DeliveryFlowScreens.kt`
- `SchedulesScreens.kt`

### 25.5 Gaps ainda abertos apos esta onda

- `pickup-proof` ainda nao esta implementado na UX operacional.
- A prova de entrega continua sem captura real de arquivo/foto.
- O mapa ja usa coordenadas reais, mas ainda nao representa navegacao turn-by-turn de producao.
- O modelo local de persistencia ainda precisa ser remodelado para offline confiavel e reconciliacao de fila.

### 25.6 Financeiro e sessao

- `EarningsScreen.kt` deixou de usar valores mockados e passou a consumir:
- `GET /finance/wallet/balance`
- `GET /finance/transactions`
- `POST /finance/wallet/withdraw`
- `PaymentsScreen` agora reutiliza a mesma base financeira real.
- `ProfileScreen.kt` passou a limpar o `jwt_token` e encerrar tracking no logout.

### 25.7 Comunicacao operacional

- `CommunicationScreens.kt` deixou de usar inbox e chat mockados.
- `NotificationsScreen` passou a operar como caixa de entrada real de threads do backend.
- `ChatScreen` passou a abrir uma thread especifica e consumir mensagens reais.
- Foram integrados os endpoints:
- `GET /driver/communications/threads`
- `GET /driver/communications/threads/{thread_id}/messages`
- `POST /driver/communications/threads/{thread_id}/messages`
- `AppNavigation.kt` passou a suportar `chat/{threadId}` para abertura contextual da conversa.

## 26. Telas e Funcionalidades Essenciais Ainda Faltantes

Mesmo com os avancos do `P0`, o app ainda nao esta em 100% de producao. Os gaps essenciais remanescentes sao:

### 26.1 Comunicacao operacional real

- O backend ja expone:
- `GET /driver/communications/threads`
- `GET /driver/communications/threads/{thread_id}/messages`
- `POST /driver/communications/threads/{thread_id}/messages`
- A base de inbox e conversa ja foi conectada ao backend.
- Ainda falta evoluir notificacoes push reais e centro de eventos separados da mensageria de threads.

### 26.2 Compliance, privacidade e aceite de termos

- O backend ja expone:
- `GET /driver/compliance/consents`
- `POST /driver/compliance/consents/{consent_id}/accept`
- `POST /driver/compliance/consents/{consent_id}/revoke`
- `GET /driver/privacy/requests`
- `POST /driver/privacy/requests`
- O app ainda nao possui telas operacionais para aceite de termos obrigatorios, revogacao e solicitacoes LGPD.
- Para producao real, isso e tela essencial, nao detalhe opcional.

### 26.3 Gestao de dispositivos e seguranca do app

- O backend ja expone:
- `POST /driver/devices/register`
- `GET /driver/devices`
- `POST /driver/devices/{device_id}/revoke`
- `POST /driver/security/device-attestation`
- O app ainda nao possui:
- cadastro de dispositivo
- lista de dispositivos ativos
- revogacao de aparelho comprometido
- estado de risco/atestado do device

### 26.4 Jornada detalhada ainda mockada

- `JourneyDetailsScreen` ainda usa dados estaticos de horas, ganhos e lista de entregas.
- Como a tela esta acessivel no app, ela ainda pode induzir operacao falsa.
- Ou ela precisa ser implementada com dados reais, ou precisa ser retirada do fluxo ate ser substituida.

### 26.5 Offline operacional verdadeiro

- O backend ja expone `POST /driver/offline/sync`, mas o app ainda nao implementa fila persistente robusta.
- Falta persistir eventos criticos de:
- inicio de ordem
- incidentes
- check-in/check-out
- finalizacao de stop
- sincronizacao posterior segura

### 26.6 Despesas operacionais e comprovantes de custo

- O backend ja expone:
- `POST /driver/expenses`
- `POST /driver/expenses/{expense_id}/receipt`
- O app ainda nao possui tela para lancamento de custos operacionais da rua.
- Isso e importante em operacoes com reembolso, pedagio, estacionamento e avaria operacional.

### 26.7 Centro de atualizacao obrigatoria e bloqueio de versao

- O app ainda nao possui gate de versao minima, manutencao, bloqueio de build ou tela de update obrigatorio.
- Em producao real, isso e tela essencial para rollout controlado e contenção de incidentes.

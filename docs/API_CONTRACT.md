# Contrato de API
Data: 21/06/2026
Versão: 2.0

## Visão Geral
- Base URL: `/api/v1`
- Documentação interativa: `/api/v1/docs`
- Schema OpenAPI: `/api/v1/openapi.json`
- Autenticação padrão: `Authorization: Bearer <supabase_jwt>`
- Formato de erro padrão:

```json
{
  "success": false,
  "error": "Mensagem de erro"
}
```

## Autenticação e Claims
- A API valida JWT do Supabase via `SupabaseJWTAuth`.
- Claims esperadas conforme o perfil:
- `sub`: identificador do usuário autenticado.
- `role`: papel de acesso, como `platform_admin`, `ADMIN`, `MANAGER`, `OPERATOR_ROLE`, `VIEWER`.
- `operator_id`: tenant do operador quando a rota é tenant-aware.
- Algumas rotas de webhook são públicas e usam `auth=None`.

## Healthcheck
- `GET /health`
  - Uso: liveness probe e smoke test de infraestrutura.
  - Resposta `200`:

```json
{
  "status": "ok",
  "service": "slow_lane_django_ninja"
}
```

## Accounts

### Cadastro de Operador pela Plataforma
- `POST /accounts/admin/operators`
- Perfil: `platform_admin`
- Body:

```json
{
  "name": "Operador XPTO"
}
```

### Cadastro de Motorista pelo Operador
- `POST /accounts/operator/drivers`
- Perfis: `ADMIN`, `MANAGER`, `OPERATOR_ROLE`
- Body:

```json
{
  "name": "João Silva",
  "phone": "11999999999",
  "pixKey": "joao@pix.com.br",
  "cnhNumber": "00000000000"
}
```

### Inclusão em Deny List
- `POST /accounts/operator/security/deny-list`
- Perfis: `ADMIN`, `MANAGER`
- Body:

```json
{
  "targetId": "uuid",
  "targetType": "DRIVER_ID",
  "reason": "Suspeita de fraude",
  "expiresAt": "2026-06-30T23:59:59Z"
}
```

### Callback de Login
- `POST /accounts/auth/login`
- Uso: invalida tokens antigos da fast lane do motorista logado.

## Admin Accounts

### Criar Operador e Primeiro Admin
- `POST /admin/accounts/operator`
- Perfil: `platform_admin`

### Criar Staff
- `POST /admin/accounts/staff`
- Perfis: `ADMIN`, `MANAGER`

### Listar Staff
- `GET /admin/accounts/staff`
- Perfis: contexto do operador autenticado

## Logistics Driver

### Listar Ordens Visíveis para o Motorista
- `GET /driver/orders`
- Retorna ordens `OFFERED` para a praça do operador e ordens do próprio motorista em andamento.

### Atualizar Localização
- `POST /driver/location`
- Body:

```json
{
  "lat": -23.55052,
  "lng": -46.63330,
  "heading": 180,
  "speedKmh": 32,
  "timestamp": 1710000000
}
```

### Aceitar Ordem
- `POST /driver/orders/{order_id}/accept`
- Características: idempotente, valida deny list, trava concorrência em Redis.

### Iniciar Ordem
- `POST /driver/orders/{order_id}/start`
- Características: idempotente, valida posse da ordem pelo motorista.

### Completar Stops em Lote
- `POST /driver/stops/complete-batch`
- Características: idempotente, processamento atômico.

### Check-in de Turno
- `POST /driver/shifts/check-in`

### Upload de Documentos
- `POST /driver/documents/upload`

## Logistics Operator

### Dashboard Operacional
- `GET /operator/dashboard`
- Perfis: `ADMIN`, `MANAGER`, `OPERATOR_ROLE`, `VIEWER`

### Criar ou Atualizar Contrato
- `POST /operator/contracts`

### Criar Escala
- `POST /operator/schedule`

### Despachar Ordem
- `POST /operator/orders/dispatch`
- Cria ordem com status `OFFERED`, com ou sem motorista pré-definido.

### Listar Ordens
- `GET /operator/orders`
- Filtros suportados:
- `status`
- `store_id`

### Listar Motoristas
- `GET /operator/drivers`

### Gerar URL Assinada de Proof
- `GET /operator/proofs/{proof_id}/url`
- Gera link temporário para visualização segura de comprovantes.

## Logistics Admin

### Criar Cliente
- `POST /admin/logistics/clients`

### Criar Loja
- `POST /admin/logistics/stores`

### Criar Turno
- `POST /admin/logistics/turnos`

### Criar Motorista
- `POST /admin/logistics/drivers`

### Criar Veículo
- `POST /admin/logistics/vehicles`

### Criar Escala com Gate de Onboarding
- `POST /admin/logistics/schedules`
- Valida motorista ativo, aprovado e sem documento vencido.

### Listar Motoristas
- `GET /admin/logistics/drivers`

### Atualizar Status do Motorista
- `PUT /admin/logistics/drivers/{driver_id}/status`

## Finance

### Saldo de Carteira
- `GET /finance/wallet/balance`

### Solicitação de Saque
- `POST /finance/wallet/withdraw`
- Características: idempotente, lock pessimista de carteiras, proteção contra double spending.

### Lançamento Manual
- `POST /finance/manual-entry`

### Listar Faturas
- `GET /finance/invoices`

### Listar Transações
- `GET /finance/transactions`
- Paginação nativa do Django Ninja.

### Painel Gerencial
- `GET /finance/gerencial`
- Perfis: `ADMIN`, `MANAGER`, `VIEWER`, `OPERATOR_ROLE`
- Retorna `kpis`, `snapshots` e `companies`.

## Admin Finance

### Wizard de Contrato
- `POST /admin/finance/contracts/wizard`

### Listar Contratos
- `GET /admin/finance/contracts`

## Integrações

### Webhook de Ingestão
- `POST /integration/webhooks/{source}`
- Público
- Resposta: `202 Accepted`
- Uso: entrada assíncrona de iFood, Hubster e parceiros equivalentes.

## Todos

### Criar Categoria
- `POST /todos/categories`

### Listar Categorias
- `GET /todos/categories`

### Criar Tarefa
- `POST /todos/`

### Listar Tarefas
- `GET /todos/`

### Atualizar Tarefa
- `PUT /todos/{todo_id}`

### Excluir Tarefa
- `DELETE /todos/{todo_id}`

## Observações Operacionais
- Endpoints com escrita crítica usam `transaction.atomic()`.
- Rotas sensíveis do fluxo de entregas usam Redis para coordenação de concorrência e fail-closed de segurança.
- Os modelos de domínio são `managed=False`, com banco de dados como fonte de verdade.
- Para operação enterprise, a fonte oficial de contrato em runtime deve combinar este documento com o schema OpenAPI servido pelo Ninja.

## Cobertura do App do Condutor

### Estado Atual
- O backend já suporta um núcleo operacional de entregador com despacho, aceite, recusa, detalhe de oferta, telemetria, check-in/check-out, status operacional, provas básicas, incidentes, upload documental básico e carteira.
- O backend ainda não cobre integralmente um app enterprise no padrão `Uber Driver`, `Amazon Flex`, `Onfleet Driver`, `Fleetbase Driver` e `iFood Entregador`.
- O objetivo desta seção é separar com clareza:
- o que já existe e pode ser consumido agora
- o que existe apenas parcialmente
- o que ainda precisa ser criado para produção real

### Endpoints Já Disponíveis para o Condutor
- `GET /driver/orders`
- `GET /driver/orders/{order_id}`
- `POST /driver/location`
- `POST /driver/status`
- `POST /driver/orders/{order_id}/accept`
- `POST /driver/orders/{order_id}/reject`
- `POST /driver/orders/{order_id}/start`
- `POST /driver/stops/complete-batch`
- `POST /driver/stops/{stop_id}/pickup-proof`
- `POST /driver/stops/{stop_id}/delivery-proof`
- `POST /driver/shifts/check-in`
- `POST /driver/shifts/check-out`
- `GET /driver/cockpit`
- `GET /driver/performance`
- `GET /driver/shifts/calendar`
- `POST /driver/shifts/reservations`
- `POST /driver/incidents`
- `POST /driver/incidents/{incident_id}/attachments`
- `POST /driver/devices/register`
- `GET /driver/devices`
- `POST /driver/devices/{device_id}/revoke`
- `POST /driver/security/device-attestation`
- `POST /driver/offline/sync`
- `POST /driver/expenses`
- `POST /driver/expenses/{expense_id}/receipt`
- `POST /driver/documents/upload`
- `GET /driver/compliance/consents`
- `POST /driver/compliance/consents/{consent_id}/accept`
- `POST /driver/compliance/consents/{consent_id}/revoke`
- `GET /driver/privacy/requests`
- `POST /driver/privacy/requests`
- `POST /accounts/auth/login`
- `GET /finance/wallet/balance`
- `POST /finance/wallet/withdraw`
- `GET /finance/transactions`

### Endpoints Já Disponíveis para Operação e Lojista
- `POST /operator/orders/dispatch`
- `POST /operator/orders/{order_id}/reassign`
- `GET /operator/communications/threads`
- `POST /operator/communications/threads`
- `POST /operator/communications/threads/{thread_id}/messages`
- `GET /operator/compliance/documents`
- `POST /operator/compliance/documents`
- `POST /operator/compliance/documents/{document_id}/archive`
- `GET /operator/privacy/requests`
- `POST /operator/privacy/requests/{request_id}/resolve`
- `GET /operator/compliance/retention-policies`
- `POST /operator/compliance/retention-policies`
- `POST /operator/compliance/retention-policies/{policy_id}/disable`
- `GET /client/dashboard`
- `GET /client/orders`
- `POST /client/orders/dispatch`
- `GET /client/drivers/live`
- `POST /client/orders/{order_id}/reassign`
- `GET /client/communications/threads`
- `GET /client/communications/threads/{thread_id}/messages`
- `POST /client/communications/threads`
- `POST /client/communications/threads/{thread_id}/messages`

### Matriz de Cobertura por Módulo

#### Módulo 1 — Identidade e Segurança
- Status: `PARCIAL`
- Cobertura existente:
- cadastro básico de motorista
- upload documental genérico
- deny-list
- device token efêmero para fast lane
- logout técnico via invalidação de tokens antigos
- registro de dispositivos confiáveis
- listagem de dispositivos vinculados
- revogação remota de dispositivo
- Lacunas:
- CPF/CNPJ estruturado e validado
- CNH estruturada com metadados
- documento do veículo vinculado ao veículo
- foto facial
- selfie de validação
- comprovante bancário
- comprovante de residência
- MFA
- Face ID / Fingerprint
- catálogo versionado de termos LGPD por operador
- aceite persistido de termo por motorista com device/IP/user-agent
- consentimentos, termos e histórico LGPD
- revogação auditável de consentimento pelo motorista
- abertura e acompanhamento de solicitações do titular
- política automática de retenção com minimização de payload sensível
#### Módulo 2 — Disponibilidade
- Status: `PARCIAL`
- Cobertura existente:
- flag `online`
- status operacional `ONLINE`, `OFFLINE`, `PAUSED`, `EN_ROUTE`, `IN_SERVICE`, `RESTING`
- atualização de localização
- check-in de turno
- check-out de turno
- sessão de turno persistida
- escalas e turnos
- agenda do motorista
- reserva de turno persistida
- Lacunas:
- cálculo de horas trabalhadas via API do app
- vagas abertas por turno para autoagendamento

#### Módulo 3 — Recebimento de Serviços
- Status: `PARCIAL`
- Cobertura existente:
- listagem de ordens
- detalhe da oferta
- aceite idempotente com trava concorrencial
- recusa com motivo
- despacho manual pelo operador
- despacho manual pelo lojista via portal
- redistribuição segura em estados `OFFERED` e `ACCEPTED`
- Lacunas:
- autoaceite configurável
- payload rico da oferta com SLA, peso, volume e quantidade de volumes
- filtros e preferências operacionais do condutor
- redistribuição assistida após coleta já iniciada

#### Módulo 4 — Execução da Rota
- Status: `PARCIAL`
- Cobertura existente:
- iniciar ordem
- completar stops em lote
- roteirização gulosa por proximidade
- geofence e tracking em tempo real
- Lacunas:
- endpoints dedicados para `cheguei na coleta`
- endpoints dedicados para `coleta realizada`
- endpoints dedicados para `cheguei na entrega`
- endpoint de `finalização` desacoplado do lote de stops
- roteirização dinâmica exposta ao app
- integração explícita com Google Maps, Waze e navegador interno

#### Módulo 5 — Prova de Coleta
- Status: `PARCIAL`
- Cobertura existente:
- PIN por stop
- metadado temporal na conclusão do stop
- endpoint específico de prova de coleta
- GPS e precisão persistidos junto da prova
- QR Code e código de barras persistidos
- Lacunas:
- foto de coleta
- assinatura

#### Módulo 6 — Prova de Entrega
- Status: `PARCIAL`
- Cobertura existente:
- modelo `Proof`
- criação de proof pelo app do entregador
- URL assinada para o operador visualizar provas
- QR Code
- código de confirmação
- vínculo do dispositivo e coordenadas à prova
- envelope de confirmação de entrega enriquecido para integrações outbound
- envio outbound ativo para parceiro Open Delivery no evento de entrega concluída
- Lacunas:
- assinatura digital
- reconhecimento facial opcional
- homologação final por parceiro externo (iFood/99Food/Delivery Direto/Anota AI)
- auditoria de aceite/ack por parceiro ainda depende de homologação final em ambiente real

#### Módulo 7 — Comunicação
- Status: `PARCIAL`
- Cobertura existente:
- thread persistida operador ↔ entregador
- thread persistida lojista ↔ entregador
- histórico de mensagens por ordem
- Lacunas:
- chamadas mascaradas
- mensagens rápidas padronizadas
- SLA e playbook operacional por tipo de incidente

#### Módulo 8 — Gestão de Ocorrências
- Status: `PARCIAL`
- Cobertura existente:
- abertura de incidente
- anexos de foto, vídeo, áudio e documento
- Lacunas:
- classificação do incidente
- trilha de tratamento operacional

#### Módulo 9 — Financeiro
- Status: `PARCIAL/BOM`
- Cobertura existente:
- saldo de carteira
- saque
- extrato de transações
- motor contábil com ledger
- criação de despesa do condutor
- anexo de comprovante de despesa
- prestação de contas de combustível
- prestação de contas de pedágio
- prestação de contas de estacionamento
- cálculo de `businessDate` alinhado ao `cutoffHour/cutoffMinute` do contrato na criação manual
- Lacunas:
- bônus e incentivos explicitados por endpoint de app
- adiantamento configurável por regra de negócio
- comprovante de liquidação PIX para o condutor

#### Módulo 10 — Performance
- Status: `PARCIAL`
- Cobertura existente:
- dados gerenciais para operação
- KPIs pessoais do entregador por período
- Lacunas:
- ranking individual
- metas diárias
- metas semanais
- metas mensais

#### Módulo 11 — Frota
- Status: `PARCIAL`
- Cobertura existente:
- cadastro de veículo no administrativo
- Lacunas:
- checklist de saída
- checklist de retorno
- avarias
- quilometragem
- odômetro com foto

#### Módulo 12 — Operação Offline
- Status: `PARCIAL`
- Cobertura existente:
- recebimento de lote offline persistido por dispositivo
- Lacunas:
- fila offline
- sincronização posterior de provas e ocorrências
- reconciliação de conflitos

#### Módulo 13 — Auditoria e Antifraude
- Status: `PARCIAL`
- Cobertura existente:
- telemetria
- geofence
- deny-list
- outbox de eventos
- device attestation com trilha de eventos
- bloqueio de confiança do aparelho por risco alto/crítico
- webhook inbound validado por assinatura para Delivery Direto
- resolução de loja por `merchantId`/referência externa em integrações
- auditoria persistida de eventos inbound/outbound de integração
- adapter com semântica de status por provedor e prevenção de regressão de status inbound
- trilha de `externalEventId` para eventos inbound/outbound
- polling ativo para integrações `Open Delivery` com `OAuth client_credentials`
- ack explícito de eventos polled antes de novo ciclo de polling
- polling ativo para `iFood Mercado` com leitura/ack de eventos por loja
- webhook `Anota AI` endurecido com validação de `token` de integração
- suporte parcial a `99Food` via trilho `Open Delivery` com `baseUrl` específica do parceiro
- Lacunas:
- fake GPS
- mock location
- root/jailbreak
- spoofing app detection
- score de fraude por evento

#### Integração por Parceiro
- Status: `PARCIAL`
- Cobertura existente:
- `StoreIntegration` com `authMode`, `baseUrl` e `webhookUrl`
- fallback legado para integrações ainda não migradas do campo `apiKey`
- `Delivery Direto Open Delivery` com `oauth/token`, `events:polling`, `acknowledgment`, `orders/{orderId}/pickedUp` e `orders/{orderId}/delivered`
- `99Food` preparado para `Open Delivery` com `base URL` própria e polling compartilhado
- skip explícito de confirmação outbound final no `99Food`, já que o código de entrega não é exposto pelo conector público
- `iFood Mercado` com `polling` de `/pedido/eventos/{idLoja}` e ack em `/pedido/eventos/verificado`
- mapeamento de status `PE0`, `SEP`, `FIN` e `CAN` para o domínio interno
- skip explícito de outbound de ciclo de pedido no `iFood Mercado` até homologação específica
- `Anota AI` com autenticação inbound por `token` e extração mais robusta de `order/store`
- mapeamento inicial de status `READY`, `DELIVERED` e `CANCELLED_BY_STORE`
- scheduler Celery para polling periódico de parceiros
- Lacunas:
- homologação ativa equivalente para `iFood Restaurantes/Merchant API`, detalhes finais do `99Food` e `Anota AI`
- mapeamento outbound adicional para `confirm` e `readyForPickup`
- observabilidade por parceiro com dashboards e alertas dedicados

#### Módulo 14 — IA Operacional
- Status: `MUITO PARCIAL`
- Cobertura existente:
- heurística de escala
- heurística de roteirização
- Lacunas:
- assistente do condutor
- classificação automática de ocorrências
- sugestão de melhor rota
- sugestão de melhor região
- sugestão de melhor horário

#### Módulo 15 — Experiência de Usuário / Cockpit do Condutor
- Status: `PARCIAL`
- Cobertura existente:
- dashboard consolidado do turno
- próxima parada
- ganho acumulado do dia
- saldo de carteira
- Lacunas:
- SLA restante
- meta diária
- alertas operacionais
- checklists pendentes
- ocorrências abertas
- central unificada de comunicação consolidada no cockpit

## Backlog Enterprise de Endpoints do Condutor

### Prioridade P0 — Obrigatórios para Produção Real

#### 1. Cockpit do Condutor
- Método: `GET`
- Rota: `/driver/cockpit`
- Auth: `Bearer JWT`
- Objetivo: entregar o estado operacional consolidado do turno
- Observação operacional: o cockpit precisa refletir multiaceite real; a resposta agora inclui `active_orders`, `active_orders_count` e `active_orders_limit`, mantendo `active_order` apenas como compatibilidade legada
- Resposta mínima:

```json
{
  "driver": {
    "id": "uuid",
    "name": "João Silva",
    "status": "ONLINE"
  },
  "shift": {
    "id": "uuid",
    "started_at": "2026-06-21T08:00:00Z",
    "worked_minutes": 215
  },
  "today": {
    "earnings_cents": 18500,
    "deliveries": 14,
    "goal_progress_percent": 72
  },
  "active_order": {
    "order_id": "uuid",
    "next_stop_id": "uuid",
    "next_stop_type": "PICKUP"
  },
  "active_orders": [
    {
      "order_id": "uuid",
      "manifest_id": null,
      "next_stop_id": "uuid",
      "next_stop_type": "PICKUP"
    }
  ],
  "active_orders_count": 2,
  "active_orders_limit": 3,
  "alerts": [
    {
      "code": "SLA_RISK",
      "message": "Entrega 102 com risco de SLA"
    }
  ],
  "pending_checklists": 1,
  "open_incidents": 0,
  "unread_messages": 3
}
```
- Dependências:
- agregação de ordens, jornada, financeiro, metas e alertas

#### 2. Alterar Status Operacional
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/status`
- Auth: `Bearer JWT`
- Body:

```json
{
  "status": "PAUSED",
  "reason": "ALMOCO"
}
```
- Objetivo: controlar `ONLINE`, `OFFLINE`, `PAUSED`, `RESTING`, `IN_SERVICE`
- Dependências:
- enum de status do motorista
- trilha de auditoria

#### 3. Recusar Oferta com Motivo
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/orders/{order_id}/reject`
- Auth: `Bearer JWT`
- Body:

```json
{
  "reason_code": "DISTANCIA_INVIAVEL",
  "reason_text": "Muito longe da minha operação atual"
}
```
- Objetivo: permitir recusa auditável e alimentar regras de redistribuição

#### 4. Detalhe Completo da Oferta
- Situação: `IMPLEMENTADO PARCIAL`
- Método: `GET`
- Rota: `/driver/orders/{order_id}`
- Auth: `Bearer JWT`
- Objetivo: exibir oferta com payload completo para aceite
- Resposta mínima:

```json
{
  "id": "uuid",
  "origin": {
    "name": "Dark Store Centro",
    "address": "Rua A, 100"
  },
  "destination": {
    "name": "Cliente Final",
    "address": "Rua B, 200"
  },
  "distance_meters": 5400,
  "estimated_seconds": 1800,
  "fare_cents": 2200,
  "sla_seconds": 2400,
  "weight_grams": 1200,
  "volume_cm3": 4500,
  "packages_count": 2,
  "stops": [
    {
      "id": "uuid",
      "sequence": 1,
      "type": "PICKUP"
    }
  ]
}
```

#### 5. Devolver Ordem Aceita
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/orders/{order_id}/release`
- Auth: `Bearer JWT`
- Body:

```json
{
  "reason": "Aceitei por engano e preciso liberar a corrida"
}
```
- Objetivo: permitir devolução segura da corrida pelo motorista apenas no estado `ACCEPTED`
- Regras:
- não cancela o pedido comercial da loja; apenas reabre a corrida para redistribuição
- bloqueia devolução parcial quando a ordem pertence a manifesto agrupado
- gera auditoria operacional e evento `ORDER_RELEASED_BY_DRIVER`

#### 5. Registrar Prova de Coleta
- Situação: `IMPLEMENTADO PARCIAL`
- Método: `POST`
- Rota: `/driver/stops/{stop_id}/pickup-proof`
- Auth: `Bearer JWT`
- Body `multipart/form-data`
- Campos:
- `proof_type`
- `file`
- `lat`
- `lng`
- `gps_accuracy_meters`
- `captured_at`
- `pin_code`
- `qr_code`
- `barcode`
- Objetivo: suportar evidência jurídica da coleta

#### 6. Registrar Prova de Entrega
- Situação: `IMPLEMENTADO PARCIAL`
- Método: `POST`
- Rota: `/driver/stops/{stop_id}/delivery-proof`
- Auth: `Bearer JWT`
- Body `multipart/form-data`
- Campos:
- `proof_type`
- `file`
- `lat`
- `lng`
- `gps_accuracy_meters`
- `captured_at`
- `pin_code`
- `confirmation_code`
- `signature_payload`
- Objetivo: suportar POD enterprise

#### 7. Registrar Ocorrência Operacional
- Situação: `IMPLEMENTADO BASE`
- Método: `POST`
- Rota: `/driver/incidents`
- Auth: `Bearer JWT`
- Body:

```json
{
  "order_id": "uuid",
  "stop_id": "uuid",
  "type": "CLIENTE_AUSENTE",
  "description": "Cliente não atendeu após 3 tentativas",
  "lat": -23.55,
  "lng": -46.63,
  "captured_at": "2026-06-21T14:00:00Z"
}
```
- Dependências:
- modelo de incidente
- anexos
- workflow operacional

#### 8. Anexar Evidência a Ocorrência
- Situação: `IMPLEMENTADO BASE`
- Método: `POST`
- Rota: `/driver/incidents/{incident_id}/attachments`
- Auth: `Bearer JWT`
- Body `multipart/form-data`
- Campos:
- `file`
- `attachment_type`
- `lat`
- `lng`
- `captured_at`

#### 9. Encerrar Jornada
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/shifts/check-out`
- Auth: `Bearer JWT`
- Objetivo: formalizar horário final, tempo trabalhado e pendências do turno

#### 10. KPIs Pessoais do Entregador
- Situação: `IMPLEMENTADO PARCIAL`
- Método: `GET`
- Rota: `/driver/performance`
- Auth: `Bearer JWT`
- Query params:
- `period=today|week|month`
- Resposta mínima:

```json
{
  "deliveries": 18,
  "earnings_cents": 25400,
  "sla_success_rate": 97.2,
  "acceptance_rate": 91.0,
  "cancellation_rate": 1.1,
  "rating": 4.8
}
```

### Prioridade P1 — Necessários para Escala e Operação Avançada

#### 11. Reservar Horário
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/shifts/reservations`
- Auth: `Bearer JWT`
- Objetivo: permitir que o condutor reserve janelas disponíveis

#### 12. Listar Disponibilidade e Agenda
- Situação: `IMPLEMENTADO PARCIAL`
- Método: `GET`
- Rota: `/driver/shifts/calendar`
- Auth: `Bearer JWT`
- Objetivo: expor agenda do entregador; vagas abertas ainda não estão disponíveis

#### 13. Reordenar ou Consultar Rota Otimizada
- Método: `GET`
- Rota: `/driver/routes/{manifest_id}`
- Auth: `Bearer JWT`
- Objetivo: retornar sequência atual, ETA e justificativa de otimização

#### 14. Navegação Externa
- Método: `GET`
- Rota: `/driver/navigation/{stop_id}`
- Auth: `Bearer JWT`
- Objetivo: retornar deeplinks seguros para Google Maps e Waze

#### 15. Chat com Operação
- Método: `GET`
- Rota: `/driver/chats/operations`
- Auth: `Bearer JWT`

#### 16. Enviar Mensagem para Operação
- Método: `POST`
- Rota: `/driver/chats/operations/messages`
- Auth: `Bearer JWT`

#### 17. Mensagens Rápidas
- Método: `GET`
- Rota: `/driver/quick-messages`
- Auth: `Bearer JWT`

#### 18. Solicitar Contato com Cliente
- Método: `POST`
- Rota: `/driver/orders/{order_id}/contact`
- Auth: `Bearer JWT`
- Objetivo: mascarar número e auditar tentativa de contato

#### 19. Prestação de Contas
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/expenses`
- Auth: `Bearer JWT`
- Body:

```json
{
  "type": "PEDAGIO",
  "amount_cents": 1800,
  "description": "Pedágio Marginal",
  "order_id": "uuid"
}
```

#### 20. Anexar Comprovante de Despesa
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/expenses/{expense_id}/receipt`
- Auth: `Bearer JWT`

### Prioridade P2 — Segurança, Offline e Antifraude

#### 21. Registrar Dispositivo
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/devices/register`
- Auth: `Bearer JWT`
- Objetivo: controlar aparelho confiável, device fingerprint e limite de aparelhos

#### 22. Listar Dispositivos Vinculados
- Situação: `IMPLEMENTADO`
- Método: `GET`
- Rota: `/driver/devices`
- Auth: `Bearer JWT`

#### 23. Revogar Dispositivo
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/devices/{device_id}/revoke`
- Auth: `Bearer JWT`

#### 24. Consentimentos e Termos
- Situação: `IMPLEMENTADO`
- Método: `GET`
- Rota: `/driver/compliance/consents`
- Auth: `Bearer JWT`

#### 25. Aceitar Termo
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/compliance/consents/{consent_id}/accept`
- Auth: `Bearer JWT`

#### 25.1. Revogar Termo
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/compliance/consents/{consent_id}/revoke`
- Auth: `Bearer JWT`

#### 25.1. Publicar Documento de Compliance
- Situação: `IMPLEMENTADO BASE`
- Método: `POST`
- Rota: `/operator/compliance/documents`
- Auth: `Bearer JWT`

#### 25.2. Listar Documentos de Compliance
- Situação: `IMPLEMENTADO BASE`
- Método: `GET`
- Rota: `/operator/compliance/documents`
- Auth: `Bearer JWT`

#### 25.3. Arquivar Documento de Compliance
- Situação: `IMPLEMENTADO BASE`
- Método: `POST`
- Rota: `/operator/compliance/documents/{document_id}/archive`
- Auth: `Bearer JWT`

#### 25.4. Abrir Solicitação do Titular
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/driver/privacy/requests`
- Auth: `Bearer JWT`

#### 25.5. Listar Solicitações do Titular
- Situação: `IMPLEMENTADO`
- Método: `GET`
- Rotas:
- `/driver/privacy/requests`
- `/operator/privacy/requests`
- Auth: `Bearer JWT`

#### 25.6. Resolver Solicitação do Titular
- Situação: `IMPLEMENTADO`
- Método: `POST`
- Rota: `/operator/privacy/requests/{request_id}/resolve`
- Auth: `Bearer JWT`

#### 25.7. Gerenciar Política de Retenção
- Situação: `IMPLEMENTADO`
- Métodos:
- `GET /operator/compliance/retention-policies`
- `POST /operator/compliance/retention-policies`
- `POST /operator/compliance/retention-policies/{policy_id}/disable`
- Auth: `Bearer JWT`
- Observação: a task `logistics.tasks.execute_retention_policies` aplica minimização real de `Proof`, `DriverConsentAcceptance`, `DriverOfflineSyncBatch`, `DriverDeviceSecurityEvent` e `DriverIncident`.

#### 26. Sincronização Offline
- Situação: `IMPLEMENTADO BASE`
- Método: `POST`
- Rota: `/driver/offline/sync`
- Auth: `Bearer JWT`
- Objetivo: subir lote de eventos acumulados offline

#### 27. Auditoria de Segurança do Device
- Situação: `IMPLEMENTADO BASE`
- Método: `POST`
- Rota: `/driver/security/device-attestation`
- Auth: `Bearer JWT`
- Objetivo: receber flags de root, jailbreak, mock location e spoofing

### Prioridade P3 — IA Operacional e Diferenciação de Produto

#### 28. Assistente do Condutor
- Método: `GET`
- Rota: `/driver/assistant/insights`
- Auth: `Bearer JWT`
- Objetivo: retornar insights operacionais contextualizados

#### 29. Classificação Automática de Ocorrência
- Método: `POST`
- Rota: `/driver/incidents/classify`
- Auth: `Bearer JWT`
- Objetivo: classificar texto, foto e contexto geográfico

#### 30. Recomendação de Região e Horário
- Método: `GET`
- Rota: `/driver/assistant/opportunity-zones`
- Auth: `Bearer JWT`
- Objetivo: sugerir melhor região e melhor horário com base em oferta e performance

## Decisão de Produto para o Backend
- Para o app do condutor em nível enterprise, o contrato atual cobre aproximadamente:
- `bom` em telemetria, aceite concorrencial, wallet e base de despacho
- `médio/bom` em escalas, dispositivos, despesas, portal básico do lojista e redistribuição segura pré-coleta
- `ainda parcial` em comunicação avançada, homologação específica por parceiro e offline completo; `LGPD avançado` agora cobre revogação, solicitações do titular e retenção com minimização
- A recomendação continua sendo homologar parceiros externos, aplicar migrations novas e validar UAT operacional antes de afirmar prontidão total de produção.

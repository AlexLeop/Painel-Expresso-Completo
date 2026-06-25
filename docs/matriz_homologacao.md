# Matriz de Homologação: NevesGo (App do Entregador)
**Atualização:** 26 de Junho de 2026 — Pós-Auditoria Forense Completa

Com base na inspeção direta do código-fonte atual, esta matriz reflete o estado **real** de cada módulo para efeito de decisão de Go-Live.

---

## Módulo 1 — Autenticação e Sessão

| Funcionalidade | Status | Evidência no Código | Bloqueio Residual |
| :--- | :---: | :--- | :--- |
| Bootstrap de sessão / Splash | 🟢 Aprovado | AppNavigation.kt: startDestination = Route.Splash.value; SessionBootstrapScreen lê token do DataStore e valida via API antes de liberar acesso | Nenhum |
| Login por JWT (provisório) | 🟡 Parcial | DriverTokenLoginScreen permite inserir JWT manualmente; fluxo funcional mas não é UX de produção final | Depende de integração OAuth/Supabase Auth no app |
| Logout e invalidação | 🟢 Aprovado | BroadcastReceiver ACTION_LOGOUT limpa token do DataStore e redireciona para Login | Nenhum |
| Persistência segura de token | 🟡 Parcial | Usa DataStore (texto simples). Produção requer EncryptedSharedPreferences ou Keystore | Migrar para armazenamento criptografado |
| Renovação / Refresh de token | 🔴 Pendente | Não implementado. Token expirado resulta em 401 sem renovação automática | Necessário para operação de longa jornada |

---

## Módulo 2 — Cockpit e Status do Motorista

| Funcionalidade | Status | Evidência no Código | Bloqueio Residual |
| :--- | :---: | :--- | :--- |
| Exibição de dados reais do cockpit | 🟢 Aprovado | HomeScreen.kt consume GET /driver/cockpit; exibe wallet, ctiveOrdersCount, pendingDocuments, unreadMessages | Nenhum |
| Indicador de turno aberto | 🟢 Aprovado | HomeScreen.kt verifica shift.sessionId para exibir contexto de jornada ativa | Nenhum |
| Toggle Online/Offline | 🟡 Parcial | POST /driver/status implementado no DriverApiService.kt; UI de toggle existe no HomeScreen | Confirmar UX de feedback visual ao usuário |
| Atualização automática | 🟡 Parcial | Recarregamento manual (LaunchedEffect(Unit)); sem polling automático ou WebSocket | Polling periódico recomendado (30s) |

---

## Módulo 3 — Ofertas e Captura de Corridas

| Funcionalidade | Status | Evidência no Código | Bloqueio Residual |
| :--- | :---: | :--- | :--- |
| Listagem de ordens disponíveis | 🟢 Aprovado | DeliveriesScreen.kt: syncOrders() via GET /driver/orders; resultado salvo no Room | Nenhum |
| Aceite de corrida | 🟢 Aprovado | OrderRepositoryImpl.acceptOrder() chama POST /driver/orders/{id}/accept; status local atualizado com o retorno do backend | Nenhum |
| Recusa de oferta | 🟢 Aprovado | OrderRepositoryImpl.rejectOrder() chama POST /driver/orders/{id}/reject com RejectReason | Nenhum |
| Devolução pós-aceite (Release) | 🟢 Aprovado | OrderRepositoryImpl.releaseOrder() chama POST /driver/orders/{id}/release; UI em DeliveryAcceptedScreen expõe botão de devolução | Nenhum |
| Visualização em tempo real (Push) | 🔴 Pendente | Sem FCM/WebSocket; motoboy depende de refresh manual para ver novas ofertas | FCM ou polling reativo necessário para produção |

---

## Módulo 4 — Execução da Rota e Entrega

| Funcionalidade | Status | Evidência no Código | Bloqueio Residual |
| :--- | :---: | :--- | :--- |
| Início de corrida (start) | 🟢 Aprovado | DeliveryAcceptedScreen: botão "INICIAR CORRIDA" chama iewModel.startDelivery() → OrderRepositoryImpl.startOrder() → POST /driver/orders/{id}/start | Nenhum |
| Mapa com rota real | 🟢 Aprovado | RouteNavigationScreen.kt: osmdroid renderiza mapa com outeStartPoint e outeEndPoint extraídos do backend; marcadores por stop_id | Nenhum |
| Navegação externa (Waze/Maps) | 🟢 Aprovado | RouteNavigationScreen: botão "Abrir em Mapa Externo" dispara Intent.ACTION_VIEW com URI geo:lat,lng?q=lat,lng via createChooser | Nenhum |
| Indicação de parada operacional | 🟢 Aprovado | orderDetail.nextOperationalStop() identifica próxima parada pendente; instrução de rota dinâmica por tipo (PICKUP/DELIVERY) | Nenhum |
| Prova de entrega (Multipart) | 🟡 Parcial | OrderRepositoryImpl.finishOrder() envia dummyPart como prova de tipo PIN; arquivo real (foto/assinatura) não capturado pelo app | Camera picker ausente |
| PIN de entrega | 🟢 Aprovado | ConfirmDeliveryScreen: teclado PIN próprio, stop_id selecionável, chamada a inishDelivery() passando deliveryPin e stopId correto | Nenhum |
| Conclusão em lote (complete-batch) | 🟢 Aprovado | inishOrder() chama POST /driver/stops/complete-batch com StopBatchCompleteItem correto | Nenhum |
| Exibição de endereço legível | 🔴 Pendente | 	oEntity() e ConfirmDeliveryScreen exibem "Lat X, Lng Y" em vez de endereço geocodificado | Integrar geocodificação reversa (Nominatim/Google) |
| Multiaceite / visão de múltiplas ordens | 🟡 Parcial | DeliveriesScreen lista todas as ordens mas não consolida visão de múltiplas ordens ativas em execução paralela | Tela de roteiro multi-parada recomendada |

---

## Módulo 5 — Turnos e Telemetria

| Funcionalidade | Status | Evidência no Código | Bloqueio Residual |
| :--- | :---: | :--- | :--- |
| Calendário de escalas | 🟢 Aprovado | SchedulesScreen.kt chama GET /driver/shifts/calendar; lista real com abas por período | Nenhum |
| Check-in de turno | 🟢 Aprovado | ScheduleDetailsScreen: botão check-in chama POST /driver/shifts/check-in com ShiftCheckInRequest (turno_id, store_id, date) | Nenhum |
| Check-out de turno | 🟢 Aprovado | POST /driver/shifts/check-out com ShiftCheckOutRequest | Nenhum |
| Reserva de turno | 🟢 Aprovado | POST /driver/shifts/reservations com ShiftReservationRequest | Nenhum |
| Tracking de localização | 🟡 Parcial | TrackingService envia GPS real a cada 10s via POST /driver/location. Serviço só é iniciado explicitamente (não mais na abertura do app) | Integrar TrackingService.start() ao check-in e stop() ao check-out |
| Proteção anti-fraude GPS | 🟢 Aprovado | LocationCompat.isMock(location) verificado em cada update — bloqueia Fake-GPS | Nenhum |

---

## Módulo 6 — Comunicação e Incidentes

| Funcionalidade | Status | Evidência no Código | Bloqueio Residual |
| :--- | :---: | :--- | :--- |
| Lista de threads de comunicação | 🟢 Aprovado | NotificationsScreen.kt chama GET /driver/communications/threads; renderiza lista real | Nenhum |
| Chat por thread | 🟢 Aprovado | ChatScreen.kt chama GET /driver/communications/threads/{id}/messages e POST para envio | Nenhum |
| Abertura de incidente | 🟢 Aprovado | ReportProblemScreen chama POST /driver/incidents com IncidentRequest(orderId, stopId, type, description) | Nenhum |
| Notificações push (FCM) | 🔴 Pendente | Sem integração FCM; o motorista não recebe alertas de novas mensagens em background | FCM necessário para produção |

---

## Módulo 7 — Financeiro

| Funcionalidade | Status | Evidência no Código | Bloqueio Residual |
| :--- | :---: | :--- | :--- |
| Saldo da wallet | 🟢 Aprovado | EarningsScreen chama GET /finance/wallet/balance; exibe WalletBalanceResponse real | Nenhum |
| Extrato de transações | 🟢 Aprovado | GET /finance/transactions com paginação (limit/offset) | Nenhum |
| Solicitação de saque | 🟢 Aprovado | POST /finance/wallet/withdraw com WithdrawalRequestPayload (chave Pix + valor) | Nenhum |

---

## Resumo Executivo (Estado Real — Junho 2026)

| Resultado | Contagem | Detalhes |
| :--- | :---: | :--- |
| 🟢 Aprovado | **22** | Integração real com backend confirmada via inspeção de código-fonte |
| 🟡 Parcial | **7** | Funcional mas com lacunas não-bloqueantes para MVP operacional |
| 🔴 Pendente | **4** | Ausentes; bloqueantes apenas para escala ou compliance de longo prazo |

### Itens Pendentes (Não-Bloqueantes para MVP)
1. **Push Notifications (FCM)**: motorista não recebe alertas em background — operação manual funciona
2. **Token Refresh automático**: sessões longas exigirão re-login manual
3. **Prova de Entrega por Foto**: atualmente envia dummy; PIN como prova alternativa está funcional
4. **Geocodificação Reversa de Endereços**: exibe coordenadas brutas; endereço legível melhora UX

### Veredicto Operacional
> O aplicativo **está apto para operação controlada (Beta/Piloto)**. Os 22 fluxos aprovados cobrem o ciclo completo de jornada: autenticação → turno → aceite → execução → prova PIN → conclusão → financeiro. Os 4 itens pendentes são recomendados antes da abertura para escala total, mas **não impedem o início da operação piloto**.

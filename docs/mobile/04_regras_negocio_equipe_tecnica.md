# NevesGo — Regras de Negócio (Equipe Técnica e Estratégia)

---

## 1. Autenticação e Sessão

### 1.1 Fluxo de Login
- `SplashScreen` chama `apiService.completeLoginBootstrap()` ao iniciar.
- Endpoint: `POST /accounts/auth/login`
- Se 2xx → navega para `home`; qualquer outra resposta → navega para `login`
- Token JWT armazenado em `SecureStorage` (EncryptedSharedPreferences)

### 1.2 Renovação de Token
- `TokenAuthenticator` (OkHttp Authenticator) intercepta respostas 401 e tenta refresh via Supabase
- **BUG CRÍTICO**: `supabaseUrl = ""` e `supabaseKey = ""` estão vazios no código — o refresh NUNCA é executado
- Consequência: o token expira → todas as requisições retornam 401 → broadcast `com.example.ACTION_LOGOUT` → usuário deslogado sem aviso

### 1.3 Logout
- `ProfileScreen.SettingsItem("Sair da Conta")` executa:
  1. `TrackingService.stop(context)`
  2. `SecureStorage.clearToken(context)`
  3. `navController.navigate("login") { popUpTo(0) }`
- Também acionado pelo broadcast `com.example.ACTION_LOGOUT` registrado em `NevesGoApp()`

---

## 2. Disponibilidade do Motorista

### 2.1 Toggle Online/Offline
- Chamado via `DriverViewModel.setAvailability(isOnline: Boolean)`
- Payload: `POST /driver/status` com body `{status: "ONLINE" | "OFFLINE"}`
- Após sucesso: `loadCockpit()` é chamado para atualizar o estado local
- `_statusUpdateInFlight` controla o loading state durante a atualização

### 2.2 TrackingService — Lógica de Ciclo de Vida
- Inicia quando: `cockpit.driver.online == true` **OU** `cockpit.shift?.sessionId != null`
- Para quando: nenhuma das condições acima é verdadeira
- Também inicia/para explicitamente no check-in/check-out de turno

---

## 3. Fluxo de Pedido (State Machine)

### 3.1 Estados e Transições
```
OFFERED  →  ACCEPTED  →  STARTED  →  ARRIVED  →  COMPLETED
               ↓
         RETURNING_TO_STORE
               ↓
        CANCELED_IN_TRANSIT
```

### 3.2 Regras de Cada Transição

| Transição | Endpoint | Arquivo | Comportamento pós-sucesso |
|---|---|---|---|
| OFFERED → ACCEPTED | `POST /driver/orders/{id}/accept` | `DeliveryViewModel.acceptDelivery()` | Atualiza Room DB com status ACCEPTED, navega para `corrida_aceita/{orderId}` |
| ACCEPTED → STARTED | `POST /driver/orders/{id}/start` | `DeliveryViewModel.startDelivery()` | Atualiza Room DB, navega para `navigation_screen/{orderId}` |
| STARTED → ARRIVED | `POST /driver/orders/{id}/arrive` | `RouteNavigationScreen` (via `arrivedAtStop`) | Atualiza Room DB, navega para `confirmar_entrega/{orderId}` |
| ARRIVED → COMPLETED | `POST /driver/stops/{stopId}/delivery-proof` + `POST /driver/stops/complete-batch` | `OrderRepositoryImpl.finishOrder()` | Atualiza Room DB para COMPLETED, navega para `entrega_finalizada/{fareCents}` |
| Qualquer → RELEASED | `POST /driver/orders/{id}/release` | `DeliveryViewModel.releaseDelivery()` | Status volta para OFFERED, pedido retorna ao pool |
| OFFERED → REJECTED | `POST /driver/orders/{id}/reject` | `DeliveryViewModel.rejectDelivery()` | OrderEntity deletado do Room DB |

### 3.3 Sincronização de Pedidos
- `DeliveryViewModel.init {}` chama `repository.syncOrders()` uma vez ao iniciar
- FCM trigger: qualquer push recebido chama `syncOrders()` novamente
- `syncOrders()` faz:
  1. `GET /driver/orders` — lista resumida
  2. Para CADA pedido, chama `GET /driver/orders/{order_id}` em paralelo (`async/awaitAll`)
  3. `orderDao.clearAll()` + `orderDao.insertAll(entities)`
- **Problema de performance**: N+1 API calls por sync (1 lista + N detalhes)

### 3.4 Mapeamento de Entidade (DriverOrderSummary → OrderEntity)
- `originAddress`: geocoding reverso da lat/lng de `details.origin.location`
- `destinationAddress`: geocoding reverso de `details.destination.lastStopLocation`
- Geocoding usa `android.location.Geocoder` — **chamada síncrona** dentro de `async {}` no IO dispatcher
- `slaSeconds` sempre 0 — campo não populado da API

---

## 4. Conclusão de Entrega (Proof of Delivery)

### 4.1 Sequência de API Calls
```
1. POST /driver/stops/{stop_id}/delivery-proof (multipart)
   Fields: proofType ("PIN" | "PHOTO"), lat (null), lng (null), capturedAt (ISO-8601), file (nullable)
   
2. POST /driver/stops/complete-batch
   Body: [{ stopId, deliveryPin, timestamp }]
```
Se o passo 1 falhar → retorna erro e NÃO tenta o passo 2
Se o passo 2 falhar → Order recebe `syncStatus = "PENDING_COMPLETE_BATCH"` no Room DB

### 4.2 Seleção de Parada
- A UI filtra stops de `OrderDetailResponse.stops` onde:
  - `stop.isCompleted != true`
  - `stop.type != "PICKUP"` (somente DELIVERY)
- Chips horizontais permitem selecionar qual parada concluir

### 4.3 PIN vs Foto
- PIN: teclado customizado 4 dígitos — totalmente funcional
- Foto: `enabled = false` hardcoded no botão — câmera NÃO integrada nesta tela
  - **Nota**: CameraX está nas dependências (`build.gradle`) mas não está conectado à UI de confirmação

---

## 5. Relatório de Incidentes

### 5.1 Payload
```kotlin
IncidentRequest(
  orderId: String?,
  stopId: String?,
  type: String,       // "Nao encontrei o cliente", "Endereco incorreto", etc.
  description: String,
  lat: Double?,       // GPS_SPOOFING usa lat/lng; manual usa null
  lng: Double?
)
```

### 5.2 Fluxo com Evidência Fotográfica
1. `POST /driver/incidents` → retorna `incidentId`
2. Se `incidentProofUri != null`: `POST /driver/incidents/{incidentId}/attachments` (multipart com imagem)

### 5.3 GPS Spoofing
- `TrackingService.sendLocationToServer()` checa `LocationCompat.isMock(location)`
- Se mock: chama `apiService.reportIncident(IncidentRequest(type = "GPS_SPOOFING", ...))` **ANTES** de enviar a localização
- O entregador não é notificado nem bloqueado — apenas o backend é avisado

---

## 6. Gerenciamento de Turnos (Escalas)

### 6.1 Tipos de Turno
- `SCHEDULE`: turno publicado aberto a entregadores da escala
- `RESERVATION`: turno reservado para um entregador específico

### 6.2 Lógica de Botões na UI (SchedulesScreen)
```kotlin
val hasOpenSession = cockpit.shift?.sessionId != null
val isThisShiftActive = cockpit.shift?.sessionId == item.turnoId

when {
  isThisShiftActive -> mostrar "FAZER CHECK-OUT"
  hasOpenSession -> mostrar "JA EXISTE JORNADA ABERTA" (desabilitado)
  item.kind == "RESERVATION" -> mostrar "FAZER CHECK-IN"
  item.kind == "SCHEDULE" -> mostrar "RESERVAR + CHECK-IN" ou "FAZER CHECK-IN"
}
```

### 6.3 Check-in/Check-out
- Check-in: `POST /driver/shifts/check-in` → em sucesso: `TrackingService.start()`
- Check-out: `POST /driver/shifts/check-out` → em sucesso: `TrackingService.stop()`
- Cockpit é recarregado após ambas as operações

---

## 7. Rastreamento GPS

### 7.1 Configuração do FusedLocationProvider
```
interval = 10.000ms
minUpdateInterval = 5.000ms
priority = HIGH_ACCURACY (se ACCESS_FINE_LOCATION) | BALANCED_POWER (se apenas COARSE)
```

### 7.2 Endpoint de Telemetria
- URL construída dinamicamente: substitui porta 8000 por 8001 e `api/v1/` por `telemetry` na base URL
- Exemplo: `http://api.expressoneves.com.br:8001/telemetry`
- Header: `X-Device-Token: {device_token}` obtido de SecureStorage

### 7.3 Buffer Offline
```kotlin
// Ao falhar:
db.telemetryDao().insert(TelemetryEntity(lat, lng, heading, speedKmh, timestamp))

// No próximo sucesso:
val offline = db.telemetryDao().getAll()
offline.forEach { enviar ponto cached }
db.telemetryDao().clearAll()
// Então enviar ponto atual
```

---

## 8. Módulo Financeiro

### 8.1 Endpoints
- `GET /finance/wallet/balance` → `WalletBalance(balanceCents, updatedAt)`
- `GET /finance/transactions?limit=50&offset=0` → `List<TransactionItem>`
- `POST /finance/wallet/withdraw` → body: `{pixKey: String, amountCents: Int}`

### 8.2 Cálculo do Breakdown
Calculado localmente na UI:
```kotlin
val totalIn = transactions.filter { it.type !in listOf("PAYOUT", "PENALTY") }.sumOf { it.amountCents }
val totalOut = transactions.filter { it.type in listOf("PAYOUT", "PENALTY") }.sumOf { it.amountCents }
val net = totalIn - totalOut
```

### 8.3 PaymentsScreen
- Reutiliza `FinanceDashboardScreen` com `title = "Pagamentos"` e `showBack = true`
- Exatamente o mesmo conteúdo de `EarningsScreen` — sem diferenciação de negócio

---

## 9. Sistema de Comunicação

### 9.1 Modelo de Dados
```
CommunicationThreadItem {
  threadId, subject?, orderId?, sourceType, status, updatedAt?
}
CommunicationMessageItem {
  messageId, senderType, senderName, message, createdAt?
}
```

### 9.2 Lógica de Renderização das Bolhas
- `senderType == "DRIVER"` → bolha vermelha, lado direito
- qualquer outro → bolha cinza, lado esquerdo; ícone diferente se senderName.contains("loja")

### 9.3 Limitações Técnicas
- `ChatScreen` recarrega lista inteira ao enviar mensagem (sem WebSocket/SSE)
- `NotificationsScreen` tem dois botões "Atualizar" (TopBar actions + TextButton) com lógica idêntica
- Sem polling automático — dados ficam obsoletos sem interação do usuário

---

## 10. Segurança e Infraestrutura

### 10.1 Stack de Interceptors OkHttp (em ordem)
1. `OfflineInterceptor` — cache de rede
2. `AuthInterceptor` — adiciona token
3. `RetryInterceptor` — retry com backoff
4. `IdempotencyInterceptor` — chave de idempotência
5. `HttpLoggingInterceptor` — apenas DEBUG
6. `TokenAuthenticator` — renovação de token em 401

### 10.2 Persistência de Tokens
- `SecureStorage.getToken()` / `saveToken()` / `clearToken()` — usa EncryptedSharedPreferences
- **Inconsistência**: Alguns lugares ainda usam `DataStore<Preferences>` para `jwt_token` (código legado em `AppNavigation.kt` e `ProfileScreen.kt`) enquanto a implementação principal usa `SecureStorage`

### 10.3 Broadcast Receiver de Logout
- Registrado em `NevesGoApp()` com ação `com.example.ACTION_LOGOUT`
- Android 13+: registrado com `RECEIVER_NOT_EXPORTED` (correto)
- Qualquer componente do app pode disparar o logout via broadcast

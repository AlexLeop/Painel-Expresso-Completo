# NevesGo — Features Faltantes, Bugs e Erros (Equipe Técnica)

---

## 🔴 BUGS CRÍTICOS (Quebram funcionalidade principal)

### BUG-001 — Token Refresh Não Funciona
**Arquivo**: `TokenAuthenticator.kt`
**Linha crítica**: `val supabaseUrl = ""` e `val supabaseKey = ""`
**Impacto**: Quando o JWT expira, o `TokenAuthenticator` tenta refresh mas falha silenciosamente pois a URL está vazia. Todas as requisições passam a retornar 401 → broadcast `ACTION_LOGOUT` → usuário deslogado.
**Consequência operacional**: Entregador pode ser deslogado no meio de uma entrega ativa.
**Correção**: Preencher `supabaseUrl` e `supabaseKey` via `BuildConfig` ou `SecureStorage`. Alternativa: remover o `TokenAuthenticator` e implementar refresh via endpoint próprio do Django DRF.

---

### BUG-002 — Câmera/Foto de Comprovante Desabilitada Permanentemente
**Arquivo**: `DeliveryFlowScreens.kt` — `ConfirmDeliveryScreen`
**Código**:
```kotlin
Button(
    onClick = { /* camera nao implementada aqui */ },
    enabled = false  // HARDCODED
)
```
**Impacto**: Entregadores só podem usar PIN para confirmar entrega. Sem opção de foto. A dependência `CameraX` está no `build.gradle` mas não conectada à UI.
**Correção**: Implementar `ActivityResultContracts.TakePicture()` ou `PickVisualMedia`, vincular ao `deliveryProofUri` já presente em `OrderRepositoryImpl.finishOrder()`.

---

### BUG-003 — Timestamp Hardcoded na Lista de Entregas Concluídas
**Arquivo**: `DeliveriesScreen.kt` — `CompletedDeliveryCard`
**Código**: `Text("Finalizado hoje, 14:32")`
**Impacto**: Todas as entregas concluídas exibem o mesmo horário fake, independente do horário real de conclusão.
**Correção**: Adicionar campo `completedAt: String?` em `OrderEntity` e populá-lo ao concluir a entrega. Usar `OffsetDateTime.parse()` para formatar.

---

### BUG-004 — Número de Paradas Hardcoded no Alerta de Nova Corrida
**Arquivo**: `HomeScreen.kt` — `NewDeliveryAlertSheet`
**Código**: `Text("1 parada")` 
**Impacto**: UI sempre mostra "1 parada" independente de o pedido ter múltiplas paradas (multi-stop).
**Correção**: Usar `pendingOrder.stops?.size` do `OrderDetailResponse` ou incluir o campo `stopCount` no `DriverOrderSummary`.

---

### BUG-005 — Geocoder Síncrono em Contexto Assíncrono
**Arquivo**: `OrderRepositoryImpl.kt` — função `getAddress()`
**Problema**: `Geocoder.getFromLocation()` é uma chamada bloqueante (pode levar vários segundos). É chamada dentro de `async {}` no `syncOrders()`, que roda em `Dispatchers.IO`. Em Android 13+, `getFromLocation()` deve ser chamado via listener assíncrono.
**Impacto**: Risco de ANR (Application Not Responding) em dispositivos lentos ou quando há muitos pedidos para sincronizar.
**Correção**: Usar `Geocoder.getFromLocation(lat, lng, maxResults, listener)` (API 33+) com fallback para a versão síncrona em API < 33, dentro do dispatcher correto.

---

### BUG-006 — GlobalScope Usado em FirebaseMessagingService
**Arquivo**: `MyFirebaseMessagingService.kt`
**Código**:
```kotlin
kotlinx.coroutines.GlobalScope.launch(Dispatchers.IO) {
    it.container.orderRepository.syncOrders()
}
```
**Impacto**: `GlobalScope` não respeita o ciclo de vida do Service. Pode causar memory leaks e operações pendentes após o service ser destruído.
**Correção**: Criar um `CoroutineScope(SupervisorJob() + Dispatchers.IO)` no service e cancelá-lo em `onDestroy()`, similar ao `TrackingService`.

---

## 🟠 BUGS MODERADOS (Degradam experiência ou dados)

### BUG-007 — `slaSeconds` Sempre Zero
**Arquivo**: `OrderRepositoryImpl.kt` — `DriverOrderSummary.toEntity()`
**Código**: `slaSeconds = 0`
**Impacto**: Campo de SLA (tempo limite de entrega) não é populado. UI não pode exibir countdown de prazo de entrega.

---

### BUG-008 — Tecla Vírgula Sem Função no Teclado PIN
**Arquivo**: `DeliveryFlowScreens.kt` — `ConfirmDeliveryScreen`
**Problema**: O teclado numérico customizado exibe a tecla "," mas ela não dispara nenhuma ação.
**Correção**: Trocar a tecla "," por vazio/espaço ou pelo caractere `⌫` de backspace duplicado, ou removê-la.

---

### BUG-009 — PaymentsScreen é Duplicata de EarningsScreen
**Arquivo**: `ExtendedEarningsScreens.kt`
**Código**: `PaymentsScreen` chama `FinanceDashboardScreen(title = "Pagamentos", ...)` — idêntico ao `EarningsScreen`
**Impacto**: Duas telas acessíveis por rotas diferentes (`earnings` e `pagamentos`) exibem exatamente o mesmo conteúdo. Confusão para o usuário.

---

### BUG-010 — JourneyDetailsScreen com Dados Hardcoded
**Arquivo**: `ExtendedEarningsScreens.kt`
**Problema**: `JourneyDetailsScreen` exibe dados completamente estáticos (título "Jornada de 25 de Outubro", tempo "08h 45m", 12 entregas, R$ 215,50, lista de pedidos com IDs hardcoded).
**Impacto**: Tela sem funcionalidade real — dados falsos para o entregador.
**Correção**: Integrar com API de histórico de jornada.

---

### BUG-011 — Inconsistência no Armazenamento de Token (DataStore vs SecureStorage)
**Arquivos**: `AppNavigation.kt`, `ProfileScreen.kt` (importam `stringPreferencesKey("jwt_token")` do DataStore), mas `SecureStorage.kt` é a implementação principal.
**Problema**: Código legado ainda referencia DataStore para o token. Se algum path lê do DataStore e outro lê do SecureStorage, podem ocorrer estados inconsistentes.
**Correção**: Remover todas as referências a DataStore para o token JWT e usar exclusivamente `SecureStorage`.

---

### BUG-012 — Tema Escuro não Funciona
**Arquivo**: `ProfileScreen.kt`
**Código**: `SettingsSwitchItem(Icons.Filled.DarkMode, "Tema Escuro", false)`
**Problema**: O Switch exibe estado local mas não persiste e não chama nenhuma função de mudança de tema.

---

### BUG-013 — trackedOrderId não Utilizado no TrackingService
**Arquivo**: `TrackingService.kt`
**Código**: `private var trackedOrderId: String? = null` declarado mas nunca lido ou gravado.
**Impacto**: Se a intenção era rastrear a localização associada a uma ordem específica, esse link está perdido.

---

### BUG-014 — Meus Dados sem Implementação
**Arquivo**: `ProfileScreen.kt`
**Código**: `SettingsItem(Icons.Filled.Person, "Meus Dados", "Visualizar e editar dados pessoais")` — sem `onClick`
**Impacto**: Entregador não consegue ver nem editar seus dados pessoais.

---

### BUG-015 — Idioma sem Funcionalidade
**Arquivo**: `ProfileScreen.kt`
**Código**: `SettingsItem(Icons.Filled.Language, "Idioma", "Português", hasAction = true)` — sem `onClick`
**Impacto**: Item de UI morto.

---

## 🟡 FEATURES FALTANTES (Não implementadas mas necessárias)

### FEAT-001 — Auto-Refresh de Chat (Polling ou WebSocket)
**Tela**: `ChatScreen`
**Problema**: Mensagens só atualizam quando o usuário aperta "Atualizar". Sem polling ou WebSocket.
**Solução sugerida**: Polling com `LaunchedEffect + delay(5000)` ou migração para WebSocket/Server-Sent Events.

---

### FEAT-002 — Notificação Push para Mensagem Recebida em Chat
**Arquivo**: `MyFirebaseMessagingService.kt`
**Problema**: Todo push apenas dispara `syncOrders()`. Não há diferenciação para mensagens de chat que poderiam mostrar uma notificação local.
**Solução**: Verificar `remoteMessage.data["type"]` e exibir `NotificationCompat.Builder` local para tipo `CHAT_MESSAGE`.

---

### FEAT-003 — Deep Link em Notificações Push
**Problema**: Ao tocar na notificação FCM (especialmente para nova corrida), o app abre na tela principal sem navegar para a tela relevante.
**Solução**: Adicionar `PendingIntent` com rota específica no payload FCM.

---

### FEAT-004 — Integração Câmera para Prova de Entrega
**Ver BUG-002** — infraestrutura de API já existe (`finishOrder` aceita `deliveryProofUri`), apenas a captura via câmera na UI está faltando.

---

### FEAT-005 — Tela "Meus Dados" (Perfil do Entregador)
**Problema**: Item no menu existe mas sem funcionalidade.
**Dados esperados**: Nome, foto, CNH, veículo, dados bancários/PIX, avaliação.

---

### FEAT-006 — Countdown de SLA na Entrega
**Problema**: `slaSeconds` existe na `OrderEntity` mas sempre vale 0.
**Funcionalidade esperada**: Exibir countdown de prazo na tela de navegação.

---

### FEAT-007 — Paginação do Histórico de Transações
**Arquivo**: `EarningsScreen.kt`
**Problema**: `GET /finance/transactions?limit=50&offset=0` — `offset` está hardcoded em 0. Sem scroll infinito.
**Solução**: Implementar `LazyColumn` com detecção de fim de lista e incremento de `offset`.

---

### FEAT-008 — Histórico de Jornadas Real
**Arquivo**: `ExtendedEarningsScreens.kt` — `JourneyDetailsScreen`
**Problema**: Tela com dados hardcoded. Precisa de endpoint de histórico de jornada.

---

### FEAT-009 — Bloqueio de Entregador com GPS Falso
**Problema**: GPS spoofing é detectado e reportado, mas o entregador não é bloqueado nem notificado.
**Solução**: Ao detectar mock, parar TrackingService, exibir dialog de aviso e aguardar liberação da operação.

---

### FEAT-010 — Feedback Visual de Sincronização Pendente
**Problema**: Pedidos com `syncStatus = "PENDING_COMPLETE_BATCH"` ficam no estado COMPLETED no Room DB local, mas o backend não foi notificado. Não há indicação visual para o entregador.
**Solução**: Exibir badge de "Pendente de Sincronização" no card da entrega e tentar reenvio automático.

---

### FEAT-011 — Suporte a Múltiplas Paradas (Multi-Stop Real)
**Problema**: O modelo de dados suporta múltiplas paradas (`stops: List<StopDetail>`), mas o alerta de corrida mostra "1 parada" fixo e a UI de navegação assume stop única em vários pontos.

---

### FEAT-012 — Tela de Avaliação Pós-Entrega
**Problema**: Não existe tela de feedback ou avaliação do entregador após a conclusão da corrida.

---

## ⚙️ DÉBITO TÉCNICO E MELHORIAS DE CÓDIGO

| ID | Descrição | Arquivo |
|---|---|---|
| TEC-001 | `namespace = "com.example"` genérico demais — risco em produção | `build.gradle.kts` |
| TEC-002 | Sem flavors de build (dev/staging/prod) — mesma APK para todos ambientes | `build.gradle.kts` |
| TEC-003 | `security-crypto:1.1.0-alpha06` em produção — versão alpha instável | `build.gradle.kts` |
| TEC-004 | Sem injeção de dependência formal (Hilt/Koin) — `AppContainer` manual não escala | `MyApplication.kt` |
| TEC-005 | `DeliveryViewModel` compartilhado entre múltiplas telas sem escopo isolado | `DeliveryViewModel.kt` |
| TEC-006 | N+1 API calls em `syncOrders()` (1 GET /orders + N GET /orders/{id} em paralelo) | `OrderRepositoryImpl.kt` |
| TEC-007 | OSRM público sem SLA — instável para produção | `RouteNavigationScreen.kt` |
| TEC-008 | `TrackingService` usa `Looper.getMainLooper()` para location callback (deveria ser null ou handler separado) | `TrackingService.kt` |
| TEC-009 | Sem cobertura de testes implementada (frameworks configurados mas sem casos) | Toda a codebase |
| TEC-010 | Sem ProGuard rules para Moshi + OkHttp — risk of reflection issues em release | `proguard-rules.pro` |
| TEC-011 | `IdempotencyInterceptor` gera novo UUID por tentativa de retry, quebrando a idempotência | Interceptors |
| TEC-012 | DataStore importado em AppNavigation.kt e ProfileScreen.kt mas não deveria ser usado para token | múltiplos arquivos |

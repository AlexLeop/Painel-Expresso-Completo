# Frente 3: Arquitetura de Front-End e UX de Alta Disponibilidade
**Estratégia "Offline-First", Sincronização e Reactivity (React Native & Next.js)**

Para que o sistema suporte o rigor físico e as áreas de sombra de conectividade (3G/4G intermitente no trânsito urbano), a camada de visualização (Front-End) não pode ser um mero espelho "burro" do banco de dados. Ela deve atuar como um sistema distribuído inteligente.

---

## 1. Next.js (Torre de Controle): O Radar Logístico em Tempo Real

O painel de despacho não pode sofrer de latência ou depender de `F5` (reloads). Ele deve operar como uma torre de controle de tráfego aéreo.

### A. Rastreamento Instantâneo de Veículos (Supabase Broadcast)
Para evitar que o Next.js faça milhares de consultas por segundo na API do Django apenas para saber onde estão as motos:
*   **O Contrato:** O FastAPI (na ingestão de telemetria) emitirá as coordenadas do GPS *diretamente* para o **Supabase Realtime (via funcionalidade Broadcast)** num canal fechado do tenant (ex: `channel:telemetry_operator_<id>`).
*   **Next.js Subscriptions:** O Front-End assina este canal em memória. Os pinos dos motoboys no mapa do *React Leaflet* ou *Google Maps* deslizarão pela tela a cada ping em milissegundos, **sem jamais tocar no banco de dados PostgreSQL** ou onerar o servidor.

### B. Transição de Status de Pedidos (Postgres Changes)
*   **O Contrato:** Para o ciclo de vida do pedido (ex: `PREPARING` -> `READY_FOR_DISPATCH`), o Next.js assinará a funcionalidade **Postgres Changes** do Supabase para a tabela `Order` (filtrada pelo RLS do `operator_id`).
*   **UX:** Quando o Django/Celery alterar o status de um pedido no banco, o Supabase dispara um evento via WebSocket. O Next.js atualiza o quadro Kanban do despachante instantaneamente.

---

## 2. React Native (App do Motoboy): A Máquina "Offline-First"

A exigência de conexão ininterrupta é o maior causador de atritos (e abandonos de plataforma) na logística *Last-Mile*. O App do entregador deve ser blindado contra túneis, garagens subterrâneas e torres de celular inoperantes.

### A. O Banco de Dados Local (WatermelonDB)
Utilizaremos o **WatermelonDB** (montado sobre SQLite) no React Native. Diferente do Redux ou Async Storage, o WatermelonDB consegue gerenciar dezenas de milhares de registros (rotas, metadados de pedidos) com consultas a nível nativo (C++ via JSI) rodando a 60 FPS na UI principal sem travamentos.

### B. O Fluxo de Proof of Delivery (POD) "Shadow Sync"
1. **Atuação Offline:** O motorista chega no subsolo de um condomínio (sem 4G). Ele finaliza a entrega no app, coleta a assinatura vetorial (SVG) do cliente e tira a foto do pacote na porta.
2. **Gravação Local:** O app registra a parada como `COMPLETED` no WatermelonDB, gera o PIN e encadeia as fotos. O motorista fica livre para prosseguir para a próxima entrega.
3. **Background Sync:** Um serviço em background (escutando via `NetInfo`) detecta quando a moto sobe a rampa e o 4G é restabelecido.
4. **Resolução de Fila:** O *Sync Engine* dispara o `POST /api/v1/stops/{id}/complete` em lote (Batch) para o Django contendo os metadados pendentes. Se ocorrer um erro no servidor (ex: Django offline), a fila permanece intacta no SQLite até que um `HTTP 200` seja retornado.

> [!IMPORTANT]
> **Bloqueio de Recursos Físicos:** Como definido na arquitetura principal, a atuação Offline-First é restrita a operações que **não exigem consenso físico** (como comprovar que entregou algo que já estava com ele). Ações competitivas, como **Aceitar um novo Pedido** ou **Rejeitar uma Ordem**, verificarão ativamente a conexão e bloquearão o botão da UI caso o motorista esteja offline, impedindo duplicações de alocação física.

---

## 3. Contrato de API Reativa: O Combate às "Race Conditions" de UI

O cenário mais frustrante para um entregador Nuvem é a "Disputa de Tela": clicar em "Aceitar" em uma corrida rentável e ver uma tela de carregamento infinita, apenas para receber um erro opaco porque outro motoboy aceitou 1 segundo antes.

### A. Anulação Pessimista e UX Rápida
*   **Ao Clicar no Botão (Front-End):** O React Native dispara um `POST` com o `Idempotency-Key` e aplica um *loading state* isolado apenas no botão apertado.
*   **Lógica Atômica (Back-End):** O Django bate no Redis (Token Bucket com script Lua atômico). Se o pacote já foi capturado, retorna em `< 50ms` um erro claro: `HTTP 409 Conflict (ALREADY_ASSIGNED)`.
*   **Feedback Visual Imediato:** O App consome o erro 409, aplica uma animação de *fade-out* (removendo o card da tela graciosamente) e lança um "Toast" (Aviso): *"Outro entregador foi mais rápido!"*.

### B. "The Disappearing Card" (Broadcast de Fuga)
Para evitar que múltiplos entregadores tentem clicar na mesma ordem esgotada:
*   Assim que a Ordem X for aceita pelo Entregador A, o Django DRF emite uma notificação via Supabase Realtime.
*   O App de todos os outros entregadores (B, C e D) possui um *listener* ativo. Ao receberem a notificação de que a Ordem X foi atribuída, o card da oferta desaparece fisicamente de suas telas em milissegundos, antes mesmo que eles tenham a chance de tocar na tela, criando uma UI reativa "água e óleo" onde ofertas esgotadas somem sem atrito.

---

## Aprovação do Escopo Front-End

Este artefato encerra a fase de concepção técnica (Planejamento e Arquitetura) cobrindo:
1. O Esquema Físico Contábil/DB (`schema.sql`).
2. Os Contratos de Comunicação e Segurança (`system_communication_and_security_contracts.md`).
3. O Design de Reatividade e UX (`frontend_architecture_offline_first.md`).

A arquitetura geral do ecossistema LogiPay está sólida e preparada para a codificação massiva. 
**Por favor, analise as definições de UX Offline-First deste artefato e confirme sua aprovação para iniciarmos o "Dia Zero".**

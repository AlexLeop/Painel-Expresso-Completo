# NevesGo — Regras de Negócio do Aplicativo
## Documento para CEO e CTO

---

## 🎯 Visão Geral do Produto

O **NevesGo** é o aplicativo móvel oficial da **Expresso Neves** para a gestão operacional dos entregadores. Ele conecta motoristas às rotas de entrega em tempo real, controla jornadas de trabalho, processa pagamentos e mantém comunicação direta com a operação.

---

## 🔑 Módulos de Negócio e suas Regras

### 1. Autenticação e Identidade

- O entregador acessa o app com **e-mail e senha**. A autenticação é gerenciada via **JWT (tokens Supabase)**.
- O app verifica automaticamente se há uma sessão válida ao ser aberto. Se válida, o entregador vai direto para o app sem precisar fazer login novamente.
- Ao sair da conta, todo o histórico de sessão é limpo localmente e o rastreamento GPS é encerrado.

> **⚠️ Risco Crítico:** O mecanismo de renovação automática de sessão (refresh de token) está configurado mas **não funciona** — as credenciais Supabase estão ausentes no código. Quando o token expirar, o entregador é deslogado sem aviso, podendo perder entregas em andamento.

---

### 2. Disponibilidade do Entregador (Online/Offline)

- O entregador controla sua disponibilidade manualmente via botão na tela principal.
- **ONLINE**: Apto a receber novas corridas. O backend começa a ofertar pedidos.
- **OFFLINE**: Não recebe novos pedidos. Pode continuar entregas já aceitas.
- O rastreamento GPS em background é ligado/desligado conforme o status do turno, não apenas do botão Online/Offline.

---

### 3. Gestão de Pedidos e Fluxo de Entrega

O fluxo de uma entrega segue este ciclo obrigatório:

```
OFFERED → ACCEPTED → STARTED → ARRIVED → COMPLETED
```

| Etapa | Ação do Entregador | O que acontece no sistema |
|---|---|---|
| **OFFERED** | Recebe alerta com countdown de 10s | Backend oferta o pedido |
| **ACCEPTED** | Aceita o pedido (swipe) | Sistema reserva a corrida para o entregador |
| **STARTED** | Clica "Iniciar Corrida" | Sistema registra início da corrida |
| **ARRIVED** | Swipe "Cheguei" na tela de navegação | Sistema registra chegada ao destino |
| **COMPLETED** | Insere PIN de 4 dígitos do cliente | Sistema libera pagamento ao entregador |

**Estados especiais:**
- `CANCELED_IN_TRANSIT`: Pedido cancelado após início
- `RETURNING_TO_STORE`: Entregador retornando ao ponto de origem
- Entregador pode **devolver** um pedido aceito antes de iniciá-lo (recoloca no pool)
- Entregador pode **recusar** um pedido oferecido com justificativa

**Prova de entrega:**
- O sistema suporta dois tipos: **PIN de 4 dígitos** (confirmado pelo cliente) ou **Foto** (comprovante)
- Atualmente apenas o PIN está funcional. A funcionalidade de foto está bloqueada no app.

---

### 4. Jornadas de Trabalho (Turnos/Escalas)

- A Expresso Neves opera com **escalas de turno** cadastradas no backend
- Há dois tipos de entrada em turno:
  - **SCHEDULE**: Turno disponível para qualquer entregador da escala
  - **RESERVATION**: Turno reservado para um entregador específico
- O entregador faz **check-in** ao iniciar o turno e **check-out** ao finalizar
- **Apenas 1 turno pode estar aberto por entregador ao mesmo tempo**
- O check-in ativa automaticamente o rastreamento GPS em background
- O check-out para o rastreamento GPS

---

### 5. Rastreamento em Tempo Real (GPS)

- O app envia a **localização GPS do entregador a cada 10 segundos** para o backend
- Isso acontece enquanto o entregador tiver um turno ativo ou estiver ONLINE
- O sistema detecta automaticamente **uso de GPS falso (spoofing)** e reporta um incidente de segurança ao backend

**Operação offline:**
- Se o entregador perder conexão, os pontos GPS são armazenados localmente no dispositivo
- Quando a internet volta, os pontos são enviados em lote automaticamente
- Isso garante rastreabilidade mesmo em áreas com sinal fraco

---

### 6. Módulo Financeiro

- Cada entregador possui uma **carteira digital** no sistema
- Ao completar uma entrega, o valor é creditado na carteira
- O entregador pode solicitar **saque via PIX** a qualquer momento, informando a chave PIX e o valor desejado
- O histórico de transações mostra entradas (bônus, créditos de entrega) e saídas (penalidades, saques)

**Categorias de transação:**
| Tipo | Direção |
|---|---|
| PAYOUT | Saída (saque) |
| PENALTY | Saída (penalidade) |
| BONUS | Entrada |
| Outros | Entrada |

---

### 7. Comunicação Operacional

- O app possui um sistema de **mensagens por threads** entre entregador e operação/lojas
- Threads podem ser vinculadas a um pedido específico, a uma loja ou ser gerais
- O entregador pode enviar e receber mensagens em tempo real
- **Limitação atual**: Não há atualização automática de mensagens — o entregador precisa atualizar manualmente

---

### 8. Relato de Incidentes

Entregadores podem reportar problemas durante a entrega, incluindo:
- Não encontrou o cliente
- Endereço incorreto ou estabelecimento fechado
- Problema com o veículo
- Outros

O sistema registra o incidente com localização, horário e descrição. O backend também aceita fotos como evidência.

---

## 📊 Capacidades e Limites Operacionais

| Parâmetro | Valor Atual |
|---|---|
| Frequência de rastreamento GPS | 10 segundos |
| Cache offline de GPS | Ilimitado (Room DB local) |
| Histórico de transações por página | 50 itens |
| Tempo do alerta de nova corrida | 10 segundos |
| Tentativas de reenvio de requisição | 3 (com backoff de 1s, 2s, 4s) |
| Cache HTTP offline | 7 dias |
| Turnos simultâneos por entregador | 1 (regra de negócio) |

---

## 🚨 Riscos Críticos para a Operação

| Risco | Impacto |
|---|---|
| Token de sessão não renova automaticamente | Entregador deslogado durante entrega ativa |
| Foto de comprovante não funcional | Apenas PIN disponível — sem evidência visual de entrega |
| Horário de conclusão de entrega hardcoded na UI | Dados históricos incorretos para o entregador |
| GPS falso detectado mas entregador não é bloqueado | Fraude operacional não é prevenida, apenas registrada |
| Sem notificação quando nova mensagem chega no chat | Comunicação operacional ineficiente |

---

## ✅ Pontos Fortes da Plataforma

- **Operação offline robusta**: O app funciona sem internet, sincronizando dados ao reconectar
- **Anti-fraude de GPS**: Detecção automática de localização falsa
- **Segurança de dados**: Tokens armazenados em área criptografada do dispositivo
- **Idempotência de operações**: Proteção contra dupla aceitação de pedidos
- **Arquitetura escalável**: Separação clara entre camadas de negócio, dados e interface

# Contratos de Comunicação e Arquitetura de Segurança
**Sistema Logístico de Alta Performance (Django DRF + FastAPI + Redis + Supabase)**

Este documento estabelece as diretrizes arquiteturais definitivas para o tráfego de rede, autenticação de dispositivos, ingestão em tempo real e proteção de operações financeiras. O foco desta arquitetura é **desacoplamento agressivo** para escalar a milhões de entregas sem degradação do banco relacional.

---

## 1. Topologia de Comunicação (The Two-Lane Architecture)

Para proteger a camada de regras de negócio (Django) contra exaustão por "barulho" contínuo (pings de GPS a cada 5 segundos), a comunicação entre o front-end (React Native) e o back-end é bifurcada em duas "pistas" de tráfego:

```mermaid
flowchart TD
    App[App React Native (Entregador)]
    
    subgraph Fast Lane (Alta Frequência / Baixo Custo)
        FastAPI[FastAPI Ingestion Gateway\nEasypanel]
        Redis[(Redis - Memory Store)]
        Realtime[Supabase Realtime\nWebSockets]
    end
    
    subgraph Slow Lane (Transacional / Regras de Negócio)
        Django[Django DRF API]
        Celery[Celery Workers]
        PG[(Supabase PostgreSQL)]
    end
    
    App -->|HTTP POST (GPS Pings)\nDevice Token| FastAPI
    FastAPI -->|O(1) Validação| Redis
    FastAPI -->|GEOADD & RPUSH| Redis
    Redis -->|Geofencing Trigger| Realtime
    
    App -->|HTTP POST/GET (Financeiro, Pod)\nSupabase JWT| Django
    Django -->|Leitura/Escrita Atômica| PG
    
    Redis -.->|Worker a cada 2 min (Batch)| PG
    Django -.->|Valida Deny-list| Redis
    Celery -.->|Valida Deny-list (Pre-run)| Redis
```

---

## 2. Camada de Telemetria (FastAPI Ingestion)

A ingestão de telemetria é o tendão de Aquiles de sistemas logísticos. O **FastAPI** rodará de forma isolada (ex: container no Easypanel) e será um serviço *stateless* voltado puramente para I/O e Cache.

### 2.1. Regra de Isolamento Físico
> [!IMPORTANT]
> **Proibição de Acesso Direto:** O serviço FastAPI **NÃO** possui a string de conexão do PostgreSQL e não acessa o ORM. Sua única dependência de estado é o **Redis**.

### 2.2. Fluxo de Ingestão de GPS
1. O App envia um `POST /api/v1/telemetry` contendo o payload de coordenadas, velocidade, direção (heading) e o *Device Token*.
2. O FastAPI valida o token contra o Redis.
3. Se válido, o FastAPI executa duas operações atômicas no Redis:
   - **Live Tracking:** `GEOADD driver_positions <lon> <lat> <driver_id>` (Atualiza o mapa da Torre de Controle instantaneamente via Pub/Sub).
   - **Histórico (Slow Path):** `RPUSH telemetry_buffer '{"driver_id": "...", "lat": ..., "lon": ..., "ts_device": ..., "ts_server": ...}'` (Adiciona na fila para o Celery fazer o *bulk insert* na tabela particionada do PostgreSQL a cada 2 minutos).

> [!WARNING]
> **Mitigação de Deriva de Relógio (Clock Skew):** O FastAPI **não pode confiar** no timestamp enviado pelo celular (`ts_device`) para ordenação e particionamento do banco de dados, devido ao risco de relógios desconfigurados ou spoofing intencional. O relógio do servidor `NOW()` no milissegundo do recebimento (`ts_server`) é a única fonte da verdade que o *worker* utilizará para persistir na tabela `Position`. O `ts_device` servirá apenas para métricas de latência.

### 2.3. Política de Fail-Closed (Falha Segura)
> [!CAUTION]
> Se o FastAPI perder a conectividade com o Redis, ele **DEVE** retornar imediatamente `503 Service Unavailable` e descartar o *payload*. É expressamente proibido o comportamento "fail-open" (aceitar pings às cegas). É matematicamente preferível perder 2 minutos de trilha geográfica do que permitir que um dispositivo bloqueado pela *Deny-list* contamine a base de dados em um momento de queda do cache.

---

## 3. Estratégia de Segurança "Device-Level" (Performance Extrema)

A verificação de assinaturas criptográficas de JWT (RSA/HMAC) a cada ping de GPS causa alto consumo de CPU (CPU-bound) na camada de Ingress.

### 3.1. Device Tokens
A rotação de telemetria utilizará **Device Tokens**, que são strings baseadas em *hashes* (ex: SHA-256 de um segredo longo gerado na hora do login) ou chaves opacas simples, geradas pelo Django durante a autenticação inicial.

### 3.2. Validação O(1) no Redis
*   Ao realizar o login pelo Django, o sistema emite o JWT principal para o App e gera um `Device Token`.
*   O Django salva o mapeamento no Redis: `SET device_token:<hash> <driver_id> EX 86400` (Validade máxima de 24h).
*   Quando o ping de GPS bate no FastAPI, em vez de decodificar um JWT, o FastAPI faz um simples `GET device_token:<hash>`. 
*   **Tempo de Execução:** Menos de 0.5ms. Baixíssimo uso de CPU, permitindo que uma única instância FastAPI aguente +10.000 requests por segundo.

### 3.3. Janela de Ataque e Token Rotation
Tokens de longa duração criam uma janela para *GPS Spoofing* se o dispositivo for fisicamente comprometido.
> [!TIP]
> **Obrigatoriedade de Rotação:** O Front-End e o Django implementarão um mecanismo de *Token Rotation* leve. O `Device Token` deve ser obrigatoriamente invalidado e renovado toda vez que o motoboy iniciar um novo Turno (`ScheduleEntry`) ou no máximo a cada 12 horas. Isso esmaga a janela de utilidade de um token roubado para poucas horas.

---

## 4. Protocolo de Segurança Unificada (A "Deny-list" Global)

A segurança deve ser fluida e fechar vetores de fraude assíncrona ("Fissura do Celery"). O coração do sistema de bloqueio reside em uma **Deny-list Centralizada no Redis**.

### 4.1. Arquitetura da Deny-list
Sempre que um usuário é demitido, deslogado ou flagrado em fraude no sistema, o Django faz um `SET deny_list:driver:<driver_id> 1 EX <ttl_do_jwt_restante>`.

### 4.2. Barreira 1: Telemetria (FastAPI)
Antes de processar o GPS, o FastAPI executa um `MGET device_token:<hash> deny_list:driver:<driver_id>`. Se a Deny-list retornar `1`, o FastAPI:
1. Deleta o *Device Token* do Redis preventivamente.
2. Retorna `401 Unauthorized` obrigando o aplicativo do motorista a deslogar o GPS e destruir a sessão local.

### 4.3. Barreira 2: Operações Financeiras Assíncronas (Celery)
O Django DRF já protege as requisições web lendo a Deny-list. Para as tarefas de *background* já enfileiradas (ex: Pagamento Pix via Asaas, Despacho para iFood), a regra de contrato é clara:
> [!WARNING]  
> **Trava de Execução (Pre-run):** Nenhuma transação no Celery deve tocar APIs externas de terceiros sem executar uma checagem em O(1) na Deny-list. Se `deny_list:driver:<driver_id>` for verdadeiro no instante em que a task acordar, a transação aborta como `FAILED (Blocked Mid-Flight)`. O banco PostgreSQL corrobora isso bloqueando qualquer *UPDATE* na `WithdrawalRequest` via *Trigger*.

---

## 5. Contratos de Comunicação Front-End/Back-End

### 5.1. Segregação de Responsabilidades (REST vs Realtime)
*   **Ações Transacionais (Síncronas):** Aceitar pedido, cancelar corrida, solicitar saque, atualizar dados bancários. **Via Django DRF (HTTP POST/PUT com JWT)**. O Front-end aguarda o `HTTP 200/201`.
*   **Geofencing & Dashboard (Assíncronas):** O Dashboard do operador e as notificações automáticas de "Entregador Chegou" não rodam *polling* contra o Django. Elas escutam o **Supabase Realtime** (WebSockets) que reage aos eventos injetados no PostgreSQL pelas filas de *Geofence* processadas em background.

### 5.2. Chaves de Idempotência (Mitigação de Double-booking)
Para proteger o sistema financeiro contra problemas de conectividade (onde o App do motorista trava em túneis ou elevadores e re-envia a mesma requisição HTTP):
> [!CAUTION]  
> **Obrigatoriedade de Contrato Front-end:** Toda requisição `POST` ou `PUT` que altere estado (Ex: `/api/v1/orders/{id}/accept` ou `/api/v1/wallet/withdraw`) **DEVE** conter o header `Idempotency-Key` (um UUID v4 gerado no dispositivo).
> **Ação do Django:** O Django verificará no Redis `SETNX idempotency:<key> 1 EX 86400`. Se retornar `0`, significa requisição duplicada e o Django retorna `409 Conflict` ou apenas repete o response da primeira execução guardado em cache, protegendo as carteiras contra múltiplos débitos.

---

## 6. Obrigatoriedade do PIN (Proof of Delivery Criptográfico)

A conclusão de uma entrega (`COMPLETED`) finaliza o compromisso financeiro, tornando a fatura B2B exigível contra a Loja. Falhas ou fraude neste ponto quebram o faturamento do lojista.

### 6.1. O Contrato de Finalização
*   Quando a Ordem requer PIN (ex: Jóias, Eletrônicos de alto valor, Farmácia), a API do Django gera o código (ex: numérico de 4 a 6 dígitos) na criação do manifesto. O lojista transmite este código apenas para o recebedor legítimo.
*   **A Regra da API:** O *payload* `POST /api/v1/stops/{id}/complete` **TEM** que trazer o campo `"deliveryPin"`.

### 6.2. Rejeição no Nível do ORM
> [!IMPORTANT]
> O Django comparará estritamente o PIN submetido contra o armazenado no banco, preferencialmente utilizando `check_password` (se o PIN estiver hasheado no banco por motivos de segurança). 
> Se o PIN estiver vazio ou divergir, a API deve estourar um `HTTP 400 Bad Request` com o código interno `INVALID_POD_PIN`, inviabilizando que a transição lógica para `COMPLETED` ocorra. O pagamento logístico ao motoboy permanecerá travado até a submissão correta.

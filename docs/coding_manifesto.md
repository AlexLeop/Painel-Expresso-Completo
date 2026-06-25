# Manifesto de Engenharia: LogiPay Core

**A Constituição Arquitetural de Alta Disponibilidade e Segurança Física**

Este manifesto estabelece os princípios inegociáveis de engenharia de software para o desenvolvimento do ecossistema logístico. Ele não é um guia de sugestões; é um contrato estrito de execução. Qualquer *Pull Request* ou *Commit* que viole os preceitos abaixo introduzirá vazamentos de caixa e degradação de performance e deve ser sumariamente rejeitado.

---

## I. A Doutrina do Banco de Dados (Supabase PostgreSQL)

A base de dados é a última linha de defesa. A aplicação é passageira, os dados são eternos.

1. **A Lei das Partidas Dobradas (Imutabilidade Absoluta):** O dinheiro não surge nem desaparece. Toda movimentação na tabela `WalletTransaction` exigirá *sempre* a definição de uma Origem e um Destino (XOR estrito em SQL). É **terminantemente proibido** o uso de `FLOAT` ou `DECIMAL`. Todo e qualquer valor financeiro será representado em `BIGINT` (centavos/Cents).
2. **Multi-Tenancy por Isolamento Criptográfico (RLS):** Nenhuma query na aplicação confiará cega e exclusivamente na cláusula `WHERE operator_id = X` do ORM. O isolamento de clientes (Tenants) será reforçado pela trava física de *Row Level Security* (RLS) baseada no JWT injetado na sessão do PostgreSQL. O vazamento de dados *Cross-Tenant* é a falha máxima.
3. **A Geografia é Projetada e Indexada:** Todo dado de coordenadas utilizará a extensão PostGIS com o tipo `Geography` (em Metros), garantindo precisão curva-terrestre. Todo filtro espacial possuirá obrigatoriamente um índice espacial `GiST`.
4. **As Regras de Contorno de Performance:** Tabelas de hiper-crescimento (como `Position`) não existirão como entidades monolíticas. Elas **sempre** utilizarão Particionamento Declarativo por Tempo (`PARTITION BY RANGE`). Consultar o histórico bruto exigirá passagem obrigatória pela chave de particionamento.

---

## II. A Doutrina do Back-End Distribuído (Django & FastAPI)

O motor do sistema deve tratar cada transação com ceticismo absoluto e segregar gargalos de IO da lógica de negócios pesada.

1. **Desacoplamento de Pistas (Fast Lane vs Slow Lane):**
   * A ingestão de telemetria de alta frequência (GPS) **nunca** baterá no banco relacional ou no ORM do Django. Ela deve bater em um serviço de borda puramente focado em IO (FastAPI) e ser absorvida por um cache em memória (Redis).
   * O Django processará exclusivamente a *Slow Lane*: regras contratuais, roteirização assíncrona, e mutações de estado transacional sob bloqueios rígidos.
2. **Pessimismo Concorrente (The Anti-Thundering Herd):** Toda operação de captura de recursos limitados (aceite de pedido) passará por controle atômico. Operadores que demandam transações complexas usarão bloqueios nativos do banco (`SELECT FOR UPDATE` do Django ORM) envoltos em transações de escopo estrito (`transaction.atomic`).
3. **Obrigatoriedade da Idempotência:** Nenhuma operação mutável (POST/PUT) que altere finanças ou alocação logística será aceita sem uma `Idempotency-Key` atrelada à camada do Redis. Repetições de tráfego resultantes de falhas de 3G/4G não podem, sob hipótese alguma, duplicar débitos em carteiras.
4. **Resiliência Assíncrona Celery (O Fim do Fogo Amigo):** Operações que tocam a rede externa (Asaas, iFood, Webhooks) **nunca** bloquearão a *Thread* principal do servidor HTTP. Elas existirão puramente no modelo *Outbox Pattern* e no enfileiramento do Celery com *Exponential Backoff*.

---

## III. A Doutrina da Borda Móvel (React Native & Next.js)

O Front-End deve ser hostil à conectividade perfeita e complacente com os gargalos humanos nas ruas.

1. **O Voto de Silêncio do Polling:** Aplicações Web (Next.js Torre de Controle) estão proibidas de executar ciclos infinitos de requisições de API (`setInterval` polling) para monitorar posição de frota ou status de pedido. Toda a visibilidade instantânea será acoplada diretamente em memórias de *Broadcast* (Supabase Realtime WebSockets).
2. **A Autonomia das Zonas Sombrias (Offline-First):** O App do Entregador confiará na memória local (SQLite/WatermelonDB) para armazenar Provas de Entrega (POD/PIN/Assinatura). A UI nunca bloqueará a coleta de dados devido a uma queda de sinal. O *Background Sync* garantirá a entrega eventual (`Eventual Consistency`) quando houver retorno à cobertura.
3. **Pessimismo de UI na Competição:** Requisições competitivas (disputa de ordens no auto-dispatch) terão feedback visual instantâneo. Falhas de concorrência (`HTTP 409 Conflict`) devem resultar em deleção graciosa na UI e transparência imediata ao motorista, extirpando a síndrome de telas estáticas de "Carregando".

---

## IV. A Doutrina de Segurança Contínua (Zero-Trust & Deny-list)

Um sistema onde o JWT validado basta, é um sistema onde um motorista banido continua operando.

1. **A Fissura Assíncrona:** A autorização baseada em tokens expiráveis é lenta para desarmar ameaças ativas. A segurança dependerá de uma *Deny-list* de persistência central (Redis).
2. **Trava Interceptadora Geral:** Antes de gravar uma posição de rastreio (FastAPI), antes de rotear um pedido (Django Web) ou antes de liquidar um Pix no background (Celery), a verificação constante contra a *Deny-list* O(1) do cache e a validação lógica contra o estado nativo do banco (`active = True`) são compulsórias e inescapáveis.
3. **Falha Segura (Fail-Closed):** Em caso de perda de comunicação com o servidor de cache (Redis) ou com a base de segurança, os serviços de borda e filas devem **colapsar suas operações com recusa (`HTTP 503 / REJECTED`)**. A indisponibilidade de sistema temporária é infinitamente superior ao risco contábil cego.
4. **Criptografia Fática:** Todo e qualquer dado que configure Segredo de Cliente (ex: credenciais do lojista no iFood/Saipos) existirá na base criptografado de ponta a ponta na camada de aplicação, nunca trafegando em texto puro no log do provedor de infraestrutura.

---

> *"Engenharia excelente não é a arte de construir sistemas que nunca falham. É a arquitetura que garante que, quando os componentes colapsarem, a consistência contábil e a verdade sistêmica estarão rigorosamente intactas."*
> **— Manifested for LogiPay Core, 2026**

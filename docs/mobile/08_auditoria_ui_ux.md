# NevesGo — Auditoria de UX/UI: App vs. Google Stitch
## Relatório de Visão Computacional e Comparativo de Código

> [!NOTE]
> Este documento apresenta o resultado da análise de visão computacional das interfaces desenhadas no Google Stitch (pasta `stitch_nevesgo`) comparadas com a implementação real em Kotlin/Jetpack Compose. O documento `DESIGN.md` foi a base referencial para a identidade visual (Corporate Modern with a Functional Edge).

---

## 1. Identidade Visual e Estilo Base

### Análise do `DESIGN.md` (Referência)
- **Cores Primárias**: Fundo Cinza Frio (`#F8FAFC` a `#94A3B8`), Preto Puro (`#000000`) para estrutura/títulos e ações secundárias. Vermelho (`#b71519`) **apenas** para alertas de alta prioridade, ações ativas, e o botão "Aceitar" primário. Âmbar para alertas secundários.
- **Formas**: Bordas arredondadas (0.5rem / 8px) para botões e inputs; (1rem / 16px) para containers e cartões.
- **Tipografia**: Inter, oversized para legibilidade em movimento. Geist para dados monospaced.
- **Hierarquia Visual**: Sombras difusas sutis para elevar cartões, "Level 2" com borders pretas de 1px em tarefas ativas.

### 🔴 O que está no App (Código Kotlin)
- A cor primária padrão (`primary` theme) no app é o Vermelho (`ExpressoRed`), o que significa que o App espalha botões e highlights em vermelho em excesso, diminuindo o impacto da cor de alerta.
- O App implementa o `LightColorScheme` forçado (fundo branco), não há o cinza frio (#f7f9fb) preenchido em todos os fundos principais. O app tem fundos brancos puros (Surface).
- A tipografia "Inter" foi implementada com sucesso no código usando GoogleFonts.

**Veredito de Branding**: ❌ Inconsistente. O app atual sobrecarrega a tela com elementos vermelhos de alta energia, perdendo o princípio "Corporate Modern with a Functional Edge" de usar o vermelho como sinal de gatilho/emergência e usar o preto como base utilitária.

---

## 2. Análise por Telas (Módulo a Módulo)

### 🗺️ Módulo 1.0 — Dashboard e Alerta de Nova Corrida
**Visão Computacional do Stitch:**
- Header pill superior compacto com a foto e status ("ONLINE E DISPONÍVEL") com toggle switch.
- Alerta modal exibe agrupamento claro para corridas multi-paradas (Múltiplas bolinhas verdes de "RETIRADA" e marcadores de "ENTREGA" detalhando cada waypoint da rota).
- O timer da nova corrida (24s) usa barra vermelha, e o botão de aceitar é Preto (`Aceitar Pedidos`).

**Realidade no App Kotlin:**
- A barra de progresso / bottom sheet da `HomeScreen` tem apenas suporte visual textual simplificado para "1 parada" fixo (Bug #004). O app não desenrola os waypoints dinamicamente como no protótipo.
- O botão de aceitar no app usa a técnica de Swipe (`SwipeButton`) para prevenir miss-clicks, enquanto o Stitch indica um botão de toque simples, largo em preto.

**Conclusão de UX**: O App tem uma mecânica de segurança anti-erro melhor (Swipe to accept), mas falha drasticamente na exibição dos waypoints.

---

### 📦 Módulo 2.0 — Minhas Entregas
**Visão Computacional do Stitch:**
- Organização por abas: `Em curso` | `Em espera` | `Agendadas`.
- Categorização clara na tela: "ENTREGA ATUAL" (Cards maiores, pílula vermelha "Entregando", botão "Ver Rota" em preto sólido) e "HISTÓRICO RECENTE" compactado.

**Realidade no App Kotlin:**
- Abas implementadas diferem do Stitch: o código usa "Pendentes", "Em Andamento", "Todas". 
- Não existe divisão horizontal de "Entrega Atual" e "Histórico Recente" na mesma aba, obrigando o entregador a trocar de abas constantemente.
- Valores e botões no App estão coloridos de vermelho (`primary`); o design pede pretos.

---

### 💰 Módulo 3.0 — Carteira e Saque
**Visão Computacional do Stitch:**
- Título da barra "Carteira".
- Card de saldo muito proeminente (fundo preto com degradê sutil ou vermelho), com destaque grande em branco para o valor da conta e um botão largo "Solicitar Saque".
- Componente de Filtro Temporal por Pill Tabs: `Dia | Semana (ativo, vermelho) | Mês`.
- Gráfico de barras verticais vermelho de "Entradas Recentes (Últimos 7 dias)"
- Lista de Transações com ícone redondo rosa, valor positivo vermelho com sinal `+`.

**Realidade no App Kotlin:**
- A tela no app tem o título "Ganhos". (Outra rota idêntica chama-se "Pagamentos" que duplica o UI, BUG-009).
- Não há Filtro de período (Tabs Dia/Semana/Mês) implementado. A listagem é feita por paginação simples, exibindo sempre o total de ganhos não filtrado por esses ranges.
- Gráfico de barras de 7 dias é inexistente no app. O app usa breakdown de `totalIn` e `totalOut` em linhas de texto.

---

### 📅 Módulo 4.0 — Escalas e Agendamento
**Visão Computacional do Stitch:**
- Abas: `Disponíveis | Minhas Escalas`.
- Navegação horizontal por data através de Chips ("Hoje, 24 Mai", "Amanhã, 25 Mai"). 
- Banner informacional sutil rosa no topo ("12 novas vagas disponíveis para hoje").
- Cards de vaga muito detalhados: Título forte, endereço, Turno ("Manhã 08h-14h"), e em negrito vermelho o valor ("GARANTIDO MÍNIMO R$ 180,00"). Botão outline "Ver Detalhes".

**Realidade no App Kotlin:**
- O app tem 3 abas: "Disponíveis", "Reservas", "Canceladas". (Foge do modelo Stitch de 2 abas).
- O carrossel de Chips de datas NÃO está implementado na interface. O endpoint da API aceita o parâmetro de data, mas o app não expõe os chips dinâmicos horizontalmente.
- O App omite a copy comercial motivacional (ex: "GARANTIDO MÍNIMO").

---

### 👤 Módulo 5.0 — Perfil 
**Visão Computacional do Stitch:**
- Card header impressionante (nível, pontuação e fidelidade): Traz a foto circular, "Nível Diamante" com rating de estrela "4.95". Subcards textuais: "2.481 ENTREGAS" e "3 ANOS NA FLASH" (texto em vermelho).
- Dupla de Cards Quadrados lado a lado: "Veículo Atual" (Dark Theme) e "Ganhos Mês" (Light Theme) para métricas rápidas.
- Listagem agrupada (`rounded-lg`) de menu de configuração.

**Realidade no App Kotlin:**
- Tela no App é muito crua. (Feature F1 e F6 faltantes catalogadas no relatório anterior). 
- O menu de opções tem coisas "mortas" que foram abandonadas ("Meus Dados", "Idioma").
- Rating ("Nível Diamante") e informações agregadas do entregador simplesmente não existem.
- O background do botão de "Perfil" da Bottom Nav tem um encapsulamento total vermelho no Stitch (completamente divergente dos outros ícones da navbar que são outline) e no App isso foi feito como ícone genérico outline.

---

## 3. Recomendações e Plano de Ação de UX/UI

> [!WARNING]
> O app Kotlin não reflete o `DESIGN.md`. A equipe de desenvolvimento optou por aplicar o Material3 com paleta customizada (usando vermelho em todo lugar como cor de destaque genérica), quebrando a utilidade emocional que o design sistemático prescrevia.

### Próximos Passos Imediatos para a Equipe de Front-end:
1. **Refatoração do Theme.kt e Color.kt**: Alterar o `Primary` para `ExpressoBlack`. Utilizar `Secondary` para `ExpressoRed` de maneira que botões normais se tornem pretos e apenas botões críticos de Aceitar Corridas / Notificações de Problemas permaneçam vermelhos brilhantes. Isso diminuirá a poluição cognitiva na estrada.
2. **Implementar Filtros e Gráficos da Carteira (Stitch 3.0)**: O entregador confia no app quando enxerga seus ganhos com precisão (gráfico semanal). É a feature motivacional número 1.
3. **Refatorar Alerta de Nova Corrida (Stitch 1.0)**: Construir o pipeline dinâmico de `stops` na interface (Waypoints da Rota) usando uma `LazyColumn` rápida para não forçar "1 parada" hardcoded.
4. **Implementação do Gamification (Stitch 5.0)**: Adicionar ao Perfil a exibição da Avaliação do entregador (estrelas e número de entregas). Essa métrica aumenta a retenção e sensação de pertencimento do parceiro logístico.

---
**Status da Auditoria de UI**: Concluída.

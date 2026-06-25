# Matriz de Homologação: NevesGo (App do Entregador)

Com base na auditoria técnica e operacional do aplicativo, esta é a Matriz Objetiva de Homologação detalhando o estado de cada tela e fluxo, com foco na prontidão para uso em produção.

| Módulo / Fluxo | Funcionalidade | Status | Observações / Bloqueios Críticos |
| :--- | :--- | :--- | :--- |
| **Autenticação** | Login e Acesso | 🔴 Reprovado | Login final inexistente; bootstrap temporário por JWT manual em `AppNavigation.kt`. |
| **Autenticação** | Offline e Reconciliação | 🔴 Reprovado | Apenas demonstrativo (`OfflineSyncManager.kt` contém apenas placeholders). |
| **Ofertas e Captura** | Visualização de Corridas Pendentes | 🟡 Parcial | Lista disponível, mas falta atualização em tempo real (necessita polling/websocket/push). |
| **Ofertas e Captura** | Captura / Aceite de Corridas | 🟡 Parcial | App consegue aceitar a corrida, mas a interface não reflete o estado ativamente e dinamicamente. |
| **Ofertas e Captura** | Recusa de Oferta Atribuída | 🔴 Reprovado | Backend suporta a ação, mas a UI de oferta não executa a recusa real (botão na tela apenas fecha o modal). |
| **Ofertas e Captura** | Cancelamento de Corrida Aceita | 🟡 Parcial | UX frágil: navega imediatamente sem esperar confirmação visual de sucesso do backend. |
| **Execução da Rota** | Agrupamento de Múltiplos Pedidos | 🔴 Reprovado | App opera por `orderId` individual; sem roteiro único ou visão consolidada de múltiplas paradas. |
| **Execução da Rota** | Rastreamento em Tempo Real (Tracking) | 🔴 Reprovado | Tracking acoplado à abertura da tela de rota. Não rastreia motoboys ociosos ou fora do aplicativo. |
| **Execução da Rota** | Opções de Navegação (Mapas) | 🔴 Reprovado | Apenas navegação interna (osmdroid). Faltam opções (intents) para Google Maps e Waze. |
| **Execução da Rota** | Início da Corrida | 🔴 Reprovado | Abrir a tela de navegação altera o status para `STARTED` automaticamente, o que é um erro operacional. |
| **Comunicação** | Canais de Contato | 🟡 Parcial | Chat funcional, mas faltam chamadas de voz e atalhos diretos claros diferenciando loja e operador. |
| **Finalização** | Prova de Entrega (Delivery Proof) | 🔴 Reprovado | Risco crítico de crash/quebra: app envia `file = null`, mas o backend exige um arquivo obrigatório. |
| **Finalização** | Código de Confirmação (PIN) | 🟡 Parcial | Validação do PIN correta no backend, mas o fluxo não pode ser atestado como seguro devido à prova de entrega quebrada. |
| **UX Operacional** | UI/UX de Mercado | 🟡 Parcial | Base visual consistente, mas com lacunas operacionais severas (ex: endereços mostrados como Lat/Lng, dados falsos em algumas telas). |

## Resumo Executivo
- **Aprovado (🟢)**: 0 funcionalidades
- **Parcial (🟡)**: 6 funcionalidades
- **Reprovado (🔴)**: 8 funcionalidades

O aplicativo **não está apto para operação comercial em tempo real**. A prioridade imediata deve ser a correção dos bloqueios na **Prova de Entrega**, desacoplamento do **Tracking** e implementação de navegação externa.

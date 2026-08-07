# NevesGo — Resumo Executivo da Auditoria Técnica
## Versão: 1.0 | Data da Auditoria: Julho 2025

---

## O que é o NevesGo?

O **NevesGo** é o aplicativo Android da **Expresso Neves** para entregadores. Desenvolvido em Kotlin com Jetpack Compose, ele permite que motoristas recebam corridas, naveguem até os destinos, confirmem entregas, gerenciem turnos de trabalho e acompanhem ganhos — tudo em um único app. A comunicação com o backend Django DRF ocorre via API REST, com suporte a push notifications (Firebase) e rastreamento GPS em tempo real.

---

## 🏗️ Estado Atual do Produto

O aplicativo está **estruturalmente bem construído** para uma versão 1.0. A arquitetura MVVM é sólida, há suporte offline, criptografia de dados e mecanismos de proteção contra fraude. No entanto, **existem 2 bugs críticos que impedem a operação segura em produção**, além de 13+ funcionalidades incompletas ou ausentes que limitam a experiência do entregador.

---

## 🟢 Pontos Fortes

| Área | O que foi bem feito |
|---|---|
| **Arquitetura** | MVVM limpo com separação clara de camadas (UI, Domain, Data) |
| **Offline First** | Room DB armazena pedidos e telemetria offline; sincronização automática ao reconectar |
| **Segurança de Dados** | Tokens JWT armazenados em área criptografada do dispositivo |
| **Anti-Fraude** | Detecção automática de GPS falso com reporte ao backend |
| **Idempotência** | UUID por requisição evita duplicidade de operações críticas |
| **Resiliência de Rede** | Retry automático com backoff exponencial (3 tentativas) |
| **Push + Sync** | Firebase Cloud Messaging aciona sincronização de pedidos em tempo real |
| **Navegação** | Rota calculada via OSRM com fallback para linha direta |

---

## 🔴 Problemas Críticos (Bloqueia Lançamento)

### 1. Entregadores Perdem Sessão Durante Entregas
O mecanismo de renovação de token JWT está implementado mas **configurado com credenciais em branco**. Quando o token expira (típico: a cada 1 hora), o entregador é deslogado automaticamente — mesmo durante uma entrega ativa. Isso cria:
- Corridas travadas em estado inconsistente
- Dados de entrega perdidos
- Frustração do entregador

**→ Correção**: Preencher credenciais Supabase no `TokenAuthenticator`. Estimativa: **2-4 horas de trabalho**.

### 2. Comprovante Fotográfico Bloqueado
O app suporta dois tipos de prova de entrega: PIN (funciona) e Foto (bloqueada em código). A câmera está completamente desativada.

**Risco**: Sem foto, disputas de "não recebi" ficam sem evidência para a empresa. A API backend já aceita o upload — falta apenas a integração da câmera na UI.

**→ Correção**: Integrar `CameraX` (já nas dependências) com o fluxo de confirmação. Estimativa: **1-2 dias de trabalho**.

---

## 🟠 Riscos Operacionais (Resolver em até 30 dias)

| Risco | Impacto | Esforço |
|---|---|---|
| GPS falso detectado mas entregador não bloqueado | Fraude operacional possível | Médio |
| Chat sem atualização automática | Comunicação com operação ineficiente | Médio |
| Dados históricos com timestamps falsos | Desconfiança do entregador | Baixo |
| Servidor de mapas externo sem SLA | Roteirização pode falhar em produção | Alto (infraestrutura) |

---

## 🟡 Funcionalidades Incompletas (Roadmap)

### Prioridade Alta (30-60 dias)
- **Perfil do Entregador**: Tela existe no menu mas sem funcionalidade — dados pessoais, foto, documentos
- **Notificações Push Contextuais**: Todas as mensagens fazem a mesma ação; falta diferenciação para chat, pagamentos, avisos
- **Histórico de Jornadas Real**: Tela exibe dados de exemplo hardcoded
- **SLA/Countdown de Entrega**: Campo existe na base de dados mas sempre zerado

### Prioridade Média (60-90 dias)
- **Multi-Paradas**: O backend suporta rotas complexas, mas o app exibe "1 parada" sempre
- **Rating Pós-Entrega**: Sem sistema de avaliação do entregador
- **Paginação de Transações**: Histórico financeiro limitado a 50 itens sem scroll infinito

---

## 📐 Débito Técnico Relevante

| Item | Risco |
|---|---|
| `namespace = "com.example"` (genérico) | Conflito em produção na Play Store |
| Sem flavors de build (dev/staging/prod) | APK de desenvolvimento igual à de produção |
| Dependência Security Crypto em versão alpha | Instabilidade em produção |
| N+1 chamadas de API na sincronização de pedidos | Performance degradada com muitos pedidos |
| Sem testes automatizados implementados | Risco de regressão a cada entrega |

---

## 📋 Plano de Ação Recomendado

### Sprint 0 — Pré-Lançamento (Esta Semana)
- [ ] Corrigir BUG-001: Preencher credenciais de refresh de token
- [ ] Corrigir BUG-002: Integrar câmera no fluxo de prova de entrega
- [ ] Corrigir BUG-003: Timestamp real na lista de entregas concluídas
- [ ] Definir namespace correto `br.com.expressoneves.entregador`

### Sprint 1 — Semanas 1-2 (Estabilização)
- [ ] Bloquear entregador ao detectar GPS falso
- [ ] Corrigir inconsistência DataStore vs SecureStorage
- [ ] Adicionar flavors de build (debug/staging/release)
- [ ] Implementar polling ou WebSocket no chat

### Sprint 2 — Meses 1-2 (Completude)
- [ ] Implementar tela de Perfil do Entregador com API
- [ ] Notificações push diferenciadas por tipo
- [ ] Histórico de jornadas com dados reais
- [ ] Substituir OSRM público por solução com SLA
- [ ] Adicionar testes unitários para fluxo de pedidos

### Trimestre 2 — Funcionalidades de Crescimento
- [ ] Sistema de rating pós-entrega
- [ ] Suporte a multi-paradas
- [ ] Tema escuro funcional
- [ ] Onboarding para novos entregadores

---

## 📊 Scoreboard da Auditoria

| Dimensão | Nota | Justificativa |
|---|---|---|
| Arquitetura | 8/10 | MVVM sólido, sem DI formal |
| Funcionalidades | 5/10 | 2 críticas bloqueadas, muitas incompletas |
| Segurança | 6/10 | Boa base, mas refresh de token quebrado |
| Performance | 6/10 | N+1 queries, geocoding síncrono |
| Experiência do Entregador (UX) | 6/10 | Fluxo core funciona, mas muitos placeholders |
| Confiabilidade Offline | 8/10 | Robusto com Room DB e retry automático |
| Qualidade de Código | 7/10 | Limpo, mas sem testes e com dead code |
| **MÉDIA GERAL** | **6.6/10** | **Pronto para Beta, não para Produção** |

---

## ✅ Conclusão

O NevesGo tem uma **base técnica sólida e escalável**. Com correção dos 2 bugs críticos identificados (estimativa de 2-3 dias de trabalho de um desenvolvedor), o app pode ser lançado para testes com entregadores reais (beta fechado). Para um lançamento em produção completo, recomenda-se o roadmap de 90 dias com as funcionalidades de completude.

> **Recomendação**: Não lançar para produção sem corrigir BUG-001 (token refresh) e BUG-002 (câmera). Os demais itens podem ser tratados em sprints pós-lançamento.

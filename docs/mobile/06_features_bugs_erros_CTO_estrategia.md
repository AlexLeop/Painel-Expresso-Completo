# NevesGo — Features Faltantes, Bugs e Erros (CTO e Equipes de Estratégia)

---

## 🚨 Problemas Críticos para o Negócio

### 1. Entregadores São Deslogados Durante Entregas Ativas
**Impacto operacional**: Quando o token JWT expira (duração típica: 1 hora), o entregador perde a sessão sem aviso. Se estiver com uma entrega em andamento, a tela trava com erro e a corrida fica em estado inconsistente no sistema.

**Por que acontece**: O mecanismo de renovação automática de token está implementado no código mas as credenciais de conexão com o Supabase estão em branco.

**Risco**: Perda de corridas em andamento, frustração do entregador, dados inconsistentes no backend.

**Prioridade**: 🔴 **URGENTE — Corrigir antes do lançamento**

---

### 2. Confirmação de Entrega por Foto Não Funciona
**Impacto**: O sistema foi projetado para aceitar dois tipos de comprovante — PIN do cliente ou foto. A funcionalidade de foto está completamente bloqueada no app (botão desabilitado em código).

**Consequência de negócio**:
- Sem comprovante fotográfico, disputas de entrega ficam sem evidência
- O modelo de negócio baseado em foto como prova legal não está funcionando
- Se o cliente negar que recebeu, a empresa não tem como provar

**Prioridade**: 🔴 **URGENTE**

---

### 3. Dados Históricos de Entregas Exibem Informações Falsas
**Impacto**: A tela de histórico de entregas sempre mostra o horário "14:32" para todas as entregas concluídas. Isso afeta:
- A confiança do entregador nos dados do app
- Qualquer relatório ou auditoria que use dados exibidos na UI

---

## 🟠 Riscos Operacionais Significativos

### 4. GPS Falso Registrado mas Entregador Não é Bloqueado
**Situação atual**: O app detecta quando o entregador usa localização falsa (GPS spoofing) e envia um alerta ao backend. Porém, o entregador **não recebe nenhuma notificação e não é bloqueado**.

**Risco de fraude**: Entregadores mal-intencionados podem usar apps de GPS fake para simular que fizeram uma entrega sem sair do lugar, recebendo pagamento indevidamente.

**Recomendação**: Ao detectar GPS falso, bloquear a entrega e exibir mensagem ao entregador. O desbloqueio deve ser manual pela operação.

---

### 5. Sem Comunicação em Tempo Real no Chat
**Situação atual**: O sistema de mensagens entre entregador e operação existe, mas as mensagens só aparecem quando o entregador pressiona um botão de "Atualizar" manualmente.

**Impacto operacional**: Se a operação enviar uma mensagem urgente (exemplo: "Não entregue! Pedido cancelado!"), o entregador não vê a tempo e pode continuar a entrega.

---

### 6. Servidor de Mapas Externo sem Acordo de Nível de Serviço
**Situação atual**: O app usa um servidor público gratuito (OSRM project-osrm.org) para calcular rotas. Esse servidor não tem garantia de disponibilidade.

**Risco**: Se o servidor estiver fora do ar (manutenção, sobrecarga), os entregadores não conseguem calcular rotas e o app exibe uma linha reta entre origem e destino como fallback.

**Recomendação**: Contratar uma solução de roteamento com SLA (ex: Google Directions API, Mapbox, ou instância própria do OSRM).

---

## 🟡 Features Faltantes de Alto Valor

### F1 — Perfil Completo do Entregador
**Situação**: O menu de perfil existe mas a opção "Meus Dados" não tem funcionalidade. O entregador não consegue ver ou editar seus próprios dados (nome, foto, veículo, documentos, chave PIX padrão).

**Impacto**: Entregadores precisam contatar a operação por outros meios para atualizar seus dados.

---

### F2 — Notificações Push Contextuais
**Situação**: O app recebe notificações push do Firebase, mas todas elas fazem a mesma coisa (atualizar lista de pedidos). Não existem notificações distintas para:
- 💬 Nova mensagem de chat recebida
- 🚗 Nova corrida disponível na área
- 💰 Pagamento creditado na carteira
- ⚠️ Aviso da operação

---

### F3 — Histórico Real de Jornadas
**Situação**: A tela "Jornada Ativa" exibe apenas dados de exemplo (fictícios). Não há integração com um endpoint de histórico real de jornadas.

**Impacto**: Entregadores não conseguem acompanhar sua produtividade histórica. Equipe de estratégia não tem visão do desempenho individual via app.

---

### F4 — Contador de Prazo de Entrega (SLA)
**Situação**: O sistema guarda um campo de prazo (`slaSeconds`) mas sempre com valor zero. A UI não exibe nenhum countdown de tempo para o entregador.

**Impacto**: Entregadores não sabem se estão dentro do prazo de entrega. Sem pressão visual, atrasos podem aumentar.

---

### F5 — Suporte Real a Múltiplas Paradas
**Situação**: O backend suporta pedidos com múltiplas paradas (ex: uma coleta e 3 entregas), mas o app exibe "1 parada" fixo no alerta de nova corrida.

**Impacto**: Entregadores aceitam pedidos sem saber a real complexidade da rota, podendo recusar após aceitar (impacto na operação).

---

### F6 — Avaliação e Rating do Entregador
**Situação**: Não existe tela de avaliação pós-entrega. Sem sistema de rating, não é possível medir qualidade do serviço ao cliente.

---

### F7 — Saque PIX sem Validação de Limite
**Situação**: O formulário de saque permite qualquer valor, incluindo valores maiores que o saldo da carteira. A validação de saldo mínimo não está implementada no app (pode existir no backend).

---

### F8 — Indicador de Pedidos Pendentes de Sincronização
**Situação**: Quando o entregador confirma uma entrega sem internet, o pedido fica marcado localmente como concluído mas o backend não foi notificado. Não há nenhuma indicação visual disso.

**Risco**: O backend pode considerar o pedido ainda em andamento enquanto o entregador já o concluiu.

---

## 📱 Experiência do Entregador (UX)

| Item | Situação Atual | Impacto |
|---|---|---|
| Tema Escuro | Switch presente mas não funciona | Entregadores em campo à noite sem opção de modo escuro |
| Idioma | Opção presente mas sem funcionalidade | Sem suporte a idiomas diferentes (ex: entregadores imigrantes) |
| Onboarding | Sem tela de orientação para novos entregadores | Curva de aprendizado do app maior |
| Acessibilidade | Não avaliada nesta auditoria | Potencial risco de conformidade WCAG |

---

## 📊 Resumo de Prioridades

### Crítico (Lançamento Bloqueado)
1. **BUG-001**: Token refresh não funciona → Deslogins durante entregas
2. **BUG-002**: Foto de comprovante desabilitada → Sem evidência de entrega

### Alta Prioridade (Primeiros 30 dias pós-lançamento)
3. **F1**: Perfil do entregador
4. **F2**: Notificações contextuais
5. **F9 (Anti-fraude)**: Bloquear entregador com GPS falso
6. **BUG-003/010**: Dados históricos e status de sincronização

### Média Prioridade (60-90 dias)
7. **F4**: Contador de SLA
8. **F3**: Histórico de jornadas real
9. **F5**: Multi-stop real
10. **F7**: Chat em tempo real
11. **F6**: Rating pós-entrega

### Baixa Prioridade (Roadmap futuro)
12. Tema escuro funcional
13. Paginação do histórico financeiro
14. Tela de onboarding
15. Suporte a idiomas

import React, { useState, useEffect } from "react";
import {
  Plug,
  Layers,
  Activity,
  Plus,
  Copy,
  Check,
  ExternalLink,
  RefreshCw,
  Play,
  Pause,
  Trash2,
  Code,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Server,
  FileCode,
  HelpCircle,
} from "lucide-react";
import {
  Connector,
  StoreIntegration,
  WebhookLogItem,
  StoreOption,
  fetchConnectors,
  fetchStoreIntegrations,
  fetchOperatorStores,
  createStoreIntegration,
  updateStoreIntegration,
  deleteStoreIntegration,
  fetchIntegrationLogs,
} from "../services/integrations";

export function Integracoes() {
  const [activeTab, setActiveTab] = useState<"marketplace" | "integrations" | "logs" | "docs">("marketplace");
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [integrations, setIntegrations] = useState<StoreIntegration[]>([]);
  const [stores, setStores] = useState<StoreOption[]>([]);
  const [logs, setLogs] = useState<WebhookLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filtros
  const [connectorFilter, setConnectorFilter] = useState<string>("all");
  const [logStatusFilter, setLogStatusFilter] = useState<string>("all");

  // Modal de Criação / Wizard
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(null);
  const [selectedStoreId, setSelectedStoreId] = useState<string>("");
  const [autoCreateOrder, setAutoCreateOrder] = useState<boolean>(true);
  const [wizardSubmitting, setWizardSubmitting] = useState(false);
  const [wizardError, setWizardError] = useState<string | null>(null);
  const [createdIntegrationResult, setCreatedIntegrationResult] = useState<StoreIntegration | null>(null);

  // Modal de Credenciais / Detalhes
  const [credentialsModalItem, setCredentialsModalItem] = useState<StoreIntegration | null>(null);

  // Modal de Logs de uma integração específica
  const [viewingLogsIntegration, setViewingLogsIntegration] = useState<StoreIntegration | null>(null);
  const [selectedIntegrationLogs, setSelectedIntegrationLogs] = useState<WebhookLogItem[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // Feedback de cópia
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [connData, integData, storeData] = await Promise.all([
        fetchConnectors(),
        fetchStoreIntegrations(),
        fetchOperatorStores(),
      ]);
      setConnectors(connData);
      setIntegrations(integData);
      setStores(storeData);

      // Carregar logs da primeira integração se houver
      if (integData.length > 0) {
        const firstLogRes = await fetchIntegrationLogs(integData[0].id, { limit: 50 });
        setLogs(firstLogRes.logs);
      }
    } catch (err) {
      console.error("Erro ao carregar dados do Hub:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const [integData, connData] = await Promise.all([
        fetchStoreIntegrations(),
        fetchConnectors(),
      ]);
      setIntegrations(integData);
      setConnectors(connData);
    } finally {
      setRefreshing(false);
    }
  };

  // Abrir wizard para conector específico
  const handleOpenWizard = (connector?: Connector) => {
    setSelectedConnector(connector || connectors[0] || null);
    setSelectedStoreId(stores[0]?.id || "");
    setAutoCreateOrder(true);
    setWizardError(null);
    setCreatedIntegrationResult(null);
    setIsWizardOpen(true);
  };

  const handleCreateIntegration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStoreId) {
      setWizardError("Selecione uma loja para conectar.");
      return;
    }
    if (!selectedConnector) {
      setWizardError("Selecione um conector de integração.");
      return;
    }

    setWizardSubmitting(true);
    setWizardError(null);
    try {
      const result = await createStoreIntegration({
        store_id: selectedStoreId,
        connector_slug: selectedConnector.slug,
        auto_create_order: autoCreateOrder,
        config: {},
      });
      setCreatedIntegrationResult(result);
      await handleRefresh();
    } catch (err: any) {
      setWizardError(err.message || "Falha ao criar integração.");
    } finally {
      setWizardSubmitting(false);
    }
  };

  const handleToggleActive = async (integration: StoreIntegration) => {
    try {
      await updateStoreIntegration(integration.id, {
        active: !integration.active,
      });
      await handleRefresh();
    } catch (err) {
      console.error("Erro ao alternar status da integração:", err);
    }
  };

  const handleDeleteIntegration = async (id: string) => {
    if (!confirm("Tem certeza que deseja excluir esta integração? Os webhooks enviados deixarão de ser processados.")) {
      return;
    }
    try {
      await deleteStoreIntegration(id);
      await handleRefresh();
    } catch (err) {
      console.error("Erro ao excluir integração:", err);
    }
  };

  const handleViewLogs = async (integration: StoreIntegration) => {
    setViewingLogsIntegration(integration);
    setLogsLoading(true);
    try {
      const res = await fetchIntegrationLogs(integration.id, { limit: 50 });
      setSelectedIntegrationLogs(res.logs);
    } finally {
      setLogsLoading(false);
    }
  };

  const filteredConnectors = connectors.filter((c) => {
    if (connectorFilter === "all") return true;
    return c.status === connectorFilter;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/40 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand/10 text-brand flex items-center justify-center font-bold">
              <Plug className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                Hub de Integrações
              </h1>
              <p className="text-sm text-muted-foreground">
                Conecte PDVs, cardápios digitais e plataformas de delivery diretamente às lojas dos seus clientes.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-3 py-2 text-sm font-medium border border-border/60 rounded-lg hover:bg-muted/50 transition-colors flex items-center gap-1.5 text-muted-foreground"
            title="Atualizar dados"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            Atualizar
          </button>

          <button
            onClick={() => handleOpenWizard()}
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-brand text-brand-foreground hover:bg-brand/90 transition-all shadow-sm flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Nova Integração
          </button>
        </div>
      </div>

      {/* Tabs de Navegação */}
      <div className="flex items-center gap-2 border-b border-border/40">
        <button
          onClick={() => setActiveTab("marketplace")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "marketplace"
              ? "border-brand text-brand font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Layers className="w-4 h-4" />
          Marketplace de Conectores
          <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-muted font-normal">
            {connectors.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("integrations")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "integrations"
              ? "border-brand text-brand font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Plug className="w-4 h-4" />
          Minhas Integrações
          <span className="ml-1 px-2 py-0.5 text-xs rounded-full bg-brand/10 text-brand font-semibold">
            {integrations.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("logs")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "logs"
              ? "border-brand text-brand font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Activity className="w-4 h-4" />
          Auditoria de Webhooks
        </button>

        <button
          onClick={() => setActiveTab("docs")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "docs"
              ? "border-brand text-brand font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileCode className="w-4 h-4" />
          Documentação do Webhook
        </button>
      </div>

      {/* Conteúdo da Tab 1: Marketplace */}
      {activeTab === "marketplace" && (
        <div className="space-y-6">
          {/* Barra de Filtros */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Escolha uma plataforma para integrar com um clique. Conectores ativos geram corridas automaticamente.
            </p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium">Status:</span>
              <select
                value={connectorFilter}
                onChange={(e) => setConnectorFilter(e.target.value)}
                className="text-xs bg-muted/40 border border-border/60 rounded-md px-2.5 py-1.5 text-foreground"
              >
                <option value="all">Todos os Status</option>
                <option value="active">Ativos</option>
                <option value="beta">Beta</option>
                <option value="deprecated">Descontinuados</option>
              </select>
            </div>
          </div>

          {/* Grid de Conectores */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredConnectors.map((connector) => {
              const isActive = connector.status === "active";
              const isBeta = connector.status === "beta";

              return (
                <div
                  key={connector.id}
                  className="group relative flex flex-col justify-between p-5 rounded-2xl border border-border/50 bg-card hover:border-brand/40 hover:shadow-md transition-all duration-200"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <div className="w-12 h-12 rounded-xl bg-muted/60 flex items-center justify-center font-bold text-foreground overflow-hidden border border-border/40">
                        {connector.icon_url ? (
                          <img
                            src={connector.icon_url}
                            alt={connector.name}
                            className="w-full h-full object-contain p-2"
                          />
                        ) : (
                          <Plug className="w-6 h-6 text-brand" />
                        )}
                      </div>

                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                          isActive
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                            : isBeta
                            ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                            : "bg-muted text-muted-foreground border border-border/40"
                        }`}
                      >
                        {isActive ? "Ativo" : isBeta ? "Beta" : "Em breve"}
                      </span>
                    </div>

                    <div>
                      <h3 className="font-semibold text-foreground text-base group-hover:text-brand transition-colors">
                        {connector.name}
                      </h3>
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                        {connector.description || "Conector plug-and-play para automação de pedidos de delivery."}
                      </p>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground pt-1">
                      <ShieldCheck className="w-3.5 h-3.5 text-brand" />
                      <span>Autenticação: {connector.auth_type.replace("_", " ")}</span>
                    </div>
                  </div>

                  <div className="mt-5 pt-4 border-t border-border/30 flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground font-mono">
                      v{connector.version}
                    </span>
                    <button
                      onClick={() => handleOpenWizard(connector)}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-foreground text-background hover:bg-brand hover:text-brand-foreground transition-all flex items-center gap-1.5 shadow-sm"
                    >
                      Conectar Loja
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Conteúdo da Tab 2: Minhas Integrações */}
      {activeTab === "integrations" && (
        <div className="space-y-4">
          {integrations.length === 0 ? (
            <div className="text-center py-16 px-4 border border-dashed border-border rounded-2xl space-y-4 bg-muted/10">
              <div className="w-14 h-14 rounded-2xl bg-brand/10 text-brand flex items-center justify-center mx-auto">
                <Plug className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-foreground">Nenhuma integração ativa ainda</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1">
                  Conecte as lojas dos seus clientes aos seus PDVs ou ao Webhook Genérico para começar a receber corridas automaticamente.
                </p>
              </div>
              <button
                onClick={() => handleOpenWizard()}
                className="px-4 py-2 text-sm font-semibold rounded-lg bg-brand text-brand-foreground hover:bg-brand/90 transition-all inline-flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Criar Primeira Integração
              </button>
            </div>
          ) : (
            <div className="border border-border/60 rounded-xl overflow-hidden bg-card shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-muted/40 border-b border-border/50 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="py-3.5 px-4">Loja</th>
                      <th className="py-3.5 px-4">Plataforma</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4">Automação</th>
                      <th className="py-3.5 px-4">Último Webhook</th>
                      <th className="py-3.5 px-4">Erros</th>
                      <th className="py-3.5 px-4 text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {integrations.map((item) => (
                      <tr key={item.id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3.5 px-4">
                          <span className="font-semibold text-foreground">{item.store_name}</span>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-brand" />
                            <span className="font-medium text-foreground">{item.connector_name}</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              item.active
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                                : "bg-muted text-muted-foreground border border-border/40"
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${item.active ? "bg-emerald-500" : "bg-muted-foreground"}`} />
                            {item.active ? "Ativa" : "Pausada"}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                              item.auto_create_order
                                ? "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                                : "bg-muted text-muted-foreground"
                            }`}
                          >
                            {item.auto_create_order ? "Cria Corrida" : "Apenas Ingestão"}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-xs text-muted-foreground">
                          {item.last_webhook_at ? (
                            new Date(item.last_webhook_at).toLocaleString("pt-BR")
                          ) : (
                            <span className="text-muted-foreground/60">Nenhum evento</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          {item.error_count > 0 ? (
                            <span className="inline-flex items-center gap-1 text-xs text-red-500 font-semibold" title={item.error_message || "Erro no processamento"}>
                              <AlertTriangle className="w-3.5 h-3.5" />
                              {item.error_count} falha(s)
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs text-emerald-500 font-medium">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              0 falhas
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => setCredentialsModalItem(item)}
                              className="px-2.5 py-1 text-xs font-medium border border-border/60 rounded-md hover:bg-muted/40 transition-colors"
                              title="Ver URL e Chaves"
                            >
                              Credenciais
                            </button>

                            <button
                              onClick={() => handleViewLogs(item)}
                              className="px-2.5 py-1 text-xs font-medium border border-border/60 rounded-md hover:bg-muted/40 transition-colors"
                              title="Histórico de logs"
                            >
                              Logs
                            </button>

                            <button
                              onClick={() => handleToggleActive(item)}
                              className={`p-1.5 rounded-md transition-colors ${
                                item.active
                                  ? "text-amber-600 hover:bg-amber-500/10"
                                  : "text-emerald-600 hover:bg-emerald-500/10"
                              }`}
                              title={item.active ? "Pausar integração" : "Ativar integração"}
                            >
                              {item.active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                            </button>

                            <button
                              onClick={() => handleDeleteIntegration(item.id)}
                              className="p-1.5 rounded-md text-red-500 hover:bg-red-500/10 transition-colors"
                              title="Excluir integração"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Conteúdo da Tab 3: Auditoria de Webhooks */}
      {activeTab === "logs" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Monitoramento em tempo real de cada requisição de webhook recebida pelo gateway do operador.
            </p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium">Status:</span>
              <select
                value={logStatusFilter}
                onChange={(e) => setLogStatusFilter(e.target.value)}
                className="text-xs bg-muted/40 border border-border/60 rounded-md px-2.5 py-1.5 text-foreground"
              >
                <option value="all">Todos os Status</option>
                <option value="processed">Processados (Sucesso)</option>
                <option value="failed">Falhas</option>
                <option value="duplicate">Duplicados</option>
                <option value="received">Recebidos</option>
              </select>
            </div>
          </div>

          {logs.length === 0 ? (
            <div className="text-center py-14 px-4 border border-dashed border-border rounded-xl bg-muted/10 space-y-2">
              <Activity className="w-8 h-8 text-muted-foreground/60 mx-auto" />
              <p className="text-sm text-muted-foreground">Nenhum evento de webhook registrado ainda.</p>
            </div>
          ) : (
            <div className="border border-border/60 rounded-xl overflow-hidden bg-card shadow-sm">
              <table className="w-full text-left text-sm">
                <thead className="bg-muted/40 border-b border-border/50 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Horário</th>
                    <th className="py-3 px-4">Conector</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Tempo</th>
                    <th className="py-3 px-4">Corrida Criada</th>
                    <th className="py-3 px-4">Detalhes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40 font-mono text-xs">
                  {logs
                    .filter((l) => logStatusFilter === "all" || l.status === logStatusFilter)
                    .map((log) => (
                      <tr key={log.id} className="hover:bg-muted/20">
                        <td className="py-3 px-4 text-muted-foreground font-sans">
                          {new Date(log.created_at).toLocaleString("pt-BR")}
                        </td>
                        <td className="py-3 px-4 font-semibold text-foreground font-sans">
                          {log.connector_slug}
                        </td>
                        <td className="py-3 px-4 font-sans">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                              log.status === "processed"
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                : log.status === "failed"
                                ? "bg-red-500/10 text-red-600 dark:text-red-400"
                                : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                            }`}
                          >
                            {log.status === "processed" ? (
                              <CheckCircle2 className="w-3 h-3" />
                            ) : log.status === "failed" ? (
                              <XCircle className="w-3 h-3" />
                            ) : (
                              <Clock className="w-3 h-3" />
                            )}
                            {log.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {log.processing_ms !== null ? `${log.processing_ms} ms` : "-"}
                        </td>
                        <td className="py-3 px-4">
                          {log.order_id ? (
                            <span className="text-brand font-semibold hover:underline cursor-pointer">
                              {log.order_id.slice(0, 8)}...
                            </span>
                          ) : (
                            <span className="text-muted-foreground/60">-</span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-sans text-muted-foreground">
                          {log.error_detail ? (
                            <span className="text-red-500 line-clamp-1" title={log.error_detail}>
                              {log.error_detail}
                            </span>
                          ) : (
                            <span className="text-emerald-600 dark:text-emerald-400">Corrida gerada com sucesso</span>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Conteúdo da Tab 4: Documentação Técnica */}
      {activeTab === "docs" && (
        <div className="space-y-6">
          <div className="bg-card border border-border/60 rounded-2xl p-6 space-y-4">
            <div className="flex items-center gap-2">
              <FileCode className="w-5 h-5 text-brand" />
              <h2 className="text-lg font-bold text-foreground">Especificação do Webhook Genérico</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              Qualquer software de PDV, cardápio digital ou loja virtual pode despachar entregas automaticamente para a sua frota enviando um webhook padronizado.
            </p>

            <div className="space-y-3 pt-2">
              <h3 className="text-sm font-semibold text-foreground">1. Endpoint de Recebimento</h3>
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/60 font-mono text-xs text-foreground border border-border/50">
                <span>POST https://api.expresso.neves/api/v1/integration/webhooks/generic-webhook/&#123;INTEGRATION_ID&#125;</span>
                <button
                  onClick={() => handleCopy("POST /api/v1/integration/webhooks/generic-webhook/{INTEGRATION_ID}", "endpoint")}
                  className="px-2 py-1 rounded bg-background border border-border/60 text-xs flex items-center gap-1 hover:bg-muted"
                >
                  {copiedKey === "endpoint" ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedKey === "endpoint" ? "Copiado" : "Copiar"}
                </button>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <h3 className="text-sm font-semibold text-foreground">2. Autenticação e Segurança (HMAC-SHA256)</h3>
              <p className="text-xs text-muted-foreground">
                Toda requisição deve conter o cabeçalho <code className="bg-muted px-1.5 py-0.5 rounded font-mono text-foreground">X-Webhook-Signature</code> gerado calculando o HMAC-SHA256 do corpo bruto (raw bytes) usando o seu <code className="bg-muted px-1.5 py-0.5 rounded font-mono text-foreground">webhook_secret</code>.
              </p>
              <div className="p-3 rounded-lg bg-muted/60 font-mono text-xs text-foreground border border-border/50">
                X-Webhook-Signature: sha256=a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-foreground">3. Formato do Payload JSON</h3>
                <button
                  onClick={() =>
                    handleCopy(
                      JSON.stringify(
                        {
                          order_id: "PED-12345",
                          customer: { name: "Maria Silva", phone: "11988887777" },
                          delivery_address: {
                            street: "Av. Paulista",
                            number: "1000",
                            neighborhood: "Bela Vista",
                            city: "São Paulo",
                            state: "SP",
                            zip: "01310-100",
                            instructions: "Apto 42, Bloco B",
                          },
                          items: [
                            { name: "Pizza Calabresa Grande", qty: 1, price_cents: 4500 },
                            { name: "Refrigerante 2L", qty: 1, price_cents: 1200 },
                          ],
                          total_cents: 5700,
                          payment_method: "online",
                          notes: "Entregar sem buzinar",
                        },
                        null,
                        2
                      ),
                      "payload"
                    )
                  }
                  className="px-2.5 py-1 rounded bg-background border border-border/60 text-xs flex items-center gap-1 hover:bg-muted"
                >
                  {copiedKey === "payload" ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  Copiar JSON
                </button>
              </div>

              <pre className="p-4 rounded-xl bg-zinc-950 text-zinc-100 font-mono text-xs overflow-x-auto border border-zinc-800">
{`{
  "order_id": "PED-12345",
  "customer": {
    "name": "Maria Silva",
    "phone": "11988887777"
  },
  "delivery_address": {
    "street": "Av. Paulista",
    "number": "1000",
    "neighborhood": "Bela Vista",
    "city": "São Paulo",
    "state": "SP",
    "zip": "01310-100",
    "instructions": "Apto 42, Bloco B"
  },
  "items": [
    { "name": "Pizza Calabresa Grande", "qty": 1, "price_cents": 4500 },
    { "name": "Refrigerante 2L", "qty": 1, "price_cents": 1200 }
  ],
  "total_cents": 5700,
  "payment_method": "online",
  "notes": "Entregar sem buzinar"
}`}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Wizard de Criação de Integração */}
      {isWizardOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="bg-card border border-border/70 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95">
            {!createdIntegrationResult ? (
              <form onSubmit={handleCreateIntegration} className="space-y-4">
                <div className="flex items-center justify-between border-b border-border/50 pb-3">
                  <div>
                    <h3 className="font-bold text-lg text-foreground">Conectar Nova Loja</h3>
                    <p className="text-xs text-muted-foreground">
                      Vincule um ponto de coleta a uma plataforma parceira
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsWizardOpen(false)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted/60"
                  >
                    ✕
                  </button>
                </div>

                {wizardError && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs">
                    {wizardError}
                  </div>
                )}

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1.5">
                      1. Loja do Cliente
                    </label>
                    <select
                      value={selectedStoreId}
                      onChange={(e) => setSelectedStoreId(e.target.value)}
                      className="w-full text-sm bg-muted/40 border border-border/60 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-brand/40"
                      required
                    >
                      <option value="">Selecione uma loja...</option>
                      {stores.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1.5">
                      2. Conector / Plataforma
                    </label>
                    <select
                      value={selectedConnector?.slug || ""}
                      onChange={(e) => {
                        const conn = connectors.find((c) => c.slug === e.target.value);
                        setSelectedConnector(conn || null);
                      }}
                      className="w-full text-sm bg-muted/40 border border-border/60 rounded-lg p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-brand/40"
                      required
                    >
                      {connectors.map((c) => (
                        <option key={c.id} value={c.slug}>
                          {c.name} ({c.status.toUpperCase()})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="pt-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={autoCreateOrder}
                        onChange={(e) => setAutoCreateOrder(e.target.checked)}
                        className="rounded border-border text-brand focus:ring-brand"
                      />
                      <span className="text-xs text-foreground font-medium">
                        Criar corrida automaticamente ao receber webhook
                      </span>
                    </label>
                    <p className="text-[11px] text-muted-foreground ml-6 mt-0.5">
                      Se desmarcado, os pedidos serão enfileirados apenas para conferência manual.
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-border/40">
                  <button
                    type="button"
                    onClick={() => setIsWizardOpen(false)}
                    className="px-4 py-2 text-sm font-medium border border-border/60 rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={wizardSubmitting}
                    className="px-5 py-2 text-sm font-semibold rounded-lg bg-brand text-brand-foreground hover:bg-brand/90 transition-all flex items-center gap-2 shadow-sm"
                  >
                    {wizardSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Plug className="w-4 h-4" />}
                    Criar Conexão
                  </button>
                </div>
              </form>
            ) : (
              /* Sucesso e Exibição de Credenciais */
              <div className="space-y-4 animate-in fade-in">
                <div className="text-center space-y-2">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center mx-auto">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <h3 className="font-bold text-lg text-foreground">Integração Criada com Sucesso!</h3>
                  <p className="text-xs text-muted-foreground">
                    Configure a URL e o Segredo no painel do seu PDV/Cardápio para começar a despachar pedidos.
                  </p>
                </div>

                <div className="space-y-3 pt-2">
                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1">
                      URL do Webhook
                    </label>
                    <div className="flex items-center gap-1.5">
                      <input
                        type="text"
                        readOnly
                        value={`${window.location.origin}${createdIntegrationResult.webhook_url}`}
                        className="w-full text-xs font-mono bg-muted/60 border border-border/60 rounded-lg p-2.5 text-foreground"
                      />
                      <button
                        onClick={() =>
                          handleCopy(
                            `${window.location.origin}${createdIntegrationResult.webhook_url}`,
                            "res_url"
                          )
                        }
                        className="p-2.5 rounded-lg border border-border/60 bg-muted/30 hover:bg-muted"
                      >
                        {copiedKey === "res_url" ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-foreground mb-1">
                      Chave Secreta (webhook_secret)
                    </label>
                    <div className="flex items-center gap-1.5">
                      <input
                        type="text"
                        readOnly
                        value={createdIntegrationResult.webhook_secret || ""}
                        className="w-full text-xs font-mono bg-muted/60 border border-border/60 rounded-lg p-2.5 text-foreground"
                      />
                      <button
                        onClick={() =>
                          handleCopy(createdIntegrationResult.webhook_secret || "", "res_sec")
                        }
                        className="p-2.5 rounded-lg border border-border/60 bg-muted/30 hover:bg-muted"
                      >
                        {copiedKey === "res_sec" ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                    <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-1 flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Copie agora. Por segurança, este segredo completo não será exibido novamente.
                    </p>
                  </div>
                </div>

                <div className="pt-3 border-t border-border/40 text-center">
                  <button
                    onClick={() => {
                      setIsWizardOpen(false);
                      setCreatedIntegrationResult(null);
                    }}
                    className="w-full py-2.5 text-sm font-semibold rounded-lg bg-foreground text-background hover:bg-foreground/90 transition-all"
                  >
                    Concluir
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL: Visualizar Credenciais */}
      {credentialsModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="bg-card border border-border/70 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border/50 pb-3">
              <div>
                <h3 className="font-bold text-base text-foreground">Credenciais da Integração</h3>
                <p className="text-xs text-muted-foreground">{credentialsModalItem.store_name}</p>
              </div>
              <button
                onClick={() => setCredentialsModalItem(null)}
                className="p-1 rounded-lg text-muted-foreground hover:bg-muted"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  URL Completa do Webhook
                </label>
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    readOnly
                    value={`${window.location.origin}${credentialsModalItem.webhook_url}`}
                    className="w-full text-xs font-mono bg-muted/60 border border-border/60 rounded-lg p-2 text-foreground"
                  />
                  <button
                    onClick={() =>
                      handleCopy(`${window.location.origin}${credentialsModalItem.webhook_url}`, "cred_url")
                    }
                    className="p-2 rounded-lg border border-border/60 hover:bg-muted"
                  >
                    {copiedKey === "cred_url" ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Webhook Secret (Mascarado)
                </label>
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    readOnly
                    value={credentialsModalItem.webhook_secret || ""}
                    className="w-full text-xs font-mono bg-muted/60 border border-border/60 rounded-lg p-2 text-foreground"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2 text-right">
              <button
                onClick={() => setCredentialsModalItem(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-foreground text-background hover:bg-foreground/90 transition-all"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Logs de Integração Específica */}
      {viewingLogsIntegration && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="bg-card border border-border/70 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border/50 pb-3">
              <div>
                <h3 className="font-bold text-base text-foreground">
                  Logs: {viewingLogsIntegration.store_name} ({viewingLogsIntegration.connector_name})
                </h3>
                <p className="text-xs text-muted-foreground">Últimos eventos recebidos para esta conexão</p>
              </div>
              <button
                onClick={() => setViewingLogsIntegration(null)}
                className="p-1 rounded-lg text-muted-foreground hover:bg-muted"
              >
                ✕
              </button>
            </div>

            {logsLoading ? (
              <div className="py-12 text-center">
                <RefreshCw className="w-6 h-6 animate-spin text-brand mx-auto" />
              </div>
            ) : selectedIntegrationLogs.length === 0 ? (
              <div className="py-12 text-center text-sm text-muted-foreground">
                Nenhum webhook recebido ainda para esta integração.
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto divide-y divide-border/40 font-mono text-xs">
                {selectedIntegrationLogs.map((l) => (
                  <div key={l.id} className="py-2.5 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            l.status === "processed"
                              ? "bg-emerald-500/10 text-emerald-500"
                              : l.status === "failed"
                              ? "bg-red-500/10 text-red-500"
                              : "bg-amber-500/10 text-amber-500"
                          }`}
                        >
                          {l.status.toUpperCase()}
                        </span>
                        <span className="text-muted-foreground font-sans">
                          {new Date(l.created_at).toLocaleString("pt-BR")}
                        </span>
                      </div>
                      {l.error_detail && (
                        <p className="text-red-500 text-[11px] font-sans mt-1">{l.error_detail}</p>
                      )}
                    </div>
                    <div className="text-right text-muted-foreground">
                      {l.processing_ms !== null && <span>{l.processing_ms} ms</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="pt-2 text-right border-t border-border/40">
              <button
                onClick={() => setViewingLogsIntegration(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-foreground text-background hover:bg-foreground/90 transition-all"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

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
  Search,
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 py-2">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight">
            Hub de Integrações
          </h1>
          <p className="text-[13px] font-medium text-zinc-500 mt-1">
            Conecte PDVs, cardápios digitais e plataformas de delivery diretamente às lojas dos seus clientes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-3 py-2 text-sm font-medium border border-zinc-200 rounded-lg hover:bg-zinc-50 transition-colors flex items-center gap-1.5 text-zinc-600 shadow-sm"
            title="Atualizar dados"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            Atualizar
          </button>

          <button
            onClick={() => handleOpenWizard()}
            className="bg-zinc-900 hover:bg-zinc-800 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Nova Integração
          </button>
        </div>
      </div>

      {/* Tabs de Navegação */}
      <div className="glass-panel overflow-hidden flex flex-col">
        <div className="p-1.5 border-b border-zinc-100 flex items-center gap-1 bg-zinc-50/30 overflow-x-auto">
          {([
            { id: "marketplace" as const, icon: Layers, label: "Marketplace", count: connectors.length },
            { id: "integrations" as const, icon: Plug, label: "Minhas Integrações", count: integrations.length },
            { id: "logs" as const, icon: Activity, label: "Auditoria de Webhooks" },
            { id: "docs" as const, icon: FileCode, label: "Documentação" },
          ]).map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-[13px] font-semibold rounded-lg transition-all flex items-center gap-2 shrink-0 ${
                activeTab === tab.id
                  ? "bg-white text-zinc-900 shadow-sm border border-zinc-200"
                  : "text-zinc-500 hover:text-zinc-800 hover:bg-white/50"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {tab.count !== undefined && (
                <span className={`ml-0.5 px-1.5 py-0.5 text-[10px] rounded-full font-bold ${
                  activeTab === tab.id ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-600"
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        <div className="p-5">
          {/* Tab 1: Marketplace */}
          {activeTab === "marketplace" && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <p className="text-[13px] text-zinc-500 font-medium">
                  Escolha uma plataforma para integrar com um clique.
                </p>
                <select
                  value={connectorFilter}
                  onChange={(e) => setConnectorFilter(e.target.value)}
                  className="text-xs bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-zinc-700 font-medium shadow-sm"
                >
                  <option value="all">Todos os Status</option>
                  <option value="active">Ativos</option>
                  <option value="beta">Beta</option>
                  <option value="deprecated">Descontinuados</option>
                </select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredConnectors.map((connector) => {
                  const isActive = connector.status === "active";
                  const isBeta = connector.status === "beta";

                  return (
                    <div
                      key={connector.id}
                      className="group relative flex flex-col justify-between p-5 rounded-xl border border-zinc-200 bg-white hover:border-zinc-300 hover:shadow-md transition-all duration-200"
                    >
                      <div className="space-y-3">
                        <div className="flex items-start justify-between">
                          <div className="w-11 h-11 rounded-xl bg-zinc-100 flex items-center justify-center font-bold text-zinc-800 overflow-hidden border border-zinc-200">
                            {connector.icon_url ? (
                              <img
                                src={connector.icon_url}
                                alt={connector.name}
                                className="w-full h-full object-contain p-2"
                              />
                            ) : (
                              <Plug className="w-5 h-5 text-zinc-600" />
                            )}
                          </div>

                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border ${
                              isActive
                                ? "bg-emerald-50 text-emerald-700 border-emerald-200/60"
                                : isBeta
                                ? "bg-amber-50 text-amber-700 border-amber-200/60"
                                : "bg-zinc-100 text-zinc-600 border-zinc-200"
                            }`}
                          >
                            {isActive ? "Ativo" : isBeta ? "Beta" : "Em breve"}
                          </span>
                        </div>

                        <div>
                          <h3 className="font-bold text-zinc-900 text-sm group-hover:text-zinc-700 transition-colors">
                            {connector.name}
                          </h3>
                          <p className="text-xs text-zinc-500 line-clamp-2 mt-1">
                            {connector.description || "Conector plug-and-play para automação de pedidos de delivery."}
                          </p>
                        </div>

                        <div className="flex items-center gap-1.5 text-[11px] text-zinc-500">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Autenticação: {connector.auth_type.replace("_", " ")}</span>
                        </div>
                      </div>

                      <div className="mt-4 pt-3 border-t border-zinc-100 flex items-center justify-between">
                        <span className="text-[10px] text-zinc-400 font-mono">
                          v{connector.version}
                        </span>
                        <button
                          onClick={() => handleOpenWizard(connector)}
                          className="px-3 py-1.5 text-xs font-bold rounded-lg bg-zinc-900 text-white hover:bg-zinc-800 transition-all flex items-center gap-1.5 shadow-sm"
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

          {/* Tab 2: Minhas Integrações */}
          {activeTab === "integrations" && (
            <div className="space-y-4">
              {integrations.length === 0 ? (
                <div className="text-center py-16 px-4 border border-dashed border-zinc-200 rounded-xl space-y-4 bg-zinc-50/50">
                  <div className="w-14 h-14 rounded-2xl bg-zinc-100 text-zinc-500 flex items-center justify-center mx-auto">
                    <Plug className="w-7 h-7" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-900">Nenhuma integração ativa ainda</h3>
                    <p className="text-sm text-zinc-500 max-w-md mx-auto mt-1">
                      Conecte as lojas dos seus clientes aos seus PDVs ou ao Webhook Genérico para começar a receber corridas automaticamente.
                    </p>
                  </div>
                  <button
                    onClick={() => handleOpenWizard()}
                    className="px-4 py-2 text-sm font-bold rounded-lg bg-zinc-900 text-white hover:bg-zinc-800 transition-all inline-flex items-center gap-2 shadow-sm"
                  >
                    <Plus className="w-4 h-4" />
                    Criar Primeira Integração
                  </button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-semibold text-[10px] uppercase tracking-wider">
                      <tr>
                        <th className="py-2.5 px-4">Loja</th>
                        <th className="py-2.5 px-4">Plataforma</th>
                        <th className="py-2.5 px-4">Status</th>
                        <th className="py-2.5 px-4">Automação</th>
                        <th className="py-2.5 px-4">Último Webhook</th>
                        <th className="py-2.5 px-4">Erros</th>
                        <th className="py-2.5 px-4 text-right">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                      {integrations.map((item) => (
                        <tr key={item.id} className="hover:bg-zinc-50/80 transition-colors">
                          <td className="py-3 px-4">
                            <span className="font-semibold text-zinc-900">{item.store_name}</span>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-zinc-900" />
                              <span className="font-medium text-zinc-700">{item.connector_name}</span>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                                item.active
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200/60"
                                  : "bg-zinc-100 text-zinc-600 border-zinc-200"
                              }`}
                            >
                              <span className={`w-1.5 h-1.5 rounded-full ${item.active ? "bg-emerald-500" : "bg-zinc-400"}`} />
                              {item.active ? "Ativa" : "Pausada"}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider border ${
                                item.auto_create_order
                                  ? "bg-blue-50 text-blue-700 border-blue-200/60"
                                  : "bg-zinc-100 text-zinc-600 border-zinc-200"
                              }`}
                            >
                              {item.auto_create_order ? "Cria Corrida" : "Apenas Ingestão"}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-xs text-zinc-500">
                            {item.last_webhook_at ? (
                              new Date(item.last_webhook_at).toLocaleString("pt-BR")
                            ) : (
                              <span className="text-zinc-400">Nenhum evento</span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            {item.error_count > 0 ? (
                              <span className="inline-flex items-center gap-1 text-xs text-red-600 font-bold" title={item.error_message || "Erro no processamento"}>
                                <AlertTriangle className="w-3.5 h-3.5" />
                                {item.error_count} falha(s)
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                0 falhas
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => setCredentialsModalItem(item)}
                                className="px-2.5 py-1 text-xs font-semibold border border-zinc-200 rounded-md hover:bg-zinc-50 transition-colors text-zinc-700 shadow-sm"
                                title="Ver URL e Chaves"
                              >
                                Credenciais
                              </button>

                              <button
                                onClick={() => handleViewLogs(item)}
                                className="px-2.5 py-1 text-xs font-semibold border border-zinc-200 rounded-md hover:bg-zinc-50 transition-colors text-zinc-700 shadow-sm"
                                title="Histórico de logs"
                              >
                                Logs
                              </button>

                              <button
                                onClick={() => handleToggleActive(item)}
                                className={`p-1.5 rounded-md transition-colors ${
                                  item.active
                                    ? "text-amber-600 hover:bg-amber-50"
                                    : "text-emerald-600 hover:bg-emerald-50"
                                }`}
                                title={item.active ? "Pausar integração" : "Ativar integração"}
                              >
                                {item.active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                              </button>

                              <button
                                onClick={() => handleDeleteIntegration(item.id)}
                                className="p-1.5 rounded-md text-red-500 hover:bg-red-50 transition-colors"
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
              )}
            </div>
          )}

          {/* Tab 3: Auditoria de Webhooks */}
          {activeTab === "logs" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-[13px] text-zinc-500 font-medium">
                  Monitoramento em tempo real de cada requisição de webhook recebida.
                </p>
                <select
                  value={logStatusFilter}
                  onChange={(e) => setLogStatusFilter(e.target.value)}
                  className="text-xs bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-zinc-700 font-medium shadow-sm"
                >
                  <option value="all">Todos os Status</option>
                  <option value="processed">Processados (Sucesso)</option>
                  <option value="failed">Falhas</option>
                  <option value="duplicate">Duplicados</option>
                  <option value="received">Recebidos</option>
                </select>
              </div>

              {logs.length === 0 ? (
                <div className="text-center py-14 px-4 border border-dashed border-zinc-200 rounded-xl bg-zinc-50/50 space-y-2">
                  <Activity className="w-8 h-8 text-zinc-400 mx-auto" />
                  <p className="text-sm text-zinc-500 font-medium">Nenhum evento de webhook registrado ainda.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-semibold text-[10px] uppercase tracking-wider">
                      <tr>
                        <th className="py-2.5 px-4">Horário</th>
                        <th className="py-2.5 px-4">Conector</th>
                        <th className="py-2.5 px-4">Status</th>
                        <th className="py-2.5 px-4">Tempo</th>
                        <th className="py-2.5 px-4">Corrida Criada</th>
                        <th className="py-2.5 px-4">Detalhes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100 font-mono text-xs">
                      {logs
                        .filter((l) => logStatusFilter === "all" || l.status === logStatusFilter)
                        .map((log) => (
                          <tr key={log.id} className="hover:bg-zinc-50/80 transition-colors">
                            <td className="py-3 px-4 text-zinc-500 font-sans">
                              {new Date(log.created_at).toLocaleString("pt-BR")}
                            </td>
                            <td className="py-3 px-4 font-semibold text-zinc-900 font-sans">
                              {log.connector_slug}
                            </td>
                            <td className="py-3 px-4 font-sans">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                                  log.status === "processed"
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200/60"
                                    : log.status === "failed"
                                    ? "bg-red-50 text-red-700 border-red-200/60"
                                    : "bg-amber-50 text-amber-700 border-amber-200/60"
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
                            <td className="py-3 px-4 text-zinc-500">
                              {log.processing_ms !== null ? `${log.processing_ms} ms` : "-"}
                            </td>
                            <td className="py-3 px-4">
                              {log.order_id ? (
                                <span className="text-zinc-900 font-bold hover:underline cursor-pointer">
                                  {log.order_id.slice(0, 8)}...
                                </span>
                              ) : (
                                <span className="text-zinc-400">-</span>
                              )}
                            </td>
                            <td className="py-3 px-4 font-sans text-zinc-500">
                              {log.error_detail ? (
                                <span className="text-red-600 line-clamp-1 font-medium" title={log.error_detail}>
                                  {log.error_detail}
                                </span>
                              ) : (
                                <span className="text-emerald-600 font-medium">Corrida gerada com sucesso</span>
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

          {/* Tab 4: Documentação Técnica */}
          {activeTab === "docs" && (
            <div className="space-y-5">
              <div className="bg-white border border-zinc-200 rounded-xl p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-zinc-700" />
                  <h2 className="text-base font-bold text-zinc-900">Especificação do Webhook Genérico</h2>
                </div>
                <p className="text-[13px] text-zinc-500">
                  Qualquer software de PDV, cardápio digital ou loja virtual pode despachar entregas automaticamente para a sua frota enviando um webhook padronizado.
                </p>

                <div className="space-y-3 pt-2">
                  <h3 className="text-sm font-bold text-zinc-900">1. Endpoint de Recebimento</h3>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-50 font-mono text-xs text-zinc-900 border border-zinc-200">
                    <span>POST https://api.expresso.neves/api/v1/integration/webhooks/generic-webhook/&#123;INTEGRATION_ID&#125;</span>
                    <button
                      onClick={() => handleCopy("POST /api/v1/integration/webhooks/generic-webhook/{INTEGRATION_ID}", "endpoint")}
                      className="px-2 py-1 rounded bg-white border border-zinc-200 text-xs flex items-center gap-1 hover:bg-zinc-100 text-zinc-600 shadow-sm"
                    >
                      {copiedKey === "endpoint" ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                      {copiedKey === "endpoint" ? "Copiado" : "Copiar"}
                    </button>
                  </div>
                </div>

                <div className="space-y-3 pt-2">
                  <h3 className="text-sm font-bold text-zinc-900">2. Autenticação e Segurança (HMAC-SHA256)</h3>
                  <p className="text-xs text-zinc-500">
                    Toda requisição deve conter o cabeçalho <code className="bg-zinc-100 px-1.5 py-0.5 rounded font-mono text-zinc-900 border border-zinc-200">X-Webhook-Signature</code> gerado calculando o HMAC-SHA256 do corpo bruto usando o seu <code className="bg-zinc-100 px-1.5 py-0.5 rounded font-mono text-zinc-900 border border-zinc-200">webhook_secret</code>.
                  </p>
                  <div className="p-3 rounded-lg bg-zinc-50 font-mono text-xs text-zinc-900 border border-zinc-200">
                    X-Webhook-Signature: sha256=a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e
                  </div>
                </div>

                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-zinc-900">3. Formato do Payload JSON</h3>
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
                      className="px-2.5 py-1 rounded bg-white border border-zinc-200 text-xs flex items-center gap-1 hover:bg-zinc-100 text-zinc-600 shadow-sm"
                    >
                      {copiedKey === "payload" ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                      Copiar JSON
                    </button>
                  </div>

                  <pre className="p-4 rounded-xl bg-zinc-900 text-zinc-100 font-mono text-xs overflow-x-auto border border-zinc-700">
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
        </div>

        <div className="px-4 py-3 border-t border-zinc-200 bg-zinc-50 flex items-center justify-center">
          <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
            {activeTab === "marketplace" && `${filteredConnectors.length} conectores disponíveis`}
            {activeTab === "integrations" && `${integrations.length} integrações configuradas`}
            {activeTab === "logs" && `${logs.length} eventos registrados`}
            {activeTab === "docs" && "Documentação técnica do webhook genérico"}
          </span>
        </div>
      </div>

      {/* MODAL: Wizard de Criação de Integração */}
      {isWizardOpen && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs" onClick={() => setIsWizardOpen(false)} />
          <div className="relative bg-white border border-zinc-200 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-5 z-10">
            {!createdIntegrationResult ? (
              <form onSubmit={handleCreateIntegration} className="space-y-4">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                  <div>
                    <h3 className="font-bold text-lg text-zinc-900">Conectar Nova Loja</h3>
                    <p className="text-xs text-zinc-500 font-medium">
                      Vincule um ponto de coleta a uma plataforma parceira
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsWizardOpen(false)}
                    className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors"
                  >
                    ✕
                  </button>
                </div>

                {wizardError && (
                  <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
                    {wizardError}
                  </div>
                )}

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                      1. Loja do Cliente
                    </label>
                    <select
                      value={selectedStoreId}
                      onChange={(e) => setSelectedStoreId(e.target.value)}
                      className="w-full text-sm bg-white border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-300 shadow-sm"
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
                    <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                      2. Conector / Plataforma
                    </label>
                    <select
                      value={selectedConnector?.slug || ""}
                      onChange={(e) => {
                        const conn = connectors.find((c) => c.slug === e.target.value);
                        setSelectedConnector(conn || null);
                      }}
                      className="w-full text-sm bg-white border border-zinc-200 rounded-lg p-2.5 text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-300 shadow-sm"
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
                        className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
                      />
                      <span className="text-xs text-zinc-700 font-semibold">
                        Criar corrida automaticamente ao receber webhook
                      </span>
                    </label>
                    <p className="text-[11px] text-zinc-500 ml-6 mt-0.5">
                      Se desmarcado, os pedidos serão enfileirados apenas para conferência manual.
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-zinc-100">
                  <button
                    type="button"
                    onClick={() => setIsWizardOpen(false)}
                    className="px-4 py-2 text-sm font-bold border border-zinc-200 rounded-lg hover:bg-zinc-50 transition-colors text-zinc-700 shadow-sm"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={wizardSubmitting}
                    className="px-5 py-2 text-sm font-bold rounded-lg bg-zinc-900 text-white hover:bg-zinc-800 transition-all flex items-center gap-2 shadow-sm"
                  >
                    {wizardSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Plug className="w-4 h-4" />}
                    Criar Conexão
                  </button>
                </div>
              </form>
            ) : (
              /* Sucesso e Exibição de Credenciais */
              <div className="space-y-4">
                <div className="text-center space-y-2">
                  <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-200">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <h3 className="font-bold text-lg text-zinc-900">Integração Criada com Sucesso!</h3>
                  <p className="text-xs text-zinc-500 font-medium">
                    Configure a URL e o Segredo no painel do seu PDV/Cardápio para começar a despachar pedidos.
                  </p>
                </div>

                <div className="space-y-3 pt-2">
                  <div>
                    <label className="block text-xs font-bold text-zinc-700 mb-1">
                      URL do Webhook
                    </label>
                    <div className="flex items-center gap-1.5">
                      <input
                        type="text"
                        readOnly
                        value={`${window.location.origin}${createdIntegrationResult.webhook_url}`}
                        className="w-full text-xs font-mono bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 shadow-sm"
                      />
                      <button
                        onClick={() =>
                          handleCopy(
                            `${window.location.origin}${createdIntegrationResult.webhook_url}`,
                            "res_url"
                          )
                        }
                        className="p-2.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 shadow-sm"
                      >
                        {copiedKey === "res_url" ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4 text-zinc-500" />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-zinc-700 mb-1">
                      Chave Secreta (webhook_secret)
                    </label>
                    <div className="flex items-center gap-1.5">
                      <input
                        type="text"
                        readOnly
                        value={createdIntegrationResult.webhook_secret || ""}
                        className="w-full text-xs font-mono bg-zinc-50 border border-zinc-200 rounded-lg p-2.5 text-zinc-900 shadow-sm"
                      />
                      <button
                        onClick={() =>
                          handleCopy(createdIntegrationResult.webhook_secret || "", "res_sec")
                        }
                        className="p-2.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 shadow-sm"
                      >
                        {copiedKey === "res_sec" ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4 text-zinc-500" />}
                      </button>
                    </div>
                    <p className="text-[11px] text-amber-700 mt-1 flex items-center gap-1 font-medium">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Copie agora. Por segurança, este segredo completo não será exibido novamente.
                    </p>
                  </div>
                </div>

                <div className="pt-3 border-t border-zinc-100 text-center">
                  <button
                    onClick={() => {
                      setIsWizardOpen(false);
                      setCreatedIntegrationResult(null);
                    }}
                    className="w-full py-2.5 text-sm font-bold rounded-lg bg-zinc-900 text-white hover:bg-zinc-800 transition-all shadow-sm"
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
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs" onClick={() => setCredentialsModalItem(null)} />
          <div className="relative bg-white border border-zinc-200 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4 z-10">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div>
                <h3 className="font-bold text-base text-zinc-900">Credenciais da Integração</h3>
                <p className="text-xs text-zinc-500 font-medium">{credentialsModalItem.store_name}</p>
              </div>
              <button
                onClick={() => setCredentialsModalItem(null)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-zinc-700 mb-1">
                  URL Completa do Webhook
                </label>
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    readOnly
                    value={`${window.location.origin}${credentialsModalItem.webhook_url}`}
                    className="w-full text-xs font-mono bg-zinc-50 border border-zinc-200 rounded-lg p-2 text-zinc-900 shadow-sm"
                  />
                  <button
                    onClick={() =>
                      handleCopy(`${window.location.origin}${credentialsModalItem.webhook_url}`, "cred_url")
                    }
                    className="p-2 rounded-lg border border-zinc-200 hover:bg-zinc-50 shadow-sm"
                  >
                    {copiedKey === "cred_url" ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4 text-zinc-500" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 mb-1">
                  Webhook Secret (Mascarado)
                </label>
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    readOnly
                    value={credentialsModalItem.webhook_secret || ""}
                    className="w-full text-xs font-mono bg-zinc-50 border border-zinc-200 rounded-lg p-2 text-zinc-900 shadow-sm"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2 text-right">
              <button
                onClick={() => setCredentialsModalItem(null)}
                className="px-4 py-2 text-xs font-bold rounded-lg bg-zinc-900 text-white hover:bg-zinc-800 transition-all shadow-sm"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Logs de Integração Específica */}
      {viewingLogsIntegration && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs" onClick={() => setViewingLogsIntegration(null)} />
          <div className="relative bg-white border border-zinc-200 rounded-xl max-w-2xl w-full p-6 shadow-2xl space-y-4 z-10">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div>
                <h3 className="font-bold text-base text-zinc-900">
                  Logs: {viewingLogsIntegration.store_name} ({viewingLogsIntegration.connector_name})
                </h3>
                <p className="text-xs text-zinc-500 font-medium">Últimos eventos recebidos para esta conexão</p>
              </div>
              <button
                onClick={() => setViewingLogsIntegration(null)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors"
              >
                ✕
              </button>
            </div>

            {logsLoading ? (
              <div className="py-12 text-center">
                <RefreshCw className="w-6 h-6 animate-spin text-zinc-400 mx-auto" />
              </div>
            ) : selectedIntegrationLogs.length === 0 ? (
              <div className="py-12 text-center text-sm text-zinc-500 font-medium">
                Nenhum webhook recebido ainda para esta integração.
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto divide-y divide-zinc-100 font-mono text-xs">
                {selectedIntegrationLogs.map((l) => (
                  <div key={l.id} className="py-2.5 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                            l.status === "processed"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200/60"
                              : l.status === "failed"
                              ? "bg-red-50 text-red-700 border-red-200/60"
                              : "bg-amber-50 text-amber-700 border-amber-200/60"
                          }`}
                        >
                          {l.status.toUpperCase()}
                        </span>
                        <span className="text-zinc-500 font-sans">
                          {new Date(l.created_at).toLocaleString("pt-BR")}
                        </span>
                      </div>
                      {l.error_detail && (
                        <p className="text-red-600 text-[11px] font-sans mt-1 font-medium">{l.error_detail}</p>
                      )}
                    </div>
                    <div className="text-right text-zinc-500">
                      {l.processing_ms !== null && <span>{l.processing_ms} ms</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="pt-2 text-right border-t border-zinc-100">
              <button
                onClick={() => setViewingLogsIntegration(null)}
                className="px-4 py-2 text-xs font-bold rounded-lg bg-zinc-900 text-white hover:bg-zinc-800 transition-all shadow-sm"
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

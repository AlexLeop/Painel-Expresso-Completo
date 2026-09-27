import { logger } from "@/lib/logger";
import { useState, useEffect, useMemo, useCallback } from "react";
import { Navigate } from "react-router-dom";
import { formatCurrency, cn } from "../lib/utils";
import { getCompanyConfig } from "../services/company-config";
import { authFetch } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import CreditQueuePanel from "../components/CreditQueuePanel";
import AcertoInLoco from "../components/AcertoInLoco";
import { StoreBalancesTab } from "../components/financeiro/StoreBalancesTab";
import { DriverWalletsTab } from "../components/financeiro/DriverWalletsTab";
import { DreTab } from "../components/financeiro/DreTab";
import { CashReconciliationTab } from "../components/financeiro/CashReconciliationTab";
import {
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertCircle,
  Wallet,
  History,
  ListChecks,
  Info,
  ChevronRight,
  Play,
  RefreshCw,
  Calculator,
  Store,
  PieChart,
  Banknote,
} from "lucide-react";

interface DriverBalance {
  id: string;
  name: string;
  balance: number | null;
  loading: boolean;
  error?: string;
}

export interface CreditLogItem {
  id: string;
  date: string;
  driverId: string;
  driverName: string;
  companyId: string;
  companyName: string;
  amount: number;
  breakdown: { diaria: number; extras: number; adiantamentos: number };
  status: "success" | "failed" | "pending";
  createdAt: string;
  processedBy: string;
  lastError?: string;
}

export function Financeiro() {
  const { session } = useAuth();
  const user = session?.user;

  // Lojistas devem ver seus extratos e créditos de loja, nunca o painel operacional de créditos da central
  const rawRole = (user?.role || "").toLowerCase();
  const isLojista =
    rawRole === "lojista" ||
    rawRole === "cliente" ||
    Boolean(user?.client_id) ||
    Boolean(user?.store_id);

  if (isLojista) {
    return <Navigate to="/extrato" replace />;
  }

  const companyId = user?.machine_empresa_id || user?.company_id || "";
  const companies = Array.isArray(user?.companies) ? user?.companies : [];
  const currentCompany = companies?.find(
    (c: any) => String(c.id) === String(companyId),
  );
  const companyName = currentCompany?.nome || "Operação";
  const isAdmin =
    user?.role === "superadmin" ||
    user?.role === "operador_admin" ||
    user?.role === "operador_staff" ||
    user?.role === "admin" ||
    user?.role === "master" ||
    user?.role === "administrador" ||
    user?.is_platform_admin === true;

  const [activeTab, setActiveTab] = useState<
    "store_balances" | "dre" | "cash_reconciliation" | "overview" | "queue" | "log" | "balances" | "acerto"
  >("store_balances");
  const [creditLog, setCreditLog] = useState<CreditLogItem[]>([]);
  const [driverBalances, setDriverBalances] = useState<DriverBalance[]>([]);
  const [loadingBalances, setLoadingBalances] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processingResults, setProcessingResults] = useState<string[]>([]);
  const [stats, setStats] = useState({ total: 0, pending: 0, credited: 0, failed: 0 });

  const loadDriverBalances = useCallback(async () => {
    if (!companyId) return;
    setLoadingBalances(true);
    try {
      const resDrivers = await authFetch(
        `/api/v1/db/company-drivers?company_id=${companyId}&active_only=0`,
      );
      if (!resDrivers.ok) throw new Error("Erro ao buscar motoboys");
      const drivers = await resDrivers.json();

      const initialBalances = drivers.map((d: any) => ({
        id: d.id,
        name: d.name,
        balance: null,
        loading: true,
      }));
      setDriverBalances(initialBalances);

      for (const driver of drivers) {
        try {
          const res = await authFetch(
            `/api/v1/db/driver-balance?condutor_id=${driver.id}`,
          );
          if (res.ok) {
            const data = await res.json();
            setDriverBalances((prev) =>
              prev.map((db) =>
                db.id === driver.id
                  ? { ...db, balance: data.saldo || 0, loading: false }
                  : db,
              ),
            );
          } else {
            setDriverBalances((prev) =>
              prev.map((db) =>
                db.id === driver.id
                  ? { ...db, loading: false, error: "Erro API" }
                  : db,
              ),
            );
          }
        } catch {
          setDriverBalances((prev) =>
            prev.map((db) =>
              db.id === driver.id
                ? { ...db, loading: false, error: "Erro rede" }
                : db,
            ),
          );
        }
      }
    } catch (err) {
      logger.error(err);
    } finally {
      setLoadingBalances(false);
    }
  }, [companyId]);

  useEffect(() => {
    if (activeTab === "balances" && driverBalances.length === 0) {
      loadDriverBalances();
    }
  }, [activeTab, loadDriverBalances, driverBalances.length]);

  // Período da semana atual (segunda a domingo)
  const weekPeriod = useMemo(() => {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    const start = new Date(now.setDate(diff));
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    end.setHours(23, 59, 59, 999);

    return {
      start: start.toISOString().split("T")[0],
      end: end.toISOString().split("T")[0],
      label: `${start.toLocaleDateString("pt-BR")} a ${end.toLocaleDateString("pt-BR")}`,
    };
  }, []);

  const loadData = useCallback(async () => {
    try {
      // 1. Carregar estatísticas reais do banco de dados (zero mock / zero localStorage)
      const resStats = await authFetch(
        `/api/v1/operator/credit-stats?start_date=${weekPeriod.start}&end_date=${weekPeriod.end}${
          companyId ? `&company_id=${companyId}` : ""
        }`,
      );
      if (resStats.ok) {
        const statsData = await resStats.json();
        setStats({
          total: statsData.total ?? 0,
          pending: statsData.pending ?? 0,
          credited: statsData.credited ?? 0,
          failed: statsData.failed ?? 0,
        });
      }

      // 2. Carregar log real da fila de cálculos do banco de dados
      const resQueue = await authFetch(
        `/api/v1/db/credit-queue?company_id=${companyId || "global"}`,
      );
      if (resQueue.ok) {
        const queueData = await resQueue.json();
        const items = (queueData.items || []).map((item: any) => ({
          id: item.id,
          date: item.created_at ? item.created_at.split("T")[0] : "",
          driverId: item.driver_id,
          driverName: item.driver_name || "Motoboy",
          companyId: item.company_id,
          companyName: item.company_name || companyName,
          amount: item.net_amount || 0,
          breakdown: { diaria: item.net_amount || 0, extras: 0, adiantamentos: 0 },
          status:
            item.status === "credited"
              ? "success"
              : item.status === "failed" || item.status === "dead"
                ? "failed"
                : "pending",
          createdAt: item.created_at || new Date().toISOString(),
          processedBy: "operador",
          lastError: item.last_error,
        }));
        setCreditLog(items);
      }
    } catch (err) {
      logger.error("Erro ao carregar dados financeiros reais:", err);
    }
  }, [companyId, weekPeriod, companyName]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const config = useMemo(() => {
    if (!companyId) return null;
    return getCompanyConfig(Number(companyId), companyName);
  }, [companyId, companyName]);

  const yesterday = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().split("T")[0];
  }, []);

  const processCredits = async (targetDate?: string) => {
    setProcessing(true);
    setProcessingResults([]);

    try {
      const body: any = {};
      if (companyId) body.company_id = companyId;
      if (targetDate) body.date = targetDate;

      // Executa no back-end real do Django Ninja (Celery / PostgreSQL)
      const res = await authFetch("/api/v1/operator/process-credits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (res.ok && data.results) {
        const lines = (data.results as any[]).map((r) => {
          if (r.status === "credited")
            return `✓ ${r.driver}: ${formatCurrency(r.amount)}`;
          if (r.status === "skipped")
            return `○ ${r.driver}: ${r.reason || "sem pendência"}`;
          return `✕ ${r.driver}: ${r.reason || "erro"}`;
        });
        setProcessingResults(
          lines.length > 0 ? lines : ["Nenhum crédito pendente processado para a data."],
        );
      } else {
        setProcessingResults([data.error || "Erro ao processar créditos."]);
      }
    } catch (err) {
      setProcessingResults(["Erro de conexão com o servidor ao processar créditos."]);
    } finally {
      setProcessing(false);
      loadData();
    }
  };


  const tabs = [
    { key: "store_balances", label: "Saldo das Lojas", icon: Store },
    { key: "dre", label: "DRE Operacional", icon: PieChart },
    { key: "cash_reconciliation", label: "Conferência de Caixa", icon: Banknote },
    { key: "acerto", label: "Acerto In-Loco", icon: Calculator },
    { key: "overview", label: "Regras", icon: Info },
    { key: "queue", label: "Fila de Créditos", icon: ListChecks },
    { key: "log", label: "Log de Créditos", icon: History },
    ...(isAdmin ? [{ key: "balances", label: "Saldos Motoboys", icon: Wallet }] : []),
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-5 rounded-xl shadow-sm ring-1 ring-zinc-950/5">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight">
            Financeiro
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {companyName} • Gestão de créditos automáticos
          </p>
        </div>
        <div className="flex items-center gap-3 mt-4 sm:mt-0">
          <button
            disabled={processing || stats.pending === 0}
            onClick={() => processCredits(yesterday)}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-100 text-zinc-700 rounded-lg hover:bg-zinc-200 text-sm font-bold uppercase tracking-wider transition-all border border-zinc-200 disabled:opacity-50"
          >
            {processing ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Clock className="h-4 w-4" />
            )}
            {processing
              ? "Processando..."
              : `Creditar Ontem (${yesterday.split("-").reverse().slice(0, 2).join("/")})`}
          </button>
          <button
            disabled={processing || !config?.autoCredit.enabled}
            onClick={() => processCredits()}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 text-sm font-bold uppercase tracking-wider transition-all shadow-sm disabled:opacity-50"
          >
            {processing ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {processing ? "Processando..." : "Processar Créditos"}
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Diárias na Semana"
          value={stats.total}
          icon={TrendingUp}
          color="blue"
        />
        <StatCard
          label="Pendentes"
          value={stats.pending}
          icon={Clock}
          color="orange"
        />
        <StatCard
          label="Creditadas"
          value={stats.credited}
          icon={CheckCircle2}
          color="green"
        />
        <StatCard
          label="Falhas"
          value={stats.failed}
          icon={AlertCircle}
          color="red"
        />
      </div>

      {/* Configuration & Processing Results */}
      {(config || processingResults.length > 0) && (
        <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 p-5">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider">
                Configuração de Crédito
              </h3>
              <p className="text-xs text-zinc-500 mt-1">
                {config?.autoCredit.enabled
                  ? `Ativo • Corte às ${String(config.autoCredit.cutoffHour).padStart(2, "0")}:${String(config.autoCredit.cutoffMinute).padStart(2, "0")}`
                  : "Desativado • Configure nas configurações da empresa"}
              </p>
            </div>
            {processingResults.length > 0 && (
              <button
                onClick={() => setProcessingResults([])}
                className="text-[10px] font-bold text-zinc-400 hover:text-zinc-600 uppercase tracking-widest"
              >
                Limpar Log
              </button>
            )}
          </div>

          {processingResults.length > 0 && (
            <div className="mt-4 p-3 bg-zinc-50 rounded-lg border border-zinc-100 max-h-40 overflow-y-auto">
              {processingResults.map((res, i) => (
                <div
                  key={i}
                  className="text-[11px] font-mono text-zinc-600 py-0.5 border-b border-zinc-200/50 last:border-0"
                >
                  {res}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="flex bg-white p-1 rounded-xl shadow-sm ring-1 ring-zinc-950/5">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-bold uppercase tracking-wider rounded-lg transition-all",
              activeTab === tab.key
                ? "bg-zinc-900 text-white shadow-md"
                : "text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50",
            )}
          >
            <tab.icon className="h-4 w-4" />
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <InfoBox
              step="1"
              title="Lançamento"
              description="Gestor marca presença na tela de Lançamentos. Diária auto-preenchida pelo dia da semana."
              color="orange"
            />
            <InfoBox
              step="2"
              title="Ajuste"
              description="A loja tem até o horário de corte para ajustar diárias (turno duplo, descontos, extras)."
              color="blue"
            />
            <InfoBox
              step="3"
              title="Crédito"
              description="Sistema credita automaticamente na carteira Machine. Fórmula: Diária + Extras - Adiantamentos."
              color="green"
            />

            {config && (
              <div className="md:col-span-3 bg-indigo-50 border border-indigo-100 p-5 rounded-xl">
                <h4 className="text-sm font-bold text-indigo-900 uppercase tracking-wider mb-2">
                  Regra de Extras por Km
                </h4>
                <p className="text-xs text-indigo-700 leading-relaxed">
                  {config.extraKm.mode === "disabled" &&
                    "Esta loja não possui pagamento de extra por KM excedente configurado."}
                  {config.extraKm.mode === "fixed" &&
                    `Valor fixo de ${formatCurrency(config.extraKm.fixedAmount)} para corridas acima de ${config.extraKm.minKm}km.`}
                  {config.extraKm.mode === "delivery_fee" &&
                    `Taxa adicional de entrega (${formatCurrency(config.taxaCorridaPerEntrega)}) para corridas acima de ${config.extraKm.minKm}km.`}
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === "queue" && (
          <CreditQueuePanel companyId={String(companyId)} />
        )}

        {activeTab === "log" && (
          <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left whitespace-nowrap text-xs">
                <thead className="bg-zinc-50/80 border-b border-zinc-200 text-zinc-500 text-[10px] font-bold uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4">Data</th>
                    <th className="px-4 py-4">Motoboy</th>
                    <th className="px-4 py-4 text-right">Diária</th>
                    <th className="px-4 py-4 text-right">Extras</th>
                    <th className="px-4 py-4 text-right">Adiant.</th>
                    <th className="px-4 py-4 text-right">Total</th>
                    <th className="px-4 py-4 text-center">Status</th>
                    <th className="px-6 py-4 text-right">Processado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {creditLog.length === 0 ? (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-6 py-12 text-center text-zinc-400"
                      >
                        Nenhum crédito processado no período selecionado.
                      </td>
                    </tr>
                  ) : (
                    creditLog.map((entry) => (
                      <tr
                        key={entry.id}
                        className="hover:bg-zinc-50/50 transition-colors"
                      >
                        <td className="px-6 py-4 font-bold text-zinc-900">
                          {entry.date.split("-").reverse().join("/")}
                        </td>
                        <td className="px-4 py-4 text-zinc-700 font-medium">
                          {entry.driverName}
                        </td>
                        <td className="px-4 py-4 text-right font-mono">
                          {formatCurrency(entry.breakdown.diaria)}
                        </td>
                        <td className="px-4 py-4 text-right font-mono text-emerald-600">
                          {entry.breakdown.extras > 0
                            ? `+${formatCurrency(entry.breakdown.extras)}`
                            : "—"}
                        </td>
                        <td className="px-4 py-4 text-right font-mono text-rose-500">
                          {entry.breakdown.adiantamentos > 0
                            ? `-${formatCurrency(entry.breakdown.adiantamentos)}`
                            : "—"}
                        </td>
                        <td
                          className={cn(
                            "px-4 py-4 text-right font-mono font-bold",
                            entry.amount >= 0
                              ? "text-zinc-900"
                              : "text-rose-600",
                          )}
                        >
                          {formatCurrency(entry.amount)}
                        </td>
                        <td className="px-4 py-4 text-center">
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border",
                              entry.status === "success"
                                ? "bg-emerald-50 text-emerald-700 border-emerald-100"
                                : entry.status === "pending"
                                  ? "bg-amber-50 text-amber-700 border-amber-100"
                                  : "bg-rose-50 text-rose-700 border-rose-100",
                            )}
                          >
                            {entry.status === "success"
                              ? "Sucesso"
                              : entry.status === "pending"
                                ? "Pendente"
                                : "Falha"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right text-zinc-400 text-[10px] font-bold uppercase tracking-widest">
                          {new Date(entry.createdAt).toLocaleDateString(
                            "pt-BR",
                          )}{" "}
                          {new Date(entry.createdAt).toLocaleTimeString(
                            "pt-BR",
                            { hour: "2-digit", minute: "2-digit" },
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "balances" && <DriverWalletsTab />}

        {activeTab === "store_balances" && <StoreBalancesTab />}
        {activeTab === "dre" && <DreTab />}
        {activeTab === "cash_reconciliation" && <CashReconciliationTab />}
        {activeTab === "acerto" && <AcertoInLoco />}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number | string;
  icon: any;
  color: string;
}) {
  const colorClasses: any = {
    blue: "text-blue-600 bg-blue-50 border-blue-100",
    orange: "text-orange-600 bg-orange-50 border-orange-100",
    green: "text-emerald-600 bg-emerald-50 border-emerald-100",
    red: "text-rose-600 bg-rose-50 border-rose-100",
  };

  return (
    <div className="bg-white p-5 rounded-xl shadow-sm ring-1 ring-zinc-950/5 flex items-center gap-4">
      <div className={cn("p-3 rounded-lg border", colorClasses[color])}>
        <Icon className="h-6 w-6" />
      </div>
      <div>
        <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
          {label}
        </p>
        <p className="text-2xl font-bold text-zinc-900 tracking-tight mt-1">
          {value}
        </p>
      </div>
    </div>
  );
}

function InfoBox({
  step,
  title,
  description,
  color,
}: {
  step: string;
  title: string;
  description: string;
  color: string;
}) {
  const borderColors: any = {
    orange: "border-orange-500",
    blue: "border-blue-500",
    green: "border-emerald-500",
  };

  return (
    <div
      className={cn(
        "bg-white p-6 rounded-xl shadow-sm ring-1 ring-zinc-950/5 border-t-4",
        borderColors[color],
      )}
    >
      <div className="flex items-center gap-3 mb-3">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-900 text-white text-[10px] font-bold">
          {step}
        </span>
        <h4 className="font-bold text-zinc-900 uppercase tracking-wider text-sm">
          {title}
        </h4>
      </div>
      <p className="text-xs text-zinc-500 leading-relaxed">{description}</p>
    </div>
  );
}

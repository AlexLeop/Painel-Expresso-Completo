import { logger } from "@/lib/logger";
import { useState, useEffect, useMemo, useCallback } from "react";
import { formatCurrency, cn } from "../lib/utils";
import {
  getCreditStats,
  getCreditLog,
  getCreditLogForWeek,
  getDailyEntriesForWeek,
  getDriverDayAggregation,
  getPendingCreditsForDate,
  addCreditLogEntry,
  markDailyEntryCredited,
  markDailyEntryFailed,
  pullEntriesFromSupabase,
  type CreditLogEntry,
} from "../services/entries-store";
import { getCompanyConfig } from "../services/company-config";
import { authFetch } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import CreditQueuePanel from "../components/CreditQueuePanel";
import AcertoInLoco from "../components/AcertoInLoco";
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
} from "lucide-react";

interface DriverBalance {
  id: string;
  name: string;
  balance: number | null;
  loading: boolean;
  error?: string;
}

export function Financeiro() {
  const { session } = useAuth();
  const user = session?.user;
  const companyId = user?.machine_empresa_id || user?.company_id || "";
  const companies = Array.isArray(user?.companies) ? user?.companies : [];
  const currentCompany = companies?.find(
    (c: any) => String(c.id) === String(companyId),
  );
  const companyName = currentCompany?.nome || "Empresa";
  const isAdmin =
    user?.role === "admin" ||
    user?.role === "master" ||
    user?.role === "administrador";

  const [activeTab, setActiveTab] = useState<
    "overview" | "queue" | "log" | "balances" | "acerto"
  >("acerto");
  const [creditLog, setCreditLog] = useState<CreditLogEntry[]>([]);
  const [driverBalances, setDriverBalances] = useState<DriverBalance[]>([]);
  const [loadingBalances, setLoadingBalances] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processingResults, setProcessingResults] = useState<string[]>([]);
  const [syncVersion, setSyncVersion] = useState(0);

  const loadDriverBalances = useCallback(async () => {
    if (!companyId) return;
    setLoadingBalances(true);
    try {
      // 1. Fetch active drivers for the company
      const resDrivers = await authFetch(
        `/api/db/company-drivers?company_id=${companyId}&active_only=0`,
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

      // 2. Fetch balances for each driver
      for (const driver of drivers) {
        try {
          const res = await authFetch(
            `/api/machine/credits/driver/balance?condutor_id=${driver.id}`,
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
    const day = now.getDay(); // 0 (Dom) a 6 (Sab)
    const diff = now.getDate() - day + (day === 0 ? -6 : 1); // Ajuste para segunda
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
    if (!companyId) return;

    await pullEntriesFromSupabase(companyId, weekPeriod.start, weekPeriod.end);

    const allDailies = getDailyEntriesForWeek(
      companyId,
      weekPeriod.start,
      weekPeriod.end,
    );
    const creditedEntries = allDailies.filter(
      (e) => e.creditStatus === "credited",
    );

    const logMap = new Map<string, CreditLogEntry>();
    for (const entry of creditedEntries) {
      const key = `${entry.driverId}_${entry.date}`;
      if (!logMap.has(key)) {
        logMap.set(key, {
          id: `auto_${key}`,
          date: entry.date,
          driverId: entry.driverId,
          driverName: entry.driverName,
          companyId: entry.companyId,
          companyName: companyName,
          amount: 0,
          breakdown: { diaria: 0, extras: 0, adiantamentos: 0 },
          status: "success",
          createdAt: entry.creditedAt || new Date().toISOString(),
          processedBy: "cron",
        });
      }
      const logEntry = logMap.get(key)!;
      logEntry.breakdown.diaria += entry.amount;
      logEntry.amount += entry.amount;
    }

    const oldLog = getCreditLogForWeek(
      companyId,
      weekPeriod.start,
      weekPeriod.end,
    );
    for (const entry of oldLog) {
      const key = `manual_${entry.driverId}_${entry.date}`;
      if (!logMap.has(key)) logMap.set(key, entry);
    }

    const log = Array.from(logMap.values()).sort((a, b) =>
      b.date.localeCompare(a.date),
    );
    setCreditLog(log);
    setSyncVersion((v) => v + 1);
  }, [companyId, weekPeriod, companyName]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const stats = useMemo(() => {
    if (!companyId) return { total: 0, pending: 0, credited: 0, failed: 0 };
    return getCreditStats(companyId, weekPeriod.start, weekPeriod.end);
  }, [companyId, weekPeriod, syncVersion]);

  const config = useMemo(() => {
    if (!companyId) return null;
    return getCompanyConfig(companyId, companyName);
  }, [companyId, companyName]);

  // Data de ontem para o botão rápido
  const yesterday = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().split("T")[0];
  }, []);

  const processCredits = async (targetDate?: string) => {
    if (!companyId || !config) return;
    setProcessing(true);
    setProcessingResults([]);

    try {
      const body: any = { company_id: companyId };
      if (targetDate) body.date = targetDate;

      const res = await authFetch("/api/cron/auto-credit", {
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
        setProcessingResults(lines);
      }
    } catch (err) {
      setProcessingResults(["Erro de conexão com o servidor"]);
    } finally {
      setProcessing(false);
      loadData();
    }
  };

  const tabs = [
    { key: "acerto", label: "Acerto In-Loco", icon: Calculator },
    { key: "overview", label: "Resumo", icon: Info },
    { key: "queue", label: "Fila de Créditos", icon: ListChecks },
    { key: "log", label: "Log de Créditos", icon: History },
    ...(isAdmin ? [{ key: "balances", label: "Saldos", icon: Wallet }] : []),
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
                                : "bg-rose-50 text-rose-700 border-rose-100",
                            )}
                          >
                            {entry.status === "success" ? "Sucesso" : "Falha"}
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

        {activeTab === "balances" && (
          <div className="bg-white rounded-xl shadow-sm ring-1 ring-zinc-950/5 overflow-hidden">
            <div className="p-5 border-b border-zinc-200 flex justify-between items-center bg-zinc-50/50">
              <div>
                <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider">
                  Saldos na Plataforma
                </h3>
                <p className="text-xs text-zinc-500 mt-1">
                  Saldos atualizados em tempo real na carteira da Machine.
                </p>
              </div>
              <button
                onClick={loadDriverBalances}
                disabled={loadingBalances}
                className="flex items-center gap-2 px-3 py-1.5 bg-white border border-zinc-200 text-zinc-700 rounded-lg hover:bg-zinc-50 text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
              >
                <RefreshCw
                  className={cn(
                    "h-3.5 w-3.5",
                    loadingBalances && "animate-spin",
                  )}
                />
                Atualizar
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left whitespace-nowrap text-sm">
                <thead className="bg-zinc-50/80 border-b border-zinc-200 text-zinc-500 text-[10px] font-bold uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-4">Motoboy</th>
                    <th className="px-6 py-4 text-right">
                      Saldo Atual (Machine)
                    </th>
                    <th className="px-6 py-4 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {driverBalances.length === 0 && !loadingBalances ? (
                    <tr>
                      <td
                        colSpan={3}
                        className="px-6 py-12 text-center text-zinc-400 text-sm"
                      >
                        Nenhum motoboy encontrado.
                      </td>
                    </tr>
                  ) : (
                    driverBalances.map((driver) => (
                      <tr
                        key={driver.id}
                        className="hover:bg-zinc-50/50 transition-colors"
                      >
                        <td className="px-6 py-4 font-bold text-zinc-900">
                          {driver.name}
                        </td>
                        <td className="px-6 py-4 text-right">
                          {driver.loading ? (
                            <span className="text-zinc-400 font-medium text-xs flex items-center justify-end gap-2">
                              <RefreshCw className="h-3 w-3 animate-spin" />{" "}
                              Carregando...
                            </span>
                          ) : driver.error ? (
                            <span className="text-rose-500 font-medium text-xs">
                              {driver.error}
                            </span>
                          ) : (
                            <span
                              className={cn(
                                "font-mono font-bold text-base",
                                (driver.balance || 0) >= 0
                                  ? "text-zinc-900"
                                  : "text-rose-600",
                              )}
                            >
                              {formatCurrency(driver.balance || 0)}
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-center">
                          {!driver.loading && !driver.error && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-100">
                              Sincronizado
                            </span>
                          )}
                          {driver.error && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-100">
                              Falha na Leitura
                            </span>
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

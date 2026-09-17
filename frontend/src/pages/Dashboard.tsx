import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  LayoutDashboard,
  TrendingUp,
  DollarSign,
  Truck,
  Bike,
  Store,
  Activity,
  RefreshCw,
  Info,
  CalendarDays,
  FileSpreadsheet,
  Wallet,
  CheckCircle2,
  ArrowUpRight,
  MapPin,
  Receipt,
  Award,
  Zap,
  ChevronRight,
  BarChart3,
  Clock,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { formatCurrency, cn } from "../lib/utils";
import { motion } from "framer-motion";
import { useAuth } from "../contexts/AuthContext";
import { useApiQuery } from "../lib/useApiQuery";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { Skeleton } from "../components/ui/Skeleton";

type RangeKey = "today" | "last7" | "month" | "all";
type ChartView = "revenue" | "rides";

function TooltipBadge({ label }: { label: string }) {
  return (
    <span
      className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-zinc-100 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-200 transition-colors cursor-help"
      title={label}
    >
      <Info className="h-3 w-3" />
    </span>
  );
}

function SegmentedControl({
  value,
  onChange,
}: {
  value: RangeKey;
  onChange: (next: RangeKey) => void;
}) {
  const items: Array<{ key: RangeKey; label: string }> = [
    { key: "today", label: "Hoje" },
    { key: "last7", label: "7 dias" },
    { key: "month", label: "Mês" },
    { key: "all", label: "Geral" },
  ];
  return (
    <div
      className="inline-flex items-center bg-zinc-100/80 p-1 rounded-xl border border-zinc-200/80 shadow-inner"
      role="group"
      aria-label="Filtro de período"
    >
      {items.map((it) => {
        const active = it.key === value;
        return (
          <button
            key={it.key}
            type="button"
            onClick={() => onChange(it.key)}
            className={cn(
              "h-8 px-3 rounded-lg text-[11px] font-bold tracking-wide transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]",
              active
                ? "bg-white text-zinc-900 shadow-sm font-extrabold"
                : "text-zinc-500 hover:text-zinc-800 hover:bg-white/50",
            )}
            aria-pressed={active}
          >
            {it.label}
          </button>
        );
      })}
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string | number;
  sub?: string;
  badge?: string;
  badgeType?: "success" | "warning" | "info" | "neutral";
  icon: React.ReactNode;
  iconBg: string;
  help?: string;
  live?: boolean;
}

function StatCard({
  title,
  value,
  sub,
  badge,
  badgeType = "neutral",
  icon,
  iconBg,
  help,
  live,
}: StatCardProps) {
  const badgeStyles = {
    success: "bg-emerald-50 text-emerald-700 border-emerald-200/60",
    warning: "bg-amber-50 text-amber-700 border-amber-200/60",
    info: "bg-blue-50 text-blue-700 border-blue-200/60",
    neutral: "bg-zinc-100 text-zinc-600 border-zinc-200/60",
  };

  return (
    <div className="relative overflow-hidden bg-white border border-zinc-200/80 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-zinc-300 transition-all duration-300 flex flex-col justify-between group">
      <div>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider truncate">
              {title}
            </span>
            {help && <TooltipBadge label={help} />}
          </div>
          <div
            className={cn(
              "h-9 w-9 rounded-xl flex items-center justify-center shadow-sm shrink-0 transition-transform group-hover:scale-105",
              iconBg,
            )}
          >
            {icon}
          </div>
        </div>

        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-black text-zinc-900 tracking-tight font-sans">
            {value}
          </span>
          {live && (
            <span className="relative flex h-2 w-2 mb-1">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-zinc-100 flex items-center justify-between gap-2">
        <span className="text-xs text-zinc-500 font-medium truncate">
          {sub || "Atualizado em tempo real"}
        </span>
        {badge && (
          <span
            className={cn(
              "text-[10px] font-bold px-2 py-0.5 rounded-md border shrink-0",
              badgeStyles[badgeType],
            )}
          >
            {badge}
          </span>
        )}
      </div>
    </div>
  );
}

export function Dashboard() {
  const { session } = useAuth();
  const user = session?.user;
  const [range, setRange] = useState<RangeKey>("last7");
  const [chartView, setChartView] = useState<ChartView>("revenue");

  const companyId =
    user?.machine_empresa_id || user?.company_id || "";

  const role = user?.role || "superadmin";
  const isSuperAdmin = role === "superadmin";
  const isOperador = role === "operador_admin" || role === "operador_staff";
  const isLojista = role === "lojista";

  // ─── Query Principal do Dashboard (Back-end Consolidado) ──────────────────
  const statsKey = `/api/v1/db/dashboard-stats?range=${range}${
    companyId ? `&company_id=${companyId}` : ""
  }`;

  const {
    data: statsData,
    isLoading: loadingStats,
    isValidating: validatingStats,
    refresh: refreshStats,
  } = useApiQuery<any>(statsKey, { refreshInterval: 20_000 });

  // ─── Query de Apoio de Lojas e Drivers (para cache local) ─────────────────
  const {
    data: companiesData,
    refresh: refreshCompanies,
  } = useApiQuery<any[]>("/api/v1/db/companies", { refreshInterval: 60_000 });

  const {
    data: driversData,
    refresh: refreshDrivers,
  } = useApiQuery<any[]>("/api/v1/db/company-drivers?active_only=1", {
    refreshInterval: 60_000,
  });

  const isLoading = loadingStats && !statsData;
  const isRefreshing = validatingStats && !isLoading;

  const handleRefresh = () => {
    refreshStats();
    refreshCompanies();
    refreshDrivers();
  };

  const lastUpdated = useMemo(() => {
    return new Date().toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statsData]);

  // ─── Métricas Consolidadas ───────────────────────────────────────────────
  const metrics = useMemo(() => {
    const totalOrders = statsData?.total_orders ?? 0;
    const completedOrders = statsData?.completed_orders ?? 0;
    const activeOrders = statsData?.active_orders ?? 0;
    const faturamentoTotal = statsData?.faturamento_total ?? 0;
    const averageTicket = statsData?.average_ticket ?? 0;
    const completionRate = statsData?.completion_rate ?? (completedOrders > 0 ? 100 : 0);

    const companiesList = Array.isArray(companiesData) ? companiesData : [];
    const driversList = Array.isArray(driversData) ? driversData : [];

    const activeStores =
      statsData?.active_stores ??
      companiesList.filter((c: any) => c.active !== false).length;
    const totalStores = statsData?.total_stores ?? companiesList.length;

    const activeDrivers =
      statsData?.active_drivers ??
      driversList.filter((d: any) => d.ativo !== false && d.active !== false).length;

    return {
      faturamentoTotal,
      completedOrders,
      activeOrders,
      totalOrders,
      averageTicket,
      completionRate,
      activeStores,
      totalStores,
      activeDrivers,
    };
  }, [statsData, companiesData, driversData]);

  // ─── Dados para o Gráfico ────────────────────────────────────────────────
  const chartData = useMemo(() => {
    if (statsData?.chart_data && Array.isArray(statsData.chart_data)) {
      return statsData.chart_data;
    }
    return [];
  }, [statsData]);

  // ─── Ranking de Lojas Parceiras ──────────────────────────────────────────
  const topStores = useMemo(() => {
    if (statsData?.top_stores && Array.isArray(statsData.top_stores) && statsData.top_stores.length > 0) {
      return statsData.top_stores;
    }
    // Fallback derivado das empresas cadastradas
    const list = Array.isArray(companiesData) ? companiesData : [];
    return list.slice(0, 6).map((c: any) => ({
      id: c.id,
      nome: c.nome || c.name || "Loja Parceira",
      corridas: 0,
      faturamento: 0,
      ticket_medio: 0,
      percentual: 0,
    }));
  }, [statsData, companiesData]);

  // ─── Radar de Entregas Recentes / Ativas ──────────────────────────────────
  const recentOrders = useMemo(() => {
    if (statsData?.recent_orders && Array.isArray(statsData.recent_orders)) {
      return statsData.recent_orders;
    }
    return [];
  }, [statsData]);

  // Totais resumidos do gráfico
  const chartSummary = useMemo(() => {
    if (chartData.length === 0) return { totalVal: 0, maxVal: 0, avgVal: 0 };
    const totalVal = chartData.reduce(
      (acc: number, item: any) =>
        acc + (chartView === "revenue" ? item.faturamento || 0 : item.corridas || 0),
      0,
    );
    const maxVal = Math.max(
      ...chartData.map((i: any) =>
        chartView === "revenue" ? i.faturamento || 0 : i.corridas || 0,
      ),
      0,
    );
    const avgVal = chartData.length > 0 ? totalVal / chartData.length : 0;
    return { totalVal, maxVal, avgVal };
  }, [chartData, chartView]);

  return (
    <div className="flex-1 space-y-6 pb-12">
      {/* ─── Header Principal ────────────────────────────────────────────── */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-zinc-200/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-black text-zinc-900 tracking-tight flex items-center gap-2">
              <LayoutDashboard className="h-6 w-6 text-[#E55C00]" />
              Dashboard
            </h1>
            <span
              className={cn(
                "px-2.5 py-0.5 rounded-full text-[11px] font-extrabold uppercase tracking-wider border shadow-xs",
                isSuperAdmin
                  ? "bg-orange-50 text-[#E55C00] border-orange-200"
                  : isOperador
                    ? "bg-indigo-50 text-indigo-700 border-indigo-200"
                    : "bg-emerald-50 text-emerald-700 border-emerald-200",
              )}
            >
              {isSuperAdmin
                ? "SuperAdmin Master"
                : isOperador
                  ? "Operação Logística"
                  : "Painel da Loja"}
            </span>
          </div>
          <p className="text-[13px] font-medium text-zinc-500 mt-1">
            Visão unificada em tempo real de faturamento, frotas, entregas e parceiros
          </p>
        </div>

        {/* Controles de Período e Sincronização */}
        <div className="flex flex-wrap items-center gap-2.5">
          <SegmentedControl value={range} onChange={setRange} />

          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 text-xs font-bold text-zinc-700 bg-white hover:bg-zinc-50 px-3.5 py-2 rounded-xl border border-zinc-200/80 shadow-xs transition-colors disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]"
            title="Atualizar dados agora"
          >
            <RefreshCw
              className={cn(
                "w-3.5 h-3.5 text-zinc-500",
                isRefreshing && "animate-spin text-[#E55C00]",
              )}
            />
            <span className="hidden sm:inline">
              {lastUpdated ? `Atualizado ${lastUpdated}` : "Sincronizar"}
            </span>
          </button>
        </div>
      </header>

      {/* ─── Grid de KPIs Principais ──────────────────────────────────────── */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, idx) => (
            <Skeleton key={idx} className="h-32 rounded-2xl" />
          ))}
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4"
        >
          <StatCard
            title="Faturamento"
            value={formatCurrency(metrics.faturamentoTotal)}
            sub={
              range === "today"
                ? "Receita de hoje"
                : range === "month"
                  ? "Receita do mês"
                  : "Volume no período"
            }
            badge="Receita"
            badgeType="success"
            icon={<DollarSign className="w-4 h-4 text-emerald-600" />}
            iconBg="bg-emerald-50 text-emerald-600 border border-emerald-100"
            help="Soma dos valores das corridas concluídas e movimentações financeiras"
          />

          <StatCard
            title="Entregas Concluídas"
            value={metrics.completedOrders}
            sub={`De ${metrics.totalOrders} solicitadas`}
            badge="Finalizadas"
            badgeType="info"
            icon={<CheckCircle2 className="w-4 h-4 text-blue-600" />}
            iconBg="bg-blue-50 text-blue-600 border border-blue-100"
            help="Quantidade de entregas com entrega finalizada no período"
          />

          <StatCard
            title="Em Andamento"
            value={metrics.activeOrders}
            sub="Corridas na rua agora"
            badge="Radar Ao Vivo"
            badgeType="warning"
            live={metrics.activeOrders > 0}
            icon={<Activity className="w-4 h-4 text-[#E55C00]" />}
            iconBg="bg-orange-50 text-[#E55C00] border border-orange-100"
            help="Entregas em trânsito, aceitas ou em despacho neste momento"
          />

          <StatCard
            title="Ticket Médio"
            value={formatCurrency(metrics.averageTicket)}
            sub="Média por entrega"
            badge="Desempenho"
            badgeType="neutral"
            icon={<Receipt className="w-4 h-4 text-violet-600" />}
            iconBg="bg-violet-50 text-violet-600 border border-violet-100"
            help="Faturamento total dividido pelo total de entregas concluídas"
          />

          <StatCard
            title="Taxa de Conclusão"
            value={`${metrics.completionRate}%`}
            sub="Eficiência operacional"
            badge="Sucesso"
            badgeType={metrics.completionRate >= 90 ? "success" : "warning"}
            icon={<TrendingUp className="w-4 h-4 text-teal-600" />}
            iconBg="bg-teal-50 text-teal-600 border border-teal-100"
            help="Percentual de corridas concluídas com êxito vs canceladas"
          />

          <StatCard
            title="Lojas & Frota"
            value={`${metrics.activeStores} / ${metrics.activeDrivers}`}
            sub="Lojas ativas · Motoboys"
            badge="Operação"
            badgeType="neutral"
            icon={<Store className="w-4 h-4 text-amber-600" />}
            iconBg="bg-amber-50 text-amber-600 border border-amber-100"
            help="Lojas parceiras ativas e motoboys cadastrados e disponíveis"
          />
        </motion.div>
      )}

      {/* ─── Atalhos de Ação Rápida ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          to="/corridas"
          className="group bg-white hover:bg-zinc-50/80 border border-zinc-200/80 hover:border-orange-300 rounded-2xl p-4 shadow-xs hover:shadow-sm transition-all flex items-center justify-between"
        >
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="h-10 w-10 rounded-xl bg-orange-50 border border-orange-100 text-[#E55C00] flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <MapPin className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-zinc-900 group-hover:text-[#E55C00] transition-colors truncate">
                Corridas & Despacho
              </h2>
              <p className="text-[12px] text-zinc-500 font-medium truncate">
                Acompanhamento e mapa ao vivo
              </p>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-zinc-400 group-hover:text-[#E55C00] group-hover:translate-x-0.5 transition-all shrink-0" />
        </Link>

        <Link
          to="/relatorios"
          className="group bg-white hover:bg-zinc-50/80 border border-zinc-200/80 hover:border-blue-300 rounded-2xl p-4 shadow-xs hover:shadow-sm transition-all flex items-center justify-between"
        >
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="h-10 w-10 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <FileSpreadsheet className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-zinc-900 group-hover:text-blue-600 transition-colors truncate">
                Relatórios & Fechamento
              </h2>
              <p className="text-[12px] text-zinc-500 font-medium truncate">
                Extratos semanais e produção
              </p>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-zinc-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all shrink-0" />
        </Link>

        <Link
          to="/escala"
          className="group bg-white hover:bg-zinc-50/80 border border-zinc-200/80 hover:border-emerald-300 rounded-2xl p-4 shadow-xs hover:shadow-sm transition-all flex items-center justify-between"
        >
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="h-10 w-10 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <CalendarDays className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-zinc-900 group-hover:text-emerald-600 transition-colors truncate">
                Escala de Motoboys
              </h2>
              <p className="text-[12px] text-zinc-500 font-medium truncate">
                Diárias, turnos e garantidos
              </p>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-zinc-400 group-hover:text-emerald-600 group-hover:translate-x-0.5 transition-all shrink-0" />
        </Link>

        <Link
          to="/financeiro"
          className="group bg-white hover:bg-zinc-50/80 border border-zinc-200/80 hover:border-violet-300 rounded-2xl p-4 shadow-xs hover:shadow-sm transition-all flex items-center justify-between"
        >
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="h-10 w-10 rounded-xl bg-violet-50 border border-violet-100 text-violet-600 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <Wallet className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-zinc-900 group-hover:text-violet-600 transition-colors truncate">
                Gestão Financeira
              </h2>
              <p className="text-[12px] text-zinc-500 font-medium truncate">
                Saldos, cobranças e repasses
              </p>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-zinc-400 group-hover:text-violet-600 group-hover:translate-x-0.5 transition-all shrink-0" />
        </Link>
      </div>

      {/* ─── Layout de Conteúdo: Gráficos + Ranking vs Radar Ao Vivo ─────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Coluna Esquerda: Gráfico de Evolução e Ranking de Lojas (2 colunas) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Card Gráfico de Evolução */}
          <div className="bg-white border border-zinc-200/80 rounded-2xl shadow-sm p-5 sm:p-6 flex flex-col">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-100">
              <div>
                <h2 className="text-sm font-black text-zinc-900 flex items-center gap-2 uppercase tracking-wide">
                  <BarChart3 className="w-4 h-4 text-[#E55C00]" />
                  Evolução da Operação
                </h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Desempenho diário de faturamento e volume no período selecionado
                </p>
              </div>

              {/* Seletor Faturamento vs Volume */}
              <div className="inline-flex items-center bg-zinc-100 p-1 rounded-xl border border-zinc-200/60 self-start sm:self-auto">
                <button
                  type="button"
                  onClick={() => setChartView("revenue")}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-bold transition-all",
                    chartView === "revenue"
                      ? "bg-white text-zinc-900 shadow-xs font-extrabold"
                      : "text-zinc-500 hover:text-zinc-800",
                  )}
                >
                  Faturamento (R$)
                </button>
                <button
                  type="button"
                  onClick={() => setChartView("rides")}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-bold transition-all",
                    chartView === "rides"
                      ? "bg-white text-zinc-900 shadow-xs font-extrabold"
                      : "text-zinc-500 hover:text-zinc-800",
                  )}
                >
                  Corridas (Qtd)
                </button>
              </div>
            </div>

            {/* Gráfico Recharts */}
            <div className="w-full pt-4 min-h-[290px]">
              <ErrorBoundary>
                {chartData.length === 0 ? (
                  <div className="h-[280px] flex flex-col items-center justify-center text-zinc-400 text-xs">
                    <BarChart3 className="w-8 h-8 text-zinc-300 mb-2 stroke-[1.5]" />
                    Nenhum dado registrado para o período selecionado.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart
                      data={chartData}
                      margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient
                          id="colorRevenue"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="5%"
                            stopColor="#E55C00"
                            stopOpacity={0.25}
                          />
                          <stop
                            offset="95%"
                            stopColor="#E55C00"
                            stopOpacity={0}
                          />
                        </linearGradient>
                        <linearGradient
                          id="colorRides"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="5%"
                            stopColor="#3B82F6"
                            stopOpacity={0.25}
                          />
                          <stop
                            offset="95%"
                            stopColor="#3B82F6"
                            stopOpacity={0}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="#f4f4f5"
                      />
                      <XAxis
                        dataKey="time"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#a1a1aa", fontSize: 11, fontWeight: 600 }}
                        dy={8}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#a1a1aa", fontSize: 11, fontWeight: 600 }}
                        dx={-4}
                        tickFormatter={(val) =>
                          chartView === "revenue"
                            ? `R$ ${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}`
                            : `${val}`
                        }
                      />
                      <Tooltip
                        contentStyle={{
                          borderRadius: "14px",
                          border: "1px solid #e4e4e7",
                          boxShadow:
                            "0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04)",
                          fontSize: "12px",
                          padding: "10px 14px",
                        }}
                        labelStyle={{
                          color: "#09090b",
                          fontWeight: 800,
                          marginBottom: "4px",
                        }}
                        formatter={(val: any) => [
                          chartView === "revenue"
                            ? formatCurrency(Number(val) || 0)
                            : `${val} corridas`,
                          chartView === "revenue" ? "Faturamento" : "Volume",
                        ]}
                      />
                      <Area
                        type="monotone"
                        dataKey={chartView === "revenue" ? "faturamento" : "corridas"}
                        stroke={chartView === "revenue" ? "#E55C00" : "#3B82F6"}
                        strokeWidth={2.5}
                        fillOpacity={1}
                        fill={
                          chartView === "revenue"
                            ? "url(#colorRevenue)"
                            : "url(#colorRides)"
                        }
                        activeDot={{
                          r: 6,
                          fill: chartView === "revenue" ? "#E55C00" : "#3B82F6",
                          stroke: "#ffffff",
                          strokeWidth: 2,
                        }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </ErrorBoundary>
            </div>

            {/* Rodapé Resumo do Gráfico */}
            <div className="mt-4 pt-3 border-t border-zinc-100 grid grid-cols-3 gap-2 text-center">
              <div className="p-2 rounded-xl bg-zinc-50/80">
                <span className="text-[10px] uppercase font-bold text-zinc-400 block">
                  Total Acumulado
                </span>
                <span className="text-sm font-black text-zinc-900">
                  {chartView === "revenue"
                    ? formatCurrency(chartSummary.totalVal)
                    : `${chartSummary.totalVal} corridas`}
                </span>
              </div>
              <div className="p-2 rounded-xl bg-zinc-50/80">
                <span className="text-[10px] uppercase font-bold text-zinc-400 block">
                  Pico do Período
                </span>
                <span className="text-sm font-black text-zinc-900">
                  {chartView === "revenue"
                    ? formatCurrency(chartSummary.maxVal)
                    : `${chartSummary.maxVal} corridas`}
                </span>
              </div>
              <div className="p-2 rounded-xl bg-zinc-50/80">
                <span className="text-[10px] uppercase font-bold text-zinc-400 block">
                  Média Diária
                </span>
                <span className="text-sm font-black text-zinc-900">
                  {chartView === "revenue"
                    ? formatCurrency(chartSummary.avgVal)
                    : `${chartSummary.avgVal.toFixed(1)} corridas`}
                </span>
              </div>
            </div>
          </div>

          {/* Card Ranking das Lojas Parceiras */}
          <div className="bg-white border border-zinc-200/80 rounded-2xl shadow-sm p-5 sm:p-6">
            <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
              <div>
                <h2 className="text-sm font-black text-zinc-900 flex items-center gap-2 uppercase tracking-wide">
                  <Award className="w-4 h-4 text-[#E55C00]" />
                  Ranking de Lojas Parceiras
                </h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Lojas com maior volume e faturamento na operação
                </p>
              </div>
              <Link
                to="/empresas"
                className="text-xs font-bold text-[#E55C00] hover:underline flex items-center gap-1"
              >
                Ver todas ({metrics.totalStores})
                <ChevronRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="mt-4 divide-y divide-zinc-100">
              {topStores.length === 0 ? (
                <div className="py-8 text-center text-xs text-zinc-400">
                  Nenhuma loja parceira com dados registrados neste período.
                </div>
              ) : (
                topStores.map((store: any, idx: number) => {
                  const medal =
                    idx === 0
                      ? "🥇"
                      : idx === 1
                        ? "🥈"
                        : idx === 2
                          ? "🥉"
                          : `${idx + 1}º`;
                  return (
                    <div
                      key={store.id || idx}
                      className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 group hover:bg-zinc-50/60 px-2 rounded-xl transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="w-6 text-center text-xs font-black text-zinc-600 shrink-0">
                          {medal}
                        </span>
                        <div className="h-9 w-9 rounded-xl bg-orange-50/80 border border-orange-100 flex items-center justify-center text-[#E55C00] font-black text-xs shrink-0">
                          <Store className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-bold text-zinc-900 truncate">
                            {store.nome}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-zinc-400">
                            <span>{store.corridas || 0} entregas</span>
                            <span>•</span>
                            <span>
                              Ticket: {formatCurrency(store.ticket_medio || 0)}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 self-end sm:self-center shrink-0">
                        <div className="w-24 sm:w-32 bg-zinc-100 h-2 rounded-full overflow-hidden hidden md:block">
                          <div
                            className="bg-[#E55C00] h-full rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(store.percentual || 15, 100)}%` }}
                          />
                        </div>
                        <div className="text-right">
                          <span className="text-sm font-black text-zinc-900 block font-sans">
                            {formatCurrency(store.faturamento || 0)}
                          </span>
                          <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                            {store.percentual || 0}% do topo
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Coluna Direita: Radar de Entregas em Tempo Real (1 coluna) */}
        <div className="space-y-6">
          {/* Radar Ao Vivo */}
          <div className="bg-[#0e0e10] border border-[#1e1e24] text-white rounded-2xl shadow-xl flex flex-col overflow-hidden relative">
            <div className="absolute top-0 right-0 p-24 bg-[#E55C00]/15 blur-[60px] rounded-full pointer-events-none" />

            {/* Cabeçalho do Radar */}
            <div className="p-5 border-b border-zinc-800/80 flex items-center justify-between relative z-10 bg-[#0e0e10]/80 backdrop-blur-md">
              <div>
                <h2 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
                  Radar em Tempo Real
                </h2>
                <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-bold mt-0.5">
                  Fluxo de Entregas & Despacho
                </p>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                {metrics.activeOrders} ativas
              </span>
            </div>

            {/* Lista de Entregas do Radar */}
            <div className="p-4 overflow-y-auto max-h-[480px] space-y-2.5 relative z-10">
              {recentOrders.length === 0 ? (
                <div className="py-12 text-center text-xs text-zinc-500">
                  <Truck className="w-8 h-8 text-zinc-700 mx-auto mb-2 opacity-50" />
                  Nenhuma entrega ativa no momento.
                </div>
              ) : (
                recentOrders.map((ride: any) => {
                  const isTransit =
                    ride.status === "STARTED" ||
                    ride.status === "ARRIVED" ||
                    ride.status === 1;
                  const isDone =
                    ride.status === "COMPLETED" || ride.status === 2;
                  const isCanceled =
                    ride.status === "CANCELED" ||
                    ride.status === "CANCELED_IN_TRANSIT";

                  return (
                    <div
                      key={ride.id}
                      className="p-3 bg-white/[0.03] hover:bg-white/[0.07] border border-white/5 hover:border-white/10 rounded-xl transition-colors flex items-start justify-between gap-3 group"
                    >
                      <div className="flex items-start gap-2.5 min-w-0">
                        <span
                          className={cn(
                            "mt-1.5 h-2 w-2 rounded-full shrink-0",
                            isTransit
                              ? "bg-blue-400 ring-4 ring-blue-400/20 animate-pulse"
                              : isDone
                                ? "bg-emerald-400 ring-4 ring-emerald-400/20"
                                : isCanceled
                                  ? "bg-rose-400 ring-4 ring-rose-400/20"
                                  : "bg-amber-400 ring-4 ring-amber-400/20",
                          )}
                        />
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-zinc-100 truncate group-hover:text-white transition-colors">
                            {ride.motoboy || "Aguardando motoboy"}
                          </p>
                          <div className="flex items-center gap-1.5 text-[11px] text-zinc-400 mt-0.5 truncate">
                            <Store className="w-3 h-3 text-[#E55C00] shrink-0" />
                            <span className="truncate">{ride.empresa}</span>
                          </div>
                          <div className="flex items-center gap-2 mt-1 font-mono text-[10px] text-zinc-500">
                            <span>{ride.id}</span>
                            <span>•</span>
                            <span>{ride.time}</span>
                          </div>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <span
                          className={cn(
                            "text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border font-mono",
                            isTransit
                              ? "text-blue-400 border-blue-400/30 bg-blue-400/10"
                              : isDone
                                ? "text-emerald-400 border-emerald-400/30 bg-emerald-400/10"
                                : isCanceled
                                  ? "text-rose-400 border-rose-400/30 bg-rose-400/10"
                                  : "text-amber-400 border-amber-400/30 bg-amber-400/10",
                          )}
                        >
                          {ride.status_label || ride.status}
                        </span>
                        {ride.valor > 0 && (
                          <p className="text-xs font-bold text-zinc-200 mt-2 font-mono">
                            {formatCurrency(ride.valor)}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Rodapé do Radar com Link para Corridas */}
            <div className="p-3.5 border-t border-zinc-800/80 bg-zinc-950 text-center relative z-10">
              <Link
                to="/corridas"
                className="text-xs font-bold text-[#E55C00] hover:text-orange-400 flex items-center justify-center gap-1.5 transition-colors"
              >
                Abrir Central de Corridas & Mapa ao Vivo
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Card Saúde da Operação */}
          <div className="bg-white border border-zinc-200/80 rounded-2xl shadow-sm p-5 space-y-4">
            <h2 className="text-xs font-black text-zinc-900 uppercase tracking-wide flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#E55C00]" />
              Saúde da Operação
            </h2>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs font-bold mb-1">
                  <span className="text-zinc-600">Taxa de Sucesso</span>
                  <span className="text-emerald-600">{metrics.completionRate}%</span>
                </div>
                <div className="w-full bg-zinc-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${metrics.completionRate}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-bold mb-1">
                  <span className="text-zinc-600">Disponibilidade de Frota</span>
                  <span className="text-blue-600">
                    {metrics.activeDrivers} motoboys ativos
                  </span>
                </div>
                <div className="w-full bg-zinc-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-blue-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${Math.min((metrics.activeDrivers / (metrics.activeDrivers || 1)) * 100, 100)}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-bold mb-1">
                  <span className="text-zinc-600">Lojas em Atendimento</span>
                  <span className="text-[#E55C00]">
                    {metrics.activeStores} ativas
                  </span>
                </div>
                <div className="w-full bg-zinc-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-[#E55C00] h-full rounded-full transition-all duration-500"
                    style={{ width: `${metrics.totalStores > 0 ? (metrics.activeStores / metrics.totalStores) * 100 : 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;

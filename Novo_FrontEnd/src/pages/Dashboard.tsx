import { useMemo, useState, useEffect } from "react";
import { getSession } from "../lib/api";
import { useApiQuery } from "../lib/useApiQuery";
import {
  Users,
  Truck,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  MapPin,
  Activity,
  LayoutDashboard,
  Loader2,
  RefreshCw,
  Info,
  CalendarDays,
  FileSpreadsheet,
  ChevronDown,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { formatCurrency, cn } from "../lib/utils";
import { motion } from "framer-motion";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

type RangeKey = "today" | "last7" | "month";
type LayoutMode = "v2" | "classic";

function formatDateISO(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDaysISO(dateISO: string, delta: number) {
  const [y, m, d] = dateISO.split("-").map(Number);
  const dt = new Date(y, (m || 1) - 1, d || 1);
  dt.setDate(dt.getDate() + delta);
  return formatDateISO(dt);
}

function buildISODateRange(startISO: string, endISO: string) {
  const out: string[] = [];
  let cur = startISO;
  while (cur <= endISO) {
    out.push(cur);
    cur = addDaysISO(cur, 1);
    if (out.length > 400) break;
  }
  return out;
}

function TooltipBadge({ label }: { label: string }) {
  return (
    <span
      className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-zinc-100 text-zinc-500 hover:text-zinc-800 hover:bg-zinc-200 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]"
      tabIndex={0}
      role="img"
      aria-label={label}
      title={label}
    >
      <Info className="h-3.5 w-3.5" />
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
  ];
  return (
    <div
      className="inline-flex items-center bg-white border border-zinc-200/80 rounded-xl p-1 shadow-sm"
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
              "h-9 px-3 rounded-lg text-[11px] font-extrabold uppercase tracking-widest transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]",
              active
                ? "bg-[#0a0a0a] text-white shadow-[0_8px_20px_-12px_rgba(0,0,0,0.45)]"
                : "text-zinc-600 hover:bg-zinc-50",
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

export function Dashboard() {
  const [range, setRange] = useState<RangeKey>("last7");
  const [layoutMode, setLayoutMode] = useState<LayoutMode>(() => {
    try {
      const v = localStorage.getItem("nevesgo:dashboardLayout");
      return v === "classic" ? "classic" : "v2";
    } catch {
      return "v2";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("nevesgo:dashboardLayout", layoutMode);
    } catch {
      return;
    }
  }, [layoutMode]);

  const session = getSession();
  const companyId = session?.user?.machine_empresa_id || session?.user?.company_id || "";

  const { startISO, endISO } = useMemo(() => {
    const today = formatDateISO(new Date());
    if (range === "today") return { startISO: today, endISO: today };
    if (range === "month") {
      const now = new Date();
      return {
        startISO: formatDateISO(new Date(now.getFullYear(), now.getMonth(), 1)),
        endISO: today,
      };
    }
    return { startISO: addDaysISO(today, -6), endISO: today };
  }, [range]);

  // ─── Queries SWR (com cache compartilhado entre páginas) ──────────────────
  const entriesKey = companyId
    ? `/api/db/entries?company_id=${companyId}&start=${startISO}&end=${endISO}`
    : null;
  const driversKey = companyId
    ? `/api/db/company-drivers?company_id=${companyId}`
    : null;
  const ridesKey = companyId
    ? `/api/machine/rides?empresa_id=${companyId}&limite=20&status_solicitacao=D`
    : null;

  const {
    data: entriesRaw,
    isLoading: loadingEntries,
    isValidating: validatingEntries,
    error: errorEntries,
    refresh: refreshEntries,
  } = useApiQuery<any[]>(entriesKey, { refreshInterval: 30_000 });
  const {
    data: driversRaw,
    isLoading: loadingDrivers,
    refresh: refreshDrivers,
  } = useApiQuery<any[]>(driversKey, { refreshInterval: 60_000 });
  const {
    data: ridesRaw,
    isLoading: loadingRides,
    isValidating: validatingRides,
    refresh: refreshRides,
  } = useApiQuery<any>(ridesKey, { refreshInterval: 30_000 });

  const isLoading = loadingEntries || loadingDrivers || loadingRides;
  const isRefreshing = (validatingEntries || validatingRides) && !isLoading;
  const error = errorEntries ?? null;

  const lastUpdated = useMemo(() => {
    if (isLoading) return "";
    return new Date().toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, validatingEntries, validatingRides]);

  const handleRefresh = () => {
    refreshEntries();
    refreshDrivers();
    refreshRides();
  };

  // ─── Derivações dos dados ─────────────────────────────────────────────────
  const entries: any[] = Array.isArray(entriesRaw) ? entriesRaw : [];
  const drivers: any[] = Array.isArray(driversRaw) ? driversRaw : [];

  const machineRides: any[] = useMemo(() => {
    if (!ridesRaw) return [];
    if (ridesRaw.response && Array.isArray(ridesRaw.response))
      return ridesRaw.response;
    if (ridesRaw.rides && Array.isArray(ridesRaw.rides)) return ridesRaw.rides;
    if (Array.isArray(ridesRaw)) return ridesRaw;
    return [];
  }, [ridesRaw]);

  const data = useMemo(() => {
    const dailyMap: Record<string, number> = {};
    entries.forEach((e: any) => {
      const day = e.date ? e.date.slice(0, 10) : "";
      if (day) {
        const val = Number(e.amount) || 0;
        if (e.type === "diaria" || e.type === "extra") {
          dailyMap[day] = (dailyMap[day] || 0) + val;
        } else if (e.type === "adiantamento") {
          dailyMap[day] = (dailyMap[day] || 0) - val;
        }
      }
    });
    const rangeDays = buildISODateRange(startISO, endISO);
    return rangeDays.map((key) => ({
      time: key.slice(5),
      faturamento: dailyMap[key] || 0,
    }));
  }, [entries, startISO, endISO]);

  const stats = useMemo(() => {
    const faturamento = entries.reduce((acc: number, e: any) => {
      if (e.type === "diaria" || e.type === "extra")
        return acc + (Number(e.amount) || 0);
      if (e.type === "adiantamento") return acc - (Number(e.amount) || 0);
      return acc;
    }, 0);
    return {
      corridasHoje: machineRides.length,
      motoboysAtivos: drivers.filter(
        (d: any) => d.ativo !== false && d.status !== "inativo",
      ).length,
      faturamento,
      garantidas: entries.filter((e: any) => e.type === "diaria").length,
    };
  }, [entries, drivers, machineRides]);

  const recentRides = useMemo(() => {
    if (machineRides.length > 0) {
      return machineRides.slice(0, 8).map((r: any) => ({
        id: `#${r.id?.toString() || "???"}`,
        motoboy: r.motoboy?.nome || r.nome_condutor || "Aguardando condutor...",
        empresa: r.endereco_partida || r.empresa || "Entrega Expressa",
        status:
          r.status === 1
            ? "Em andamento"
            : r.status === 2
              ? "Finalizada"
              : "Em trânsito",
        time: r.data_hora_solicitacao
          ? new Date(r.data_hora_solicitacao).toLocaleTimeString("pt-BR", {
              hour: "2-digit",
              minute: "2-digit",
            })
          : "Agora",
      }));
    }
    return entries.slice(0, 5).map((e: any) => ({
      id: `#${e.id?.toString().slice(-6) || "???"}`,
      motoboy: e.driverName || "Sem motorista",
      empresa: e.description || "Lançamento",
      status:
        e.type === "diaria"
          ? "Diária"
          : e.type === "adiantamento"
            ? "Adiantamento"
            : e.type || "Lançamento",
      time: e.date || "recente",
    }));
  }, [machineRides, entries]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-zinc-200/80">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight flex items-center gap-2">
            <LayoutDashboard className="h-5 w-5 text-[#E55C00]" />
            Dashboard
          </h1>
          <p className="text-[13px] font-medium text-zinc-500 mt-1 max-w-xl">
            Visão rápida da operação, desempenho e atalhos para ações do dia
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <SegmentedControl value={range} onChange={setRange} />
          <button
            type="button"
            onClick={() =>
              setLayoutMode((v) => (v === "v2" ? "classic" : "v2"))
            }
            className="hidden sm:flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600 bg-white hover:bg-zinc-50 px-3 py-2 rounded-xl border border-zinc-200/80 shadow-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]"
            aria-label="Alternar layout do dashboard"
            title={
              layoutMode === "v2"
                ? "Usando Layout novo"
                : "Usando Layout clássico"
            }
          >
            <span
              className={cn(
                "inline-flex h-2 w-2 rounded-full",
                layoutMode === "v2" ? "bg-[#E55C00]" : "bg-zinc-400",
              )}
            />
            {layoutMode === "v2" ? "Layout novo" : "Clássico"}
            <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />
          </button>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-zinc-600 bg-white hover:bg-zinc-50 px-3 py-2 rounded-xl border border-zinc-200/80 shadow-sm disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]"
            title="Sincronizar agora"
            aria-label="Sincronizar agora"
          >
            <RefreshCw
              className={cn(
                "w-3.5 h-3.5 text-zinc-500",
                isRefreshing && "animate-spin",
              )}
            />
            {lastUpdated ? `Atualizado ${lastUpdated}` : "Sincronizando..."}
          </button>
        </div>
      </header>

      {error && (
        <div
          className="bg-rose-50 border border-rose-200/70 rounded-2xl px-4 py-3 text-rose-700 text-[13px] font-semibold flex items-start gap-3"
          role="alert"
        >
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-rose-100 text-rose-700 font-black">
            !
          </span>
          <div className="min-w-0">
            <div className="font-extrabold">Falha ao sincronizar</div>
            <div className="text-rose-700/80 font-medium truncate">{error}</div>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6"
      >
        <StatCard
          title="Entregas Ativas"
          value={isLoading ? "..." : stats.corridasHoje}
          help="Quantidade de entregas com status 'D' na Machine (em andamento)."
          change="Radar Machine"
          trend="neutral"
          icon={<Truck className="w-4 h-4 text-[#E55C00]" />}
        />
        <StatCard
          title="Motoboys Ativos"
          value={isLoading ? "..." : stats.motoboysAtivos}
          help="Motoboys vinculados à empresa (ativos no cadastro)."
          change="Cadastro"
          trend="neutral"
          icon={<Users className="w-4 h-4 text-[#E55C00]" />}
        />
        <StatCard
          title={
            range === "today"
              ? "Movimento do Dia"
              : range === "last7"
                ? "Movimento (7 dias)"
                : "Movimento do Mês"
          }
          value={isLoading ? "..." : formatCurrency(stats.faturamento)}
          help="Saldo calculado por lançamentos: diária + extra - adiantamento."
          change="Financeiro"
          trend="neutral"
          icon={<ArrowUpRight className="w-4 h-4 text-[#E55C00]" />}
        />
        <StatCard
          title="Diárias / Garantidos"
          value={isLoading ? "..." : stats.garantidas}
          help="Quantidade de lançamentos do tipo 'diária' no período."
          change="Lançamentos"
          trend="neutral"
          icon={<Clock className="w-4 h-4 text-[#E55C00]" />}
        />
      </motion.div>

      {layoutMode === "v2" && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6"
        >
          <a
            href="/corridas"
            className="group bg-white border border-zinc-200/80 rounded-2xl shadow-sm p-5 hover:border-zinc-300 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]"
            aria-label="Ir para Corridas"
          >
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-extrabold uppercase tracking-widest text-zinc-500">
                Ação rápida
              </div>
              <div className="h-9 w-9 rounded-xl bg-[#0a0a0a] text-white flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow">
                <MapPin className="h-4 w-4 text-[#E55C00]" />
              </div>
            </div>
            <div className="mt-5">
              <div className="text-base font-extrabold text-zinc-900 tracking-tight">
                Corridas
              </div>
              <div className="text-[13px] font-medium text-zinc-500 mt-1">
                Acompanhar entregas e mapa em tempo real
              </div>
            </div>
          </a>
          <a
            href="/relatorios"
            className="group bg-white border border-zinc-200/80 rounded-2xl shadow-sm p-5 hover:border-zinc-300 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]"
            aria-label="Ir para Relatórios"
          >
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-extrabold uppercase tracking-widest text-zinc-500">
                Ação rápida
              </div>
              <div className="h-9 w-9 rounded-xl bg-[#0a0a0a] text-white flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow">
                <FileSpreadsheet className="h-4 w-4 text-[#E55C00]" />
              </div>
            </div>
            <div className="mt-5">
              <div className="text-base font-extrabold text-zinc-900 tracking-tight">
                Relatórios
              </div>
              <div className="text-[13px] font-medium text-zinc-500 mt-1">
                Fechamento, garantidos e produção por semana
              </div>
            </div>
          </a>
          <a
            href="/escala"
            className="group bg-white border border-zinc-200/80 rounded-2xl shadow-sm p-5 hover:border-zinc-300 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E55C00]"
            aria-label="Ir para Escala"
          >
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-extrabold uppercase tracking-widest text-zinc-500">
                Ação rápida
              </div>
              <div className="h-9 w-9 rounded-xl bg-[#0a0a0a] text-white flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow">
                <CalendarDays className="h-4 w-4 text-[#E55C00]" />
              </div>
            </div>
            <div className="mt-5">
              <div className="text-base font-extrabold text-zinc-900 tracking-tight">
                Escala
              </div>
              <div className="text-[13px] font-medium text-zinc-500 mt-1">
                Definir garantido/diária por dia e turnos
              </div>
            </div>
          </a>
        </motion.div>
      )}

      {/* Main Content Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="lg:col-span-2 space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white border border-zinc-200/80 rounded-2xl shadow-sm p-6 flex flex-col min-w-0"
          >
            <div className="flex items-center justify-between pb-4 border-b border-zinc-100 mb-6">
              <div>
                <h3 className="text-sm font-bold text-zinc-800 flex items-center gap-2 uppercase tracking-wide">
                  <Activity className="w-4 h-4 text-[#E55C00]" />
                  Evolução (Período)
                </h3>
                <p className="text-xs text-zinc-400 mt-1">
                  Volume por dia no período selecionado
                </p>
              </div>
              <div className="text-right">
                <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider block mb-0.5">
                  Total do Período
                </span>
                <span className="text-xl font-black text-zinc-900">
                  {new Intl.NumberFormat("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                  }).format(
                    data.reduce((acc, curr) => acc + curr.faturamento, 0),
                  )}
                </span>
              </div>
            </div>
            <div className="w-full min-w-0">
              <ResponsiveContainer width="99%" height={280}>
                <AreaChart
                  data={data}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id="colorCorridas"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="5%"
                        stopColor="#E55C00"
                        stopOpacity={0.18}
                      />
                      <stop offset="95%" stopColor="#E55C00" stopOpacity={0} />
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
                    dy={15}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#a1a1aa", fontSize: 11, fontWeight: 600 }}
                    dx={-10}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: "12px",
                      border: "1px solid #e4e4e7",
                      boxShadow:
                        "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
                      fontFamily: "var(--font-sans)",
                      fontSize: "13px",
                      padding: "12px 16px",
                    }}
                    labelStyle={{
                      color: "#09090b",
                      fontWeight: 800,
                      marginBottom: "6px",
                    }}
                    itemStyle={{ color: "#4f46e5", fontWeight: 600 }}
                    cursor={{
                      stroke: "#e4e4e7",
                      strokeWidth: 1,
                      strokeDasharray: "4 4",
                    }}
                    formatter={(value: number) =>
                      new Intl.NumberFormat("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                      }).format(value)
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="faturamento"
                    stroke="#E55C00"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorCorridas)"
                    activeDot={{
                      r: 6,
                      fill: "#E55C00",
                      stroke: "#FFE7D6",
                      strokeWidth: 3,
                    }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        </div>

        {/* Live feed */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-[#0a0a0a] border border-[#1a1a1a] text-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] flex flex-col overflow-hidden relative"
        >
          <div className="absolute top-0 right-0 p-32 bg-[#E55C00]/10 blur-[80px] rounded-full pointer-events-none" />
          <div className="p-5 border-b border-[#1a1a1a] flex items-center justify-between relative z-10 bg-[#0a0a0a]/50 backdrop-blur-md">
            <div>
              <h3 className="text-[15px] font-bold tracking-tight text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-500 animate-pulse" />
                Radar de Entregas Ativas
              </h3>
              <p className="text-[10px] text-zinc-400 mt-1 uppercase tracking-widest font-bold">
                Monitoramento Machine em Tempo Real
              </p>
            </div>
          </div>
          <div className="p-5 overflow-y-auto flex-1 relative z-10 hide-scrollbar max-h-[400px]">
            <div className="space-y-2">
              {recentRides.length === 0 && (
                <div className="text-center py-8 text-xs text-zinc-500">
                  Nenhuma entrega ativa encontrada no momento.
                </div>
              )}
              {recentRides.map((ride) => (
                <div
                  key={ride.id}
                  className="flex items-start gap-4 p-3 hover:bg-[#1a1a1a] rounded-xl transition-colors cursor-pointer border border-transparent hover:border-white/5 group bg-white/[0.02]"
                >
                  <div
                    className={cn(
                      "mt-1.5 w-2 h-2 rounded-full ring-[3px] shrink-0 shadow-sm transition-all",
                      ride.status === "Em trânsito"
                        ? "bg-blue-400 ring-blue-400/20 shadow-blue-500/20 animate-pulse"
                        : ride.status === "Finalizada"
                          ? "bg-emerald-400 ring-emerald-400/20 shadow-emerald-500/20"
                          : "bg-amber-400 ring-amber-400/20 shadow-amber-500/20 animate-pulse",
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-bold text-zinc-100 truncate group-hover:text-white transition-colors">
                      {ride.motoboy}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] font-mono font-bold text-indigo-400">
                        {ride.id}
                      </span>
                      <span className="w-1 h-1 rounded-full bg-zinc-700"></span>
                      <span
                        className="text-[11px] font-medium text-zinc-400 truncate max-w-[140px]"
                        title={ride.empresa}
                      >
                        {ride.empresa}
                      </span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <span
                      className={cn(
                        "text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border font-mono",
                        ride.status === "Em trânsito"
                          ? "text-blue-400 border-blue-400/30 bg-blue-400/10"
                          : ride.status === "Finalizada"
                            ? "text-emerald-400 border-emerald-400/30 bg-emerald-400/10"
                            : "text-amber-400 border-amber-400/30 bg-amber-400/10",
                      )}
                    >
                      {ride.status}
                    </span>
                    <p className="text-[10px] font-mono text-zinc-500 mt-2 flex justify-end items-center gap-1 group-hover:text-zinc-400 transition-colors">
                      {ride.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

function StatCard({ title, value, change, trend, icon, help }: any) {
  return (
    <motion.div
      variants={itemVariants}
      className="glass-panel p-6 flex flex-col relative overflow-hidden group hover:border-zinc-300 transition-all duration-300 bg-white border border-zinc-200/80 rounded-2xl shadow-sm"
    >
      <div className="flex justify-between items-start z-10 relative">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest truncate">
            {title}
          </h3>
          {help ? <TooltipBadge label={help} /> : null}
        </div>
        <div className="p-2 bg-zinc-50 border border-zinc-100 rounded-xl text-zinc-400 group-hover:text-zinc-900 group-hover:shadow-sm transition-all">
          {icon}
        </div>
      </div>
      <div className="mt-6 flex items-end justify-between z-10 relative bg-transparent">
        <p className="text-2xl font-black text-zinc-900 tracking-tight font-sans leading-none">
          {value}
        </p>
        <div
          className={cn(
            "flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg shadow-[0_1px_2px_rgba(0,0,0,0.05)] font-mono",
            trend === "up"
              ? "text-emerald-700 bg-emerald-50 border border-emerald-200/60"
              : trend === "down"
                ? "text-rose-700 bg-rose-50 border border-rose-200/60"
                : "text-zinc-600 bg-zinc-50 border border-zinc-200/60",
          )}
        >
          {change}
        </div>
      </div>
      <div className="absolute -bottom-6 -right-6 w-32 h-32 bg-gradient-to-br from-zinc-50 to-zinc-100 rounded-full opacity-50 blur-2xl group-hover:from-indigo-50/40 group-hover:scale-110 transition-all duration-500 pointer-events-none" />
    </motion.div>
  );
}

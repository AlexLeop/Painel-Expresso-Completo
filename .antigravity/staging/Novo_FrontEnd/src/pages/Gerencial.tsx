import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line,
} from "recharts";
import {
  Store,
  Bike,
  Truck,
  TrendingUp,
  DollarSign,
  AlertTriangle,
  Award,
  Activity,
} from "lucide-react";
import { formatCurrency, cn } from "../lib/utils";
import { useAuth } from "../contexts/AuthContext";
import { useApiQuery } from "../lib/useApiQuery";
import { Skeleton } from "../components/ui/Skeleton";
import { ErrorBoundary } from "../components/ErrorBoundary";

function KpiCard({
  title,
  value,
  icon,
  color,
  sub,
}: {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: "orange" | "blue" | "green" | "red" | "purple";
  sub?: string;
}) {
  const colors = {
    orange: "from-orange-500 to-orange-600",
    blue: "from-blue-500 to-blue-600",
    green: "from-emerald-500 to-emerald-600",
    red: "from-rose-500 to-rose-600",
    purple: "from-violet-500 to-violet-600",
  };
  return (
    <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 p-5 flex items-center gap-4">
      <div
        className={cn(
          "h-12 w-12 rounded-xl bg-gradient-to-br flex items-center justify-center text-white shadow-md shrink-0",
          colors[color],
        )}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
          {title}
        </p>
        <p className="text-2xl font-black text-zinc-900 tracking-tight truncate">
          {value}
        </p>
        {sub && <p className="text-[11px] text-zinc-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

const COLORS = [
  "#E55C00",
  "#3B82F6",
  "#10B981",
  "#8B5CF6",
  "#F59E0B",
  "#EF4444",
  "#06B6D4",
  "#84CC16",
];

export function Gerencial() {
  const { session } = useAuth();
  const user = session?.user;

  // Dados consolidados de todas as empresas
  const { data: companiesRaw, isLoading: loadingCompanies } = useApiQuery<
    any[]
  >("/api/db/companies", { refreshInterval: 120_000 });
  const { data: driversRaw, isLoading: loadingDrivers } = useApiQuery<any[]>(
    "/api/db/company-drivers?active_only=1",
    { refreshInterval: 120_000 },
  );
  const { data: snapshotsRaw, isLoading: loadingSnaps } = useApiQuery<any>(
    "/api/db/snapshots?limit=50",
    { refreshInterval: 300_000 },
  );

  const isLoading = loadingCompanies || loadingDrivers || loadingSnaps;

  const companies: any[] = useMemo(
    () => (Array.isArray(companiesRaw) ? companiesRaw : []),
    [companiesRaw],
  );
  const drivers: any[] = useMemo(
    () => (Array.isArray(driversRaw) ? driversRaw : []),
    [driversRaw],
  );
  const snapshots: any[] = useMemo(() => {
    if (!snapshotsRaw) return [];
    if (Array.isArray(snapshotsRaw)) return snapshotsRaw;
    if (Array.isArray(snapshotsRaw.snapshots)) return snapshotsRaw.snapshots;
    return [];
  }, [snapshotsRaw]);

  // ── KPIs Globais ──────────────────────────────────────────────────────────
  const kpis = useMemo(() => {
    const totalLojas = companies.length;
    const totalMotoboys = drivers.length;
    const faturamentoMes = snapshots
      .filter((s) => {
        const d = new Date(s.week_start || s.created_at || "");
        const now = new Date();
        return (
          d.getFullYear() === now.getFullYear() &&
          d.getMonth() === now.getMonth()
        );
      })
      .reduce(
        (acc, s) => acc + Number(s.total_liquido || s.total_payout || 0),
        0,
      );

    const semanaAtual = snapshots
      .slice(0, companies.length)
      .reduce(
        (acc, s) => acc + Number(s.total_liquido || s.total_payout || 0),
        0,
      );

    return { totalLojas, totalMotoboys, faturamentoMes, semanaAtual };
  }, [companies, drivers, snapshots]);

  // ── Ranking de Lojas ──────────────────────────────────────────────────────
  const rankingLojas = useMemo(() => {
    const byCompany: Record<
      string,
      { nome: string; total: number; semanas: number; corridas: number }
    > = {};

    for (const s of snapshots.slice(0, 100)) {
      const cId = String(s.company_id || s.empresa_id || "");
      const company = companies.find(
        (c) => String(c.id) === cId || String(c.machine_empresa_id) === cId,
      );
      const nome = company?.nome || s.company_name || `Empresa ${cId}`;
      if (!byCompany[cId])
        byCompany[cId] = { nome, total: 0, semanas: 0, corridas: 0 };
      byCompany[cId].total += Number(s.total_liquido || s.total_payout || 0);
      byCompany[cId].semanas += 1;
      byCompany[cId].corridas += Number(s.total_corridas || s.rides_count || 0);
    }

    return Object.values(byCompany)
      .sort((a, b) => b.total - a.total)
      .slice(0, 8);
  }, [snapshots, companies]);

  // ── Tendência das últimas 8 semanas ───────────────────────────────────────
  const trendData = useMemo(() => {
    const byWeek: Record<string, { semana: string; faturamento: number }> = {};

    for (const s of snapshots.slice(0, 80)) {
      const weekLabel = s.week_start
        ? s.week_start.slice(5).replace("-", "/")
        : "??";
      if (!byWeek[weekLabel])
        byWeek[weekLabel] = { semana: weekLabel, faturamento: 0 };
      byWeek[weekLabel].faturamento += Number(
        s.total_liquido || s.total_payout || 0,
      );
    }

    return Object.values(byWeek).slice(-8);
  }, [snapshots]);

  if (isLoading) {
    return (
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        <Skeleton className="w-64 h-8 rounded-lg" />
        <Skeleton className="w-full h-32 rounded-xl" />
        <Skeleton className="w-full h-64 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 pb-20 bg-[#F9F9FA]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-black text-zinc-900 tracking-tight flex items-center gap-2">
            <Activity className="h-6 w-6 text-[#E55C00]" />
            Painel Gerencial
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Visão consolidada de toda a operação · Expresso Neves
          </p>
        </div>
        <div className="px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-700 flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          {user?.name || "Administrador"}
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Lojas Ativas"
          value={kpis.totalLojas}
          icon={<Store className="h-5 w-5" />}
          color="orange"
        />
        <KpiCard
          title="Motoboys Ativos"
          value={kpis.totalMotoboys}
          icon={<Bike className="h-5 w-5" />}
          color="blue"
          sub="Todos vinculados"
        />
        <KpiCard
          title="Faturamento do Mês"
          value={formatCurrency(kpis.faturamentoMes)}
          icon={<DollarSign className="h-5 w-5" />}
          color="green"
        />
        <KpiCard
          title="Volume esta Semana"
          value={formatCurrency(kpis.semanaAtual)}
          icon={<TrendingUp className="h-5 w-5" />}
          color="purple"
        />
      </div>

      {/* Gráficos e Ranking */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tendência Semanal */}
        <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-zinc-900">
              Faturamento Semanal (últimas semanas)
            </h2>
            <Truck className="h-4 w-4 text-zinc-400" />
          </div>
          {trendData.length > 0 ? (
            <ErrorBoundary>
            <ResponsiveContainer
              width="100%"
              height={200}
              minWidth={1}
              minHeight={1}
            >
              <LineChart
                data={trendData}
                margin={{ top: 4, right: 8, bottom: 0, left: -20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="semana" tick={{ fontSize: 10 }} />
                <YAxis
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  formatter={(v: any) => [formatCurrency(v), "Faturamento"]}
                />
                <Line
                  type="monotone"
                  dataKey="faturamento"
                  stroke="#E55C00"
                  strokeWidth={2.5}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
            </ErrorBoundary>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-zinc-400 text-sm">
              Nenhum snapshot encontrado.
            </div>
          )}
        </div>

        {/* Ranking de Lojas */}
        <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-zinc-900">
              Ranking de Lojas por Volume
            </h2>
            <Award className="h-4 w-4 text-zinc-400" />
          </div>
          {rankingLojas.length > 0 ? (
            <ErrorBoundary>
            <ResponsiveContainer
              width="100%"
              height={200}
              minWidth={1}
              minHeight={1}
            >
              <BarChart
                data={rankingLojas}
                margin={{ top: 4, right: 8, bottom: 0, left: -20 }}
                layout="vertical"
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#f0f0f0"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`}
                />
                <YAxis
                  type="category"
                  dataKey="nome"
                  tick={{ fontSize: 9 }}
                  width={80}
                />
                <Tooltip
                  formatter={(v: any) => [formatCurrency(v), "Total Acumulado"]}
                />
                <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                  {rankingLojas.map((_, i) => (
                    <rect key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            </ErrorBoundary>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-zinc-400 text-sm">
              Nenhum dado disponível.
            </div>
          )}
        </div>
      </div>

      {/* Tabela de Lojas */}
      <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-100 flex items-center justify-between">
          <h2 className="text-sm font-bold text-zinc-900">Todas as Lojas</h2>
          <span className="text-xs text-zinc-400">
            {companies.length} empresa(s)
          </span>
        </div>
        {companies.length === 0 ? (
          <div className="p-8 text-center text-zinc-400 text-sm">
            <AlertTriangle className="h-6 w-6 mx-auto mb-2 opacity-40" />
            Nenhuma empresa encontrada.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-bold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-5 py-3">Empresa</th>
                  <th className="px-4 py-3 text-center">ID Machine</th>
                  <th className="px-4 py-3 text-center">Motoboys</th>
                  <th className="px-4 py-3 text-right">Volume Acumulado</th>
                  <th className="px-4 py-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {companies.map((c, i) => {
                  const compDrivers = drivers.filter(
                    (d) =>
                      String(d.machine_empresa_id) ===
                        String(c.machine_empresa_id) ||
                      String(d.company_id) === String(c.id),
                  );
                  const ranking = rankingLojas.find((r) => r.nome === c.nome);
                  return (
                    <tr
                      key={i}
                      className="hover:bg-zinc-50/50 transition-colors"
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="h-8 w-8 rounded-lg bg-zinc-900 text-white flex items-center justify-center font-black text-xs shrink-0">
                            {(c.nome || "E").charAt(0)}
                          </div>
                          <div>
                            <p className="font-bold text-zinc-900">{c.nome}</p>
                            <p className="text-zinc-400 text-[10px] font-mono">
                              {c.cnpj || "—"}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center font-mono text-zinc-500">
                        {c.machine_empresa_id || "—"}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full font-bold">
                          {compDrivers.length || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-emerald-600">
                        {ranking ? formatCurrency(ranking.total) : "—"}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-full text-[10px] font-bold",
                            c.ativo !== false
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-zinc-100 text-zinc-500",
                          )}
                        >
                          {c.ativo !== false ? "Ativa" : "Inativa"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

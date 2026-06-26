import { useState, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Calendar,
  Download,
  TrendingUp,
  TrendingDown,
  DollarSign,
  FileText,
} from "lucide-react";
import { formatCurrency, cn } from "../lib/utils";
import { useAuth } from "../contexts/AuthContext";
import { useApiQuery } from "../lib/useApiQuery";

type Period = "3m" | "6m" | "12m";

function DeltaBadge({ value }: { value: number }) {
  if (!Number.isFinite(value))
    return <span className="text-zinc-300 text-[10px]">—</span>;
  const up = value >= 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded-full",
        up ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700",
      )}
    >
      {up ? (
        <TrendingUp className="h-3 w-3" />
      ) : (
        <TrendingDown className="h-3 w-3" />
      )}
      {Math.abs(value).toFixed(1)}%
    </span>
  );
}

export function Historico() {
  const { session } = useAuth();
  const user = session?.user;
  const companyId = Number(user?.machine_empresa_id) || 0;
  const currentCompany = user?.companies?.find(
    (c) => Number(c.id) === companyId,
  );
  const companyName = currentCompany?.nome || "Empresa";

  const [period, setPeriod] = useState<Period>("6m");

  const snapsKey = companyId
    ? `/api/db/snapshots?company_id=${companyId}&limit=52`
    : null;

  const { data: snapsRaw, isLoading } = useApiQuery<any>(snapsKey, {
    refreshInterval: 300_000,
  });

  const snapshots: any[] = useMemo(() => {
    if (!snapsRaw) return [];
    if (Array.isArray(snapsRaw)) return snapsRaw;
    if (Array.isArray(snapsRaw.snapshots)) return snapsRaw.snapshots;
    return [];
  }, [snapsRaw]);

  // Filtrar pelo período selecionado
  const cutoffDate = useMemo(() => {
    const now = new Date();
    const months = period === "3m" ? 3 : period === "6m" ? 6 : 12;
    now.setMonth(now.getMonth() - months);
    return now.toISOString().slice(0, 10);
  }, [period]);

  const filtered = useMemo(
    () =>
      snapshots
        .filter(
          (s) =>
            (s.week_start || s.created_at || "").slice(0, 10) >= cutoffDate,
        )
        .sort((a, b) =>
          (a.week_start || a.created_at || "").localeCompare(
            b.week_start || b.created_at || "",
          ),
        ),
    [snapshots, cutoffDate],
  );

  // Dados para o gráfico de barras
  const chartData = useMemo(
    () =>
      filtered.map((s) => ({
        semana: (s.week_start || s.created_at || "")
          .slice(5, 10)
          .replace("-", "/"),
        total: Number(s.total_liquido || s.total_payout || 0),
        corridas: Number(s.total_corridas || s.rides_count || 0),
      })),
    [filtered],
  );

  // Totais do período
  const totals = useMemo(() => {
    const total = filtered.reduce(
      (s, snap) => s + Number(snap.total_liquido || snap.total_payout || 0),
      0,
    );
    const corridas = filtered.reduce(
      (s, snap) => s + Number(snap.total_corridas || snap.rides_count || 0),
      0,
    );
    const motoboys = filtered.reduce(
      (s, snap) =>
        Math.max(s, Number(snap.total_motoboys || snap.drivers_count || 0)),
      0,
    );
    const avg = filtered.length > 0 ? total / filtered.length : 0;
    return { total, corridas, motoboys, avg, semanas: filtered.length };
  }, [filtered]);

  // Variação em relação ao período anterior
  const deltaVsPrev = useMemo(() => {
    const months = period === "3m" ? 3 : period === "6m" ? 6 : 12;
    const prevCutoff = new Date();
    prevCutoff.setMonth(prevCutoff.getMonth() - months * 2);
    const prevCutoffISO = prevCutoff.toISOString().slice(0, 10);

    const prevSnaps = snapshots.filter((s) => {
      const d = (s.week_start || s.created_at || "").slice(0, 10);
      return d >= prevCutoffISO && d < cutoffDate;
    });
    const prevTotal = prevSnaps.reduce(
      (s, snap) => s + Number(snap.total_liquido || snap.total_payout || 0),
      0,
    );
    if (prevTotal === 0) return null;
    return ((totals.total - prevTotal) / prevTotal) * 100;
  }, [snapshots, totals.total, cutoffDate, period]);

  const exportSnapsCSV = () => {
    const BOM = "\uFEFF";
    const header = '"Semana";"Motoboys";"Corridas";"Total Líquido"\r\n';
    const rows = filtered
      .map((s) => {
        const semana = (s.week_start || s.created_at || "").slice(0, 10);
        const motoboys = s.total_motoboys || s.drivers_count || 0;
        const corridas = s.total_corridas || s.rides_count || 0;
        const total = Number(s.total_liquido || s.total_payout || 0)
          .toFixed(2)
          .replace(".", ",");
        return `"${semana}";"${motoboys}";"${corridas}";"${total}"`;
      })
      .join("\r\n");
    const blob = new Blob([BOM + header + rows], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `historico_${companyName.replace(/\s+/g, "_")}_${period}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#E55C00]" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 pb-20 bg-[#F9F9FA]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-black text-zinc-900 tracking-tight flex items-center gap-2">
            <Calendar className="h-6 w-6 text-[#E55C00]" />
            Histórico Financeiro
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            {companyName} · Evolução mensal e semanal de faturamento
          </p>
        </div>

        {/* Seletor de Período */}
        <div className="flex items-center gap-2">
          {(["3m", "6m", "12m"] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={cn(
                "px-4 py-2 rounded-xl text-xs font-bold transition-all",
                period === p
                  ? "bg-zinc-900 text-white shadow-sm"
                  : "bg-white text-zinc-500 hover:text-zinc-900 border border-zinc-200/80 hover:border-zinc-300",
              )}
            >
              {p === "3m" ? "3 meses" : p === "6m" ? "6 meses" : "12 meses"}
            </button>
          ))}
          <button
            onClick={exportSnapsCSV}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition-colors shadow-sm ml-2"
          >
            <Download className="h-3.5 w-3.5" /> CSV
          </button>
        </div>
      </div>

      {/* KPIs do período */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Total do Período",
            value: formatCurrency(totals.total),
            icon: <DollarSign className="h-4 w-4" />,
            color: "bg-emerald-100 text-emerald-700",
          },
          {
            label: "Média por Semana",
            value: formatCurrency(totals.avg),
            icon: <TrendingUp className="h-4 w-4" />,
            color: "bg-blue-100 text-blue-700",
          },
          {
            label: "Semanas Fechadas",
            value: totals.semanas,
            icon: <Calendar className="h-4 w-4" />,
            color: "bg-zinc-100 text-zinc-700",
          },
          {
            label: "Total de Corridas",
            value: totals.corridas.toLocaleString("pt-BR"),
            icon: <FileText className="h-4 w-4" />,
            color: "bg-orange-100 text-orange-700",
          },
        ].map((kpi, i) => (
          <div
            key={i}
            className="bg-white rounded-2xl p-4 shadow-sm ring-1 ring-zinc-200/60 flex items-center gap-3"
          >
            <div className={cn("p-2.5 rounded-xl shrink-0", kpi.color)}>
              {kpi.icon}
            </div>
            <div>
              <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                {kpi.label}
              </p>
              <p className="text-xl font-black text-zinc-900 tracking-tight">
                {kpi.value}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Gráfico de Barras */}
      <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-zinc-900">
              Faturamento por Semana Fechada
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              {period === "3m"
                ? "Últimos 3 meses"
                : period === "6m"
                  ? "Últimos 6 meses"
                  : "Último ano"}
            </p>
          </div>
          {deltaVsPrev !== null && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-400">
                vs. período anterior:
              </span>
              <DeltaBadge value={deltaVsPrev} />
            </div>
          )}
        </div>
        {chartData.length > 0 ? (
          <ResponsiveContainer
            width="100%"
            height={220}
            minWidth={1}
            minHeight={1}
          >
            <BarChart
              data={chartData}
              margin={{ top: 4, right: 8, bottom: 0, left: -8 }}
              barSize={18}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="semana" tick={{ fontSize: 9 }} />
              <YAxis
                tick={{ fontSize: 9 }}
                tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                formatter={(v: any) => [formatCurrency(v), "Total"]}
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 8,
                  border: "1px solid #e4e4e7",
                }}
              />
              <Bar dataKey="total" fill="#E55C00" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[220px] flex items-center justify-center text-zinc-400 text-sm">
            Nenhum dado para o período selecionado.
          </div>
        )}
      </div>

      {/* Tabela de Snapshots */}
      <div className="bg-white rounded-2xl shadow-sm ring-1 ring-zinc-200/60 overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-100 flex items-center justify-between">
          <h2 className="text-sm font-bold text-zinc-900">
            Semanas Fechadas ({filtered.length})
          </h2>
        </div>
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-zinc-400 text-sm">
            Nenhum fechamento encontrado no período.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-bold text-[10px] uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Semana</th>
                  <th className="px-4 py-3 text-center">Motoboys</th>
                  <th className="px-4 py-3 text-center">Corridas</th>
                  <th className="px-4 py-3 text-right">Total Líquido</th>
                  <th className="px-4 py-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {[...filtered].reverse().map((s, i) => {
                  const semana = (s.week_start || s.created_at || "").slice(
                    0,
                    10,
                  );
                  const total = Number(s.total_liquido || s.total_payout || 0);
                  const prevTotal =
                    i < filtered.length - 1
                      ? Number(
                          filtered[filtered.length - 2 - i]?.total_liquido ||
                            filtered[filtered.length - 2 - i]?.total_payout ||
                            0,
                        )
                      : null;
                  const delta =
                    prevTotal && prevTotal > 0
                      ? ((total - prevTotal) / prevTotal) * 100
                      : null;
                  return (
                    <tr
                      key={i}
                      className="hover:bg-zinc-50/50 transition-colors"
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <Calendar className="h-3.5 w-3.5 text-zinc-300" />
                          <span className="font-semibold text-zinc-900 font-mono">
                            {semana}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center text-zinc-600">
                        {s.total_motoboys || s.drivers_count || "—"}
                      </td>
                      <td className="px-4 py-3 text-center text-zinc-600">
                        {(
                          s.total_corridas ||
                          s.rides_count ||
                          0
                        ).toLocaleString("pt-BR")}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className="font-mono font-bold text-emerald-600">
                            {formatCurrency(total)}
                          </span>
                          {delta !== null && <DeltaBadge value={delta} />}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-full text-[10px] font-bold",
                            s.status === "closed" || s.fechado
                              ? "bg-zinc-100 text-zinc-600"
                              : "bg-blue-100 text-blue-700",
                          )}
                        >
                          {s.status === "closed" || s.fechado
                            ? "Fechado"
                            : "Aberto"}
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

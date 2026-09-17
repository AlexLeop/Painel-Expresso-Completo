import React, { useState, useEffect } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Filter,
  Calendar,
  Download,
  RefreshCw,
  Wallet,
  TrendingUp,
  TrendingDown,
  Bike,
  CreditCard,
  FileSpreadsheet,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { motion } from "framer-motion";
import { authFetch, getSession } from "../lib/api";
import { formatCurrency, cn } from "../lib/utils";

interface FinancialItem {
  id: string;
  date: string;
  type: "RIDE" | "RECHARGE" | "FEE" | "ADJUSTMENT";
  description: string;
  amount_cents: number;
  running_balance_cents: number;
}

interface FinancialStatementData {
  current_balance_cents: number;
  total_entries: number;
  items: FinancialItem[];
}

export function Extrato() {
  const session = getSession();
  const [statement, setStatement] = useState<FinancialStatementData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<"hoje" | "7d" | "30d" | "mes">("30d");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");

  const fetchStatement = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(`/api/v1/client/financial-statement?period=${period}`);
      if (res.ok) {
        const data = await res.json();
        setStatement(data);
      } else {
        setError("Não foi possível carregar o extrato financeiro da loja.");
      }
    } catch (err: any) {
      setError(err.message || "Erro de conexão ao buscar extrato.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatement();
  }, [period]);

  const items = statement?.items || [];

  // Filtro por tipo
  const filteredItems = items.filter((item) => {
    if (typeFilter === "ALL") return true;
    return item.type === typeFilter;
  });

  // Cálculos dos KPIs
  const currentBalanceReais = (statement?.current_balance_cents ?? 0) / 100;
  const totalEntriesCents = items
    .filter((i) => i.amount_cents > 0)
    .reduce((acc, curr) => acc + curr.amount_cents, 0);
  const totalEntriesReais = totalEntriesCents / 100;

  const totalExitsCents = items
    .filter((i) => i.amount_cents < 0)
    .reduce((acc, curr) => acc + Math.abs(curr.amount_cents), 0);
  const totalExitsReais = totalExitsCents / 100;

  const totalRidesCount = items.filter((i) => i.type === "RIDE").length;

  const getTypeLabel = (type: string) => {
    switch (type) {
      case "RECHARGE":
        return { label: "Recarga PIX", color: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" };
      case "RIDE":
        return { label: "Corrida / Entrega", color: "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200" };
      case "FEE":
        return { label: "Taxa / Diária", color: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" };
      case "ADJUSTMENT":
        return { label: "Ajuste Manual", color: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300" };
      default:
        return { label: type, color: "bg-zinc-100 text-zinc-800" };
    }
  };

  const handleExportCsv = () => {
    if (!filteredItems.length) return;
    const headers = ["Data", "Tipo", "Descricao", "Valor (R$)", "Saldo Resultante (R$)"];
    const rows = filteredItems.map((item) => [
      new Date(item.date).toLocaleString("pt-BR"),
      item.type,
      `"${item.description.replace(/"/g, '""')}"`,
      (item.amount_cents / 100).toFixed(2).replace(".", ","),
      (item.running_balance_cents / 100).toFixed(2).replace(".", ","),
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(";"), ...rows.map((e) => e.join(";"))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `extrato_financeiro_${period}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800 pb-4">
        <div>
          <nav className="text-xs text-zinc-500 mb-1 flex items-center gap-1">
            <span>Financeiro</span>
            <span>/</span>
            <span className="text-zinc-900 dark:text-zinc-100 font-medium">Extrato Financeiro</span>
          </nav>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
            Extrato Financeiro
          </h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-0.5">
            Acompanhamento contábil cronológico com evolução do saldo da loja (Running Balance).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCsv}
            disabled={filteredItems.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors shadow-sm disabled:opacity-50"
          >
            <Download className="h-3.5 w-3.5" />
            Exportar CSV
          </button>
          <button
            onClick={fetchStatement}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors shadow-sm"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Atualizar
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl flex items-center gap-3 text-rose-800 dark:text-rose-300 text-sm">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Saldo Atual */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Saldo Atual
            </span>
            <div className="h-8 w-8 rounded-xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-700 dark:text-zinc-300">
              <Wallet className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
              {formatCurrency(currentBalanceReais)}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Saldo consolidado disponível</p>
          </div>
        </div>

        {/* Total Entradas */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Total Entradas
            </span>
            <div className="h-8 w-8 rounded-xl bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-700 dark:text-emerald-300">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400 tracking-tight">
              +{formatCurrency(totalEntriesReais)}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Recargas e bônus no período</p>
          </div>
        </div>

        {/* Total Saídas */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Total Saídas
            </span>
            <div className="h-8 w-8 rounded-xl bg-rose-100 dark:bg-rose-950 flex items-center justify-center text-rose-700 dark:text-rose-300">
              <TrendingDown className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
              -{formatCurrency(totalExitsReais)}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Corridas e taxas faturadas</p>
          </div>
        </div>

        {/* Total Entregas */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Entregas Realizadas
            </span>
            <div className="h-8 w-8 rounded-xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-700 dark:text-zinc-300">
              <Bike className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
              {totalRidesCount}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Corridas faturadas no período</p>
          </div>
        </div>
      </div>

      {/* Barra de Filtros: Período e Tipo */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Abas de Período */}
        <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800/80 p-1 rounded-xl">
          {[
            { id: "hoje", label: "Hoje" },
            { id: "7d", label: "7 dias" },
            { id: "30d", label: "30 dias" },
            { id: "mes", label: "Mês Atual" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setPeriod(tab.id as any)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all",
                period === tab.id
                  ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm"
                  : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Filtro por Categoria */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-zinc-400 shrink-0" />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="text-xs font-semibold bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-800 rounded-xl px-3 py-2 text-zinc-900 dark:text-zinc-100 focus:outline-none"
          >
            <option value="ALL">Todos os Tipos</option>
            <option value="RIDE">Apenas Entregas</option>
            <option value="RECHARGE">Apenas Recargas</option>
            <option value="FEE">Apenas Taxas / Diárias</option>
            <option value="ADJUSTMENT">Apenas Ajustes Manuais</option>
          </select>
        </div>
      </div>

      {/* Tabela do Livro-Razão (Running Balance) */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 text-[10px] uppercase font-bold tracking-wider text-zinc-500">
              <tr>
                <th className="px-6 py-3">Data / Hora</th>
                <th className="px-6 py-3">Tipo</th>
                <th className="px-6 py-3">Descrição / Pedido</th>
                <th className="px-6 py-3 text-right">Valor (R$)</th>
                <th className="px-6 py-3 text-right">Saldo Resultante</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-zinc-500 text-xs">
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="h-4 w-4 animate-spin text-zinc-400" />
                      <span>Carregando lançamentos contábeis...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-zinc-500 text-xs">
                    Nenhum lançamento registrado no período selecionado.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => {
                  const isPositive = item.amount_cents > 0;
                  const typeBadge = getTypeLabel(item.type);
                  const amountReais = item.amount_cents / 100;
                  const runningReais = item.running_balance_cents / 100;

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition-colors"
                    >
                      <td className="px-6 py-3.5 text-xs text-zinc-500">
                        {new Date(item.date).toLocaleDateString("pt-BR", {
                          day: "2-digit",
                          month: "2-digit",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td className="px-6 py-3.5">
                        <span
                          className={cn(
                            "inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold",
                            typeBadge.color
                          )}
                        >
                          {typeBadge.label}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 font-medium text-zinc-900 dark:text-zinc-100">
                        {item.description}
                      </td>
                      <td
                        className={cn(
                          "px-6 py-3.5 text-right font-bold",
                          isPositive
                            ? "text-emerald-600 dark:text-emerald-400"
                            : "text-zinc-900 dark:text-zinc-100"
                        )}
                      >
                        {isPositive ? `+${formatCurrency(amountReais)}` : formatCurrency(amountReais)}
                      </td>
                      <td className="px-6 py-3.5 text-right font-extrabold text-zinc-900 dark:text-zinc-100">
                        {formatCurrency(runningReais)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

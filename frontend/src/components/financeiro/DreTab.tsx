import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  DollarSign,
  ArrowDownToLine,
  PieChart,
  Bike,
  Receipt,
  RefreshCw,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";
import { authFetch } from "../../lib/api";
import { formatCurrency, cn } from "../../lib/utils";

interface DreData {
  month_label: string;
  receita_bruta_reais: number;
  comissao_retida_reais: number;
  margem_percentual: number;
  saques_pagos_reais: number;
  resultado_liquido_reais: number;
  corridas_entregues: number;
  ticket_medio_reais: number;
}

export function DreTab() {
  const [data, setData] = useState<DreData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDre = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch("/api/v1/operator/financial-dashboard");
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        setError("Não foi possível carregar os dados de DRE do operador.");
      }
    } catch (err: any) {
      setError(err.message || "Erro de conexão com o servidor.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDre();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header do DRE */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
            {data?.month_label ? `Financeiro — ${data.month_label}` : "Financeiro — Mês Atual"}
          </h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Demonstrativo de Resultado do Exercício (DRE) operacional da central Expresso Neves.
          </p>
        </div>

        <button
          onClick={fetchDre}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-zinc-700 dark:text-zinc-300 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-800 rounded-xl hover:bg-zinc-100 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Atualizar
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl flex items-center gap-3 text-rose-800 dark:text-rose-300 text-sm">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 4 Cards Principais de DRE — Módulo 14 MotorK */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Receita Bruta */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Receita Bruta
            </span>
            <div className="h-8 w-8 rounded-xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-700 dark:text-zinc-300">
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
              {data ? formatCurrency(data.receita_bruta_reais) : "R$ 0,00"}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              {data ? `${data.corridas_entregues} corridas entregues` : "0 corridas"}
            </p>
          </div>
        </div>

        {/* Comissão Retida */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Comissão Retida
            </span>
            <div className="h-8 w-8 rounded-xl bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-700 dark:text-emerald-300">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400 tracking-tight">
              {data ? formatCurrency(data.comissao_retida_reais) : "R$ 0,00"}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              Margem operacional: {data?.margem_percentual.toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Saques Pagos */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Saques Pagos
            </span>
            <div className="h-8 w-8 rounded-xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-700 dark:text-zinc-300">
              <ArrowDownToLine className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
              {data ? formatCurrency(data.saques_pagos_reais) : "R$ 0,00"}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Repassado aos motoboys no mês</p>
          </div>
        </div>

        {/* Resultado Líquido */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Resultado Líquido
            </span>
            <div className="h-8 w-8 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 flex items-center justify-center">
              <PieChart className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
              {data ? formatCurrency(data.resultado_liquido_reais) : "R$ 0,00"}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Comissão − Saques pagos</p>
          </div>
        </div>
      </div>

      {/* Detalhamento e Indicadores Secundários */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-3">
          <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Bike className="h-4 w-4 text-zinc-400" />
            Indicadores de Desempenho Operacional
          </h3>
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800 text-xs">
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-zinc-500">Total de Entregas Concluídas:</span>
              <span className="font-bold text-zinc-900 dark:text-zinc-100">
                {data ? `${data.corridas_entregues} entregas` : "0"}
              </span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-zinc-500">Ticket Médio por Entrega:</span>
              <span className="font-bold text-zinc-900 dark:text-zinc-100">
                {data ? formatCurrency(data.ticket_medio_reais) : "R$ 0,00"}
              </span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-zinc-500">Taxa Média de Retenção da Central:</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">
                {data ? `${data.margem_percentual.toFixed(1)}%` : "0%"}
              </span>
            </div>
          </div>
        </div>

        <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-3">
          <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            Governança e Reconciliação Contábil
          </h3>
          <p className="text-xs text-zinc-500 leading-relaxed">
            Todas as transações são registradas de forma atômica no livro-razão (PostgreSQL Ledger). Os repasses a motoboys são validados por chaves idempotentes, e faturas de lojas pré-pagas são atualizadas em tempo real após a confirmação do PIX.
          </p>
        </div>
      </div>
    </div>
  );
}

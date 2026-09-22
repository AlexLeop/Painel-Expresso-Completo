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
  Server,
  ChevronLeft,
  ChevronRight,
  Info,
} from "lucide-react";
import { authFetch } from "../../lib/api";
import { formatCurrency, cn } from "../../lib/utils";

interface PlatformBillingDetails {
  deliveries_count: number;
  calculated_cents: number;
  floor_cents: number;
  final_fee_cents: number;
  final_fee_reais: number;
  floor_reais: number;
  base_rate_reais: number;
  applied_floor: boolean;
}

interface DreData {
  month?: string;
  month_label: string;
  receita_bruta_reais: number;
  comissao_retida_reais: number;
  margem_percentual: number;
  saques_pagos_reais: number;
  custo_plataforma_reais?: number;
  plataforma_billing?: PlatformBillingDetails;
  resultado_liquido_reais: number;
  corridas_entregues: number;
  ticket_medio_reais: number;
}

export function DreTab() {
  const [data, setData] = useState<DreData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Navegação de Mês (Offset relativo ao mês atual)
  const [monthOffset, setMonthOffset] = useState(0);

  const selectedMonthString = React.useMemo(() => {
    const d = new Date();
    d.setMonth(d.getMonth() + monthOffset);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    return `${y}-${m}`;
  }, [monthOffset]);

  const fetchDre = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(`/api/v1/operator/financial-dashboard?month=${selectedMonthString}`);
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
  }, [selectedMonthString]);

  const platformCost = data?.custo_plataforma_reais ?? 0;
  const platformBilling = data?.plataforma_billing;

  return (
    <div className="space-y-6">
      {/* Header do DRE com Navegador de Mês */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-5 bg-white border border-zinc-200 rounded-2xl shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-zinc-900">
              {data?.month_label ? `DRE Financeiro — ${data.month_label}` : "DRE Financeiro — Mês Atual"}
            </h2>
            {monthOffset === 0 && (
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                Em Andamento
              </span>
            )}
          </div>
          <p className="text-xs text-zinc-500 mt-0.5">
            Demonstrativo de Resultado do Exercício consolidado: faturamento, repasses e custo da plataforma SaaS.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          {/* Controles de Navegação Mensal */}
          <div className="inline-flex items-center bg-zinc-50 border border-zinc-200 rounded-xl p-0.5 shadow-2xs">
            <button
              onClick={() => setMonthOffset((prev) => prev - 1)}
              className="p-1.5 hover:bg-white text-zinc-600 hover:text-zinc-900 rounded-lg transition-colors cursor-pointer"
              title="Mês anterior"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-3 text-xs font-semibold text-zinc-700">
              {data?.month_label || selectedMonthString}
            </span>
            <button
              onClick={() => setMonthOffset((prev) => Math.min(0, prev + 1))}
              disabled={monthOffset >= 0}
              className="p-1.5 hover:bg-white text-zinc-600 hover:text-zinc-900 disabled:opacity-40 disabled:hover:bg-transparent rounded-lg transition-colors cursor-pointer"
              title="Próximo mês"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <button
            onClick={fetchDre}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-zinc-700 bg-white border border-zinc-200 rounded-xl hover:bg-zinc-50 transition-colors cursor-pointer shadow-2xs"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Atualizar
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-800 text-sm shadow-xs">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {/* Grid de Cards de DRE Executivo */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Receita Bruta */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
              Receita Bruta
            </span>
            <div className="h-7 w-7 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-700">
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2.5">
            <span className="text-xl font-black text-zinc-900 tracking-tight">
              {data ? formatCurrency(data.receita_bruta_reais) : "R$ 0,00"}
            </span>
            <p className="text-[10px] text-zinc-500 mt-0.5">
              {data ? `${data.corridas_entregues} corridas concluídas` : "0 corridas"}
            </p>
          </div>
        </div>

        {/* Comissão Retida da Central */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
              Receita Central
            </span>
            <div className="h-7 w-7 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-700">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2.5">
            <span className="text-xl font-black text-emerald-600 tracking-tight">
              {data ? formatCurrency(data.comissao_retida_reais) : "R$ 0,00"}
            </span>
            <p className="text-[10px] text-zinc-500 mt-0.5">
              Margem bruta: {data?.margem_percentual.toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Custo da Plataforma SaaS (Alex / Expresso Neves Platform) */}
        <div className="bg-white border border-indigo-200 rounded-2xl p-4 shadow-xs bg-linear-to-b from-indigo-50/40 to-transparent">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
              Custo Plataforma SaaS
            </span>
            <div className="h-7 w-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center">
              <Server className="h-3.5 w-3.5" />
            </div>
          </div>
          <div className="mt-2.5">
            <span className="text-xl font-black text-indigo-950 tracking-tight">
              {formatCurrency(platformCost)}
            </span>
            <div className="flex items-center gap-1.5 mt-0.5">
              {platformBilling?.applied_floor ? (
                <span className="inline-flex items-center text-[9px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded">
                  Piso Mínimo ({formatCurrency(platformBilling.floor_reais)})
                </span>
              ) : (
                <span className="text-[10px] text-indigo-600">
                  {platformBilling ? `${platformBilling.deliveries_count} × ${formatCurrency(platformBilling.base_rate_reais)}` : "Licença mensal"}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Saques Pagos aos Motoboys */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
              Repasse Motoboys
            </span>
            <div className="h-7 w-7 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-700">
              <ArrowDownToLine className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2.5">
            <span className="text-xl font-black text-zinc-900 tracking-tight">
              {data ? formatCurrency(data.saques_pagos_reais) : "R$ 0,00"}
            </span>
            <p className="text-[10px] text-zinc-500 mt-0.5">Saques pagos no período</p>
          </div>
        </div>

        {/* Resultado Operacional Líquido */}
        <div className="bg-zinc-900 text-white rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
              Lucro Líquido
            </span>
            <div className="h-7 w-7 rounded-lg bg-zinc-800 text-emerald-400 flex items-center justify-center">
              <PieChart className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2.5">
            <span className={cn("text-xl font-black tracking-tight", (data?.resultado_liquido_reais ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400")}>
              {data ? formatCurrency(data.resultado_liquido_reais) : "R$ 0,00"}
            </span>
            <p className="text-[10px] text-zinc-400 mt-0.5">Receita − Saques − SaaS</p>
          </div>
        </div>
      </div>

      {/* Demonstrativo Contábil Estruturado (DRE) & Memória de Cálculo SaaS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Tabela Demonstrativa de DRE */}
        <div className="p-5 bg-white border border-zinc-200 rounded-2xl shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-zinc-900 flex items-center gap-2">
            <Receipt className="h-4 w-4 text-zinc-500" />
            Demonstrativo de Fechamento Operacional
          </h3>
          <div className="divide-y divide-zinc-100 text-xs">
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-zinc-600 font-medium">(+) Faturamento Bruto de Corridas</span>
              <span className="font-bold text-zinc-900">
                {data ? formatCurrency(data.receita_bruta_reais) : "R$ 0,00"}
              </span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-zinc-600 font-medium">(=) Receita Retida da Central (Comissão)</span>
              <span className="font-bold text-emerald-600">
                {data ? formatCurrency(data.comissao_retida_reais) : "R$ 0,00"}
              </span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-zinc-600 font-medium">(-) Repasses / Saques Liquidados a Motoboys</span>
              <span className="font-bold text-rose-600">
                {data ? `− ${formatCurrency(data.saques_pagos_reais)}` : "R$ 0,00"}
              </span>
            </div>
            <div className="py-2.5 flex items-center justify-between">
              <span className="text-indigo-700 font-semibold">(-) Licenciamento da Plataforma SaaS</span>
              <span className="font-bold text-indigo-700">
                {`− ${formatCurrency(platformCost)}`}
              </span>
            </div>
            <div className="py-3 flex items-center justify-between bg-zinc-50/80 px-3 rounded-xl border border-zinc-200/80 mt-1">
              <span className="text-xs font-black uppercase tracking-wider text-zinc-900">
                (=) Resultado Operacional Líquido do Operador
              </span>
              <span className={cn("text-sm font-black", (data?.resultado_liquido_reais ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700")}>
                {data ? formatCurrency(data.resultado_liquido_reais) : "R$ 0,00"}
              </span>
            </div>
          </div>
        </div>

        {/* Quadro de Licenciamento da Plataforma SaaS (Alex / Expresso Neves) */}
        <div className="p-5 bg-white border border-indigo-200 rounded-2xl shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-indigo-950 flex items-center gap-2">
              <Server className="h-4 w-4 text-indigo-600" />
              Contrato de Licença de Software (SaaS)
            </h3>
            <span className="px-2 py-0.5 text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-md">
              Regra de Faturamento
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-indigo-900 font-medium">Volume de Entregas no Mês:</span>
                <span className="font-bold text-indigo-950">{data?.corridas_entregues ?? 0} concluídas</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-indigo-900 font-medium">Tarifa Unitária Base:</span>
                <span className="font-bold text-indigo-950">
                  {platformBilling ? formatCurrency(platformBilling.base_rate_reais) : "R$ 0,40"} / entrega
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-indigo-900 font-medium">Piso Mínimo Mensal Garantido:</span>
                <span className="font-bold text-indigo-950">
                  {platformBilling ? formatCurrency(platformBilling.floor_reais) : "R$ 299,00"} / mês
                </span>
              </div>
              <div className="border-t border-indigo-200/60 pt-2 flex justify-between items-center">
                <span className="text-indigo-950 font-bold">Valor Apurado a Pagar à Plataforma:</span>
                <span className="text-sm font-black text-indigo-700">
                  {formatCurrency(platformCost)}
                </span>
              </div>
            </div>

            <p className="text-[11px] text-zinc-500 leading-relaxed flex items-start gap-1.5">
              <Info className="h-3.5 w-3.5 text-indigo-500 shrink-0 mt-0.5" />
              O valor devido pelo operador à plataforma de software é calculado com base nas entregas concluídas no período com garantia irrevogável do piso mínimo contratual.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}


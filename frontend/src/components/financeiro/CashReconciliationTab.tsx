import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  Banknote,
  TrendingUp,
  Receipt,
  Users,
  Search,
  RefreshCw,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Clock,
  ArrowDownRight,
  ArrowUpRight,
  Loader2,
  ShieldCheck,
  Check,
  X,
} from "lucide-react";
import { authFetch } from "../../lib/api";
import { formatCurrency, cn } from "../../lib/utils";

interface CashOrder {
  order_id: string;
  store_name: string;
  cash_amount_cents: number;
  cash_amount_reais: number;
  created_at: string;
}

interface DriverCashItem {
  driver_id: string;
  driver_name: string;
  driver_phone: string;
  cash_collected_cents: number;
  cash_collected_reais: number;
  driver_earnings_cents: number;
  driver_earnings_reais: number;
  net_due_operator_cents: number;
  net_due_operator_reais: number;
  orders_count: number;
  orders: CashOrder[];
}

interface CashReconciliationData {
  summary: {
    total_collected_cents: number;
    total_collected_reais: number;
    total_earnings_cents: number;
    total_earnings_reais: number;
    total_due_operator_cents: number;
    total_due_operator_reais: number;
    drivers_count: number;
  };
  drivers: DriverCashItem[];
}

export function CashReconciliationTab() {
  const [data, setData] = useState<CashReconciliationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<"all" | "due_operator" | "due_driver">("all");
  const [expandedDriverId, setExpandedDriverId] = useState<string | null>(null);

  // Settlement modal state
  const [settlingDriver, setSettlingDriver] = useState<DriverCashItem | null>(null);
  const [settleAmount, setSettleAmount] = useState("");
  const [settleNotes, setSettleNotes] = useState("");
  const [isSubmittingSettle, setIsSubmittingSettle] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch("/api/v1/operator/cash-reconciliation");
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error("Erro ao carregar reconciliação de dinheiro:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleOpenSettleModal = (driver: DriverCashItem) => {
    setSettlingDriver(driver);
    setSettleAmount(String(driver.net_due_operator_reais));
    setSettleNotes(`Acerto de caixa presencial na base (${driver.driver_name})`);
  };

  const handleConfirmSettle = async () => {
    if (!settlingDriver) return;
    const amountVal = parseFloat(settleAmount);
    if (isNaN(amountVal) || amountVal <= 0) {
      alert("Informe um valor válido para quitação.");
      return;
    }

    setIsSubmittingSettle(true);
    try {
      const res = await authFetch("/api/v1/operator/settle-cash", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          driver_id: settlingDriver.driver_id,
          amount_cents: Math.round(amountVal * 100),
          notes: settleNotes || "Prestação de contas física em dinheiro",
        }),
      });

      const resJson = await res.json();
      if (res.ok && resJson.success !== false) {
        showToast(
          `Baixa efetuada com sucesso para ${settlingDriver.driver_name} (R$ ${amountVal.toFixed(2)})`,
        );
        setSettlingDriver(null);
        await fetchData();
      } else {
        alert(resJson.error || "Erro ao registrar prestação de contas.");
      }
    } catch (err: any) {
      alert("Falha na comunicação com o servidor: " + err.message);
    } finally {
      setIsSubmittingSettle(false);
    }
  };

  const filteredDrivers = useMemo(() => {
    if (!data?.drivers) return [];
    return data.drivers.filter((d) => {
      const matchesSearch =
        d.driver_name.toLowerCase().includes(search.toLowerCase()) ||
        d.driver_phone.includes(search);
      if (!matchesSearch) return false;

      if (filterType === "due_operator") return d.net_due_operator_cents > 0;
      if (filterType === "due_driver") return d.net_due_operator_cents < 0;
      return true;
    });
  }, [data?.drivers, search, filterType]);

  const summary = data?.summary || {
    total_collected_cents: 0,
    total_collected_reais: 0,
    total_earnings_cents: 0,
    total_earnings_reais: 0,
    total_due_operator_cents: 0,
    total_due_operator_reais: 0,
    drivers_count: 0,
  };

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-sm font-semibold flex items-center gap-2 shadow-sm animate-fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* KPI Header Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Dinheiro Coletado */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
              Total Coletado
            </span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Banknote className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-zinc-900 tracking-tight">
            {formatCurrency(summary.total_collected_reais)}
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Dinheiro recebido das mãos dos clientes
          </p>
        </div>

        {/* Repasse aos Entregadores */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
              Ganhos dos Motoboys
            </span>
            <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-zinc-900 tracking-tight">
            {formatCurrency(summary.total_earnings_reais)}
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Remuneração acumulada em corridas
          </p>
        </div>

        {/* Saldo a Prestar Contas à Base */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
              Líquido Devido à Base
            </span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Receipt className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-amber-600 tracking-tight">
            {formatCurrency(summary.total_due_operator_reais)}
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Diferença a ser recolhida em espécie na base
          </p>
        </div>

        {/* Motoboys no Fechamento */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
              Condutores com Dinheiro
            </span>
            <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-zinc-900 tracking-tight">
            {summary.drivers_count}
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Entregadores com corridas em dinheiro hoje
          </p>
        </div>
      </div>

      {/* Action and Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white p-4 border border-zinc-200 rounded-2xl shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <input
            type="text"
            placeholder="Buscar condutor por nome ou telefone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto">
          <div className="flex items-center bg-zinc-100 p-1 rounded-xl text-xs font-bold text-zinc-600">
            <button
              onClick={() => setFilterType("all")}
              className={cn(
                "px-3 py-1.5 rounded-lg transition-all",
                filterType === "all" ? "bg-white text-zinc-900 shadow-sm" : "hover:text-zinc-900",
              )}
            >
              Todos ({data?.drivers.length || 0})
            </button>
            <button
              onClick={() => setFilterType("due_operator")}
              className={cn(
                "px-3 py-1.5 rounded-lg transition-all",
                filterType === "due_operator"
                  ? "bg-white text-amber-700 shadow-sm"
                  : "hover:text-zinc-900",
              )}
            >
              Devem à Base
            </button>
            <button
              onClick={() => setFilterType("due_driver")}
              className={cn(
                "px-3 py-1.5 rounded-lg transition-all",
                filterType === "due_driver"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "hover:text-zinc-900",
              )}
            >
              Base Deve
            </button>
          </div>

          <button
            onClick={fetchData}
            disabled={loading}
            title="Recarregar conferência de dinheiro"
            className="p-2 border border-zinc-200 rounded-xl text-zinc-600 hover:bg-zinc-50 transition-colors"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Drivers List */}
      {loading ? (
        <div className="bg-white border border-zinc-200 rounded-2xl p-12 text-center shadow-sm">
          <Loader2 className="w-8 h-8 animate-spin text-zinc-400 mx-auto mb-3" />
          <p className="text-sm font-semibold text-zinc-600">
            Carregando conferência de dinheiro em espécie...
          </p>
        </div>
      ) : filteredDrivers.length === 0 ? (
        <div className="bg-white border border-zinc-200 rounded-2xl p-12 text-center shadow-sm">
          <ShieldCheck className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-zinc-900">
            Nenhuma pendência de dinheiro em espécie
          </h3>
          <p className="text-xs text-zinc-500 max-w-md mx-auto mt-1">
            Não há entregadores com valores em espécie pendentes de prestação de contas
            ou os filtros aplicados não retornaram resultados.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredDrivers.map((driver) => {
            const isExpanded = expandedDriverId === driver.driver_id;
            const isDueOperator = driver.net_due_operator_cents > 0;
            const isZero = driver.net_due_operator_cents === 0;

            return (
              <div
                key={driver.driver_id}
                className="bg-white border border-zinc-200 rounded-2xl overflow-hidden shadow-sm transition-all hover:border-zinc-300"
              >
                <div className="p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  {/* Driver Identification */}
                  <div className="flex items-center gap-3.5">
                    <div className="w-11 h-11 rounded-2xl bg-zinc-900 text-white flex items-center justify-center font-black text-sm uppercase shrink-0">
                      {driver.driver_name.slice(0, 2)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold text-sm text-zinc-900">
                          {driver.driver_name}
                        </h4>
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-600">
                          {driver.orders_count}{" "}
                          {driver.orders_count === 1 ? "corrida" : "corridas"}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-500">
                        {driver.driver_phone || "Sem telefone"}
                      </p>
                    </div>
                  </div>

                  {/* Financial Breakdown */}
                  <div className="grid grid-cols-3 gap-4 sm:gap-6 w-full sm:w-auto text-left sm:text-right border-t sm:border-t-0 pt-3 sm:pt-0 border-zinc-100">
                    <div>
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">
                        Coletado
                      </span>
                      <span className="text-xs sm:text-sm font-bold text-zinc-800">
                        {formatCurrency(driver.cash_collected_reais)}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">
                        Ganhos
                      </span>
                      <span className="text-xs sm:text-sm font-bold text-blue-700">
                        {formatCurrency(driver.driver_earnings_reais)}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">
                        Líquido Devido
                      </span>
                      <span
                        className={cn(
                          "text-xs sm:text-sm font-black",
                          isDueOperator
                            ? "text-amber-600"
                            : isZero
                              ? "text-zinc-500"
                              : "text-emerald-600",
                        )}
                      >
                        {formatCurrency(driver.net_due_operator_reais)}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 w-full sm:w-auto justify-end border-t sm:border-t-0 pt-3 sm:pt-0 border-zinc-100">
                    <button
                      onClick={() =>
                        setExpandedDriverId(isExpanded ? null : driver.driver_id)
                      }
                      className="p-2 border border-zinc-200 text-zinc-600 hover:bg-zinc-50 rounded-xl transition-colors text-xs font-semibold flex items-center gap-1"
                      title="Ver corridas deste condutor"
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>

                    <button
                      onClick={() => handleOpenSettleModal(driver)}
                      disabled={isZero}
                      className={cn(
                        "px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm flex items-center gap-1.5",
                        isZero
                          ? "bg-zinc-100 text-zinc-400 cursor-not-allowed"
                          : "bg-zinc-900 hover:bg-zinc-800 text-white active:scale-95",
                      )}
                    >
                      <Check className="w-3.5 h-3.5" /> Dar Baixa / Quitar
                    </button>
                  </div>
                </div>

                {/* Expanded Orders Accordion */}
                {isExpanded && (
                  <div className="border-t border-zinc-100 bg-zinc-50/70 p-4 sm:p-5 space-y-3 animate-fade-in">
                    <h5 className="text-xs font-bold text-zinc-700 uppercase tracking-wider flex items-center gap-1.5">
                      <Receipt className="w-3.5 h-3.5 text-zinc-500" />
                      Corridas com recebimento em dinheiro
                    </h5>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-zinc-200/80 text-zinc-400 font-bold uppercase tracking-wider">
                            <th className="pb-2">ID Corrida</th>
                            <th className="pb-2">Loja / Estabelecimento</th>
                            <th className="pb-2">Data / Horário</th>
                            <th className="pb-2 text-right">Valor Coletado</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-200/50">
                          {driver.orders.map((ord) => (
                            <tr key={ord.order_id} className="hover:bg-white/60">
                              <td className="py-2.5 font-bold text-zinc-900">
                                {ord.order_id.slice(0, 8)}...
                              </td>
                              <td className="py-2.5 font-semibold text-zinc-700">
                                {ord.store_name}
                              </td>
                              <td className="py-2.5 text-zinc-500">
                                {new Date(ord.created_at).toLocaleString("pt-BR", {
                                  day: "2-digit",
                                  month: "2-digit",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </td>
                              <td className="py-2.5 text-right font-bold text-emerald-700">
                                {formatCurrency(ord.cash_amount_reais)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Settlement Modal */}
      {settlingDriver && (
        <div className="fixed inset-0 bg-zinc-900/40 backdrop-blur-sm z-[1000] flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-zinc-200 p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div>
                <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider block">
                  Conferência de Dinheiro
                </span>
                <h3 className="text-base font-bold text-zinc-900">
                  Quitar Acerto em Espécie
                </h3>
              </div>
              <button
                onClick={() => setSettlingDriver(null)}
                className="p-1.5 text-zinc-400 hover:text-zinc-600 rounded-lg hover:bg-zinc-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Motoboy Summary */}
            <div className="bg-zinc-50 border border-zinc-200 rounded-xl p-3.5 space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Entregador:</span>
                <span className="font-bold text-zinc-900">
                  {settlingDriver.driver_name}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Dinheiro Coletado:</span>
                <span className="font-bold text-zinc-900">
                  {formatCurrency(settlingDriver.cash_collected_reais)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Ganhos do Condutor:</span>
                <span className="font-bold text-blue-700">
                  {formatCurrency(settlingDriver.driver_earnings_reais)}
                </span>
              </div>
              <div className="flex justify-between text-xs border-t border-zinc-200/80 pt-1.5">
                <span className="font-bold text-zinc-700">Líquido Devido à Base:</span>
                <span className="font-black text-amber-600">
                  {formatCurrency(settlingDriver.net_due_operator_reais)}
                </span>
              </div>
            </div>

            {/* Input Amount */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-zinc-700 block">
                Valor a Quitar / Baixar (R$) *
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm font-bold text-zinc-400">
                  R$
                </span>
                <input
                  type="number"
                  step="0.01"
                  value={settleAmount}
                  onChange={(e) => setSettleAmount(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-zinc-300 rounded-xl font-bold text-zinc-900 focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                />
              </div>
            </div>

            {/* Notes */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-zinc-700 block">
                Observações do Acerto (Opcional)
              </label>
              <textarea
                value={settleNotes}
                onChange={(e) => setSettleNotes(e.target.value)}
                placeholder="Ex: Entregue fisicamente na base pelo condutor..."
                className="w-full px-3.5 py-2 text-sm bg-white border border-zinc-300 rounded-xl text-zinc-800 focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 resize-none min-h-[70px]"
              />
            </div>

            {/* Modal Buttons */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100">
              <button
                type="button"
                onClick={() => setSettlingDriver(null)}
                disabled={isSubmittingSettle}
                className="px-4 py-2 border border-zinc-200 bg-white text-zinc-700 rounded-xl hover:bg-zinc-50 text-xs font-bold transition-all"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleConfirmSettle}
                disabled={isSubmittingSettle}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-sm transition-all flex items-center gap-1.5"
              >
                {isSubmittingSettle ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Check className="w-4 h-4" /> Confirmar Baixa
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

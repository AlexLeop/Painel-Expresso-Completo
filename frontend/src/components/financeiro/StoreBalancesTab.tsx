import React, { useState, useEffect } from "react";
import {
  Store,
  Wallet,
  TrendingDown,
  TrendingUp,
  AlertCircle,
  Search,
  Filter,
  ArrowUpDown,
  RefreshCw,
  Plus,
  Minus,
  CheckCircle2,
  X,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { authFetch } from "../../lib/api";
import { formatCurrency, cn } from "../../lib/utils";

interface StoreBalanceItem {
  id: string;
  name: string;
  client_name: string;
  document: string;
  city: string;
  responsible: string;
  email: string;
  billing_mode: string;
  balance_cents: number;
  balance_reais: number;
  status: "DEVEDOR" | "ZERADO" | "EM_DIA";
}

interface StoreBalancesResponse {
  kpis: {
    total_em_debito_reais: number;
    total_em_credito_reais: number;
    total_de_lojas: number;
    lojas_em_debito: number;
  };
  stores: StoreBalanceItem[];
}

export function StoreBalancesTab() {
  const [data, setData] = useState<StoreBalancesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<"debt" | "credit" | "name">("debt");

  // Modal de Ajuste
  const [adjustingStore, setAdjustingStore] = useState<StoreBalanceItem | null>(null);
  const [direction, setDirection] = useState<"CREDIT" | "DEBIT">("CREDIT");
  const [amountInput, setAmountInput] = useState("");
  const [category, setCategory] = useState<string>("BONUS");
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchBalances = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch("/api/v1/operator/store-balances");
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        setError("Não foi possível carregar o saldo das lojas.");
      }
    } catch (err: any) {
      setError(err.message || "Erro de conexão ao buscar saldos.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBalances();
  }, []);

  const handleAdjustSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adjustingStore) return;
    const amountVal = parseFloat(amountInput.replace(",", "."));
    if (!amountVal || isNaN(amountVal) || amountVal <= 0) {
      alert("Por favor, digite um valor válido.");
      return;
    }
    if (!reason.trim()) {
      alert("A justificativa é obrigatória para fins de auditoria.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await authFetch("/api/v1/operator/adjust-store-balance", {
        method: "POST",
        body: JSON.stringify({
          store_id: adjustingStore.id,
          amount_cents: Math.round(amountVal * 100),
          direction,
          category,
          reason: reason.trim(),
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Erro ao ajustar saldo.");
      }

      setActionSuccess(`Saldo de ${adjustingStore.name} ajustado com sucesso!`);
      setAdjustingStore(null);
      setAmountInput("");
      setReason("");
      fetchBalances();
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(err.message || "Falha ao ajustar saldo.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const stores = data?.stores || [];

  const filteredStores = stores
    .filter((s) => {
      if (!searchTerm) return true;
      const q = searchTerm.toLowerCase();
      return (
        s.name.toLowerCase().includes(q) ||
        s.client_name.toLowerCase().includes(q) ||
        s.email.toLowerCase().includes(q) ||
        s.document.includes(q)
      );
    })
    .sort((a, b) => {
      if (sortBy === "debt") return a.balance_reais - b.balance_reais; // Menor (mais negativo) primeiro
      if (sortBy === "credit") return b.balance_reais - a.balance_reais; // Maior primeiro
      return a.name.localeCompare(b.name);
    });

  return (
    <div className="space-y-6">
      {/* Toast Feedback */}
      {actionSuccess && (
        <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-xl flex items-center gap-3 text-emerald-800 dark:text-emerald-300 text-sm">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl flex items-center gap-3 text-rose-800 dark:text-rose-300 text-sm">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top KPIs — Módulo 18 MotorK */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Total em Débito */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Total em Débito
            </span>
            <div className="h-8 w-8 rounded-xl bg-rose-100 dark:bg-rose-950 flex items-center justify-center text-rose-700 dark:text-rose-300">
              <TrendingDown className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-rose-600 dark:text-rose-400 tracking-tight">
              {data ? formatCurrency(data.kpis.total_em_debito_reais) : "R$ 0,00"}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              {data ? `${data.kpis.lojas_em_debito} loja(s) com saldo devedor` : "0 lojas"}
            </p>
          </div>
        </div>

        {/* Total em Crédito */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Total em Crédito
            </span>
            <div className="h-8 w-8 rounded-xl bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-700 dark:text-emerald-300">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400 tracking-tight">
              {data ? formatCurrency(data.kpis.total_em_credito_reais) : "R$ 0,00"}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Pagamentos e recargas antecipadas</p>
          </div>
        </div>

        {/* Total de Lojas */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Total de Lojas
            </span>
            <div className="h-8 w-8 rounded-xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-700 dark:text-zinc-300">
              <Store className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
              {data ? data.kpis.total_de_lojas : 0}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Lojas parceiras cadastradas</p>
          </div>
        </div>
      </div>

      {/* Controles de Busca e Ordenação */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="h-4 w-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por loja, empresa ou e-mail..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs font-semibold bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800/80 p-1 rounded-xl">
            <button
              onClick={() => setSortBy("debt")}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all",
                sortBy === "debt"
                  ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm"
                  : "text-zinc-600 dark:text-zinc-400"
              )}
            >
              Maior dívida primeiro
            </button>
            <button
              onClick={() => setSortBy("credit")}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all",
                sortBy === "credit"
                  ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm"
                  : "text-zinc-600 dark:text-zinc-400"
              )}
            >
              Maior saldo primeiro
            </button>
            <button
              onClick={() => setSortBy("name")}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all",
                sortBy === "name"
                  ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm"
                  : "text-zinc-600 dark:text-zinc-400"
              )}
            >
              Por Nome
            </button>
          </div>

          <button
            onClick={fetchBalances}
            disabled={loading}
            className="p-2 border border-zinc-200 dark:border-zinc-800 rounded-xl hover:bg-zinc-50 dark:hover:bg-zinc-800"
            title="Atualizar dados"
          >
            <RefreshCw className={cn("h-4 w-4 text-zinc-600", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Tabela de Lojas e Saldos */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 text-[10px] uppercase font-bold tracking-wider text-zinc-500">
              <tr>
                <th className="px-6 py-3">Loja</th>
                <th className="px-6 py-3">Responsável</th>
                <th className="px-6 py-3">Cobrança</th>
                <th className="px-6 py-3 text-right">Saldo Atual</th>
                <th className="px-6 py-3 text-center">Status</th>
                <th className="px-6 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-zinc-500 text-xs">
                    <div className="flex items-center justify-center gap-2">
                      <RefreshCw className="h-4 w-4 animate-spin text-zinc-400" />
                      <span>Carregando saldos das lojas...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredStores.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-zinc-500 text-xs">
                    Nenhuma loja encontrada para os filtros selecionados.
                  </td>
                </tr>
              ) : (
                filteredStores.map((store) => (
                  <tr
                    key={store.id}
                    className="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition-colors"
                  >
                    <td className="px-6 py-3.5 font-medium text-zinc-900 dark:text-zinc-100">
                      <div className="flex items-center gap-2.5">
                        <div className="h-8 w-8 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-700 dark:text-zinc-300 shrink-0">
                          <Store className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="font-bold text-zinc-900 dark:text-zinc-100">
                            {store.name}
                          </div>
                          <div className="text-[11px] text-zinc-500">
                            {store.client_name || "Cliente Parceiro"} {store.document ? `• ${store.document}` : ""}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-3.5 text-xs text-zinc-600 dark:text-zinc-400">
                      <div>{store.responsible || store.email || "—"}</div>
                      {store.city && <div className="text-[10px] text-zinc-400">{store.city}</div>}
                    </td>
                    <td className="px-6 py-3.5 text-xs">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-[11px]">
                        {store.billing_mode === "POS_PAGO" ? "Pós-Pago" : "Pré-Pago"}
                      </span>
                    </td>
                    <td
                      className={cn(
                        "px-6 py-3.5 text-right font-black text-sm",
                        store.balance_reais < 0
                          ? "text-rose-600 dark:text-rose-400"
                          : store.balance_reais > 0
                            ? "text-emerald-600 dark:text-emerald-400"
                            : "text-zinc-900 dark:text-zinc-100"
                      )}
                    >
                      {formatCurrency(store.balance_reais)}
                    </td>
                    <td className="px-6 py-3.5 text-center">
                      {store.status === "DEVEDOR" ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300">
                          DEVEDOR
                        </span>
                      ) : store.status === "EM_DIA" ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300">
                          EM DIA
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300">
                          ZERADO
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <button
                        onClick={() => {
                          setAdjustingStore(store);
                          setDirection("CREDIT");
                          setAmountInput("");
                          setReason("");
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 text-xs font-bold rounded-lg hover:opacity-90 transition-opacity shadow-xs"
                      >
                        Ajustar
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Ajustar Saldo */}
      <AnimatePresence>
        {adjustingStore && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-900/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4"
            >
              <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3">
                <div>
                  <h3 className="font-bold text-zinc-900 dark:text-zinc-100 text-base">
                    Ajustar Saldo da Loja
                  </h3>
                  <p className="text-xs text-zinc-500">{adjustingStore.name}</p>
                </div>
                <button
                  onClick={() => setAdjustingStore(null)}
                  className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-sm font-bold"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <form onSubmit={handleAdjustSubmit} className="space-y-4">
                {/* Saldo Atual */}
                <div className="p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-xl flex items-center justify-between text-xs">
                  <span className="text-zinc-500 font-medium">Saldo Atual:</span>
                  <span className="font-black text-sm text-zinc-900 dark:text-zinc-100">
                    {formatCurrency(adjustingStore.balance_reais)}
                  </span>
                </div>

                {/* Direção: Crédito ou Débito */}
                <div>
                  <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1.5">
                    Tipo de Ajuste:
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setDirection("CREDIT")}
                      className={cn(
                        "flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl border text-xs font-bold transition-all",
                        direction === "CREDIT"
                          ? "bg-emerald-600 text-white border-emerald-600 shadow-xs"
                          : "border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800"
                      )}
                    >
                      <Plus className="h-4 w-4" />
                      Crédito (+)
                    </button>
                    <button
                      type="button"
                      onClick={() => setDirection("DEBIT")}
                      className={cn(
                        "flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl border text-xs font-bold transition-all",
                        direction === "DEBIT"
                          ? "bg-rose-600 text-white border-rose-600 shadow-xs"
                          : "border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800"
                      )}
                    >
                      <Minus className="h-4 w-4" />
                      Débito (-)
                    </button>
                  </div>
                </div>

                {/* Valor */}
                <div>
                  <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1.5">
                    Valor (R$):
                  </label>
                  <div className="relative rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-500">
                      R$
                    </span>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      required
                      placeholder="0,00"
                      value={amountInput}
                      onChange={(e) => setAmountInput(e.target.value)}
                      className="w-full bg-transparent pl-9 pr-4 py-2.5 text-sm font-bold text-zinc-900 dark:text-zinc-100 focus:outline-none"
                    />
                  </div>
                </div>

                {/* Categoria */}
                <div>
                  <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1.5">
                    Categoria:
                  </label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full text-xs font-semibold bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-800 rounded-xl px-3 py-2.5 text-zinc-900 dark:text-zinc-100 focus:outline-none"
                  >
                    <option value="BONUS">Bônus Promocional / Bonificação</option>
                    <option value="REFUND">Estorno de Corrida / Corrida Indevida</option>
                    <option value="ADJUSTMENT">Ajuste de Conciliação Bancária</option>
                    <option value="PENALTY">Taxa Extraordinária / Penalidade</option>
                  </select>
                </div>

                {/* Motivo Obrigatório */}
                <div>
                  <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1.5">
                    Justificativa (Obrigatória para Auditoria):
                  </label>
                  <textarea
                    rows={3}
                    required
                    placeholder="Descreva o motivo do ajuste manual..."
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-800 rounded-xl p-3 text-zinc-900 dark:text-zinc-100 focus:outline-none"
                  />
                </div>

                <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setAdjustingStore(null)}
                    className="px-4 py-2 text-xs font-semibold text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-xl"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-5 py-2 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 text-xs font-bold rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    {isSubmitting ? "Gravando..." : "Confirmar Ajuste"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

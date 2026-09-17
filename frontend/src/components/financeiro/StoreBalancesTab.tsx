import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
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

  useEffect(() => {
    if (adjustingStore) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [adjustingStore]);

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
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-800 text-sm shadow-xs">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          <span className="font-medium">{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-800 text-sm shadow-xs">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {/* Top KPIs — Módulo 18 MotorK */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Total em Débito */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Total em Débito
            </span>
            <div className="h-8 w-8 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-700">
              <TrendingDown className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-rose-600 tracking-tight">
              {data ? formatCurrency(data.kpis.total_em_debito_reais) : "R$ 0,00"}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              {data ? `${data.kpis.lojas_em_debito} loja(s) com saldo devedor` : "0 lojas"}
            </p>
          </div>
        </div>

        {/* Total em Crédito */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Total em Crédito
            </span>
            <div className="h-8 w-8 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-700">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-emerald-600 tracking-tight">
              {data ? formatCurrency(data.kpis.total_em_credito_reais) : "R$ 0,00"}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Pagamentos e recargas antecipadas</p>
          </div>
        </div>

        {/* Total de Lojas */}
        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Total de Lojas
            </span>
            <div className="h-8 w-8 rounded-xl bg-zinc-100 flex items-center justify-center text-zinc-700">
              <Store className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-black text-zinc-900 tracking-tight">
              {data ? data.kpis.total_de_lojas : 0}
            </span>
            <p className="text-[11px] text-zinc-500 mt-0.5">Lojas parceiras cadastradas</p>
          </div>
        </div>
      </div>

      {/* Controles de Busca e Ordenação */}
      <div className="bg-white border border-zinc-200 rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="h-4 w-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por loja, empresa ou e-mail..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs font-semibold bg-zinc-50 border border-zinc-200 rounded-xl focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-zinc-100 p-1 rounded-xl">
            <button
              onClick={() => setSortBy("debt")}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer",
                sortBy === "debt"
                  ? "bg-white text-zinc-900 shadow-xs"
                  : "text-zinc-600 hover:text-zinc-900"
              )}
            >
              Maior dívida primeiro
            </button>
            <button
              onClick={() => setSortBy("credit")}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer",
                sortBy === "credit"
                  ? "bg-white text-zinc-900 shadow-xs"
                  : "text-zinc-600 hover:text-zinc-900"
              )}
            >
              Maior saldo primeiro
            </button>
            <button
              onClick={() => setSortBy("name")}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer",
                sortBy === "name"
                  ? "bg-white text-zinc-900 shadow-xs"
                  : "text-zinc-600 hover:text-zinc-900"
              )}
            >
              Por Nome
            </button>
          </div>

          <button
            onClick={fetchBalances}
            disabled={loading}
            className="p-2 border border-zinc-200 rounded-xl hover:bg-zinc-50 cursor-pointer"
            title="Atualizar dados"
          >
            <RefreshCw className={cn("h-4 w-4 text-zinc-600", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Tabela de Lojas e Saldos */}
      <div className="bg-white border border-zinc-200 rounded-2xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-zinc-50/80 border-b border-zinc-200 text-[10px] uppercase font-bold tracking-wider text-zinc-500">
              <tr>
                <th className="px-6 py-3">Loja</th>
                <th className="px-6 py-3">Responsável</th>
                <th className="px-6 py-3">Cobrança</th>
                <th className="px-6 py-3 text-right">Saldo Atual</th>
                <th className="px-6 py-3 text-center">Status</th>
                <th className="px-6 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
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
                  <td colSpan={6} className="px-6 py-12 text-center text-zinc-400 text-xs">
                    Nenhuma loja encontrada para os filtros selecionados.
                  </td>
                </tr>
              ) : (
                filteredStores.map((store) => (
                  <tr
                    key={store.id}
                    className="hover:bg-zinc-50/60 transition-colors"
                  >
                    <td className="px-6 py-3.5 font-medium text-zinc-900">
                      <div className="flex items-center gap-2.5">
                        <div className="h-8 w-8 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-700 shrink-0">
                          <Store className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="font-bold text-zinc-900">
                            {store.name}
                          </div>
                          <div className="text-[11px] text-zinc-500">
                            {store.client_name || "Cliente Parceiro"} {store.document ? `• ${store.document}` : ""}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-3.5 text-xs text-zinc-600">
                      <div>{store.responsible || store.email || "—"}</div>
                      {store.city && <div className="text-[10px] text-zinc-400">{store.city}</div>}
                    </td>
                    <td className="px-6 py-3.5 text-xs">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md font-semibold bg-zinc-100 text-zinc-700 text-[11px]">
                        {store.billing_mode === "POS_PAGO" ? "Pós-Pago" : "Pré-Pago"}
                      </span>
                    </td>
                    <td
                      className={cn(
                        "px-6 py-3.5 text-right font-black text-sm",
                        store.balance_reais < 0
                          ? "text-rose-600"
                          : store.balance_reais > 0
                            ? "text-emerald-600"
                            : "text-zinc-900"
                      )}
                    >
                      {formatCurrency(store.balance_reais)}
                    </td>
                    <td className="px-6 py-3.5 text-center">
                      {store.status === "DEVEDOR" ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                          DEVEDOR
                        </span>
                      ) : store.status === "EM_DIA" ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          EM DIA
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
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
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-zinc-900 text-white text-xs font-bold rounded-lg hover:bg-zinc-800 transition-colors shadow-xs cursor-pointer"
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
      {typeof document !== "undefined" &&
        createPortal(
          <AnimatePresence>
            {adjustingStore && (
              <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  onClick={() => setAdjustingStore(null)}
                  className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
                />

                <motion.div
                  initial={{ x: "100%" }}
                  animate={{ x: 0 }}
                  exit={{ x: "100%" }}
                  transition={{ type: "spring", damping: 28, stiffness: 260 }}
                  className="fixed top-0 right-0 h-full w-full max-w-lg md:max-w-xl bg-white shadow-2xl z-10 flex flex-col pointer-events-auto border-l border-zinc-200"
                >
                  {/* Header */}
                  <div className="px-6 md:px-8 py-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/80 backdrop-blur-xs shrink-0">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl shadow-sm shadow-emerald-500/20 text-white">
                        <Wallet className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-200/60 px-2 py-0.5 rounded-full">
                            Financeiro & Saldos
                          </span>
                        </div>
                        <h2 className="text-lg font-bold text-zinc-900 mt-0.5">
                          Ajustar Saldo da Loja
                        </h2>
                        <p className="text-xs text-zinc-500">{adjustingStore.name}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setAdjustingStore(null)}
                      className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-xl transition-colors cursor-pointer"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>

                  {/* Form & Body */}
                  <form
                    id="adjust-store-form"
                    onSubmit={handleAdjustSubmit}
                    className="flex-1 overflow-y-auto px-6 md:px-8 py-6 space-y-5"
                  >
                    {/* Saldo Atual */}
                    <div className="p-4 bg-zinc-50 border border-zinc-200/80 rounded-2xl flex items-center justify-between">
                      <div>
                        <span className="text-xs text-zinc-500 font-medium block">
                          Saldo Atual da Conta
                        </span>
                        <span className="text-[11px] text-zinc-400">
                          {adjustingStore.client_name || "Loja Cadastrada"}
                        </span>
                      </div>
                      <span className="font-black text-base text-zinc-900">
                        {formatCurrency(adjustingStore.balance_reais)}
                      </span>
                    </div>

                    {/* Direção: Crédito ou Débito */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-zinc-600 mb-2">
                        Tipo de Ajuste *
                      </label>
                      <div className="grid grid-cols-2 gap-2.5">
                        <button
                          type="button"
                          onClick={() => setDirection("CREDIT")}
                          className={cn(
                            "flex items-center justify-center gap-2 py-3 px-4 rounded-xl border text-xs font-bold transition-all cursor-pointer",
                            direction === "CREDIT"
                              ? "bg-emerald-600 text-white border-emerald-600 shadow-sm shadow-emerald-600/20"
                              : "border-zinc-200 text-zinc-700 hover:bg-zinc-50"
                          )}
                        >
                          <Plus className="h-4 w-4" />
                          Crédito (+)
                        </button>
                        <button
                          type="button"
                          onClick={() => setDirection("DEBIT")}
                          className={cn(
                            "flex items-center justify-center gap-2 py-3 px-4 rounded-xl border text-xs font-bold transition-all cursor-pointer",
                            direction === "DEBIT"
                              ? "bg-rose-600 text-white border-rose-600 shadow-sm shadow-rose-600/20"
                              : "border-zinc-200 text-zinc-700 hover:bg-zinc-50"
                          )}
                        >
                          <Minus className="h-4 w-4" />
                          Débito (-)
                        </button>
                      </div>
                    </div>

                    {/* Valor */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-zinc-600 mb-1.5">
                        Valor do Ajuste (R$) *
                      </label>
                      <div className="relative rounded-xl border border-zinc-200 bg-zinc-50/60 focus-within:border-zinc-900 focus-within:bg-white transition-all">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-400">
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
                          className="w-full bg-transparent pl-10 pr-4 py-3 text-sm font-bold text-zinc-900 focus:outline-none"
                        />
                      </div>
                    </div>

                    {/* Categoria */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-zinc-600 mb-1.5">
                        Categoria de Ajuste *
                      </label>
                      <select
                        value={category}
                        onChange={(e) => setCategory(e.target.value)}
                        className="w-full text-xs font-semibold bg-zinc-50/60 border border-zinc-200 rounded-xl px-3.5 py-3 text-zinc-900 focus:outline-none focus:bg-white focus:border-zinc-900 transition-all cursor-pointer"
                      >
                        <option value="BONUS">Bônus Promocional / Bonificação</option>
                        <option value="REFUND">Estorno de Corrida / Corrida Indevida</option>
                        <option value="ADJUSTMENT">Ajuste de Conciliação Bancária</option>
                        <option value="PENALTY">Taxa Extraordinária / Penalidade</option>
                      </select>
                    </div>

                    {/* Motivo Obrigatório */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-zinc-600 mb-1.5">
                        Justificativa (Obrigatória para Auditoria) *
                      </label>
                      <textarea
                        rows={3}
                        required
                        placeholder="Descreva detalhadamente o motivo do ajuste manual..."
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        className="w-full text-xs bg-zinc-50/60 border border-zinc-200 rounded-xl p-3 text-zinc-900 focus:outline-none focus:bg-white focus:border-zinc-900 transition-all resize-none"
                      />
                    </div>
                  </form>

                  {/* Standard Footer */}
                  <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex items-center justify-end gap-3 shrink-0">
                    <button
                      type="button"
                      onClick={() => setAdjustingStore(null)}
                      className="px-5 py-2.5 text-xs font-bold text-zinc-600 hover:text-zinc-900 hover:bg-zinc-200/60 rounded-xl transition-all cursor-pointer"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      form="adjust-store-form"
                      disabled={isSubmitting}
                      className="px-6 py-2.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold rounded-xl transition-all disabled:opacity-50 cursor-pointer shadow-sm"
                    >
                      {isSubmitting ? "Gravando..." : "Confirmar Ajuste"}
                    </button>
                  </div>
                </motion.div>
              </div>
            )}
          </AnimatePresence>,
          document.body
        )}
    </div>
  );
}

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  Wallet,
  TrendingDown,
  TrendingUp,
  Search,
  Filter,
  RefreshCw,
  Plus,
  Minus,
  CheckCircle2,
  X,
  History,
  FileText,
  User,
  Phone,
  Bike,
  CreditCard,
  AlertCircle,
  ArrowDownLeft,
  ArrowUpRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { authFetch } from "../../lib/api";
import { formatCurrency, cn } from "../../lib/utils";

interface DriverWalletItem {
  id: string;
  driver_id: string;
  name: string;
  phone: string;
  document: string;
  plate: string;
  vehicle_type: string;
  pixKey: string;
  pixKeyType: string;
  balance_cents: number;
  balance_reais: number;
  status: "CREDOR" | "DEVEDOR" | "ZERADO";
  active: boolean;
}

interface DriverWalletsResponse {
  kpis: {
    total_a_pagar_cents: number;
    total_a_pagar_reais: number;
    total_em_debito_cents: number;
    total_em_debito_reais: number;
    total_motoboys: number;
    motoboys_com_saldo: number;
  };
  drivers: DriverWalletItem[];
}

interface TransactionItem {
  id: string;
  created_at: string;
  category: string;
  tax_category: string;
  direction: "CREDIT" | "DEBIT";
  amount_cents: number;
  amount_reais: number;
  description: string;
}

export function DriverWalletsTab() {
  const [data, setData] = useState<DriverWalletsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "CREDOR" | "DEVEDOR" | "ZERADO">("ALL");

  // Modal de Ajuste
  const [adjustingDriver, setAdjustingDriver] = useState<DriverWalletItem | null>(null);
  const [direction, setDirection] = useState<"CREDIT" | "DEBIT">("DEBIT");
  const [category, setCategory] = useState<string>("ADVANCE");
  const [amountInput, setAmountInput] = useState("");
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Modal de Extrato
  const [viewingStatementDriver, setViewingStatementDriver] = useState<DriverWalletItem | null>(null);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [loadingTransactions, setLoadingTransactions] = useState(false);

  useEffect(() => {
    if (adjustingDriver || viewingStatementDriver) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [adjustingDriver, viewingStatementDriver]);

  const fetchWallets = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch("/api/v1/operator/driver-wallets");
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        setError("Não foi possível carregar a carteira dos motoboys.");
      }
    } catch (err: any) {
      setError(err.message || "Erro de conexão ao buscar saldos dos motoboys.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWallets();
  }, []);

  const openStatement = async (driver: DriverWalletItem) => {
    setViewingStatementDriver(driver);
    setLoadingTransactions(true);
    setTransactions([]);
    try {
      const res = await authFetch(
        `/api/v1/operator/driver-wallet/transactions?driver_id=${driver.id}&limit=100`,
      );
      if (res.ok) {
        const json = await res.json();
        setTransactions(json.transactions || []);
      }
    } catch (err) {
      console.error("Erro ao carregar extrato:", err);
    } finally {
      setLoadingTransactions(false);
    }
  };

  const handleAdjustSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adjustingDriver) return;
    const amountVal = parseFloat(amountInput.replace(",", "."));
    if (!amountVal || isNaN(amountVal) || amountVal <= 0) {
      alert("Por favor, digite um valor maior que zero.");
      return;
    }
    if (!reason.trim()) {
      alert("A justificativa é obrigatória para fins de auditoria financeira.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await authFetch("/api/v1/operator/driver-wallet/adjust", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          driver_id: adjustingDriver.id,
          amount_cents: Math.round(amountVal * 100),
          direction,
          category,
          reason: reason.trim(),
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || errJson.error || "Erro ao processar lançamento na carteira.");
      }

      setActionSuccess(`Lançamento de R$ ${amountVal.toFixed(2)} processado com sucesso na carteira de ${adjustingDriver.name}!`);
      setAdjustingDriver(null);
      setAmountInput("");
      setReason("");
      fetchWallets();
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(err.message || "Falha ao processar lançamento.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const drivers = data?.drivers || [];
  const filteredDrivers = drivers.filter((d) => {
    const matchesSearch =
      d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.phone.includes(searchTerm) ||
      (d.plate && d.plate.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (d.pixKey && d.pixKey.includes(searchTerm));

    if (!matchesSearch) return false;
    if (statusFilter !== "ALL" && d.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Notificação de Sucesso */}
      {actionSuccess && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-emerald-800 shadow-sm"
        >
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
            <span className="text-sm font-semibold">{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-emerald-600 hover:text-emerald-900"
          >
            <X className="h-4 w-4" />
          </button>
        </motion.div>
      )}

      {/* Cards de KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total a Repassar */}
        <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Total a Repassar
              </p>
              <h3 className="text-2xl font-black text-emerald-600 mt-1">
                {formatCurrency(data?.kpis?.total_a_pagar_reais || 0)}
              </h3>
            </div>
            <div className="p-2.5 bg-emerald-50 rounded-xl text-emerald-600">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
          <p className="text-[11px] text-zinc-400 mt-3 flex items-center gap-1">
            Soma dos saldos positivos de motoristas a repassar
          </p>
        </div>

        {/* Total em Débito / Vales */}
        <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Adiantamentos / Vales
              </p>
              <h3 className="text-2xl font-black text-rose-600 mt-1">
                {formatCurrency(data?.kpis?.total_em_debito_reais || 0)}
              </h3>
            </div>
            <div className="p-2.5 bg-rose-50 rounded-xl text-rose-600">
              <TrendingDown className="h-5 w-5" />
            </div>
          </div>
          <p className="text-[11px] text-zinc-400 mt-3 flex items-center gap-1">
            Valores a compensar nas próximas diárias/corridas
          </p>
        </div>

        {/* Motoboys com Saldo */}
        <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Com Movimentação
              </p>
              <h3 className="text-2xl font-black text-zinc-900 mt-1">
                {data?.kpis?.motoboys_com_saldo || 0}
              </h3>
            </div>
            <div className="p-2.5 bg-blue-50 rounded-xl text-blue-600">
              <Wallet className="h-5 w-5" />
            </div>
          </div>
          <p className="text-[11px] text-zinc-400 mt-3 flex items-center gap-1">
            Motoboys com saldo em aberto diferente de zero
          </p>
        </div>

        {/* Total Motoboys Frota */}
        <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Total na Frota
              </p>
              <h3 className="text-2xl font-black text-zinc-900 mt-1">
                {data?.kpis?.total_motoboys || 0}
              </h3>
            </div>
            <div className="p-2.5 bg-zinc-50 rounded-xl text-zinc-600">
              <Bike className="h-5 w-5" />
            </div>
          </div>
          <p className="text-[11px] text-zinc-400 mt-3 flex items-center gap-1">
            Entregadores vinculados à operação
          </p>
        </div>
      </div>

      {/* Tabela de Carteira dos Motoboys */}
      <div className="bg-white rounded-2xl border border-zinc-200 shadow-xs overflow-hidden">
        {/* Barra Superior com Busca e Filtros */}
        <div className="p-5 border-b border-zinc-100 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-zinc-50/50">
          <div>
            <h3 className="text-base font-bold text-zinc-900">
              Gestão da Carteira dos Motoboys
            </h3>
            <p className="text-xs text-zinc-500 mt-0.5">
              Controle de saldos, lançamentos manuais de vales, diárias e extrato auditado por motorista.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Input de Busca */}
            <div className="relative flex-1 md:w-64">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar motoboy, telefone, placa..."
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:border-transparent transition-all shadow-xs"
              />
            </div>

            {/* Filtro de Status */}
            <select
              value={statusFilter}
              onChange={(e: any) => setStatusFilter(e.target.value)}
              className="py-1.5 px-3 text-xs bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900 transition-all shadow-xs font-medium text-zinc-700"
            >
              <option value="ALL">Todos os Saldos</option>
              <option value="CREDOR">A Pagar (Credores)</option>
              <option value="DEVEDOR">Em Débito (Vales)</option>
              <option value="ZERADO">Zerados</option>
            </select>

            {/* Botão de Atualizar */}
            <button
              onClick={fetchWallets}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border border-zinc-200 text-zinc-700 rounded-xl hover:bg-zinc-50 text-xs font-semibold shadow-xs transition-all disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
              Atualizar
            </button>
          </div>
        </div>

        {/* Tabela */}
        <div className="overflow-x-auto">
          <table className="w-full text-left whitespace-nowrap text-sm">
            <thead className="bg-zinc-50/80 border-b border-zinc-200 text-zinc-500 text-[10px] font-bold uppercase tracking-wider">
              <tr>
                <th className="px-6 py-4">Motoboy</th>
                <th className="px-6 py-4">Telefone / PIX</th>
                <th className="px-6 py-4">Veículo / Placa</th>
                <th className="px-6 py-4 text-right">Saldo da Carteira</th>
                <th className="px-6 py-4 text-center">Situação</th>
                <th className="px-6 py-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-zinc-400 text-sm">
                    <div className="flex items-center justify-center gap-2 font-medium">
                      <RefreshCw className="h-4 w-4 animate-spin text-zinc-400" />
                      Carregando carteira dos motoboys...
                    </div>
                  </td>
                </tr>
              ) : filteredDrivers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-zinc-400 text-sm">
                    Nenhum motoboy encontrado.
                  </td>
                </tr>
              ) : (
                filteredDrivers.map((driver) => (
                  <tr key={driver.id} className="hover:bg-zinc-50/50 transition-colors">
                    {/* Motoboy */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-full bg-zinc-100 flex items-center justify-center font-bold text-zinc-700 text-xs shrink-0">
                          {driver.name ? driver.name.substring(0, 2).toUpperCase() : "MB"}
                        </div>
                        <div>
                          <p className="font-bold text-zinc-900 leading-snug">{driver.name}</p>
                          <p className="text-[11px] text-zinc-400">
                            {driver.active ? "Ativo na frota" : "Inativo"}
                          </p>
                        </div>
                      </div>
                    </td>

                    {/* Telefone / PIX */}
                    <td className="px-6 py-4 text-xs">
                      <div className="text-zinc-700 font-medium flex items-center gap-1.5">
                        <Phone className="h-3 w-3 text-zinc-400" />
                        {driver.phone || "Sem telefone"}
                      </div>
                      {driver.pixKey && (
                        <div className="text-zinc-400 text-[11px] mt-0.5 flex items-center gap-1">
                          <CreditCard className="h-2.5 w-2.5" />
                          PIX: {driver.pixKey} ({driver.pixKeyType})
                        </div>
                      )}
                    </td>

                    {/* Veículo */}
                    <td className="px-6 py-4 text-xs">
                      <div className="flex items-center gap-1.5 font-medium text-zinc-700">
                        <Bike className="h-3.5 w-3.5 text-zinc-400" />
                        {driver.plate ? driver.plate : "Placa não informada"}
                      </div>
                      <span className="text-[10px] text-zinc-400 uppercase tracking-wider">
                        {driver.vehicle_type}
                      </span>
                    </td>

                    {/* Saldo da Carteira */}
                    <td className="px-6 py-4 text-right">
                      <span
                        className={cn(
                          "font-mono font-bold text-base",
                          driver.balance_reais > 0
                            ? "text-emerald-600"
                            : driver.balance_reais < 0
                              ? "text-rose-600"
                              : "text-zinc-900",
                        )}
                      >
                        {formatCurrency(driver.balance_reais)}
                      </span>
                      <p className="text-[10px] text-zinc-400 mt-0.5">
                        {driver.balance_reais > 0
                          ? "A receber da empresa"
                          : driver.balance_reais < 0
                            ? "Débito / Vale a descontar"
                            : "Conta zerada"}
                      </p>
                    </td>

                    {/* Situação */}
                    <td className="px-6 py-4 text-center">
                      {driver.status === "CREDOR" ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          A REPASSAR
                        </span>
                      ) : driver.status === "DEVEDOR" ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                          EM DÉBITO
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-zinc-100 text-zinc-700 border border-zinc-200">
                          ZERADO
                        </span>
                      )}
                    </td>

                    {/* Ações */}
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openStatement(driver)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                          title="Ver Extrato de Transações"
                        >
                          <History className="h-3.5 w-3.5" />
                          Extrato
                        </button>
                        <button
                          onClick={() => {
                            setAdjustingDriver(driver);
                            setDirection("DEBIT");
                            setCategory("ADVANCE");
                            setAmountInput("");
                            setReason("");
                          }}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold rounded-lg transition-colors shadow-xs cursor-pointer"
                        >
                          <Wallet className="h-3.5 w-3.5" />
                          Lançar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal / Drawer: Lançar na Carteira */}
      {typeof document !== "undefined" &&
        createPortal(
          <AnimatePresence>
            {adjustingDriver && (
              <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  onClick={() => setAdjustingDriver(null)}
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
                      <div className="p-2.5 bg-zinc-900 rounded-2xl shadow-sm text-white">
                        <Wallet className="h-5 w-5" />
                      </div>
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-700 bg-zinc-100 border border-zinc-200 px-2 py-0.5 rounded-full">
                          Lançamento na Carteira
                        </span>
                        <h2 className="text-lg font-bold text-zinc-900 mt-0.5">
                          {adjustingDriver.name}
                        </h2>
                        <p className="text-xs text-zinc-500">
                          Saldo atual:{" "}
                          <span
                            className={cn(
                              "font-bold font-mono",
                              adjustingDriver.balance_reais >= 0
                                ? "text-emerald-600"
                                : "text-rose-600",
                            )}
                          >
                            {formatCurrency(adjustingDriver.balance_reais)}
                          </span>
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setAdjustingDriver(null)}
                      className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-xl transition-colors cursor-pointer"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>

                  {/* Form */}
                  <form
                    onSubmit={handleAdjustSubmit}
                    className="p-6 md:p-8 space-y-6 flex-1 overflow-y-auto"
                  >
                    {/* Tipo de Operação */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                        Tipo de Movimentação
                      </label>
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          type="button"
                          onClick={() => {
                            setDirection("DEBIT");
                            setCategory("ADVANCE");
                          }}
                          className={cn(
                            "flex items-center justify-center gap-2 p-3.5 rounded-xl border text-xs font-bold transition-all cursor-pointer",
                            direction === "DEBIT"
                              ? "bg-rose-50 border-rose-200 text-rose-700 shadow-xs ring-1 ring-rose-300"
                              : "bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50",
                          )}
                        >
                          <Minus className="h-4 w-4 text-rose-500" />
                          Débito / Desconto
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setDirection("CREDIT");
                            setCategory("BONUS");
                          }}
                          className={cn(
                            "flex items-center justify-center gap-2 p-3.5 rounded-xl border text-xs font-bold transition-all cursor-pointer",
                            direction === "CREDIT"
                              ? "bg-emerald-50 border-emerald-200 text-emerald-700 shadow-xs ring-1 ring-emerald-300"
                              : "bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50",
                          )}
                        >
                          <Plus className="h-4 w-4 text-emerald-500" />
                          Crédito / Bônus
                        </button>
                      </div>
                    </div>

                    {/* Categoria do Lançamento */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                        Categoria Contábil
                      </label>
                      <select
                        value={category}
                        onChange={(e) => setCategory(e.target.value)}
                        className="w-full px-3.5 py-2.5 text-xs bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900 transition-all shadow-xs text-zinc-900 font-medium"
                      >
                        {direction === "DEBIT" ? (
                          <>
                            <option value="ADVANCE">Adiantamento / Vale de Combustível</option>
                            <option value="PENALTY">Penalidade / Avaria / Extravio</option>
                            <option value="ADJUSTMENT">Ajuste Contábil Negativo</option>
                          </>
                        ) : (
                          <>
                            <option value="BONUS">Bônus / Corrida Extra</option>
                            <option value="DAILY_SETTLEMENT">Diária Adicional</option>
                            <option value="ADJUSTMENT">Ajuste Contábil Positivo</option>
                            <option value="REFUND">Reembolso / Estorno</option>
                          </>
                        )}
                      </select>
                    </div>

                    {/* Valor em R$ */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                        Valor (R$)
                      </label>
                      <div className="relative">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm font-bold text-zinc-400">
                          R$
                        </span>
                        <input
                          type="text"
                          required
                          value={amountInput}
                          onChange={(e) => setAmountInput(e.target.value)}
                          placeholder="0,00"
                          className="w-full pl-10 pr-3.5 py-2.5 text-base font-bold font-mono bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900 transition-all shadow-xs"
                        />
                      </div>
                    </div>

                    {/* Justificativa */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                        Justificativa / Motivo (Obrigatório)
                      </label>
                      <textarea
                        required
                        rows={3}
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Ex: Adiantamento solicitado para abastecimento do turno da tarde."
                        className="w-full p-3 text-xs bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900 transition-all shadow-xs resize-none"
                      />
                    </div>

                    {/* Ações */}
                    <div className="pt-4 border-t border-zinc-100 flex items-center justify-end gap-3">
                      <button
                        type="button"
                        onClick={() => setAdjustingDriver(null)}
                        className="px-4 py-2.5 text-xs font-bold text-zinc-600 hover:bg-zinc-100 rounded-xl transition-colors cursor-pointer"
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        disabled={isSubmitting}
                        className="px-6 py-2.5 text-xs font-bold text-white bg-zinc-900 hover:bg-zinc-800 rounded-xl shadow-sm transition-all disabled:opacity-50 cursor-pointer flex items-center gap-2"
                      >
                        {isSubmitting ? (
                          <>
                            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                            Processando...
                          </>
                        ) : (
                          "Confirmar Lançamento"
                        )}
                      </button>
                    </div>
                  </form>
                </motion.div>
              </div>
            )}
          </AnimatePresence>,
          document.body,
        )}

      {/* Modal / Drawer: Extrato de Transações */}
      {typeof document !== "undefined" &&
        createPortal(
          <AnimatePresence>
            {viewingStatementDriver && (
              <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  onClick={() => setViewingStatementDriver(null)}
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
                      <div className="p-2.5 bg-blue-500 rounded-2xl shadow-sm text-white">
                        <History className="h-5 w-5" />
                      </div>
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                          Extrato Contábil
                        </span>
                        <h2 className="text-lg font-bold text-zinc-900 mt-0.5">
                          {viewingStatementDriver.name}
                        </h2>
                        <p className="text-xs text-zinc-500">
                          Saldo atual:{" "}
                          <span
                            className={cn(
                              "font-bold font-mono",
                              viewingStatementDriver.balance_reais >= 0
                                ? "text-emerald-600"
                                : "text-rose-600",
                            )}
                          >
                            {formatCurrency(viewingStatementDriver.balance_reais)}
                          </span>
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setViewingStatementDriver(null)}
                      className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-xl transition-colors cursor-pointer"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>

                  {/* Lista de Transações */}
                  <div className="p-6 md:p-8 flex-1 overflow-y-auto space-y-3">
                    {loadingTransactions ? (
                      <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400 text-xs">
                        <RefreshCw className="h-5 w-5 animate-spin" />
                        Carregando histórico de transações...
                      </div>
                    ) : transactions.length === 0 ? (
                      <div className="py-12 text-center text-zinc-400 text-xs">
                        Nenhuma transação registrada nesta carteira até o momento.
                      </div>
                    ) : (
                      transactions.map((tx) => (
                        <div
                          key={tx.id}
                          className="p-3.5 rounded-xl border border-zinc-200/80 bg-white hover:bg-zinc-50/50 transition-colors flex items-center justify-between shadow-xs"
                        >
                          <div className="flex items-center gap-3">
                            <div
                              className={cn(
                                "p-2 rounded-xl text-white shrink-0",
                                tx.direction === "CREDIT"
                                  ? "bg-emerald-500"
                                  : "bg-rose-500",
                              )}
                            >
                              {tx.direction === "CREDIT" ? (
                                <ArrowDownLeft className="h-4 w-4" />
                              ) : (
                                <ArrowUpRight className="h-4 w-4" />
                              )}
                            </div>
                            <div>
                              <p className="text-xs font-bold text-zinc-900 leading-tight">
                                {tx.description || tx.category}
                              </p>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[10px] font-semibold text-zinc-400">
                                  {tx.created_at
                                    ? new Date(tx.created_at).toLocaleString("pt-BR", {
                                        day: "2-digit",
                                        month: "2-digit",
                                        hour: "2-digit",
                                        minute: "2-digit",
                                      })
                                    : "Data indisponível"}
                                </span>
                                <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.2 rounded bg-zinc-100 text-zinc-600">
                                  {tx.category}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="text-right">
                            <span
                              className={cn(
                                "font-mono font-bold text-sm",
                                tx.direction === "CREDIT"
                                  ? "text-emerald-600"
                                  : "text-rose-600",
                              )}
                            >
                              {tx.direction === "CREDIT" ? "+" : "-"}
                              {formatCurrency(tx.amount_reais)}
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              </div>
            )}
          </AnimatePresence>,
          document.body,
        )}
    </div>
  );
}

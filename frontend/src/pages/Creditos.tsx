import React, { useState, useEffect } from "react";
import {
  Wallet,
  Plus,
  QrCode,
  Copy,
  Check,
  Clock,
  ArrowUpRight,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
  Receipt,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { authFetch, getSession } from "../lib/api";
import { formatCurrency, cn } from "../lib/utils";

interface BalanceData {
  store_id?: string;
  store_name?: string;
  client_name?: string;
  billing_mode?: string;
  balance_cents: number;
  balance_reais: number;
  status: "DISPONIVEL" | "ZERADO" | "DEVEDOR";
  total_credits_cents?: number;
  total_debits_cents?: number;
  credit_limit_cents?: number;
}

interface InvoiceItem {
  id: string;
  description: string;
  amount_cents: number;
  amount_reais: number;
  status: "PENDING" | "PAID" | "DRAFT" | "LOCKED";
  created_at: string;
  pix_copy_paste?: string;
}

interface RechargeResponse {
  recharge_id: string;
  amount_cents: number;
  amount_reais: number;
  status: string;
  pix_copy_paste: string;
  pix_qr_code_base64?: string;
  expires_at?: string;
}

export function Creditos() {
  const session = getSession();
  const [balance, setBalance] = useState<BalanceData | null>(null);
  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Recarga selecionada
  const [selectedPack, setSelectedPack] = useState<number>(100);
  const [customAmount, setCustomAmount] = useState<string>("");
  const [isRechargeModalOpen, setIsRechargeModalOpen] = useState(false);
  const [rechargeData, setRechargeData] = useState<RechargeResponse | null>(null);
  const [isGeneratingPix, setIsGeneratingPix] = useState(false);
  const [copied, setCopied] = useState(false);
  const [simulatingPayment, setSimulatingPayment] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const fetchBalanceAndHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const [balRes, histRes] = await Promise.all([
        authFetch("/api/v1/client/balance"),
        authFetch("/api/v1/client/billing-history"),
      ]);

      if (balRes.ok) {
        const balData = await balRes.json();
        setBalance(balData);
      } else {
        setError("Não foi possível carregar o saldo atual da loja.");
      }

      if (histRes.ok) {
        const histData = await histRes.json();
        setInvoices(Array.isArray(histData) ? histData : histData.items || []);
      }
    } catch (err: any) {
      setError(err.message || "Erro de conexão com o servidor.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBalanceAndHistory();
  }, []);

  const handleRechargeSubmit = async () => {
    const finalAmount = customAmount ? parseFloat(customAmount.replace(",", ".")) : selectedPack;
    if (!finalAmount || isNaN(finalAmount) || finalAmount <= 0) {
      alert("Por favor, selecione ou digite um valor válido.");
      return;
    }

    const amountCents = Math.round(finalAmount * 100);
    setIsGeneratingPix(true);
    setError(null);

    try {
      const res = await authFetch("/api/v1/client/recharge", {
        method: "POST",
        body: JSON.stringify({ amount_cents: amountCents }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Erro ao gerar PIX para recarga.");
      }

      const data: RechargeResponse = await res.json();
      setRechargeData(data);
      setIsRechargeModalOpen(true);
    } catch (err: any) {
      setError(err.message || "Erro ao gerar PIX.");
    } finally {
      setIsGeneratingPix(false);
    }
  };

  const handleCopyPix = () => {
    if (!rechargeData?.pix_copy_paste) return;
    navigator.clipboard.writeText(rechargeData.pix_copy_paste);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleConfirmSimulation = async () => {
    if (!rechargeData?.recharge_id) return;
    setSimulatingPayment(true);
    try {
      // Confirmação simulada em desenvolvimento
      const res = await authFetch("/api/v1/client/recharge/confirm-simulation", {
        method: "POST",
        body: JSON.stringify({ recharge_id: rechargeData.recharge_id }),
      });
      if (res.ok) {
        setSuccessToast("Pagamento confirmado com sucesso! Saldo atualizado.");
        setIsRechargeModalOpen(false);
        fetchBalanceAndHistory();
        setTimeout(() => setSuccessToast(null), 4000);
      } else {
        // Fallback: recarrega dados diretamente
        fetchBalanceAndHistory();
        setIsRechargeModalOpen(false);
      }
    } catch {
      fetchBalanceAndHistory();
      setIsRechargeModalOpen(false);
    } finally {
      setSimulatingPayment(false);
    }
  };

  const packs = [
    { value: 50, label: "+ R$ 50,00" },
    { value: 100, label: "+ R$ 100,00", popular: true },
    { value: 200, label: "+ R$ 200,00" },
    { value: 500, label: "+ R$ 500,00" },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800 pb-4">
        <div>
          <nav className="text-xs text-zinc-500 mb-1 flex items-center gap-1">
            <span>Financeiro</span>
            <span>/</span>
            <span className="text-zinc-900 dark:text-zinc-100 font-medium">Créditos & Cobrança</span>
          </nav>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
            Créditos & Cobrança
          </h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-0.5">
            Gerencie seu saldo disponível para pedidos, adicione créditos via PIX e consulte faturas.
          </p>
        </div>

        <button
          onClick={fetchBalanceAndHistory}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors shadow-sm self-start sm:self-auto"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Atualizar
        </button>
      </div>

      {successToast && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-xl flex items-center gap-3 text-emerald-800 dark:text-emerald-300 text-sm"
        >
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          <span>{successToast}</span>
        </motion.div>
      )}

      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl flex items-center gap-3 text-rose-800 dark:text-rose-300 text-sm">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid Principal: Saldo Atual + Adicionar Créditos */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card Saldo em Conta */}
        <div className="lg:col-span-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="h-9 w-9 rounded-xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-800 dark:text-zinc-200">
                  <Wallet className="h-5 w-5" />
                </div>
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  Saldo em Conta
                </span>
              </div>
              {balance?.status === "DISPONIVEL" && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  DISPONÍVEL
                </span>
              )}
              {balance?.status === "ZERADO" && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                  ZERADO
                </span>
              )}
              {balance?.status === "DEVEDOR" && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                  DEVEDOR
                </span>
              )}
            </div>

            <div className="mt-6">
              <span className="text-3xl sm:text-4xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight">
                {balance ? formatCurrency(balance.balance_reais) : "R$ 0,00"}
              </span>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                {balance?.billing_mode === "POS_PAGO"
                  ? "Regime Faturado Semanal — Fechamento aos domingos."
                  : "Regime Pré-Pago — Créditos debitados automaticamente por corrida."}
              </p>
            </div>
          </div>

          <div className="mt-8 pt-4 border-t border-zinc-100 dark:border-zinc-800/80 space-y-2 text-xs text-zinc-600 dark:text-zinc-400">
            <div className="flex items-center justify-between">
              <span>Loja Ativa:</span>
              <span className="font-semibold text-zinc-900 dark:text-zinc-200">
                {balance?.store_name || session?.user?.name || "Minha Loja"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Operadora Logística:</span>
              <span className="font-semibold text-zinc-900 dark:text-zinc-200">
                Expresso Neves
              </span>
            </div>
          </div>
        </div>

        {/* Card Adicionar Créditos */}
        <div className="lg:col-span-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm space-y-5">
          <div>
            <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
              Adicionar Créditos via PIX
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              Escolha um pacote de créditos ou informe um valor personalizado. A liberação do saldo é instantânea após o pagamento.
            </p>
          </div>

          {/* Pacotes rápidos */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {packs.map((pack) => {
              const isSelected = selectedPack === pack.value && !customAmount;
              return (
                <button
                  key={pack.value}
                  type="button"
                  onClick={() => {
                    setSelectedPack(pack.value);
                    setCustomAmount("");
                  }}
                  className={cn(
                    "relative flex flex-col items-center justify-center p-4 rounded-xl border text-sm font-semibold transition-all",
                    isSelected
                      ? "border-zinc-900 dark:border-zinc-100 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 shadow-sm"
                      : "border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 text-zinc-900 dark:text-zinc-200 hover:border-zinc-300 dark:hover:border-zinc-700"
                  )}
                >
                  {pack.popular && (
                    <span className="absolute -top-2.5 px-2 py-0.5 bg-emerald-600 text-[10px] font-bold text-white rounded-full uppercase tracking-wider">
                      Popular
                    </span>
                  )}
                  <span className="text-base">{pack.label}</span>
                </button>
              );
            })}
          </div>

          {/* Campo de valor personalizado */}
          <div className="pt-2">
            <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1.5">
              Ou digite outro valor (R$):
            </label>
            <div className="relative rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 focus-within:border-zinc-900 dark:focus-within:border-zinc-100 transition-colors">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-bold text-zinc-500">
                R$
              </span>
              <input
                type="number"
                min="10"
                step="5"
                placeholder="Ex: 150,00"
                value={customAmount}
                onChange={(e) => {
                  setCustomAmount(e.target.value);
                  setSelectedPack(0);
                }}
                className="w-full bg-transparent pl-10 pr-4 py-2.5 text-sm font-semibold text-zinc-900 dark:text-zinc-100 focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>Pagamento seguro via Banco Central do Brasil (PIX)</span>
            </div>

            <button
              onClick={handleRechargeSubmit}
              disabled={isGeneratingPix}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl text-sm transition-colors shadow-sm disabled:opacity-50"
            >
              <QrCode className="h-4 w-4" />
              {isGeneratingPix ? "Gerando PIX..." : "Gerar PIX de Recarga"}
            </button>
          </div>
        </div>
      </div>

      {/* Histórico de Faturas & Recargas */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Histórico de Pagamentos
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              Faturas e recargas de saldo geradas para a sua loja.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 text-[10px] uppercase font-bold tracking-wider text-zinc-500">
              <tr>
                <th className="px-6 py-3">Descrição</th>
                <th className="px-6 py-3">Data</th>
                <th className="px-6 py-3 text-right">Valor</th>
                <th className="px-6 py-3 text-center">Status</th>
                <th className="px-6 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {invoices.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-zinc-500 text-xs">
                    Nenhuma fatura ou recarga encontrada no período.
                  </td>
                </tr>
              ) : (
                invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-zinc-50/80 dark:hover:bg-zinc-800/40 transition-colors">
                    <td className="px-6 py-3.5 font-medium text-zinc-900 dark:text-zinc-100">
                      <div className="flex items-center gap-2">
                        <Receipt className="h-4 w-4 text-zinc-400" />
                        <span>{inv.description}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5 text-xs text-zinc-500">
                      {new Date(inv.created_at).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="px-6 py-3.5 text-right font-semibold text-zinc-900 dark:text-zinc-100">
                      {formatCurrency(inv.amount_reais)}
                    </td>
                    <td className="px-6 py-3.5 text-center">
                      {inv.status === "PAID" ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300">
                          PAGO
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300">
                          PENDENTE
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      {inv.status !== "PAID" && inv.pix_copy_paste ? (
                        <button
                          onClick={() => {
                            setRechargeData({
                              recharge_id: inv.id,
                              amount_cents: inv.amount_cents,
                              amount_reais: inv.amount_reais,
                              status: "PENDING",
                              pix_copy_paste: inv.pix_copy_paste || "",
                            });
                            setIsRechargeModalOpen(true);
                          }}
                          className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 hover:underline"
                        >
                          Ver PIX
                        </button>
                      ) : (
                        <span className="text-xs text-zinc-400">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Pagamento PIX */}
      <AnimatePresence>
        {isRechargeModalOpen && rechargeData && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-900/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-xl space-y-5"
            >
              <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-lg bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-700 dark:text-emerald-300">
                    <QrCode className="h-4 w-4" />
                  </div>
                  <h3 className="font-bold text-zinc-900 dark:text-zinc-100 text-base">
                    Pagamento via PIX
                  </h3>
                </div>
                <button
                  onClick={() => setIsRechargeModalOpen(false)}
                  className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-sm font-bold"
                >
                  ✕
                </button>
              </div>

              {/* Detalhes do Valor */}
              <div className="p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-xl text-center space-y-1">
                <span className="text-xs text-zinc-500 font-medium">Valor da Recarga</span>
                <div className="text-2xl font-extrabold text-zinc-900 dark:text-zinc-100">
                  {formatCurrency(rechargeData.amount_reais)}
                </div>
                <span className="text-[11px] text-zinc-500">
                  Beneficiário: Expresso Neves Logística LTDA
                </span>
              </div>

              {/* QR Code Container */}
              <div className="flex flex-col items-center justify-center p-4 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-950">
                {rechargeData.pix_qr_code_base64 ? (
                  <img
                    src={rechargeData.pix_qr_code_base64}
                    alt="QR Code PIX"
                    className="w-48 h-48 object-contain"
                  />
                ) : (
                  <div className="w-48 h-48 bg-zinc-100 dark:bg-zinc-900 rounded-lg flex flex-col items-center justify-center text-center p-2">
                    <QrCode className="h-20 w-20 text-zinc-800 dark:text-zinc-200 mb-2" />
                    <span className="text-[10px] text-zinc-500">QR Code gerado para leitura</span>
                  </div>
                )}
                <div className="flex items-center gap-1.5 mt-3 text-xs text-zinc-500">
                  <Clock className="h-3.5 w-3.5 text-amber-500" />
                  <span>Expira em 15 minutos</span>
                </div>
              </div>

              {/* PIX Copia e Cola */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  PIX Copia e Cola:
                </label>
                <div className="relative">
                  <input
                    type="text"
                    readOnly
                    value={rechargeData.pix_copy_paste}
                    className="w-full bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-700 dark:text-zinc-300 font-mono pr-20 select-all"
                  />
                  <button
                    onClick={handleCopyPix}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 px-2.5 py-1 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 text-xs font-semibold rounded-lg hover:opacity-90 transition-opacity flex items-center gap-1"
                  >
                    {copied ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span>Copiado!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>Copiar</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Ações de simulação/verificação */}
              <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800 space-y-2">
                <button
                  onClick={handleConfirmSimulation}
                  disabled={simulatingPayment}
                  className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  {simulatingPayment ? "Processando..." : "Confirmar Pagamento (Simulação Instantânea)"}
                </button>
                <button
                  onClick={() => setIsRechargeModalOpen(false)}
                  className="w-full py-2 text-xs font-medium text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                >
                  Fechar janela
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

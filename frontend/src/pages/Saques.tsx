import React, { useState, useEffect, useCallback, useMemo } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowDownToLine,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  AlertTriangle,
  Sliders,
  DollarSign,
  Copy,
  Check,
  Search,
  Filter,
  Eye,
  ShieldAlert,
  Send,
  Bell,
  MessageSquare,
  Smartphone,
  ExternalLink,
  ChevronRight,
  Info,
  X,
} from "lucide-react";
import { authFetch } from "../lib/api";
import { formatCurrency, cn } from "../lib/utils";

interface WithdrawalItem {
  id: string;
  condutor_id: string;
  condutor_name?: string;
  amount_cents: number;
  fee_amount_cents: number;
  net_amount_cents: number;
  status: "PENDING" | "PROCESSING" | "PAID" | "REJECTED" | "FAILED";
  approval_mode: "AUTO_INSTANT" | "MANUAL_APPROVAL";
  pix_key_type?: string;
  pix_key: string;
  rejection_reason?: string;
  baas_tx_id?: string;
  baas_e2e_id?: string;
  created_at: string;
  approved_at?: string;
  paid_at?: string;
}

interface PayoutPolicyConfig {
  approval_mode: "HYBRID_THRESHOLD" | "MANUAL_ALL";
  auto_approval_threshold_cents: number;
  daily_limit_per_driver_cents: number;
  fee_mode: "ABSORBED_BY_PLATFORM" | "CHARGED_TO_DRIVER";
  payout_fee_cents: number;
  notify_push_enabled: boolean;
  notify_whatsapp_enabled: boolean;
  allow_nightly_payouts: boolean;
  is_active: boolean;
}

interface BaasBalance {
  saldo: number;
  saldo_cents: number;
  bloqueado: number;
  mock: boolean;
}

export function Saques() {
  const [withdrawals, setWithdrawals] = useState<WithdrawalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Status Filter & Search
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  // Modals
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedWithdrawalForReject, setSelectedWithdrawalForReject] = useState<WithdrawalItem | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [processingAction, setProcessingAction] = useState(false);

  // Policy Modal
  const [policyModalOpen, setPolicyModalOpen] = useState(false);
  const [policyConfig, setPolicyConfig] = useState<PayoutPolicyConfig | null>(null);
  const [savingPolicy, setSavingPolicy] = useState(false);

  // BaaS Balance
  const [baasBalance, setBaasBalance] = useState<BaasBalance | null>(null);
  const [loadingBalance, setLoadingBalance] = useState(false);

  // Details Modal
  const [detailsModalItem, setDetailsModalItem] = useState<WithdrawalItem | null>(null);

  useEffect(() => {
    if (rejectModalOpen || detailsModalItem || policyModalOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [rejectModalOpen, detailsModalItem, policyModalOpen]);

  // Feedback Notification
  const [toastMessage, setToastMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const showToast = (text: string, type: "success" | "error" = "success") => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // 1. Fetch Withdrawals
  const loadWithdrawals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = statusFilter === "ALL" 
        ? "/api/v1/admin/finance/withdrawals?limit=100" 
        : `/api/v1/admin/finance/withdrawals?status=${statusFilter}&limit=100`;
      const res = await authFetch(url);
      if (!res.ok) {
        throw new Error(`Erro ao carregar saques: ${res.status}`);
      }
      const data = await res.json();
      setWithdrawals(Array.isArray(data) ? data : data.items || []);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Falha ao carregar lista de saques.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  // 2. Fetch BaaS Balance
  const loadBaasBalance = useCallback(async () => {
    setLoadingBalance(true);
    try {
      const res = await authFetch("/api/v1/admin/finance/baas-balance");
      if (res.ok) {
        const data = await res.json();
        setBaasBalance(data);
      }
    } catch (err) {
      console.error("Falha ao buscar saldo Efí:", err);
    } finally {
      setLoadingBalance(false);
    }
  }, []);

  // 3. Fetch Payout Policy
  const loadPolicyConfig = useCallback(async () => {
    try {
      const res = await authFetch("/api/v1/admin/finance/payout-policy");
      if (res.ok) {
        const data = await res.json();
        setPolicyConfig(data);
      }
    } catch (err) {
      console.error("Falha ao carregar política de saque:", err);
    }
  }, []);

  useEffect(() => {
    loadWithdrawals();
  }, [loadWithdrawals]);

  useEffect(() => {
    loadBaasBalance();
    loadPolicyConfig();
  }, [loadBaasBalance, loadPolicyConfig]);

  // Actions: Copy Key
  const handleCopyKey = (key: string, id: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKeyId(id);
    setTimeout(() => setCopiedKeyId(null), 2000);
  };

  // Actions: Approve Single
  const handleApprove = async (id: string) => {
    if (!window.confirm("Confirmar aprovação imediata do saque PIX? Os fundos serão liquidados via Efí Pay BaaS.")) {
      return;
    }
    setProcessingAction(true);
    try {
      const res = await authFetch(`/api/v1/admin/finance/withdrawals/${id}/approve`, {
        method: "POST",
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Falha ao aprovar saque.");
      }
      showToast("Saque aprovado e enviado para liquidação PIX instantânea!", "success");
      loadWithdrawals();
      loadBaasBalance();
    } catch (err: any) {
      showToast(err.message, "error");
    } finally {
      setProcessingAction(false);
    }
  };

  // Actions: Bulk Approve
  const handleBulkApprove = async () => {
    if (selectedIds.length === 0) return;
    if (!window.confirm(`Confirmar aprovação em lote de ${selectedIds.length} saques selecionados?`)) {
      return;
    }
    setProcessingAction(true);
    try {
      const res = await authFetch("/api/v1/admin/finance/withdrawals/bulk-approve", {
        method: "POST",
        body: JSON.stringify({ withdrawal_ids: selectedIds }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Falha na aprovação em lote.");
      }
      showToast(`${data.approved_count} de ${data.requested_count} saques aprovados com sucesso!`, "success");
      setSelectedIds([]);
      loadWithdrawals();
      loadBaasBalance();
    } catch (err: any) {
      showToast(err.message, "error");
    } finally {
      setProcessingAction(false);
    }
  };

  // Actions: Reject
  const handleConfirmReject = async () => {
    if (!selectedWithdrawalForReject) return;
    if (!rejectionReason.trim()) {
      alert("Informe obrigatoriamente o motivo da rejeição para constar no extrato e notificação do entregador.");
      return;
    }
    setProcessingAction(true);
    try {
      const res = await authFetch(`/api/v1/admin/finance/withdrawals/${selectedWithdrawalForReject.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ rejection_reason: rejectionReason.trim() }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Falha ao rejeitar saque.");
      }
      showToast("Saque rejeitado e saldo estornado atomicamente para a carteira do entregador.", "success");
      setRejectModalOpen(false);
      setSelectedWithdrawalForReject(null);
      setRejectionReason("");
      loadWithdrawals();
    } catch (err: any) {
      showToast(err.message, "error");
    } finally {
      setProcessingAction(false);
    }
  };

  // Actions: Save Policy
  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policyConfig) return;
    setSavingPolicy(true);
    try {
      const res = await authFetch("/api/v1/admin/finance/payout-policy", {
        method: "PUT",
        body: JSON.stringify(policyConfig),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Falha ao salvar política.");
      }
      const updated = await res.json();
      setPolicyConfig(updated);
      showToast("Diretrizes de saque e alçada atualizadas com sucesso!", "success");
      setPolicyModalOpen(false);
    } catch (err: any) {
      showToast(err.message, "error");
    } finally {
      setSavingPolicy(false);
    }
  };

  // Metrics Calculation
  const metrics = useMemo(() => {
    let pendingCount = 0;
    let pendingAmountCents = 0;
    let paidCount = 0;
    let paidAmountCents = 0;
    let rejectedCount = 0;

    withdrawals.forEach((w) => {
      if (w.status === "PENDING") {
        pendingCount++;
        pendingAmountCents += w.amount_cents;
      } else if (w.status === "PAID") {
        paidCount++;
        paidAmountCents += w.net_amount_cents;
      } else if (w.status === "REJECTED" || w.status === "FAILED") {
        rejectedCount++;
      }
    });

    return {
      pendingCount,
      pendingTotal: pendingAmountCents / 100,
      paidCount,
      paidTotal: paidAmountCents / 100,
      rejectedCount,
    };
  }, [withdrawals]);

  // Filtered List
  const filteredWithdrawals = useMemo(() => {
    return withdrawals.filter((item) => {
      const matchesSearch =
        !searchTerm ||
        (item.condutor_name && item.condutor_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
        item.condutor_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.pix_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (item.baas_tx_id && item.baas_tx_id.toLowerCase().includes(searchTerm.toLowerCase()));
      return matchesSearch;
    });
  }, [withdrawals, searchTerm]);

  // Selection toggles
  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      const pendingIds = filteredWithdrawals.filter((w) => w.status === "PENDING").map((w) => w.id);
      setSelectedIds(pendingIds);
    } else {
      setSelectedIds([]);
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Toast Feedback */}
      {toastMessage && (
        <div
          className={cn(
            "fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg border text-sm font-medium transition-all duration-300",
            toastMessage.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-rose-50 border-rose-200 text-rose-800"
          )}
        >
          {toastMessage.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-rose-600" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-zinc-900 text-white rounded-xl shadow-sm">
              <ArrowDownToLine className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
                Gestão de Saques & PIX BaaS
              </h1>
              <p className="text-sm text-zinc-500">
                Liquidação atômica de saldo dos entregadores via SPI / Banco Central (Efí Pay).
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => {
              loadWithdrawals();
              loadBaasBalance();
            }}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-zinc-700 bg-white border border-zinc-200 rounded-lg hover:bg-zinc-50 transition shadow-sm"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin text-zinc-400")} />
            <span>Atualizar</span>
          </button>

          <button
            onClick={() => setPolicyModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-white bg-zinc-900 rounded-lg hover:bg-zinc-800 transition shadow-sm"
          >
            <Sliders className="w-4 h-4" />
            <span>Regras & Alçada</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Pendentes */}
        <div className="bg-white p-5 rounded-xl border border-amber-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-700">
              Aguardando Aprovação
            </span>
            <span className="p-2 bg-amber-50 text-amber-600 rounded-lg">
              <Clock className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-zinc-900">
              {formatCurrency(metrics.pendingTotal)}
            </div>
            <p className="text-xs text-amber-700 mt-1 font-medium">
              {metrics.pendingCount} {metrics.pendingCount === 1 ? "solicitação pendente" : "solicitações pendentes"}
            </p>
          </div>
        </div>

        {/* Card 2: Pagos */}
        <div className="bg-white p-5 rounded-xl border border-emerald-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
              Total Pago (PIX)
            </span>
            <span className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
              <CheckCircle2 className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-zinc-900">
              {formatCurrency(metrics.paidTotal)}
            </div>
            <p className="text-xs text-emerald-600 mt-1 font-medium">
              {metrics.paidCount} saques liquidados no SPI
            </p>
          </div>
        </div>

        {/* Card 3: Rejeitados / Estornados */}
        <div className="bg-white p-5 rounded-xl border border-zinc-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
              Rejeitados / Estornados
            </span>
            <span className="p-2 bg-zinc-100 text-zinc-600 rounded-lg">
              <XCircle className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-zinc-900">
              {metrics.rejectedCount}
            </div>
            <p className="text-xs text-zinc-500 mt-1">
              Saldo devolvido à carteira
            </p>
          </div>
        </div>

        {/* Card 4: Saldo Efí BaaS */}
        <div className="bg-white p-5 rounded-xl border border-blue-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-700">
                Saldo BaaS Efí
              </span>
              {baasBalance?.mock && (
                <span className="text-[10px] font-medium bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                  Mock
                </span>
              )}
            </div>
            <button
              onClick={loadBaasBalance}
              disabled={loadingBalance}
              title="Recarregar saldo Efí"
              className="p-1 hover:bg-blue-50 text-blue-600 rounded transition"
            >
              <RefreshCw className={cn("w-3.5 h-3.5", loadingBalance && "animate-spin")} />
            </button>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-blue-950">
              {baasBalance ? formatCurrency(baasBalance.saldo) : "---"}
            </div>
            <p className="text-xs text-blue-700 mt-1 font-medium">
              Disponível para liquidação imediata
            </p>
          </div>
        </div>
      </div>

      {/* Table & Filters Card */}
      <div className="bg-white border border-zinc-200 rounded-xl shadow-sm overflow-hidden">
        {/* Controls Bar */}
        <div className="p-4 border-b border-zinc-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-zinc-50/50">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
            {[
              { id: "ALL", label: "Todos" },
              { id: "PENDING", label: "Pendentes", badge: metrics.pendingCount },
              { id: "PAID", label: "Pagos" },
              { id: "REJECTED", label: "Rejeitados" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium rounded-lg transition flex items-center gap-1.5 whitespace-nowrap",
                  statusFilter === tab.id
                    ? "bg-zinc-900 text-white shadow-sm"
                    : "text-zinc-600 hover:bg-zinc-200/60"
                )}
              >
                <span>{tab.label}</span>
                {typeof tab.badge === "number" && tab.badge > 0 && (
                  <span
                    className={cn(
                      "px-1.5 py-0.2 text-[10px] font-bold rounded-full",
                      statusFilter === tab.id
                        ? "bg-amber-400 text-zinc-900"
                        : "bg-amber-100 text-amber-800"
                    )}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              placeholder="Buscar por motoboy, chave PIX ou TXID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:border-transparent"
            />
          </div>
        </div>

        {/* Bulk Action Banner */}
        {selectedIds.length > 0 && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5 flex items-center justify-between animate-fadeIn">
            <div className="flex items-center gap-2 text-xs font-medium text-amber-900">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              <span>{selectedIds.length} saques selecionados para aprovação</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSelectedIds([])}
                className="text-xs text-amber-700 hover:text-amber-900 px-2 py-1"
              >
                Desmarcar
              </button>
              <button
                onClick={handleBulkApprove}
                disabled={processingAction}
                className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-white bg-emerald-600 rounded-md hover:bg-emerald-700 transition shadow-sm disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Aprovar Selecionados</span>
              </button>
            </div>
          </div>
        )}

        {/* Table Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 uppercase tracking-wider font-semibold">
              <tr>
                <th className="p-3.5 w-8">
                  <input
                    type="checkbox"
                    onChange={handleSelectAll}
                    checked={
                      filteredWithdrawals.filter((w) => w.status === "PENDING").length > 0 &&
                      selectedIds.length === filteredWithdrawals.filter((w) => w.status === "PENDING").length
                    }
                    className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
                  />
                </th>
                <th className="p-3.5">Entregador</th>
                <th className="p-3.5">Chave PIX</th>
                <th className="p-3.5">Bruto</th>
                <th className="p-3.5">Taxa</th>
                <th className="p-3.5">Líquido PIX</th>
                <th className="p-3.5">Alçada / Modo</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Data Solicitação</th>
                <th className="p-3.5 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200">
              {loading ? (
                <tr>
                  <td colSpan={10} className="p-8 text-center text-zinc-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-zinc-400" />
                    <span>Carregando solicitações de saque...</span>
                  </td>
                </tr>
              ) : filteredWithdrawals.length === 0 ? (
                <tr>
                  <td colSpan={10} className="p-8 text-center text-zinc-500">
                    <div className="max-w-xs mx-auto text-center space-y-1">
                      <p className="font-semibold text-zinc-800">Nenhum saque encontrado</p>
                      <p className="text-xs text-zinc-400">
                        {statusFilter !== "ALL"
                          ? `Não há saques no status "${statusFilter}".`
                          : "Nenhum entregador solicitou saque no momento."}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredWithdrawals.map((item) => {
                  const isPending = item.status === "PENDING";
                  const isSelected = selectedIds.includes(item.id);

                  return (
                    <tr
                      key={item.id}
                      className={cn(
                        "hover:bg-zinc-50/80 transition-colors",
                        isSelected && "bg-amber-50/40"
                      )}
                    >
                      <td className="p-3.5">
                        {isPending ? (
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleSelect(item.id)}
                            className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
                          />
                        ) : (
                          <div className="w-4" />
                        )}
                      </td>

                      {/* Entregador */}
                      <td className="p-3.5">
                        <div className="font-medium text-zinc-900">
                          {item.condutor_name || "Entregador #" + item.condutor_id.substring(0, 8)}
                        </div>
                        <div className="text-[11px] text-zinc-400 font-mono">
                          ID: {item.condutor_id}
                        </div>
                      </td>

                      {/* Chave PIX */}
                      <td className="p-3.5">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 bg-zinc-100 text-zinc-600 rounded">
                            {item.pix_key_type || "PIX"}
                          </span>
                          <span className="font-mono text-zinc-800 text-[11px]">
                            {item.pix_key}
                          </span>
                          <button
                            onClick={() => handleCopyKey(item.pix_key, item.id)}
                            title="Copiar Chave PIX"
                            className="p-1 text-zinc-400 hover:text-zinc-700 transition"
                          >
                            {copiedKeyId === item.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </td>

                      {/* Bruto */}
                      <td className="p-3.5 font-medium text-zinc-700">
                        {formatCurrency(item.amount_cents / 100)}
                      </td>

                      {/* Taxa */}
                      <td className="p-3.5 text-zinc-500">
                        {item.fee_amount_cents > 0 ? (
                          <span className="text-rose-600 font-medium">
                            -{formatCurrency(item.fee_amount_cents / 100)}
                          </span>
                        ) : (
                          <span className="text-zinc-400 text-[11px]">Grátis</span>
                        )}
                      </td>

                      {/* Líquido */}
                      <td className="p-3.5">
                        <span className="font-bold text-emerald-600">
                          {formatCurrency(item.net_amount_cents / 100)}
                        </span>
                      </td>

                      {/* Alçada / Modo */}
                      <td className="p-3.5">
                        {item.approval_mode === "AUTO_INSTANT" ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-indigo-700 bg-indigo-50 border border-indigo-200/60 px-2 py-0.5 rounded-full">
                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                            Automático
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200/60 px-2 py-0.5 rounded-full">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                            Alçada Manual
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="p-3.5">
                        {item.status === "PENDING" && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 bg-amber-100/80 px-2 py-0.5 rounded-full">
                            <Clock className="w-3 h-3" />
                            Pendente
                          </span>
                        )}
                        {item.status === "PROCESSING" && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-800 bg-blue-100/80 px-2 py-0.5 rounded-full">
                            <RefreshCw className="w-3 h-3 animate-spin" />
                            Processando
                          </span>
                        )}
                        {item.status === "PAID" && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-100/80 px-2 py-0.5 rounded-full">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            Pago (SPI)
                          </span>
                        )}
                        {(item.status === "REJECTED" || item.status === "FAILED") && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-800 bg-rose-100/80 px-2 py-0.5 rounded-full">
                            <XCircle className="w-3 h-3 text-rose-600" />
                            Rejeitado
                          </span>
                        )}
                      </td>

                      {/* Data */}
                      <td className="p-3.5 text-zinc-500 text-[11px]">
                        {new Date(item.created_at).toLocaleString("pt-BR", {
                          day: "2-digit",
                          month: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>

                      {/* Ações */}
                      <td className="p-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {isPending ? (
                            <>
                              <button
                                onClick={() => handleApprove(item.id)}
                                disabled={processingAction}
                                title="Aprovar e Liquidar via PIX"
                                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition shadow-xs disabled:opacity-50"
                              >
                                <Check className="w-3 h-3" />
                                <span>Aprovar</span>
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedWithdrawalForReject(item);
                                  setRejectModalOpen(true);
                                }}
                                disabled={processingAction}
                                title="Rejeitar e Estornar Saldo"
                                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-md transition disabled:opacity-50"
                              >
                                <XCircle className="w-3 h-3" />
                                <span>Rejeitar</span>
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => setDetailsModalItem(item)}
                              title="Ver Detalhes do Saque / Comprovante"
                              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-zinc-600 bg-zinc-100 hover:bg-zinc-200 rounded-md transition"
                            >
                              <Eye className="w-3 h-3" />
                              <span>Detalhes</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Rejeitar com Motivo e Estorno Atômico */}
      {createPortal(
        <AnimatePresence>
          {rejectModalOpen && selectedWithdrawalForReject && (
            <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
                onClick={() => {
                  setRejectModalOpen(false);
                  setSelectedWithdrawalForReject(null);
                  setRejectionReason("");
                }}
              />
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 15 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 15 }}
                transition={{ type: "spring", damping: 25, stiffness: 250 }}
                className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 border border-zinc-200 space-y-4 z-10 pointer-events-auto"
              >
                <div className="flex items-start gap-3.5">
                  <div className="p-3 bg-rose-100 text-rose-600 rounded-2xl shrink-0">
                    <ShieldAlert className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-900">
                      Rejeitar Saque & Estornar Carteira
                    </h3>
                    <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">
                      O valor de{" "}
                      <strong>
                        {formatCurrency(selectedWithdrawalForReject.amount_cents / 100)}
                      </strong>{" "}
                      será desbloqueado e devolvido à carteira do entregador via transação contábil de estorno (REFUND).
                    </p>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-700">
                    Motivo da Rejeição (Visível no App NevesGo) <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="Ex: Chave PIX inexistente ou com titularidade divergente do cadastro."
                    className="w-full p-3 text-xs border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 resize-none outline-none transition-all"
                  />
                </div>

                <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-100">
                  <button
                    type="button"
                    onClick={() => {
                      setRejectModalOpen(false);
                      setSelectedWithdrawalForReject(null);
                      setRejectionReason("");
                    }}
                    className="px-4 py-2 text-xs font-bold text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer shadow-xs"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmReject}
                    disabled={processingAction || !rejectionReason.trim()}
                    className="px-5 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl transition-all shadow-sm disabled:opacity-50 flex items-center gap-1.5 cursor-pointer shadow-rose-600/20"
                  >
                    {processingAction && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>Confirmar Rejeição & Estorno</span>
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>,
        document.body,
      )}

      {/* Modal: Detalhes do Saque & E2E ID (Lateral Drawer) */}
      {createPortal(
        <AnimatePresence>
          {detailsModalItem && (
            <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
                onClick={() => setDetailsModalItem(null)}
              />

              <motion.div
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", damping: 30, stiffness: 300 }}
                className="fixed top-0 right-0 h-full w-full max-w-xl md:max-w-2xl bg-white shadow-2xl border-l border-zinc-200 z-10 flex flex-col pointer-events-auto overflow-hidden"
              >
                {/* Header */}
                <div className="px-6 md:px-8 py-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/70 shrink-0">
                  <div className="flex items-center gap-3.5">
                    <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center text-white shadow-md shadow-emerald-500/20 shrink-0">
                      <DollarSign className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        BaaS & Liquidação PIX
                      </span>
                      <h2 className="text-xl font-black text-zinc-900 tracking-tight mt-0.5">
                        Detalhes do Saque
                      </h2>
                      <p className="text-xs text-zinc-500 font-medium">
                        Identificador Fim-a-Fim Banco Central e comprovante de liquidação
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setDetailsModalItem(null)}
                    className="p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-5 bg-zinc-50/30 text-xs">
                  {/* Summary Card */}
                  <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <span className="text-zinc-400 block text-[11px] font-semibold">Entregador</span>
                        <span className="font-bold text-sm text-zinc-900">
                          {detailsModalItem.condutor_name || detailsModalItem.condutor_id}
                        </span>
                      </div>
                      <div>
                        <span className="text-zinc-400 block text-[11px] font-semibold">Status</span>
                        <span className="inline-block mt-0.5 px-2.5 py-0.5 rounded-full font-bold text-[10px] uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {detailsModalItem.status}
                        </span>
                      </div>
                      <div>
                        <span className="text-zinc-400 block text-[11px] font-semibold">Chave PIX Destino</span>
                        <span className="font-mono font-bold text-zinc-800">
                          {detailsModalItem.pix_key} ({detailsModalItem.pix_key_type})
                        </span>
                      </div>
                      <div>
                        <span className="text-zinc-400 block text-[11px] font-semibold">Valor Líquido Enviado</span>
                        <span className="font-black text-base text-emerald-600">
                          {formatCurrency(detailsModalItem.net_amount_cents / 100)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* E2E ID */}
                  {detailsModalItem.baas_e2e_id && (
                    <div className="bg-blue-50/60 border border-blue-200 p-4 rounded-2xl space-y-2">
                      <span className="text-xs font-bold text-blue-900 block">
                        Identificador Fim-a-Fim Banco Central (E2E ID)
                      </span>
                      <div className="flex items-center justify-between gap-3 bg-white p-2.5 rounded-xl border border-blue-100">
                        <span className="font-mono text-xs text-blue-950 select-all font-semibold break-all">
                          {detailsModalItem.baas_e2e_id}
                        </span>
                        <button
                          onClick={() => handleCopyKey(detailsModalItem.baas_e2e_id!, "e2e")}
                          className="p-2 text-blue-700 hover:bg-blue-50 rounded-lg transition-colors cursor-pointer shrink-0"
                          title="Copiar Chave E2E"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* TXID */}
                  {detailsModalItem.baas_tx_id && (
                    <div className="bg-white border border-zinc-200 p-4 rounded-2xl space-y-1 shadow-xs">
                      <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold block">
                        Efí Transaction ID (TXID)
                      </span>
                      <span className="font-mono text-xs text-zinc-800 block select-all break-all">
                        {detailsModalItem.baas_tx_id}
                      </span>
                    </div>
                  )}

                  {/* Rejection Reason */}
                  {detailsModalItem.rejection_reason && (
                    <div className="bg-rose-50 border border-rose-200 p-4 rounded-2xl space-y-1">
                      <span className="text-xs font-bold text-rose-900 block">
                        Motivo da Rejeição Registrado
                      </span>
                      <p className="text-xs text-rose-800">
                        {detailsModalItem.rejection_reason}
                      </p>
                    </div>
                  )}

                  <div className="text-[11px] text-zinc-500 pt-2 bg-zinc-50 p-3 rounded-xl border border-zinc-200">
                    Solicitado em: {new Date(detailsModalItem.created_at).toLocaleString("pt-BR")}
                    {detailsModalItem.paid_at && (
                      <span> • Liquidado em: {new Date(detailsModalItem.paid_at).toLocaleString("pt-BR")}</span>
                    )}
                  </div>
                </div>

                {/* Footer */}
                <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex justify-end shrink-0">
                  <button
                    type="button"
                    onClick={() => setDetailsModalItem(null)}
                    className="px-6 py-2.5 text-xs font-bold text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer shadow-xs"
                  >
                    Fechar
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>,
        document.body,
      )}

      {/* Modal: Regras e Alçada de Saque (PolicyConfigModal - Lateral Drawer) */}
      {createPortal(
        <AnimatePresence>
          {policyModalOpen && policyConfig && (
            <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
                onClick={() => setPolicyModalOpen(false)}
              />

              <motion.div
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", damping: 30, stiffness: 300 }}
                className="fixed top-0 right-0 h-full w-full max-w-2xl md:max-w-3xl bg-white shadow-2xl border-l border-zinc-200 z-10 flex flex-col pointer-events-auto overflow-hidden"
              >
                {/* Header */}
                <div className="px-6 md:px-8 py-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/70 shrink-0">
                  <div className="flex items-center gap-3.5">
                    <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-zinc-800 to-zinc-950 flex items-center justify-center text-white shadow-md shrink-0">
                      <Sliders className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-800 border border-zinc-200">
                        Diretrizes Operacionais
                      </span>
                      <h2 className="text-xl font-black text-zinc-900 tracking-tight mt-0.5">
                        Configuração de Alçada & BaaS
                      </h2>
                      <p className="text-xs text-zinc-500 font-medium">
                        Defina limites automáticos, taxas e regras de aprovação de saques
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setPolicyModalOpen(false)}
                    className="p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <form
                  id="policy-form"
                  onSubmit={handleSavePolicy}
                  className="flex-1 flex flex-col overflow-hidden text-xs"
                >
                  <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 bg-zinc-50/30">
                    {/* Modo de Alçada */}
                    <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs space-y-3">
                      <label className="font-bold text-xs text-zinc-800 block">
                        Modo de Aprovação de Saques
                      </label>
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          type="button"
                          onClick={() =>
                            setPolicyConfig({ ...policyConfig, approval_mode: "HYBRID_THRESHOLD" })
                          }
                          className={cn(
                            "p-3.5 rounded-xl border text-left transition-all cursor-pointer",
                            policyConfig.approval_mode === "HYBRID_THRESHOLD"
                              ? "border-zinc-900 bg-zinc-900 text-white shadow-xs"
                              : "border-zinc-200 bg-zinc-50 text-zinc-700 hover:bg-zinc-100"
                          )}
                        >
                          <div className="font-bold text-xs">Híbrido (Limite Inteligente)</div>
                          <div className={cn("text-[11px] mt-1 leading-relaxed", policyConfig.approval_mode === "HYBRID_THRESHOLD" ? "text-zinc-300" : "text-zinc-500")}>
                            Saques abaixo do limite são automáticos via BaaS; acima exigem aprovação manual.
                          </div>
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            setPolicyConfig({ ...policyConfig, approval_mode: "MANUAL_ALL" })
                          }
                          className={cn(
                            "p-3.5 rounded-xl border text-left transition-all cursor-pointer",
                            policyConfig.approval_mode === "MANUAL_ALL"
                              ? "border-zinc-900 bg-zinc-900 text-white shadow-xs"
                              : "border-zinc-200 bg-zinc-50 text-zinc-700 hover:bg-zinc-100"
                          )}
                        >
                          <div className="font-bold text-xs">100% Manual</div>
                          <div className={cn("text-[11px] mt-1 leading-relaxed", policyConfig.approval_mode === "MANUAL_ALL" ? "text-zinc-300" : "text-zinc-500")}>
                            Todos os saques passam obrigatoriamente por autorização do operador no painel.
                          </div>
                        </button>
                      </div>
                    </div>

                    {/* Limites Financeiros */}
                    <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs space-y-4">
                      <h4 className="text-xs font-bold text-zinc-800 uppercase tracking-wider">
                        Limites Financeiros por Transação
                      </h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <label className="font-semibold text-xs text-zinc-700 block">
                            Limite p/ Saque Automático (R$)
                          </label>
                          <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-xs font-bold">R$</span>
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              disabled={policyConfig.approval_mode === "MANUAL_ALL"}
                              value={(policyConfig.auto_approval_threshold_cents / 100).toFixed(2)}
                              onChange={(e) =>
                                setPolicyConfig({
                                  ...policyConfig,
                                  auto_approval_threshold_cents: Math.round(parseFloat(e.target.value || "0") * 100),
                                })
                              }
                              className="w-full pl-9 pr-3 py-2.5 border border-zinc-200 rounded-xl text-xs font-bold focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 disabled:bg-zinc-100 disabled:text-zinc-400 transition-all"
                            />
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <label className="font-semibold text-xs text-zinc-700 block">
                            Limite Diário por Entregador (R$)
                          </label>
                          <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-xs font-bold">R$</span>
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              value={(policyConfig.daily_limit_per_driver_cents / 100).toFixed(2)}
                              onChange={(e) =>
                                setPolicyConfig({
                                  ...policyConfig,
                                  daily_limit_per_driver_cents: Math.round(parseFloat(e.target.value || "0") * 100),
                                })
                              }
                              className="w-full pl-9 pr-3 py-2.5 border border-zinc-200 rounded-xl text-xs font-bold focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all"
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Modalidade da Taxa de Saque */}
                    <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs space-y-3">
                      <label className="font-bold text-xs text-zinc-800 block">
                        Cobrança da Taxa de Saque
                      </label>
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          type="button"
                          onClick={() =>
                            setPolicyConfig({ ...policyConfig, fee_mode: "ABSORBED_BY_PLATFORM" })
                          }
                          className={cn(
                            "p-3 rounded-xl border text-left transition-all cursor-pointer",
                            policyConfig.fee_mode === "ABSORBED_BY_PLATFORM"
                              ? "border-emerald-600 bg-emerald-50 text-emerald-900 shadow-xs"
                              : "border-zinc-200 bg-zinc-50 text-zinc-700 hover:bg-zinc-100"
                          )}
                        >
                          <div className="font-bold text-xs">Plataforma Absorve</div>
                          <div className="text-[11px] text-zinc-500 mt-0.5">
                            Saque 100% gratuito ao entregador parceiro.
                          </div>
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            setPolicyConfig({ ...policyConfig, fee_mode: "CHARGED_TO_DRIVER" })
                          }
                          className={cn(
                            "p-3 rounded-xl border text-left transition-all cursor-pointer",
                            policyConfig.fee_mode === "CHARGED_TO_DRIVER"
                              ? "border-zinc-900 bg-zinc-900 text-white shadow-xs"
                              : "border-zinc-200 bg-zinc-50 text-zinc-700 hover:bg-zinc-100"
                          )}
                        >
                          <div className="font-bold text-xs">Cobrar do Entregador</div>
                          <div className={cn("text-[11px] mt-0.5", policyConfig.fee_mode === "CHARGED_TO_DRIVER" ? "text-zinc-300" : "text-zinc-500")}>
                            Desconta taxa fixa do valor líquido transferido.
                          </div>
                        </button>
                      </div>

                      {policyConfig.fee_mode === "CHARGED_TO_DRIVER" && (
                        <div className="mt-3 relative w-1/2">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-xs font-bold">R$</span>
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            value={(policyConfig.payout_fee_cents / 100).toFixed(2)}
                            onChange={(e) =>
                              setPolicyConfig({
                                ...policyConfig,
                                payout_fee_cents: Math.round(parseFloat(e.target.value || "0") * 100),
                              })
                            }
                            className="w-full pl-9 pr-3 py-2 border border-zinc-200 rounded-xl text-xs font-bold focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all"
                          />
                        </div>
                      )}
                    </div>

                    {/* Notificações Independentes */}
                    <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs space-y-3">
                      <label className="font-bold text-xs text-zinc-800 block">
                        Notificações de Saque Concluído
                      </label>
                      
                      <label className="flex items-center justify-between p-3 rounded-xl border border-zinc-200 hover:bg-zinc-50 cursor-pointer transition-all">
                        <div className="flex items-center gap-3">
                          <Smartphone className="w-5 h-5 text-zinc-600" />
                          <div>
                            <div className="font-bold text-xs text-zinc-900">Push Notification (App NevesGo)</div>
                            <div className="text-[11px] text-zinc-500">Disparo via Firebase Cloud Messaging</div>
                          </div>
                        </div>
                        <input
                          type="checkbox"
                          checked={policyConfig.notify_push_enabled}
                          onChange={(e) =>
                            setPolicyConfig({ ...policyConfig, notify_push_enabled: e.target.checked })
                          }
                          className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900 w-4 h-4 cursor-pointer"
                        />
                      </label>

                      <label className="flex items-center justify-between p-3 rounded-xl border border-zinc-200 hover:bg-zinc-50 cursor-pointer transition-all">
                        <div className="flex items-center gap-3">
                          <MessageSquare className="w-5 h-5 text-emerald-600" />
                          <div>
                            <div className="font-bold text-xs text-zinc-900">WhatsApp Automático (Z-API)</div>
                            <div className="text-[11px] text-zinc-500">Mensagem instantânea com comprovante PIX</div>
                          </div>
                        </div>
                        <input
                          type="checkbox"
                          checked={policyConfig.notify_whatsapp_enabled}
                          onChange={(e) =>
                            setPolicyConfig({ ...policyConfig, notify_whatsapp_enabled: e.target.checked })
                          }
                          className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900 w-4 h-4 cursor-pointer"
                        />
                      </label>
                    </div>
                  </div>

                  {/* Standard Footer */}
                  <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex items-center justify-between gap-4 shrink-0">
                    <button
                      type="button"
                      onClick={() => setPolicyModalOpen(false)}
                      className="px-5 py-2.5 text-xs font-bold text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer shadow-xs"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={savingPolicy}
                      className="px-6 py-2.5 text-xs font-bold text-white bg-zinc-900 hover:bg-zinc-800 rounded-xl transition-all shadow-sm disabled:opacity-50 flex items-center gap-2 cursor-pointer"
                    >
                      {savingPolicy && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                      <span>Salvar Diretrizes</span>
                    </button>
                  </div>
                </form>
              </motion.div>
            </div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}

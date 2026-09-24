import React, { useState, useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  ShieldCheck,
  X,
  Building2,
  User,
  Mail,
  FileText,
  Loader2,
  Search,
  Filter,
  DollarSign,
  Percent,
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle2,
  MoreVertical,
  Edit2,
  Eye,
  KeyRound,
  Ban,
  Store,
  Bike,
  MapPin,
  Phone,
  HelpCircle,
  TrendingUp,
  RefreshCw,
  Copy,
  Check,
} from "lucide-react";
import { authFetch } from "../lib/api";
import { formatCurrency, cn } from "../lib/utils";

export type BillingPlanType =
  | "PERCENT_PER_DELIVERY"
  | "PERCENT_REVENUE"
  | "FIXED_MONTHLY"
  | "FIXED_WEEKLY"
  | "FIXED_PER_DELIVERY";

export type BillingCycle = "MENSAL" | "QUINZENAL" | "SEMANAL";

export type OperatorStatus = "ACTIVE" | "TRIAL" | "SUSPENDED" | "CANCELED";

export interface OperatorType {
  id: string;
  name: string;
  cnpj?: string;
  phone?: string;
  city?: string;
  state?: string;
  billingPlanType: BillingPlanType;
  billingRateValue: number;
  billingCycle: BillingCycle;
  dueDay: number;
  trialDays: number;
  gracePeriodDays: number;
  notes?: string;
  status: OperatorStatus;
  createdAt?: string;
  updatedAt?: string;
  managerName?: string;
  managerEmail?: string;
  storesCount?: number;
  driversCount?: number;
}

export const BILLING_PLANS: Record<
  BillingPlanType,
  {
    label: string;
    badge: string;
    unit: string;
    description: string;
    isPercentage: boolean;
    helperText: string;
  }
> = {
  PERCENT_PER_DELIVERY: {
    label: "Percentual por Corrida",
    badge: "% Corrida",
    unit: "%",
    description: "Percentual cobrado da franquia sobre o valor de cada entrega concluída",
    isPercentage: true,
    helperText: "Ex: 3.5% sobre o valor total de cada corrida despachada",
  },
  PERCENT_REVENUE: {
    label: "Percentual sobre Faturamento",
    badge: "% Faturamento",
    unit: "%",
    description: "Percentual fixado sobre o faturamento total bruto gerado pela base",
    isPercentage: true,
    helperText: "Ex: 4.0% sobre o faturamento bruto consolidado no período",
  },
  FIXED_MONTHLY: {
    label: "Fixo Mensal (Mensalidade)",
    badge: "Fixo Mensal",
    unit: "R$",
    description: "Valor fixo mensal recorrente acordado pelo licenciamento da plataforma",
    isPercentage: false,
    helperText: "Ex: R$ 890,00 cobrados mensalmente do franqueado",
  },
  FIXED_WEEKLY: {
    label: "Fixo Semanal",
    badge: "Fixo Semanal",
    unit: "R$",
    description: "Taxa fixa semanal cobrada do operador logístico",
    isPercentage: false,
    helperText: "Ex: R$ 250,00 debitados semanalmente",
  },
  FIXED_PER_DELIVERY: {
    label: "Fixo por Corrida Despachada",
    badge: "R$ / Corrida",
    unit: "R$",
    description: "Taxa em Reais fixa para cada entrega despachada pelo sistema",
    isPercentage: false,
    helperText: "Ex: R$ 0,50 por corrida despachada pela base",
  },
};

export const STATUS_CONFIG: Record<
  OperatorStatus,
  { label: string; bg: string; text: string; border: string; dot: string }
> = {
  ACTIVE: {
    label: "Ativo",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    dot: "bg-emerald-500",
  },
  TRIAL: {
    label: "Em Testes (Trial)",
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    dot: "bg-amber-500",
  },
  SUSPENDED: {
    label: "Suspenso / Bloqueado",
    bg: "bg-rose-50",
    text: "text-rose-700",
    border: "border-rose-200",
    dot: "bg-rose-500",
  },
  CANCELED: {
    label: "Cancelado",
    bg: "bg-zinc-100",
    text: "text-zinc-600",
    border: "border-zinc-200",
    dot: "bg-zinc-400",
  },
};

export function Operadores() {
  const [operadores, setOperadores] = useState<OperatorType[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [planFilter, setPlanFilter] = useState<string>("ALL");

  // Modais / Drawers
  const [isFormDrawerOpen, setIsFormDrawerOpen] = useState(false);
  const [selectedOperatorForEdit, setSelectedOperatorForEdit] = useState<OperatorType | null>(null);

  const [isDetailsDrawerOpen, setIsDetailsDrawerOpen] = useState(false);
  const [selectedOperatorForDetails, setSelectedOperatorForDetails] = useState<OperatorType | null>(null);

  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [selectedOperatorForStatus, setSelectedOperatorForStatus] = useState<OperatorType | null>(null);

  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [selectedOperatorForPassword, setSelectedOperatorForPassword] = useState<OperatorType | null>(null);

  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    fetchOperadores();
  }, []);

  const fetchOperadores = async () => {
    setLoading(true);
    try {
      const res = await authFetch("/api/admin/operators");
      if (res.ok) {
        const data = await res.json();
        setOperadores(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error("Erro ao buscar operadores:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(text);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // KPIs
  const stats = useMemo(() => {
    const total = operadores.length;
    const active = operadores.filter((o) => o.status === "ACTIVE").length;
    const trial = operadores.filter((o) => o.status === "TRIAL").length;
    const suspended = operadores.filter((o) => o.status === "SUSPENDED").length;
    return { total, active, trial, suspended };
  }, [operadores]);

  // Filtros
  const filteredOperadores = useMemo(() => {
    return operadores.filter((op) => {
      const matchesSearch =
        !search ||
        op.name.toLowerCase().includes(search.toLowerCase()) ||
        (op.cnpj && op.cnpj.includes(search)) ||
        (op.city && op.city.toLowerCase().includes(search.toLowerCase())) ||
        (op.managerName && op.managerName.toLowerCase().includes(search.toLowerCase())) ||
        (op.managerEmail && op.managerEmail.toLowerCase().includes(search.toLowerCase()));

      const matchesStatus = statusFilter === "ALL" || op.status === statusFilter;
      const matchesPlan = planFilter === "ALL" || op.billingPlanType === planFilter;

      return matchesSearch && matchesStatus && matchesPlan;
    });
  }, [operadores, search, statusFilter, planFilter]);

  const formatBillingRate = (type: BillingPlanType, val: number) => {
    const plan = BILLING_PLANS[type] || BILLING_PLANS.PERCENT_PER_DELIVERY;
    if (plan.isPercentage) {
      return `${val.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 })}%`;
    }
    return formatCurrency(val);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center text-white shadow-md shadow-emerald-600/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-zinc-900 tracking-tight">
                Operadores Logísticos
              </h1>
              <p className="text-xs text-zinc-500 font-medium">
                Gestão de Franquias Master, Planos de Cobrança SaaS e Permissões
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={fetchOperadores}
            disabled={loading}
            className="p-2.5 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-xl text-zinc-600 transition-all cursor-pointer shadow-2xs hover:text-zinc-900 disabled:opacity-50"
            title="Atualizar lista"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>

          <button
            onClick={() => {
              setSelectedOperatorForEdit(null);
              setIsFormDrawerOpen(true);
            }}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-emerald-600/20 hover:shadow-emerald-600/30"
          >
            <Plus className="h-4 w-4" /> Novo Operador
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <div className="bg-white p-4 rounded-2xl border border-zinc-200 shadow-2xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">
              Total Franquias
            </p>
            <h3 className="text-2xl font-black text-zinc-900 mt-1">{stats.total}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-zinc-100 flex items-center justify-center text-zinc-600">
            <Building2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-zinc-200 shadow-2xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-emerald-600 uppercase tracking-wider">
              Ativos / Em Operação
            </p>
            <h3 className="text-2xl font-black text-emerald-700 mt-1">{stats.active}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-zinc-200 shadow-2xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-amber-600 uppercase tracking-wider">
              Em Testes (Trial)
            </p>
            <h3 className="text-2xl font-black text-amber-700 mt-1">{stats.trial}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-zinc-200 shadow-2xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-rose-600 uppercase tracking-wider">
              Bloqueados / Suspensos
            </p>
            <h3 className="text-2xl font-black text-rose-700 mt-1">{stats.suspended}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
            <Ban className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-3.5 rounded-2xl border border-zinc-200 shadow-2xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por nome, CNPJ, cidade, gerente..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3.5 py-2 text-xs font-medium bg-zinc-50 border border-zinc-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
          {/* Status Filter */}
          <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-600">
            <Filter className="w-3.5 h-3.5 text-zinc-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 bg-zinc-50 border border-zinc-200 rounded-xl text-xs font-semibold text-zinc-700 outline-none focus:border-emerald-500 cursor-pointer"
            >
              <option value="ALL">Todos os Status</option>
              <option value="ACTIVE">Ativos</option>
              <option value="TRIAL">Em Testes (Trial)</option>
              <option value="SUSPENDED">Suspensos</option>
              <option value="CANCELED">Cancelados</option>
            </select>
          </div>

          {/* Plan Filter */}
          <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-600">
            <DollarSign className="w-3.5 h-3.5 text-zinc-400" />
            <select
              value={planFilter}
              onChange={(e) => setPlanFilter(e.target.value)}
              className="px-3 py-1.5 bg-zinc-50 border border-zinc-200 rounded-xl text-xs font-semibold text-zinc-700 outline-none focus:border-emerald-500 cursor-pointer"
            >
              <option value="ALL">Todos os Modelos SaaS</option>
              <option value="PERCENT_PER_DELIVERY">% por Corrida</option>
              <option value="PERCENT_REVENUE">% sobre Faturamento</option>
              <option value="FIXED_MONTHLY">Fixo Mensal</option>
              <option value="FIXED_WEEKLY">Fixo Semanal</option>
              <option value="FIXED_PER_DELIVERY">Fixo por Corrida</option>
            </select>
          </div>
        </div>
      </div>

      {/* Operators Table */}
      <div className="bg-white rounded-2xl shadow-2xs border border-zinc-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-50/80 border-b border-zinc-200 text-zinc-500 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-5 py-3.5">Operador / Base</th>
                <th className="px-4 py-3.5">CNPJ</th>
                <th className="px-4 py-3.5">Gerente Responsável</th>
                <th className="px-4 py-3.5">Modelo de Cobrança (SaaS)</th>
                <th className="px-4 py-3.5 text-center">Operação</th>
                <th className="px-4 py-3.5 text-center">Status</th>
                <th className="px-5 py-3.5 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {loading && operadores.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-zinc-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
                    Carregando operadores logísticos...
                  </td>
                </tr>
              ) : filteredOperadores.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-zinc-400">
                    <Building2 className="w-8 h-8 text-zinc-300 mx-auto mb-2" />
                    Nenhum operador logístico encontrado para os filtros selecionados.
                  </td>
                </tr>
              ) : (
                filteredOperadores.map((op) => {
                  const statusConf = STATUS_CONFIG[op.status] || STATUS_CONFIG.ACTIVE;
                  const planConf = BILLING_PLANS[op.billingPlanType] || BILLING_PLANS.PERCENT_PER_DELIVERY;

                  return (
                    <tr
                      key={op.id}
                      className="hover:bg-zinc-50/80 transition-colors group"
                    >
                      {/* Name and Location */}
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-700 font-bold text-sm shrink-0">
                            {op.name ? op.name.charAt(0).toUpperCase() : "O"}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-zinc-900 text-sm">
                                {op.name}
                              </span>
                              <button
                                onClick={() => handleCopy(op.id)}
                                title="Copiar ID"
                                className="text-zinc-400 hover:text-zinc-600 transition-all"
                              >
                                {copiedId === op.id ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100" />
                                )}
                              </button>
                            </div>
                            <div className="flex items-center gap-2 text-[11px] text-zinc-500 mt-0.5">
                              {op.city ? (
                                <span className="flex items-center gap-1">
                                  <MapPin className="w-3 h-3 text-zinc-400" />
                                  {op.city}
                                  {op.state ? `/${op.state}` : ""}
                                </span>
                              ) : (
                                <span className="text-zinc-400">Sem cidade</span>
                              )}
                              {op.phone && (
                                <span className="flex items-center gap-1 text-zinc-500">
                                  <Phone className="w-3 h-3 text-zinc-400" />
                                  {op.phone}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* CNPJ */}
                      <td className="px-4 py-4 font-mono text-zinc-600 text-xs">
                        {op.cnpj || <span className="text-zinc-300 font-sans">-</span>}
                      </td>

                      {/* Manager */}
                      <td className="px-4 py-4">
                        {op.managerName ? (
                          <div>
                            <p className="font-semibold text-zinc-800">{op.managerName}</p>
                            <p className="text-[11px] text-zinc-500 font-mono">
                              {op.managerEmail}
                            </p>
                          </div>
                        ) : (
                          <span className="text-zinc-400 text-xs">Não atribuído</span>
                        )}
                      </td>

                      {/* SaaS Billing Plan */}
                      <td className="px-4 py-4">
                        <div className="space-y-1">
                          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-100 border border-zinc-200/80 text-zinc-800 font-bold text-xs">
                            <span className="text-emerald-700">
                              {formatBillingRate(op.billingPlanType, op.billingRateValue)}
                            </span>
                            <span className="text-zinc-400 font-normal text-[11px]">•</span>
                            <span className="text-[11px] text-zinc-600 font-semibold">
                              {planConf.badge}
                            </span>
                          </div>
                          <div className="text-[10px] text-zinc-400 flex items-center gap-2">
                            <span>Vencimento dia {op.dueDay || 10}</span>
                            <span>• Ciclo {op.billingCycle || "MENSAL"}</span>
                          </div>
                        </div>
                      </td>

                      {/* Operations metrics */}
                      <td className="px-4 py-4 text-center">
                        <div className="inline-flex items-center gap-3 text-xs text-zinc-600 bg-zinc-50 px-2.5 py-1 rounded-xl border border-zinc-100">
                          <span className="flex items-center gap-1" title="Lojas Parceiras Vinculadas">
                            <Store className="w-3.5 h-3.5 text-zinc-400" />
                            <strong className="text-zinc-800">{op.storesCount || 0}</strong>
                          </span>
                          <span className="text-zinc-200">|</span>
                          <span className="flex items-center gap-1" title="Entregadores Ativos">
                            <Bike className="w-3.5 h-3.5 text-zinc-400" />
                            <strong className="text-zinc-800">{op.driversCount || 0}</strong>
                          </span>
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-4 text-center">
                        <button
                          onClick={() => {
                            setSelectedOperatorForStatus(op);
                            setIsStatusModalOpen(true);
                          }}
                          className={cn(
                            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold border transition-all cursor-pointer hover:shadow-xs",
                            statusConf.bg,
                            statusConf.text,
                            statusConf.border
                          )}
                          title="Clique para alterar o status"
                        >
                          <span className={cn("w-1.5 h-1.5 rounded-full", statusConf.dot)} />
                          {statusConf.label}
                        </button>
                      </td>

                      {/* Actions */}
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Ver Detalhes */}
                          <button
                            onClick={() => {
                              setSelectedOperatorForDetails(op);
                              setIsDetailsDrawerOpen(true);
                            }}
                            className="p-1.5 text-zinc-400 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg transition-all cursor-pointer"
                            title="Visualizar Detalhes 360°"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {/* Editar */}
                          <button
                            onClick={() => {
                              setSelectedOperatorForEdit(op);
                              setIsFormDrawerOpen(true);
                            }}
                            className="p-1.5 text-zinc-400 hover:text-zinc-900 hover:bg-zinc-100 rounded-lg transition-all cursor-pointer"
                            title="Editar Operador & Plano de Cobrança"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>

                          {/* Redefinir Senha */}
                          <button
                            onClick={() => {
                              setSelectedOperatorForPassword(op);
                              setIsPasswordModalOpen(true);
                            }}
                            className="p-1.5 text-zinc-400 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition-all cursor-pointer"
                            title="Redefinir Senha do Gerente"
                          >
                            <KeyRound className="w-4 h-4" />
                          </button>

                          {/* Alterar Status */}
                          <button
                            onClick={() => {
                              setSelectedOperatorForStatus(op);
                              setIsStatusModalOpen(true);
                            }}
                            className="p-1.5 text-zinc-400 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition-all cursor-pointer"
                            title="Alterar Status da Assinatura"
                          >
                            <Ban className="w-4 h-4" />
                          </button>
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

      {/* Drawer: Novo / Editar Operador */}
      {isFormDrawerOpen && (
        <OperatorFormDrawer
          operator={selectedOperatorForEdit}
          onClose={() => {
            setIsFormDrawerOpen(false);
            setSelectedOperatorForEdit(null);
          }}
          onSuccess={() => {
            setIsFormDrawerOpen(false);
            setSelectedOperatorForEdit(null);
            fetchOperadores();
          }}
        />
      )}

      {/* Drawer: Detalhes do Operador */}
      {isDetailsDrawerOpen && selectedOperatorForDetails && (
        <OperatorDetailsDrawer
          operator={selectedOperatorForDetails}
          onClose={() => {
            setIsDetailsDrawerOpen(false);
            setSelectedOperatorForDetails(null);
          }}
          onEdit={() => {
            setIsDetailsDrawerOpen(false);
            setSelectedOperatorForEdit(selectedOperatorForDetails);
            setIsFormDrawerOpen(true);
          }}
          onResetPassword={() => {
            setSelectedOperatorForPassword(selectedOperatorForDetails);
            setIsPasswordModalOpen(true);
          }}
          onChangeStatus={() => {
            setSelectedOperatorForStatus(selectedOperatorForDetails);
            setIsStatusModalOpen(true);
          }}
        />
      )}

      {/* Modal: Alterar Status */}
      {isStatusModalOpen && selectedOperatorForStatus && (
        <ChangeStatusModal
          operator={selectedOperatorForStatus}
          onClose={() => {
            setIsStatusModalOpen(false);
            setSelectedOperatorForStatus(null);
          }}
          onSuccess={() => {
            setIsStatusModalOpen(false);
            setSelectedOperatorForStatus(null);
            fetchOperadores();
          }}
        />
      )}

      {/* Modal: Redefinir Senha */}
      {isPasswordModalOpen && selectedOperatorForPassword && (
        <ResetPasswordModal
          operator={selectedOperatorForPassword}
          onClose={() => {
            setIsPasswordModalOpen(false);
            setSelectedOperatorForPassword(null);
          }}
        />
      )}
    </div>
  );
}

// ----------------------------------------------------------------------------
// DRAWER 1: Formulário de Cadastro e Edição de Operador (Padrão Lateral Slide-Over)
// ----------------------------------------------------------------------------
function OperatorFormDrawer({
  operator,
  onClose,
  onSuccess,
}: {
  operator: OperatorType | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const isEditing = Boolean(operator);

  const [activeTab, setActiveTab] = useState<"CADASTRO" | "COBRANCA" | "GERENTE">("CADASTRO");

  const [formData, setFormData] = useState({
    name: operator?.name || "",
    cnpj: operator?.cnpj || "",
    phone: operator?.phone || "",
    city: operator?.city || "",
    state: operator?.state || "",
    billingPlanType: operator?.billingPlanType || "PERCENT_PER_DELIVERY",
    billingRateValue: operator?.billingRateValue !== undefined ? operator.billingRateValue : 3.5,
    billingCycle: operator?.billingCycle || "MENSAL",
    dueDay: operator?.dueDay !== undefined ? operator.dueDay : 10,
    trialDays: operator?.trialDays !== undefined ? operator.trialDays : 14,
    gracePeriodDays: operator?.gracePeriodDays !== undefined ? operator.gracePeriodDays : 5,
    notes: operator?.notes || "",
    // Gerente (apenas na criação)
    managerName: operator?.managerName || "",
    managerEmail: operator?.managerEmail || "",
    managerPassword: "",
  });

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "unset";
    };
  }, []);

  const selectedPlan = BILLING_PLANS[formData.billingPlanType as BillingPlanType] || BILLING_PLANS.PERCENT_PER_DELIVERY;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (isEditing && operator) {
        const payload = {
          name: formData.name,
          cnpj: formData.cnpj,
          phone: formData.phone,
          city: formData.city,
          state: formData.state,
          billingPlanType: formData.billingPlanType,
          billingRateValue: Number(formData.billingRateValue),
          billingCycle: formData.billingCycle,
          dueDay: Number(formData.dueDay),
          trialDays: Number(formData.trialDays),
          gracePeriodDays: Number(formData.gracePeriodDays),
          notes: formData.notes,
        };
        const res = await authFetch(`/api/admin/operators/${operator.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (res.ok) {
          alert("Operador atualizado com sucesso!");
          onSuccess();
        } else {
          const err = await res.json();
          alert(err.error || "Erro ao atualizar operador");
        }
      } else {
        // Criando novo operador
        const res = await authFetch("/api/admin/operators", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...formData,
            billingRateValue: Number(formData.billingRateValue),
            dueDay: Number(formData.dueDay),
            trialDays: Number(formData.trialDays),
            gracePeriodDays: Number(formData.gracePeriodDays),
          }),
        });
        if (res.ok) {
          alert("Operador logístico e gerente cadastrados com sucesso!");
          onSuccess();
        } else {
          const err = await res.json();
          alert(err.error || "Erro ao criar operador");
        }
      }
    } catch (e: any) {
      alert("Erro na requisição: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  return createPortal(
    <AnimatePresence>
      <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
          onClick={onClose}
        />

        {/* Lateral Slide-Over Drawer */}
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
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center text-white shadow-md shadow-emerald-600/20 shrink-0">
                <Building2 className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {isEditing ? "Edição de Franquia" : "Nova Franquia"}
                </span>
                <h2 className="text-xl font-black text-zinc-900 tracking-tight mt-0.5">
                  {isEditing ? `Editar: ${operator?.name}` : "Novo Operador Logístico"}
                </h2>
                <p className="text-xs text-zinc-500 font-medium">
                  {isEditing
                    ? "Atualize os dados cadastrais e as regras de cobrança SaaS"
                    : "Cadastre uma nova base, configure o modelo de remuneração e o gerente"}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Nav Tabs */}
          <div className="px-6 md:px-8 border-b border-zinc-200 bg-white flex gap-6 shrink-0 text-xs font-bold">
            <button
              type="button"
              onClick={() => setActiveTab("CADASTRO")}
              className={cn(
                "py-3 border-b-2 transition-all cursor-pointer flex items-center gap-2",
                activeTab === "CADASTRO"
                  ? "border-emerald-600 text-emerald-700"
                  : "border-transparent text-zinc-400 hover:text-zinc-600"
              )}
            >
              <Building2 className="w-4 h-4" /> 1. Dados da Franquia
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("COBRANCA")}
              className={cn(
                "py-3 border-b-2 transition-all cursor-pointer flex items-center gap-2",
                activeTab === "COBRANCA"
                  ? "border-emerald-600 text-emerald-700"
                  : "border-transparent text-zinc-400 hover:text-zinc-600"
              )}
            >
              <DollarSign className="w-4 h-4" /> 2. Cobrança & Contrato SaaS
            </button>
            {!isEditing && (
              <button
                type="button"
                onClick={() => setActiveTab("GERENTE")}
                className={cn(
                  "py-3 border-b-2 transition-all cursor-pointer flex items-center gap-2",
                  activeTab === "GERENTE"
                    ? "border-emerald-600 text-emerald-700"
                    : "border-transparent text-zinc-400 hover:text-zinc-600"
                )}
              >
                <User className="w-4 h-4" /> 3. Gerente Master
              </button>
            )}
          </div>

          {/* Body */}
          <form
            id="operator-form"
            onSubmit={handleSubmit}
            className="flex-1 flex flex-col overflow-hidden"
          >
            <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 bg-zinc-50/40">
              {/* TAB 1: CADASTRO */}
              {activeTab === "CADASTRO" && (
                <div className="space-y-5">
                  <div className="bg-white p-5 rounded-2xl border border-zinc-200 space-y-4 shadow-2xs">
                    <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2.5">
                      <Building2 className="w-4 h-4 text-emerald-600" /> Identificação da Empresa
                    </h3>

                    <div>
                      <label className="block text-xs font-bold text-zinc-700 mb-1">
                        Razão Social / Nome da Operação *
                      </label>
                      <input
                        required
                        type="password"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                        placeholder="Ex: Expresso Neves Logística Regional LTDA"
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">CNPJ</label>
                        <input
                          type="text"
                          value={formData.cnpj}
                          onChange={(e) => setFormData({ ...formData, cnpj: e.target.value })}
                          className="w-full px-3.5 py-2.5 text-xs font-mono bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                          placeholder="00.000.000/0000-00"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Telefone / WhatsApp de Contato
                        </label>
                        <input
                          type="text"
                          value={formData.phone}
                          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                          placeholder="(11) 99999-9999"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="md:col-span-2">
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Cidade Sede
                        </label>
                        <input
                          type="text"
                          value={formData.city}
                          onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                          placeholder="Ex: Belo Horizonte"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">Estado (UF)</label>
                        <input
                          type="text"
                          maxLength={2}
                          value={formData.state}
                          onChange={(e) => setFormData({ ...formData, state: e.target.value.toUpperCase() })}
                          className="w-full px-3.5 py-2.5 text-xs font-bold uppercase text-center bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                          placeholder="MG"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={() => setActiveTab("COBRANCA")}
                      className="px-5 py-2 bg-zinc-900 hover:bg-zinc-800 text-white rounded-xl text-xs font-bold cursor-pointer"
                    >
                      Avançar para Modelo de Cobrança →
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 2: COBRANÇA SAAS */}
              {activeTab === "COBRANCA" && (
                <div className="space-y-5">
                  <div className="bg-white p-5 rounded-2xl border border-zinc-200 space-y-4 shadow-2xs">
                    <div className="flex items-center justify-between border-b border-zinc-100 pb-2.5">
                      <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2">
                        <DollarSign className="w-4 h-4 text-emerald-600" /> Modalidade de Cobrança do Sistema
                      </h3>
                      <span className="text-[11px] text-zinc-500">
                        Como este operador remunera a plataforma
                      </span>
                    </div>

                    {/* Cards com as 5 opções de plano */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {(Object.keys(BILLING_PLANS) as BillingPlanType[]).map((planKey) => {
                        const plan = BILLING_PLANS[planKey];
                        const isSelected = formData.billingPlanType === planKey;

                        return (
                          <div
                            key={planKey}
                            onClick={() => setFormData({ ...formData, billingPlanType: planKey })}
                            className={cn(
                              "p-3.5 rounded-xl border-2 transition-all cursor-pointer flex flex-col justify-between",
                              isSelected
                                ? "border-emerald-600 bg-emerald-50/50 shadow-xs"
                                : "border-zinc-200 hover:border-zinc-300 bg-white"
                            )}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <h4
                                  className={cn(
                                    "text-xs font-bold",
                                    isSelected ? "text-emerald-900" : "text-zinc-800"
                                  )}
                                >
                                  {plan.label}
                                </h4>
                                <p className="text-[11px] text-zinc-500 mt-1 leading-snug">
                                  {plan.description}
                                </p>
                              </div>
                              <span
                                className={cn(
                                  "px-2 py-0.5 rounded text-[10px] font-extrabold uppercase shrink-0",
                                  isSelected
                                    ? "bg-emerald-600 text-white"
                                    : "bg-zinc-100 text-zinc-600"
                                )}
                              >
                                {plan.unit}
                              </span>
                            </div>
                            <div className="mt-2 text-[10px] text-zinc-400 italic">
                              {plan.helperText}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Valor e Ciclo */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Valor da Taxa / Mensalidade ({selectedPlan.unit}) *
                        </label>
                        <div className="relative">
                          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-400">
                            {selectedPlan.unit}
                          </span>
                          <input
                            required
                            type="number"
                            step="0.01"
                            min="0"
                            value={formData.billingRateValue}
                            onChange={(e) =>
                              setFormData({ ...formData, billingRateValue: parseFloat(e.target.value) || 0 })
                            }
                            className="w-full pl-9 pr-3.5 py-2.5 text-xs font-bold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                            placeholder="0.00"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Ciclo de Faturamento
                        </label>
                        <select
                          value={formData.billingCycle}
                          onChange={(e) => setFormData({ ...formData, billingCycle: e.target.value as BillingCycle })}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all cursor-pointer"
                        >
                          <option value="MENSAL">Mensal</option>
                          <option value="QUINZENAL">Quinzenal</option>
                          <option value="SEMANAL">Semanal</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Dia de Vencimento da Fatura
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="31"
                          value={formData.dueDay}
                          onChange={(e) => setFormData({ ...formData, dueDay: parseInt(e.target.value) || 10 })}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                          placeholder="10"
                        />
                      </div>
                    </div>

                    {/* Carência e Tolerância */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Dias de Degustação / Carência (Trial)
                        </label>
                        <input
                          type="number"
                          min="0"
                          value={formData.trialDays}
                          onChange={(e) => setFormData({ ...formData, trialDays: parseInt(e.target.value) || 0 })}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                          placeholder="14"
                        />
                        <span className="text-[10px] text-zinc-400 mt-1 block">
                          Coloque 0 se o operador já iniciar no plano Ativo com cobrança imediata.
                        </span>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Dias de Tolerância para Inadimplência
                        </label>
                        <input
                          type="number"
                          min="0"
                          value={formData.gracePeriodDays}
                          onChange={(e) =>
                            setFormData({ ...formData, gracePeriodDays: parseInt(e.target.value) || 0 })
                          }
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                          placeholder="5"
                        />
                        <span className="text-[10px] text-zinc-400 mt-1 block">
                          Dias de atraso tolerados antes da suspensão automática da base.
                        </span>
                      </div>
                    </div>

                    {/* Observações Contratuais */}
                    <div>
                      <label className="block text-xs font-bold text-zinc-700 mb-1">
                        Termos Especiais & Observações Contratuais
                      </label>
                      <textarea
                        rows={2}
                        value={formData.notes}
                        onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                        placeholder="Ex: Isenção de taxa de instalação no primeiro trimestre..."
                      />
                    </div>
                  </div>

                  <div className="flex justify-between">
                    <button
                      type="button"
                      onClick={() => setActiveTab("CADASTRO")}
                      className="px-4 py-2 border border-zinc-200 text-zinc-600 bg-white hover:bg-zinc-50 rounded-xl text-xs font-bold cursor-pointer"
                    >
                      ← Voltar
                    </button>
                    {!isEditing && (
                      <button
                        type="button"
                        onClick={() => setActiveTab("GERENTE")}
                        className="px-5 py-2 bg-zinc-900 hover:bg-zinc-800 text-white rounded-xl text-xs font-bold cursor-pointer"
                      >
                        Avançar para Gerente Master →
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 3: GERENTE MASTER (APENAS NA CRIAÇÃO) */}
              {activeTab === "GERENTE" && !isEditing && (
                <div className="space-y-5">
                  <div className="bg-white p-5 rounded-2xl border border-zinc-200 space-y-4 shadow-2xs">
                    <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2.5">
                      <User className="w-4 h-4 text-emerald-600" /> Administrador da Franquia
                    </h3>

                    <div>
                      <label className="block text-xs font-bold text-zinc-700 mb-1">
                        Nome Completo do Gerente *
                      </label>
                      <input
                        required
                        type="text"
                        value={formData.managerName}
                        onChange={(e) => setFormData({ ...formData, managerName: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                        placeholder="Ex: João da Silva"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-zinc-700 mb-1">
                        E-mail Corporativo de Acesso *
                      </label>
                      <input
                        required
                        type="email"
                        value={formData.managerEmail}
                        onChange={(e) => setFormData({ ...formData, managerEmail: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                        placeholder="joao@franquianeves.com.br"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-zinc-700 mb-1">
                        Senha Inicial Provisória *
                      </label>
                      <input
                        required
                        type="text"
                        value={formData.managerPassword}
                        onChange={(e) => setFormData({ ...formData, managerPassword: e.target.value })}
                        className="w-full px-3.5 py-2.5 text-xs font-mono bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                        placeholder="Mínimo 10 caracteres"
                        minLength={10}
                      />
                      <span className="text-[11px] text-zinc-400 mt-1 block">
                        O gerente poderá alterar a senha no primeiro login administrativo.
                      </span>
                    </div>

                    <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-start gap-2.5">
                      <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                      <div>
                        <strong>Acesso Isolado por Tenant:</strong>
                        <p className="text-[11px] text-emerald-700 mt-0.5">
                          Este usuário será o Administrador (Staff) com isolamento estrito da base.
                          Ele terá permissão para cadastrar lojas parceiras, frotas e despachantes
                          da própria operação.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-between">
                    <button
                      type="button"
                      onClick={() => setActiveTab("COBRANCA")}
                      className="px-4 py-2 border border-zinc-200 text-zinc-600 bg-white hover:bg-zinc-50 rounded-xl text-xs font-bold cursor-pointer"
                    >
                      ← Voltar
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Standard Footer */}
            <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex items-center justify-between gap-4 shrink-0">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 border border-zinc-200 text-zinc-700 bg-white hover:bg-zinc-100 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-2xs"
              >
                Cancelar
              </button>

              <button
                type="submit"
                disabled={saving}
                className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all cursor-pointer shadow-md shadow-emerald-600/20 flex items-center gap-2 disabled:opacity-50"
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                {isEditing ? "Salvar Alterações" : "Concluir Cadastro do Operador"}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>,
    document.body
  );
}

// ----------------------------------------------------------------------------
// DRAWER 2: Visualização 360° de Detalhes do Operador
// ----------------------------------------------------------------------------
function OperatorDetailsDrawer({
  operator,
  onClose,
  onEdit,
  onResetPassword,
  onChangeStatus,
}: {
  operator: OperatorType;
  onClose: () => void;
  onEdit: () => void;
  onResetPassword: () => void;
  onChangeStatus: () => void;
}) {
  const planConf = BILLING_PLANS[operator.billingPlanType] || BILLING_PLANS.PERCENT_PER_DELIVERY;
  const statusConf = STATUS_CONFIG[operator.status] || STATUS_CONFIG.ACTIVE;

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "unset";
    };
  }, []);

  const formatRate = (type: BillingPlanType, val: number) => {
    const p = BILLING_PLANS[type] || BILLING_PLANS.PERCENT_PER_DELIVERY;
    if (p.isPercentage) {
      return `${val.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 })}%`;
    }
    return formatCurrency(val);
  };

  return createPortal(
    <AnimatePresence>
      <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
          onClick={onClose}
        />

        {/* Lateral Slide-Over Drawer */}
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
              <div className="w-12 h-12 rounded-2xl bg-emerald-600 text-white flex items-center justify-center font-black text-xl shadow-md shadow-emerald-600/20 shrink-0">
                {operator.name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-black text-zinc-900 tracking-tight">
                    {operator.name}
                  </h2>
                  <span
                    className={cn(
                      "px-2.5 py-0.5 rounded-full text-[10px] font-bold border",
                      statusConf.bg,
                      statusConf.text,
                      statusConf.border
                    )}
                  >
                    {statusConf.label}
                  </span>
                </div>
                <p className="text-xs text-zinc-500 font-mono mt-0.5">
                  ID: {operator.id}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 bg-zinc-50/40">
            {/* Card 1: Modelo de Remuneração SaaS */}
            <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-2xs space-y-4">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-2.5">
                <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-emerald-600" /> Plano SaaS & Faturamento
                </h3>
                <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-100">
                  {planConf.badge}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-zinc-50 p-3.5 rounded-xl border border-zinc-100">
                  <span className="text-[10px] font-bold uppercase text-zinc-400">
                    Taxa / Valor Acordado
                  </span>
                  <p className="text-xl font-black text-zinc-900 mt-0.5">
                    {formatRate(operator.billingPlanType, operator.billingRateValue)}
                  </p>
                  <span className="text-[10px] text-zinc-500">{planConf.description}</span>
                </div>

                <div className="bg-zinc-50 p-3.5 rounded-xl border border-zinc-100">
                  <span className="text-[10px] font-bold uppercase text-zinc-400">
                    Ciclo & Vencimento
                  </span>
                  <p className="text-sm font-bold text-zinc-900 mt-0.5">
                    Dia {operator.dueDay || 10} • {operator.billingCycle || "MENSAL"}
                  </p>
                  <span className="text-[10px] text-zinc-500">
                    Tolerância: {operator.gracePeriodDays || 5} dias de carência
                  </span>
                </div>
              </div>

              {operator.notes && (
                <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-100 text-xs text-zinc-600">
                  <span className="font-bold text-zinc-700 block mb-0.5">
                    Termos & Observações Contratuais:
                  </span>
                  {operator.notes}
                </div>
              )}
            </div>

            {/* Card 2: Operação & Escopo */}
            <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-2xs space-y-4">
              <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2.5">
                <Store className="w-4 h-4 text-emerald-600" /> Operação & Ecossistema Vinculado
              </h3>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-3 p-3.5 bg-zinc-50 rounded-xl border border-zinc-100">
                  <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-zinc-700 shrink-0">
                    <Store className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase text-zinc-400">
                      Lojas Parceiras
                    </span>
                    <p className="text-lg font-black text-zinc-900">
                      {operator.storesCount || 0}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3.5 bg-zinc-50 rounded-xl border border-zinc-100">
                  <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-zinc-700 shrink-0">
                    <Bike className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase text-zinc-400">
                      Entregadores / Motoboys
                    </span>
                    <p className="text-lg font-black text-zinc-900">
                      {operator.driversCount || 0}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Card 3: Dados Cadastrais & Localização */}
            <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-2xs space-y-3">
              <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2.5">
                <Building2 className="w-4 h-4 text-emerald-600" /> Dados Cadastrais & Contato
              </h3>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-zinc-400 font-medium block">CNPJ</span>
                  <span className="font-mono font-bold text-zinc-800">{operator.cnpj || "-"}</span>
                </div>
                <div>
                  <span className="text-zinc-400 font-medium block">Localização</span>
                  <span className="font-bold text-zinc-800">
                    {operator.city ? `${operator.city} / ${operator.state || "BR"}` : "-"}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-400 font-medium block">Telefone / WhatsApp</span>
                  <span className="font-bold text-zinc-800">{operator.phone || "-"}</span>
                </div>
                <div>
                  <span className="text-zinc-400 font-medium block">Data de Criação</span>
                  <span className="font-bold text-zinc-800">
                    {operator.createdAt
                      ? new Date(operator.createdAt).toLocaleDateString("pt-BR")
                      : "-"}
                  </span>
                </div>
              </div>
            </div>

            {/* Card 4: Gerente Responsável */}
            <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-2xs space-y-3">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-2.5">
                <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2">
                  <User className="w-4 h-4 text-emerald-600" /> Gerente Master Responsável
                </h3>
                <button
                  onClick={onResetPassword}
                  className="text-[11px] font-bold text-amber-700 hover:text-amber-800 bg-amber-50 hover:bg-amber-100 px-2.5 py-1 rounded-lg border border-amber-200 flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <KeyRound className="w-3.5 h-3.5" /> Redefinir Senha
                </button>
              </div>

              <div className="space-y-1 text-xs">
                <p className="font-bold text-zinc-900 text-sm">{operator.managerName || "Não informado"}</p>
                <p className="font-mono text-zinc-500">{operator.managerEmail || "Sem email cadastrado"}</p>
              </div>
            </div>
          </div>

          {/* Footer com Ações */}
          <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex items-center justify-between gap-3 shrink-0">
            <button
              onClick={onChangeStatus}
              className="px-4 py-2 border border-zinc-200 text-zinc-700 bg-white hover:bg-zinc-100 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-2xs flex items-center gap-1.5"
            >
              <Ban className="w-3.5 h-3.5 text-zinc-500" /> Alterar Status
            </button>

            <button
              onClick={onEdit}
              className="px-5 py-2.5 bg-zinc-900 hover:bg-zinc-800 text-white rounded-xl text-xs font-bold transition-all cursor-pointer shadow-xs flex items-center gap-2"
            >
              <Edit2 className="w-3.5 h-3.5" /> Editar Operador
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>,
    document.body
  );
}

// ----------------------------------------------------------------------------
// MODAL: Alteração de Status da Assinatura
// ----------------------------------------------------------------------------
function ChangeStatusModal({
  operator,
  onClose,
  onSuccess,
}: {
  operator: OperatorType;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [status, setStatus] = useState<OperatorStatus>(operator.status);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await authFetch(`/api/admin/operators/${operator.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        alert("Status do operador atualizado com sucesso!");
        onSuccess();
      } else {
        const err = await res.json();
        alert(err.error || "Erro ao alterar status");
      }
    } catch (e: any) {
      alert("Erro na requisição: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-zinc-950/50 backdrop-blur-xs">
      <div className="bg-white rounded-2xl shadow-2xl border border-zinc-200 max-w-md w-full p-6 space-y-5">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-zinc-900 text-sm">Alterar Status da Franquia</h3>
              <p className="text-xs text-zinc-500">{operator.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-600 p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            {(Object.keys(STATUS_CONFIG) as OperatorStatus[]).map((st) => {
              const conf = STATUS_CONFIG[st];
              const isSelected = status === st;

              return (
                <div
                  key={st}
                  onClick={() => setStatus(st)}
                  className={cn(
                    "p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between",
                    isSelected
                      ? "border-emerald-600 bg-emerald-50/40 shadow-xs"
                      : "border-zinc-200 hover:border-zinc-300 bg-white"
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    <span className={cn("w-2 h-2 rounded-full", conf.dot)} />
                    <span className="text-xs font-bold text-zinc-800">{conf.label}</span>
                  </div>
                  {isSelected && <Check className="w-4 h-4 text-emerald-600" />}
                </div>
              );
            })}
          </div>

          <p className="text-[11px] text-zinc-500 bg-zinc-50 p-3 rounded-xl border border-zinc-200">
            ℹ️ Alterar para <strong>Suspenso</strong> bloqueia o acesso dos despachantes e gerentes
            da base ao painel até a regularização do contrato ou pagamento.
          </p>

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-zinc-200 text-zinc-600 rounded-xl text-xs font-bold hover:bg-zinc-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Confirmar Alteração
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}

// ----------------------------------------------------------------------------
// MODAL: Redefinição de Senha do Gerente Master
// ----------------------------------------------------------------------------
function ResetPasswordModal({
  operator,
  onClose,
}: {
  operator: OperatorType;
  onClose: () => void;
}) {
  const [newPassword, setNewPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await authFetch(`/api/admin/operators/${operator.id}/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ newPassword }),
      });
      if (res.ok) {
        setSuccessMsg(`Senha do gerente (${operator.managerEmail}) redefinida com sucesso!`);
        setTimeout(() => {
          onClose();
        }, 2000);
      } else {
        const err = await res.json();
        alert(err.error || "Erro ao redefinir senha");
      }
    } catch (e: any) {
      alert("Erro na requisição: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-zinc-950/50 backdrop-blur-xs">
      <div className="bg-white rounded-2xl shadow-2xl border border-zinc-200 max-w-md w-full p-6 space-y-5">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 flex items-center justify-center shrink-0">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-zinc-900 text-sm">Redefinir Senha do Gerente</h3>
              <p className="text-xs text-zinc-500">{operator.managerEmail || operator.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-600 p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {successMsg ? (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-zinc-700 mb-1">
                Nova Senha de Acesso
              </label>
              <input
                required
                type="text"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 text-xs font-mono bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-emerald-500/10 focus:border-emerald-500 outline-none transition-all"
                placeholder="Digite a nova senha (mínimo 4 caracteres)"
              />
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-zinc-200 text-zinc-600 rounded-xl text-xs font-bold hover:bg-zinc-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving || newPassword.length < 4}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 disabled:opacity-50"
              >
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Salvar Nova Senha
              </button>
            </div>
          </form>
        )}
      </div>
    </div>,
    document.body
  );
}

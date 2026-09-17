import React, { useState, useEffect, useMemo, useCallback } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users,
  Search,
  Plus,
  Phone,
  MapPin,
  Calendar,
  DollarSign,
  TrendingUp,
  Package,
  ExternalLink,
  MessageSquare,
  RefreshCw,
  Loader2,
  X,
  Check,
  Building2,
  ArrowUpDown,
  UserPlus,
} from "lucide-react";
import { authFetch } from "../lib/api";
import { formatCurrency, cn } from "../lib/utils";
import { AddressAutocomplete } from "../components/AddressAutocomplete";

interface CustomerItem {
  id: string;
  name: string;
  phone: string;
  address: string;
  orders_count: number;
  total_spent_reais: number;
  ticket_medio_reais: number;
  last_order_at: string;
  store_name?: string;
}

export function Clientes() {
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"orders" | "spent" | "recent" | "name">("orders");
  const [isNewCustomerModalOpen, setIsNewCustomerModalOpen] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [number, setNumber] = useState("");
  const [complement, setComplement] = useState("");
  const [neighborhood, setNeighborhood] = useState("");
  const [notes, setNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch("/api/v1/client/customers");
      if (res.ok) {
        const data = await res.json();
        setCustomers(data.customers || []);
      }
    } catch (err) {
      console.error("Erro ao carregar clientes:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  useEffect(() => {
    if (isNewCustomerModalOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isNewCustomerModalOpen]);

  const handleSaveCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !address) {
      alert("Por favor, preencha o nome e o endereço do cliente.");
      return;
    }

    setIsSaving(true);
    try {
      const res = await authFetch("/api/v1/client/customers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          phone,
          address,
          number,
          complement,
          neighborhood,
          notes,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.customer) {
          setCustomers((prev) => [data.customer, ...prev]);
        }
        setIsNewCustomerModalOpen(false);
        // Reset form
        setName("");
        setPhone("");
        setAddress("");
        setNumber("");
        setComplement("");
        setNeighborhood("");
        setNotes("");
      } else {
        alert("Erro ao salvar cliente.");
      }
    } catch (err: any) {
      alert("Erro ao comunicar com o servidor: " + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const filteredAndSortedCustomers = useMemo(() => {
    let list = customers.filter((c) => {
      const q = search.toLowerCase();
      return (
        c.name.toLowerCase().includes(q) ||
        c.phone.toLowerCase().includes(q) ||
        c.address.toLowerCase().includes(q)
      );
    });

    list.sort((a, b) => {
      if (sortBy === "orders") return b.orders_count - a.orders_count;
      if (sortBy === "spent") return b.total_spent_reais - a.total_spent_reais;
      if (sortBy === "recent") return b.last_order_at.localeCompare(a.last_order_at);
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return 0;
    });

    return list;
  }, [customers, search, sortBy]);

  // Metric aggregates
  const totalOrders = useMemo(
    () => customers.reduce((sum, c) => sum + c.orders_count, 0),
    [customers],
  );
  const totalSpent = useMemo(
    () => customers.reduce((sum, c) => sum + c.total_spent_reais, 0),
    [customers],
  );
  const averageTicket = useMemo(
    () => (totalOrders > 0 ? totalSpent / totalOrders : 0),
    [totalOrders, totalSpent],
  );
  const recurringCustomersCount = useMemo(
    () => customers.filter((c) => c.orders_count > 1).length,
    [customers],
  );

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-5 rounded-2xl shadow-sm border border-zinc-200 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-zinc-900 text-white">
              Lojista
            </span>
            <span className="text-xs font-semibold text-zinc-500">
              Diretório de Destinatários (Módulo C6)
            </span>
          </div>
          <h1 className="text-xl font-bold text-zinc-900 tracking-tight">
            Meus Clientes
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Base consolidada de clientes finais com histórico de entregas e ticket médio
          </p>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={fetchCustomers}
            disabled={loading}
            className="p-2.5 border border-zinc-200 rounded-xl text-zinc-600 hover:bg-zinc-50 transition-colors"
            title="Atualizar lista"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
          <button
            onClick={() => setIsNewCustomerModalOpen(true)}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-900 hover:bg-zinc-800 text-white rounded-xl text-sm font-bold shadow-sm transition-all active:scale-95"
          >
            <Plus className="w-4 h-4" /> Cadastrar Cliente
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
              Total de Clientes
            </span>
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-zinc-900 tracking-tight">
            {customers.length}
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Destinatários cadastrados ou atendidos
          </p>
        </div>

        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
              Ticket Médio
            </span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-emerald-600 tracking-tight">
            {formatCurrency(averageTicket)}
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Média por entrega realizada
          </p>
        </div>

        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
              Total de Entregas
            </span>
            <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Package className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-zinc-900 tracking-tight">
            {totalOrders}
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Corridas despachadas para estes clientes
          </p>
        </div>

        <div className="bg-white border border-zinc-200 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
              Clientes Recorrentes
            </span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-amber-600 tracking-tight">
            {recurringCustomersCount}
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            Clientes com mais de 1 pedido
          </p>
        </div>
      </div>

      {/* Filter and Search Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white p-4 border border-zinc-200 rounded-2xl shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <input
            type="text"
            placeholder="Buscar por nome, telefone ou endereço..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
          />
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-500">
            <ArrowUpDown className="w-3.5 h-3.5" />
            <span>Ordenar por:</span>
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-2 text-xs font-bold bg-zinc-50 border border-zinc-200 rounded-xl text-zinc-700 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
          >
            <option value="orders">Mais Pedidos</option>
            <option value="spent">Maior Faturamento</option>
            <option value="recent">Mais Recentes</option>
            <option value="name">Ordem Alfabética</option>
          </select>
        </div>
      </div>

      {/* Customer Directory Table */}
      {loading ? (
        <div className="bg-white border border-zinc-200 rounded-2xl p-12 text-center shadow-sm">
          <Loader2 className="w-8 h-8 animate-spin text-zinc-400 mx-auto mb-3" />
          <p className="text-sm font-semibold text-zinc-600">
            Carregando catálogo de clientes...
          </p>
        </div>
      ) : filteredAndSortedCustomers.length === 0 ? (
        <div className="bg-white border border-zinc-200 rounded-2xl p-12 text-center shadow-sm">
          <Users className="w-10 h-10 text-zinc-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-zinc-900">
            Nenhum cliente encontrado
          </h3>
          <p className="text-xs text-zinc-500 max-w-sm mx-auto mt-1">
            {search
              ? "Nenhum cliente corresponde ao termo buscado."
              : "Cadastre clientes manualmente ou realize novos despachos para construir sua base."}
          </p>
        </div>
      ) : (
        <div className="bg-white border border-zinc-200 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 text-[11px] font-bold uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">Cliente</th>
                  <th className="px-5 py-3.5">Telefone</th>
                  <th className="px-5 py-3.5">Endereço Principal</th>
                  <th className="px-5 py-3.5 text-center">Pedidos</th>
                  <th className="px-5 py-3.5 text-right">Ticket Médio</th>
                  <th className="px-5 py-3.5 text-right">Total Faturado</th>
                  <th className="px-5 py-3.5 text-right">Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200/60">
                {filteredAndSortedCustomers.map((cust) => {
                  const cleanPhone = cust.phone.replace(/\D/g, "");
                  const whatsappUrl = cleanPhone
                    ? `https://wa.me/55${cleanPhone}`
                    : null;

                  return (
                    <tr
                      key={cust.id}
                      className="hover:bg-zinc-50/60 transition-colors"
                    >
                      {/* Name and Avatar */}
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-zinc-900 text-white font-black flex items-center justify-center text-xs uppercase shrink-0">
                            {cust.name.slice(0, 2)}
                          </div>
                          <div>
                            <div className="font-bold text-zinc-900">
                              {cust.name}
                            </div>
                            {cust.last_order_at && (
                              <div className="text-[10px] text-zinc-400">
                                Último pedido:{" "}
                                {new Date(cust.last_order_at).toLocaleDateString("pt-BR")}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Phone */}
                      <td className="px-5 py-4">
                        {cust.phone ? (
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-zinc-700">
                              {cust.phone}
                            </span>
                            {whatsappUrl && (
                              <a
                                href={whatsappUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="p-1 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 rounded transition-colors"
                                title="Abrir no WhatsApp"
                              >
                                <MessageSquare className="w-3.5 h-3.5" />
                              </a>
                            )}
                          </div>
                        ) : (
                          <span className="text-zinc-400 text-xs">Não informado</span>
                        )}
                      </td>

                      {/* Address */}
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1.5 text-zinc-700 max-w-xs truncate">
                          <MapPin className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                          <span className="truncate">{cust.address}</span>
                        </div>
                      </td>

                      {/* Orders Count */}
                      <td className="px-5 py-4 text-center">
                        <span
                          className={cn(
                            "px-2.5 py-0.5 rounded-full text-xs font-bold",
                            cust.orders_count > 1
                              ? "bg-indigo-50 text-indigo-700 border border-indigo-200/60"
                              : "bg-zinc-100 text-zinc-700",
                          )}
                        >
                          {cust.orders_count}
                        </span>
                      </td>

                      {/* Ticket Médio */}
                      <td className="px-5 py-4 text-right font-semibold text-zinc-700">
                        {formatCurrency(cust.ticket_medio_reais)}
                      </td>

                      {/* Total Spent */}
                      <td className="px-5 py-4 text-right font-black text-zinc-900">
                        {formatCurrency(cust.total_spent_reais)}
                      </td>

                      {/* Quick Action */}
                      <td className="px-5 py-4 text-right">
                        <a
                          href={`/corridas`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-zinc-100 hover:bg-zinc-900 hover:text-white text-zinc-700 rounded-lg text-xs font-bold transition-all shadow-sm"
                        >
                          Enviar Pedido
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal Cadastrar Cliente */}
      {createPortal(
        <AnimatePresence>
          {isNewCustomerModalOpen && (
            <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto transition-all"
                onClick={() => setIsNewCustomerModalOpen(false)}
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
                    <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 shrink-0">
                      <UserPlus className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                        Base de Clientes
                      </span>
                      <h2 className="text-xl font-black text-zinc-900 tracking-tight mt-0.5">
                        Cadastrar Cliente / Destinatário
                      </h2>
                      <p className="text-xs text-zinc-500 font-medium">
                        Adicione um cliente ou destinatário frequente para agilizar pedidos
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setIsNewCustomerModalOpen(false)}
                    className="p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <form
                  id="new-customer-form"
                  onSubmit={handleSaveCustomer}
                  className="flex-1 flex flex-col overflow-hidden"
                >
                  <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-5 bg-zinc-50/30">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Nome Completo *
                        </label>
                        <input
                          required
                          type="text"
                          placeholder="Ex: Maria Oliveira"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Telefone / WhatsApp
                        </label>
                        <input
                          type="text"
                          placeholder="(11) 98888-7777"
                          value={phone}
                          onChange={(e) => setPhone(e.target.value)}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-zinc-700 mb-1">
                        Endereço *
                      </label>
                      <AddressAutocomplete
                        required
                        value={address}
                        onChange={setAddress}
                        placeholder="Rua, Avenida, Praça..."
                      />
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Número
                        </label>
                        <input
                          type="text"
                          placeholder="123"
                          value={number}
                          onChange={(e) => setNumber(e.target.value)}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Complemento
                        </label>
                        <input
                          type="text"
                          placeholder="Apto 102"
                          value={complement}
                          onChange={(e) => setComplement(e.target.value)}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Bairro
                        </label>
                        <input
                          type="text"
                          placeholder="Centro"
                          value={neighborhood}
                          onChange={(e) => setNeighborhood(e.target.value)}
                          className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-zinc-700 mb-1">
                        Instruções de Entrega / Notas
                      </label>
                      <textarea
                        placeholder="Ex: Tocar o interfone 102, portão preto..."
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        className="w-full p-3 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 min-h-[80px] resize-none transition-all"
                      />
                    </div>
                  </div>

                  {/* Standard Footer */}
                  <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex items-center justify-between gap-4 shrink-0">
                    <button
                      type="button"
                      onClick={() => setIsNewCustomerModalOpen(false)}
                      disabled={isSaving}
                      className="px-5 py-2.5 border border-zinc-200 text-zinc-700 bg-white hover:bg-zinc-100 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-xs"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={isSaving}
                      className="px-6 py-2.5 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-sm transition-all flex items-center gap-1.5 cursor-pointer"
                    >
                      {isSaving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <Check className="w-4 h-4" /> Salvar Cliente
                        </>
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
    </div>
  );
}

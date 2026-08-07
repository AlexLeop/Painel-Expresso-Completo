import React, { useEffect, useState } from "react";
import { X, Phone, ShieldCheck, User, Wallet, Activity } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";

export interface MotoboyType {
  id?: string;
  nome: string;
  telefone: string;
  email?: string;
  document?: string;
  pixKeyType?: string;
  pixKey?: string;
  maxActiveOrders?: number;
  placa?: string;
  modelo?: string;
  status?: string;
  avaliacao?: number;
  corridas?: number;
  faturamento?: number;
  ativo?: boolean;
}

interface MotoboyModalProps {
  isOpen: boolean;
  onClose: () => void;
  motoboy: MotoboyType | null;
  onToggleActive: (
    motoboyId: string,
    nextActive: boolean,
  ) => Promise<void> | void;
  onSave?: (data: Partial<MotoboyType>) => Promise<void>;
}

export function MotoboyModal({
  isOpen,
  onClose,
  motoboy,
  onToggleActive,
  onSave,
}: MotoboyModalProps) {
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<"geral" | "financeiro" | "operacao">("geral");
  const [formData, setFormData] = useState({ 
    nome: "", 
    telefone: "", 
    email: "",
    document: "",
    pixKeyType: "TELEFONE",
    pixKey: "",
    maxActiveOrders: 3
  });

  useEffect(() => {
    setSaving(false);
    setActiveTab("geral");
    if (!motoboy) {
      setFormData({ 
        nome: "", 
        telefone: "", 
        email: "",
        document: "",
        pixKeyType: "TELEFONE",
        pixKey: "",
        maxActiveOrders: 3
      });
    } else {
      setFormData({
        nome: motoboy.nome || "",
        telefone: motoboy.telefone || "",
        email: motoboy.email || "",
        document: motoboy.document || "",
        pixKeyType: motoboy.pixKeyType || "TELEFONE",
        pixKey: motoboy.pixKey || "",
        maxActiveOrders: motoboy.maxActiveOrders || 3
      });
    }
  }, [isOpen, motoboy]);

  if (!isOpen) return null;

  const isCreating = !motoboy;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!onSave) return;
    setSaving(true);
    try {
      await onSave(formData);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const TabButton = ({ id, icon: Icon, label }: { id: any, icon: any, label: string }) => (
    <button
      type="button"
      onClick={() => setActiveTab(id)}
      className={cn(
        "flex items-center gap-2 px-3 py-2 text-xs font-bold rounded-lg transition-colors border",
        activeTab === id
          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
          : "bg-white text-zinc-500 border-transparent hover:bg-zinc-100"
      )}
    >
      <Icon className="h-4 w-4" /> {label}
    </button>
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-zinc-900/40 backdrop-blur-sm z-[50]"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-full w-full max-w-md bg-white shadow-2xl z-[51] flex flex-col border-l border-zinc-200"
          >
            <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/50">
              <h2 className="text-lg font-bold text-zinc-900">
                {isCreating ? "Novo Motoboy (Parceiro)" : "Motoboy"}
              </h2>
              <button
                onClick={onClose}
                className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 flex flex-col overflow-hidden">
              {isCreating && (
                <div className="px-6 py-3 border-b border-zinc-100 bg-white flex gap-2 overflow-x-auto">
                  <TabButton id="geral" icon={User} label="Pessoais" />
                  <TabButton id="financeiro" icon={Wallet} label="Financeiro" />
                  <TabButton id="operacao" icon={Activity} label="Operação" />
                </div>
              )}

              <div className="flex-1 overflow-y-auto p-6 bg-zinc-50/30">
                {isCreating ? (
                  <form id="motoboy-form" onSubmit={handleSubmit} className="space-y-6">
                    {activeTab === "geral" && (
                      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">Nome Completo</label>
                          <input required type="text" value={formData.nome} onChange={e => setFormData({ ...formData, nome: e.target.value })} className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900" placeholder="Ex: João da Silva"/>
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">CPF ou CNPJ (MEI)</label>
                          <input required type="text" value={formData.document} onChange={e => setFormData({ ...formData, document: e.target.value })} className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900" placeholder="000.000.000-00"/>
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">Telefone (WhatsApp)</label>
                          <input required type="text" value={formData.telefone} onChange={e => setFormData({ ...formData, telefone: e.target.value })} className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900" placeholder="Ex: (11) 99999-9999"/>
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">E-mail</label>
                          <input required type="email" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900" placeholder="Ex: joao@email.com"/>
                          <p className="text-[10px] text-zinc-500 mt-1">Será criada uma conta de acesso para este e-mail.</p>
                        </div>
                      </motion.div>
                    )}

                    {activeTab === "financeiro" && (
                      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">Tipo de Chave PIX</label>
                          <select value={formData.pixKeyType} onChange={e => setFormData({ ...formData, pixKeyType: e.target.value })} className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900">
                            <option value="TELEFONE">Telefone</option>
                            <option value="CPF">CPF / CNPJ</option>
                            <option value="EMAIL">E-mail</option>
                            <option value="ALEATORIA">Chave Aleatória</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">Chave PIX</label>
                          <input required type="text" value={formData.pixKey} onChange={e => setFormData({ ...formData, pixKey: e.target.value })} className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900" placeholder="Chave para repasse financeiro"/>
                        </div>
                      </motion.div>
                    )}

                    {activeTab === "operacao" && (
                      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">Limite de Corridas Simultâneas</label>
                          <input required type="number" min="1" max="10" value={formData.maxActiveOrders} onChange={e => setFormData({ ...formData, maxActiveOrders: Number(e.target.value) })} className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900" placeholder="Ex: 3"/>
                          <p className="text-[10px] text-zinc-500 mt-1">Máximo de pedidos que o motoboy pode aceitar na bag antes de obrigar a entrega.</p>
                        </div>
                      </motion.div>
                    )}
                  </form>
                ) : (
                  <div className="space-y-6">
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                        <ShieldCheck className="h-4 w-4 text-emerald-500" />
                        Visão Geral
                      </h3>

                      <div>
                        <label className="block text-xs font-semibold text-zinc-700 mb-1">Nome</label>
                        <div className="w-full px-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-700 font-semibold">
                          {motoboy.nome}
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-zinc-700 mb-1">Telefone</label>
                        <div className="relative">
                          <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                          <div className="w-full pl-9 pr-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-700 font-semibold">
                            {motoboy.telefone || "—"}
                          </div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">Avaliação</label>
                          <div className="w-full px-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-700 font-semibold">
                            {motoboy.avaliacao ? motoboy.avaliacao.toFixed(1) : "N/A"}
                          </div>
                        </div>
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">Status App</label>
                          <div className="w-full px-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-700 font-semibold">
                            {motoboy.status || "—"}
                          </div>
                        </div>
                      </div>

                      <div className="pt-4 border-t border-zinc-100 mt-2">
                        <label className="block text-xs font-semibold text-zinc-700 mb-2">
                          Controle de Acesso
                        </label>
                        <button
                          type="button"
                          disabled={saving}
                          onClick={async () => {
                            setSaving(true);
                            try {
                              await onToggleActive(motoboy.id!, !!motoboy.ativo);
                              onClose();
                            } finally {
                              setSaving(false);
                            }
                          }}
                          className={cn(
                            "w-full px-4 py-2 rounded-lg text-sm font-bold shadow-sm transition-all border",
                            motoboy.ativo
                              ? "bg-white border-zinc-200 text-rose-700 hover:bg-rose-50"
                              : "bg-zinc-900 border-zinc-900 text-white hover:bg-zinc-800",
                          )}
                        >
                          {motoboy.ativo ? "Bloquear Acesso" : "Liberar Acesso"}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="p-4 border-t border-zinc-200 bg-white flex gap-3 shadow-[0_-4px_10px_rgba(0,0,0,0.02)]">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 text-sm font-bold text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-100 rounded-lg transition-colors"
              >
                {isCreating ? "Cancelar" : "Fechar"}
              </button>
              
              {isCreating && (
                <button
                  type="submit"
                  form="motoboy-form"
                  disabled={saving || !formData.nome || !formData.telefone || !formData.email || !formData.document}
                  className="flex-1 px-4 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 border border-emerald-600 rounded-lg transition-colors disabled:opacity-50"
                >
                  {saving ? "Registrando..." : "Registrar Parceiro"}
                </button>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  X,
  CalendarDays,
  Bike,
  FileText,
  ArrowUpRight,
  ArrowDownRight,
  Tag,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";

export interface LancamentoType {
  id?: number;
  motoboy: string;
  tipo: string;
  categoria: "Crédito" | "Débito";
  valor: number;
  data: string;
  descricao: string;
  entregas?: number;
  visibilidade?: "loja" | "motoboy" | "ambos";
}

interface LancamentoModalProps {
  isOpen: boolean;
  onClose: () => void;
  lancamento: LancamentoType | null;
  onSave: (lancamento: LancamentoType) => void;
  defaultCategoria: "Crédito" | "Débito";
  motoboys?: { id: string; nome: string }[];
  isAdmin?: boolean;
}

export function LancamentoModal({
  isOpen,
  onClose,
  lancamento,
  onSave,
  defaultCategoria,
  motoboys = [],
  isAdmin = false,
}: LancamentoModalProps) {
  const [formData, setFormData] = useState<LancamentoType>({
    motoboy: "",
    tipo: "",
    categoria: defaultCategoria,
    valor: 0,
    data: new Date().toLocaleDateString("pt-BR"),
    descricao: "",
    entregas: 1,
    visibilidade: "ambos",
  });

  useEffect(() => {
    if (lancamento) {
      setFormData(lancamento);
    } else {
      setFormData({
        motoboy: "",
        tipo: "",
        categoria: defaultCategoria,
        valor: 0,
        data: new Date().toLocaleDateString("pt-BR"),
        descricao: "",
        entregas: 1,
        visibilidade: "ambos",
      });
    }
  }, [lancamento, isOpen, defaultCategoria]);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const isCredit = formData.categoria === "Crédito";

  return createPortal(
    <AnimatePresence>
      {isOpen && (
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
            className="fixed top-0 right-0 h-full w-full max-w-lg md:max-w-xl bg-white shadow-2xl border-l border-zinc-200 z-10 flex flex-col pointer-events-auto overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 md:px-8 py-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/70 shrink-0">
              <div className="flex items-center gap-3.5">
                <div
                  className={cn(
                    "w-11 h-11 rounded-2xl flex items-center justify-center text-white shadow-md shrink-0",
                    isCredit
                      ? "bg-gradient-to-br from-emerald-500 to-emerald-600 shadow-emerald-500/20"
                      : "bg-gradient-to-br from-rose-500 to-rose-600 shadow-rose-500/20",
                  )}
                >
                  {isCredit ? (
                    <ArrowUpRight className="w-6 h-6" />
                  ) : (
                    <ArrowDownRight className="w-6 h-6" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700 border border-zinc-200">
                      Financeiro Operacional
                    </span>
                    <span
                      className={cn(
                        "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border",
                        isCredit
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-rose-50 text-rose-700 border-rose-200",
                      )}
                    >
                      {isCredit ? "Crédito (+)" : "Débito (-)"}
                    </span>
                  </div>
                  <h2 className="text-xl font-black text-zinc-900 tracking-tight mt-0.5">
                    {lancamento ? "Editar Lançamento" : "Novo Lançamento"}
                  </h2>
                  <p className="text-xs text-zinc-500 font-medium">
                    {isCredit
                      ? "Registro de valores a pagar/bonificar ao entregador"
                      : "Registro de deduções, adiantamentos ou penalidades"}
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

            <div className="flex-1 overflow-y-auto p-6 md:p-8 bg-zinc-50/30">
              <form
                id="lancamento-form"
                onSubmit={handleSubmit}
                className="space-y-6"
              >
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <FileText className="h-4 w-4 text-indigo-500" />
                    Detalhes do Lançamento
                  </h3>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Categoria (Entrada/Saída)
                    </label>
                    <select
                      required
                      value={formData.categoria}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          categoria: e.target.value as any,
                        })
                      }
                      className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                    >
                      <option value="Crédito">
                        Crédito (A receber / Bônus)
                      </option>
                      <option value="Débito">Débito (Vale / Desconto)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Motoboy
                    </label>
                    <div className="relative">
                      <Bike className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                      <select
                        required
                        value={formData.motoboy}
                        onChange={(e) =>
                          setFormData({ ...formData, motoboy: e.target.value })
                        }
                        className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                      >
                        <option value="" disabled>
                          Selecione um motoboy
                        </option>
                        {motoboys.length > 0 ? (
                          motoboys.map((m) => (
                            <option key={m.id || m.nome} value={m.nome}>
                              {m.nome}
                            </option>
                          ))
                        ) : (
                          <>
                            <option value="Carlos Santos">Carlos Santos</option>
                            <option value="Felipe Mendes">Felipe Mendes</option>
                            <option value="Juliana Silva">Juliana Silva</option>
                            <option value="Marcos Paulo">Marcos Paulo</option>
                            <option value="Roberto Alves">Roberto Alves</option>
                          </>
                        )}
                      </select>
                    </div>
                  </div>

                  <div
                    className={cn(
                      "grid gap-4",
                      formData.tipo === "corrida_manual"
                        ? "grid-cols-3"
                        : "grid-cols-2",
                    )}
                  >
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        Valor (R$)
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        required
                        value={
                          formData.valor === 0 &&
                          formData.tipo === "corrida_manual"
                            ? 0
                            : formData.valor || ""
                        }
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            valor: parseFloat(e.target.value) || 0,
                          })
                        }
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-mono"
                        placeholder="0.00"
                      />
                    </div>
                    {formData.tipo === "corrida_manual" && (
                      <div>
                        <label className="block text-xs font-bold text-emerald-600 mb-1">
                          Qtd. Entregas
                        </label>
                        <input
                          type="number"
                          min="1"
                          step="1"
                          required
                          value={formData.entregas || ""}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              entregas: parseInt(e.target.value, 10) || 1,
                            })
                          }
                          className="w-full px-3 py-2 text-sm bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all font-mono font-bold"
                        />
                      </div>
                    )}
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        Data
                      </label>
                      <div className="relative">
                        <CalendarDays className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                        <input
                          type="text"
                          required
                          value={formData.data}
                          onChange={(e) =>
                            setFormData({ ...formData, data: e.target.value })
                          }
                          className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                          placeholder="DD/MM/YYYY"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Tipo de Operação
                    </label>
                    <div className="relative">
                      <Tag className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                      {isCredit ? (
                        <select
                          required
                          value={
                            ["extra", "corrida_manual"].includes(formData.tipo)
                              ? formData.tipo
                              : formData.tipo
                                ? "outro"
                                : ""
                          }
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              tipo:
                                e.target.value === "outro"
                                  ? formData.tipo
                                  : e.target.value,
                            })
                          }
                          className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                        >
                          <option value="" disabled>
                            Selecione um tipo...
                          </option>
                          <option value="extra">Bônus / Extra</option>
                          <option value="corrida_manual">
                            Corrida Manual (Fora do App)
                          </option>
                          {formData.tipo &&
                            !["extra", "corrida_manual"].includes(
                              formData.tipo,
                            ) && <option value="outro">{formData.tipo}</option>}
                        </select>
                      ) : (
                        <input
                          type="text"
                          required
                          value={formData.tipo}
                          onChange={(e) =>
                            setFormData({ ...formData, tipo: e.target.value })
                          }
                          className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                          placeholder="Ex: Vale, Equipamento"
                        />
                      )}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Descrição
                    </label>
                    <textarea
                      required
                      rows={3}
                      value={formData.descricao}
                      onChange={(e) =>
                        setFormData({ ...formData, descricao: e.target.value })
                      }
                      className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all resize-none"
                      placeholder="Justificativa do lançamento..."
                    />
                  </div>

                  {isAdmin && (
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        Visibilidade no Relatório
                      </label>
                      <select
                        value={formData.visibilidade || "ambos"}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            visibilidade: e.target.value as any,
                          })
                        }
                        className="w-full px-3 py-2 text-sm bg-zinc-50/80 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                      >
                        <option value="ambos">
                          Ambos (Aparece para Loja e Motoboy)
                        </option>
                        <option value="loja">
                          Somente Loja (Ocultar do Motoboy)
                        </option>
                        <option value="motoboy">
                          Somente Motoboy (Ocultar da Loja)
                        </option>
                      </select>
                    </div>
                  )}
                </div>
              </form>
            </div>

            {/* Standard Footer */}
            <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex items-center justify-between gap-4 shrink-0">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 text-xs font-bold text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-100 rounded-xl transition-all cursor-pointer shadow-xs"
              >
                Cancelar
              </button>
              <button
                type="submit"
                form="lancamento-form"
                className={cn(
                  "px-6 py-2.5 text-white rounded-xl text-xs font-bold shadow-sm transition-all cursor-pointer",
                  isCredit
                    ? "bg-emerald-600 hover:bg-emerald-700 shadow-emerald-600/20"
                    : "bg-rose-600 hover:bg-rose-700 shadow-rose-600/20",
                )}
              >
                Salvar Lançamento
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

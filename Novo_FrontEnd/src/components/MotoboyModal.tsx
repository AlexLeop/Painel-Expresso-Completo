import React, { useEffect, useState } from "react";
import { X, Phone, ShieldCheck } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";

export interface MotoboyType {
  id: string;
  nome: string;
  telefone: string;
  placa: string;
  modelo: string;
  status: string;
  avaliacao: number;
  corridas: number;
  faturamento: number;
  ativo: boolean;
}

interface MotoboyModalProps {
  isOpen: boolean;
  onClose: () => void;
  motoboy: MotoboyType | null;
  onToggleActive: (
    motoboyId: string,
    nextActive: boolean,
  ) => Promise<void> | void;
}

export function MotoboyModal({
  isOpen,
  onClose,
  motoboy,
  onToggleActive,
}: MotoboyModalProps) {
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setSaving(false);
  }, [isOpen]);

  if (!isOpen) return null;

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
              <h2 className="text-lg font-bold text-zinc-900">Motoboy</h2>
              <button
                onClick={onClose}
                className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {!motoboy ? (
                <div className="text-sm text-zinc-500">
                  Selecione um motoboy para visualizar.
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                      <ShieldCheck className="h-4 w-4 text-emerald-500" />
                      Cadastro
                    </h3>

                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        Nome
                      </label>
                      <div className="w-full px-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-700 font-semibold">
                        {motoboy.nome}
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        Telefone
                      </label>
                      <div className="relative">
                        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                        <div className="w-full pl-9 pr-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-700 font-semibold">
                          {motoboy.telefone || "—"}
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        Status cadastral
                      </label>
                      <div className="w-full px-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-700 font-semibold">
                        {motoboy.status || "—"}
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-2">
                        Ativação do cadastro
                      </label>
                      <button
                        type="button"
                        disabled={saving}
                        onClick={async () => {
                          setSaving(true);
                          try {
                            await onToggleActive(motoboy.id, !motoboy.ativo);
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
                        {motoboy.ativo
                          ? "Desativar cadastro"
                          : "Ativar cadastro"}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-zinc-200 bg-white text-zinc-700 rounded-lg hover:bg-zinc-50 text-sm font-bold transition-all"
              >
                Cancelar
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

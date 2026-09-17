import React, { useEffect } from "react";
import { createPortal } from "react-dom";
import { X, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
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

  if (!isOpen) return null;

  return typeof document !== "undefined"
    ? createPortal(
        <AnimatePresence>
          <div className="fixed inset-0 z-[9999] overflow-hidden flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onCancel}
              className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs transition-all"
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ type: "spring", damping: 25, stiffness: 220 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-2xl shadow-2xl w-full max-w-md flex flex-col overflow-hidden border border-zinc-200 z-10"
            >
              {/* Header */}
              <div className="px-6 py-5 border-b border-zinc-100 flex items-start justify-between bg-zinc-50/50">
                <div className="flex items-center gap-3.5">
                  <div className="w-10 h-10 rounded-2xl bg-rose-50 border border-rose-100 text-rose-600 flex items-center justify-center shrink-0 shadow-xs">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-zinc-900 leading-snug">{title}</h2>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600">
                      Confirmação Necessária
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={onCancel}
                  className="p-1.5 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-xl transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Message */}
              <div className="px-6 py-5">
                <p className="text-sm text-zinc-600 leading-relaxed">{message}</p>
              </div>

              {/* Footer */}
              <div className="px-6 py-4 bg-zinc-50 border-t border-zinc-100 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-4 py-2 text-xs font-bold text-zinc-600 hover:text-zinc-900 hover:bg-zinc-200/60 rounded-xl transition-all cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={onConfirm}
                  className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all cursor-pointer"
                >
                  Confirmar Exclusão
                </button>
              </div>
            </motion.div>
          </div>
        </AnimatePresence>,
        document.body
      )
    : null;
}

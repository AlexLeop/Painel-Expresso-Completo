import React, { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
}

export function ConfirmModal({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const dialog = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const messageId = useId();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!isOpen) return;
    setError("");
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.querySelector<HTMLButtonElement>("button")?.focus();
    return () => {
      document.body.style.overflow = overflow;
      previous?.focus();
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
              onClick={() => { if (!pending) onCancel(); }}
              className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs transition-all"
            />

            <motion.div
              ref={dialog}
              role="dialog"
              aria-modal="true"
              aria-labelledby={titleId}
              aria-describedby={messageId}
              aria-busy={pending}
              onKeyDown={(event) => {
                if (event.key === "Escape" && !pending) onCancel();
                if (event.key !== "Tab") return;
                const buttons = dialog.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)");
                if (!buttons?.length) return;
                const first = buttons[0], last = buttons[buttons.length - 1];
                if (event.shiftKey && document.activeElement === first) {
                  event.preventDefault(); last.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                  event.preventDefault(); first.focus();
                }
              }}
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
                    <h2 id={titleId} className="text-base font-bold text-zinc-900 leading-snug">{title}</h2>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600">
                      Confirmação Necessária
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  aria-label="Fechar confirmação"
                  disabled={pending}
                  onClick={onCancel}
                  className="p-1.5 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-xl transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Message */}
              <div className="px-6 py-5">
                <p id={messageId} className="text-sm text-zinc-600 leading-relaxed">{message}</p>
                {error && <p role="alert">{error}</p>}
              </div>

              {/* Footer */}
              <div className="px-6 py-4 bg-zinc-50 border-t border-zinc-100 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  disabled={pending}
                  onClick={onCancel}
                  className="px-4 py-2 text-xs font-bold text-zinc-600 hover:text-zinc-900 hover:bg-zinc-200/60 rounded-xl transition-all cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={pending}
                  onClick={async () => {
                    if (pending) return;
                    setPending(true);
                    try { await onConfirm(); }
                    catch (cause) { setError(cause instanceof Error ? cause.message : "Falha ao confirmar."); }
                    finally { setPending(false); }
                  }}
                  className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all cursor-pointer"
                >
                  {pending ? "Confirmando..." : "Confirmar"}
                </button>
              </div>
            </motion.div>
          </div>
        </AnimatePresence>,
        document.body
      )
    : null;
}

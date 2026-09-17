import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, ShieldCheck, X, Building2, User, Mail, FileText, Loader2 } from "lucide-react";
import { authFetch } from "../lib/api";

export function Operadores() {
  const [operadores, setOperadores] = useState<any[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    fetchOperadores();
  }, []);

  const fetchOperadores = async () => {
    try {
      const res = await authFetch("/api/admin/operators");
      if (res.ok) {
        const data = await res.json();
        setOperadores(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-zinc-900">Operadores Logísticos</h1>
          <p className="text-sm text-zinc-500">Gestão de Franquias e Operações Base</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-zinc-900 hover:bg-zinc-800 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 cursor-pointer shadow-xs"
        >
          <Plus className="h-4 w-4" /> Novo Operador
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-zinc-200 overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 font-bold">
            <tr>
              <th className="px-5 py-3">Razão Social</th>
              <th className="px-4 py-3">CNPJ</th>
              <th className="px-4 py-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {operadores.map((op, i) => (
              <tr key={op.id || i} className="hover:bg-zinc-50/80">
                <td className="px-5 py-3.5 font-bold text-zinc-900">{op.name}</td>
                <td className="px-4 py-3.5 text-zinc-600 font-mono">{op.cnpj || "-"}</td>
                <td className="px-4 py-3.5 text-center">
                  <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-100 text-emerald-700">
                    {op.status || "Ativo"}
                  </span>
                </td>
              </tr>
            ))}
            {operadores.length === 0 && (
              <tr>
                <td colSpan={3} className="px-5 py-8 text-center text-zinc-400">
                  Nenhum operador logístico encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <NewOperatorModal
          onClose={() => setIsModalOpen(false)}
          onSuccess={() => {
            setIsModalOpen(false);
            fetchOperadores();
          }}
        />
      )}
    </div>
  );
}

function NewOperatorModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    name: "",
    cnpj: "",
    managerName: "",
    managerEmail: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "unset";
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await authFetch("/api/admin/operators", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (res.ok) {
        alert("Operador cadastrado com sucesso!");
        onSuccess();
      } else {
        const err = await res.json();
        alert(err.error || "Erro ao criar operador");
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
          className="fixed top-0 right-0 h-full w-full max-w-xl md:max-w-2xl bg-white shadow-2xl border-l border-zinc-200 z-10 flex flex-col pointer-events-auto overflow-hidden"
        >
          {/* Header */}
          <div className="px-6 md:px-8 py-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/70 shrink-0">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center text-white shadow-md shadow-emerald-600/20 shrink-0">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Franquias & Operadores
                </span>
                <h2 className="text-xl font-black text-zinc-900 tracking-tight mt-0.5">
                  Novo Operador Logístico
                </h2>
                <p className="text-xs text-zinc-500 font-medium">
                  Cadastre uma base de franquia e vincule o gerente responsável
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

          <form
            id="operator-form"
            onSubmit={handleSubmit}
            className="flex-1 flex flex-col overflow-hidden"
          >
            <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6 bg-zinc-50/30">
              {/* Section 1: Franquia */}
              <div className="bg-white p-5 rounded-2xl border border-zinc-200 space-y-4">
                <h3 className="text-xs font-bold text-emerald-700 uppercase flex items-center gap-1.5 border-b border-zinc-100 pb-2">
                  <Building2 className="h-4 w-4" /> Dados da Franquia
                </h3>
                <div>
                  <label className="block text-xs font-bold text-zinc-700 mb-1">
                    Razão Social / Nome da Base *
                  </label>
                  <input
                    required
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 outline-none transition-all"
                    placeholder="Ex: Expresso Neves Logística LTDA"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-zinc-700 mb-1">CNPJ</label>
                  <input
                    type="text"
                    value={formData.cnpj}
                    onChange={(e) => setFormData({ ...formData, cnpj: e.target.value })}
                    className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 outline-none transition-all"
                    placeholder="00.000.000/0000-00"
                  />
                </div>
              </div>

              {/* Section 2: Gerente */}
              <div className="bg-white p-5 rounded-2xl border border-zinc-200 space-y-4">
                <h3 className="text-xs font-bold text-emerald-700 uppercase flex items-center gap-1.5 border-b border-zinc-100 pb-2">
                  <User className="h-4 w-4" /> Gerente Master Responsável
                </h3>
                <div>
                  <label className="block text-xs font-bold text-zinc-700 mb-1">
                    Nome do Gerente *
                  </label>
                  <input
                    required
                    type="text"
                    value={formData.managerName}
                    onChange={(e) => setFormData({ ...formData, managerName: e.target.value })}
                    className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 outline-none transition-all"
                    placeholder="João Silva"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-zinc-700 mb-1">
                    E-mail do Gerente *
                  </label>
                  <input
                    required
                    type="email"
                    value={formData.managerEmail}
                    onChange={(e) => setFormData({ ...formData, managerEmail: e.target.value })}
                    className="w-full px-3.5 py-2.5 text-xs font-semibold bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 outline-none transition-all"
                    placeholder="joao@empresa.com"
                  />
                </div>
                <p className="text-[11px] text-zinc-500 bg-zinc-50 p-2.5 rounded-xl border border-zinc-200">
                  ℹ️ Uma conta administrativa será criada para este e-mail com acesso aos relatórios e frotas da sua franquia (senha padrão inicial: 123456).
                </p>
              </div>
            </div>

            {/* Standard Footer */}
            <div className="px-6 md:px-8 py-4 border-t border-zinc-200 bg-zinc-50/90 backdrop-blur-xs flex items-center justify-between gap-4 shrink-0">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 border border-zinc-200 text-zinc-700 bg-white hover:bg-zinc-100 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-xs"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-6 py-2.5 bg-zinc-900 hover:bg-zinc-800 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-sm transition-all flex items-center gap-2 cursor-pointer"
              >
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Cadastrando...</span>
                  </>
                ) : (
                  <span>Cadastrar Operador</span>
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>,
    document.body,
  );
}

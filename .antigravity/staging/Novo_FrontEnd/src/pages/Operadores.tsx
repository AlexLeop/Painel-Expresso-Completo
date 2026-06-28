import React, { useState, useEffect } from "react";
import { Plus, ShieldCheck, X } from "lucide-react";
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
          className="bg-zinc-900 hover:bg-zinc-800 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2"
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
              <tr key={i} className="hover:bg-zinc-50/50">
                <td className="px-5 py-3 font-bold text-zinc-900">{op.name}</td>
                <td className="px-4 py-3 text-zinc-500">{op.cnpj || "—"}</td>
                <td className="px-4 py-3 text-center">
                  <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold">
                    {op.status}
                  </span>
                </td>
              </tr>
            ))}
            {operadores.length === 0 && (
              <tr>
                <td colSpan={3} className="px-5 py-8 text-center text-zinc-500">
                  Nenhum operador cadastrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <OperadorModal
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

function OperadorModal({ onClose, onSuccess }: { onClose: () => void, onSuccess: () => void }) {
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    cnpj: "",
    managerName: "",
    managerEmail: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await authFetch("/api/admin/operators", {
        method: "POST",
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

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-100 flex items-center justify-between">
          <h2 className="text-lg font-bold text-zinc-900">Novo Operador Logístico</h2>
          <button onClick={onClose} className="p-1 hover:bg-zinc-100 rounded-full"><X className="h-5 w-5"/></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <h3 className="text-xs font-bold text-emerald-600 uppercase flex items-center gap-1">
            <ShieldCheck className="h-4 w-4" /> Dados da Franquia
          </h3>
          <div>
            <label className="block text-xs font-bold text-zinc-700 mb-1">Razão Social</label>
            <input required type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-emerald-500" placeholder="Ex: Expresso Neves Logística LTDA"/>
          </div>
          <div>
            <label className="block text-xs font-bold text-zinc-700 mb-1">CNPJ</label>
            <input type="text" value={formData.cnpj} onChange={e => setFormData({...formData, cnpj: e.target.value})} className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-emerald-500" placeholder="00.000.000/0000-00"/>
          </div>

          <h3 className="text-xs font-bold text-emerald-600 uppercase flex items-center gap-1 mt-6">
            <ShieldCheck className="h-4 w-4" /> Gerente Master
          </h3>
          <div>
            <label className="block text-xs font-bold text-zinc-700 mb-1">Nome do Gerente</label>
            <input required type="text" value={formData.managerName} onChange={e => setFormData({...formData, managerName: e.target.value})} className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-emerald-500" placeholder="João Silva"/>
          </div>
          <div>
            <label className="block text-xs font-bold text-zinc-700 mb-1">E-mail do Gerente</label>
            <input required type="email" value={formData.managerEmail} onChange={e => setFormData({...formData, managerEmail: e.target.value})} className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-emerald-500" placeholder="joao@empresa.com"/>
          </div>
          <p className="text-[11px] text-zinc-500">Uma conta será criada para este e-mail com a senha padrão (123456).</p>
          
          <div className="pt-4 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-2 rounded-lg font-bold bg-zinc-100 text-zinc-700 hover:bg-zinc-200 text-sm">Cancelar</button>
            <button type="submit" disabled={saving} className="flex-1 py-2 rounded-lg font-bold bg-emerald-600 text-white hover:bg-emerald-700 text-sm disabled:opacity-50">
              {saving ? "Salvando..." : "Cadastrar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

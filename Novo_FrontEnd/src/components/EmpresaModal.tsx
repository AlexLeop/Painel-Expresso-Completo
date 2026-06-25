import React, { useState, useEffect } from "react";
import { X, Store, MapPin, Phone, CreditCard, Plus, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { authFetch } from "../lib/api";

export interface EmpresaType {
  id?: number;
  nome: string;
  endereco: string;
  telefone: string;
  status: string;
  // Regras Financeiras
  taxaCorridaPerEntrega: number;
  pisoFixo: number;
  pisoPercentual: number;
  taxaSupervisao: number;
  debitoPendente: number;
  // Diárias por dia da semana
  diaria_weekday: number;
  diaria_saturday: number;
  diaria_sunday: number;
  diaria_holiday: number;
  // Configurações de Relatório/Cálculo
  reportType: 'producao' | 'garantida' | 'garantida_horas';
  turnos: Array<{
    id: string;
    nome: string;
    startTime: string;
    endTime: string;
    diaria: { weekday: number; saturday: number; sunday: number; holiday: number };
  }>;
  faixasHoras: Array<{
    id: string;
    label: string;
    horasMinimas: number;
    horasMaximas: number;
    valor: number;
  }>;
  extraKmMode: 'disabled' | 'fixed' | 'delivery_fee';
  extraKmMinDistance: number;
  extraKmFixedAmount: number;
  machineEmpresaId?: string;
}

interface EmpresaModalProps {
  isOpen: boolean;
  onClose: () => void;
  empresa: EmpresaType | null;
  onSave: (empresa: EmpresaType) => void;
}

export function EmpresaModal({ isOpen, onClose, empresa, onSave }: EmpresaModalProps) {
  const [formData, setFormData] = useState<EmpresaType>({
    nome: "",
    endereco: "",
    telefone: "",
    status: "Ativo",
    taxaCorridaPerEntrega: 1.60,
    pisoFixo: 350,
    pisoPercentual: 0,
    taxaSupervisao: 0,
    debitoPendente: 0,
    diaria_weekday: 60,
    diaria_saturday: 70,
    diaria_sunday: 80,
    diaria_holiday: 80,
    reportType: 'producao',
    turnos: [],
    faixasHoras: [],
    extraKmMode: 'disabled',
    extraKmMinDistance: 6,
    extraKmFixedAmount: 3,
    machineEmpresaId: "",
  });

  const [garantidoDiario, setGarantidoDiario] = useState({ weekday: 80, saturday: 80, sunday: 80, holiday: 80 });

  useEffect(() => {
    if (empresa) {
      const faixas = Array.isArray((empresa as any).faixasHoras) ? (empresa as any).faixasHoras : (Array.isArray((empresa as any).faixas_horas_config) ? (empresa as any).faixas_horas_config : []);
      const gd = faixas.find((f: any) => f.id === 'garantido_diario');
      if (gd) {
        setGarantidoDiario({
          weekday: Number(gd.weekday) || 0,
          saturday: Number(gd.saturday) || 0,
          sunday: Number(gd.sunday) || 0,
          holiday: Number(gd.holiday) || 0,
        });
      } else {
        setGarantidoDiario({ weekday: 80, saturday: 80, sunday: 80, holiday: 80 });
      }

      setFormData({
        ...empresa,
        // Garantir fallbacks para campos que podem ser novos
        taxaCorridaPerEntrega: empresa.taxaCorridaPerEntrega ?? 1.60,
        pisoFixo: empresa.pisoFixo ?? 350,
        diaria_weekday: empresa.diaria_weekday ?? 60,
        diaria_saturday: empresa.diaria_saturday ?? 70,
        diaria_sunday: empresa.diaria_sunday ?? 80,
        diaria_holiday: empresa.diaria_holiday ?? 80,
        reportType: empresa.reportType ?? 'producao',
        turnos: Array.isArray((empresa as any).turnos) ? (empresa as any).turnos : (Array.isArray((empresa as any).turnos_config) ? (empresa as any).turnos_config : []),
        faixasHoras: faixas,
        extraKmMode: empresa.extraKmMode ?? 'disabled',
        machineEmpresaId: empresa.machineEmpresaId ?? "",
      });
    }
  }, [empresa, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let finalFaixas = (formData.faixasHoras || []).filter(f => f.id !== 'garantido_diario');
    if (formData.reportType === 'garantida') {
      finalFaixas.push({
        id: 'garantido_diario',
        label: 'Garantido Diário Mínimo',
        weekday: garantidoDiario.weekday,
        saturday: garantidoDiario.saturday,
        sunday: garantidoDiario.sunday,
        holiday: garantidoDiario.holiday,
      } as any);
    }
    onSave({ ...formData, faixasHoras: finalFaixas });
  };

  const updateGarantidoDiario = (field: keyof typeof garantidoDiario, val: number) => {
    const updated = { ...garantidoDiario, [field]: val };
    setGarantidoDiario(updated);
    const currentFaixas = (formData.faixasHoras || []).filter(f => f.id !== 'garantido_diario');
    currentFaixas.push({
      id: 'garantido_diario',
      label: 'Garantido Diário Mínimo',
      ...updated,
    } as any);
    setFormData({ ...formData, faixasHoras: currentFaixas });
  };

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
                {empresa ? "Editar Empresa" : "Nova Empresa"}
              </h2>
              <button
                onClick={onClose}
                className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <form id="empresa-form" onSubmit={handleSubmit} className="space-y-6">
                
                {/* Informações Principais */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <Store className="h-4 w-4 text-indigo-500" />
                    Informações Principais
                  </h3>
                  
                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Nome Fantasia</label>
                    <input
                      type="text"
                      required
                      value={formData.nome}
                      onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                      className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                      placeholder="Ex: Burger King - Centro"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Endereço Completo</label>
                    <div className="relative">
                      <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                      <input
                        type="text"
                        required
                        value={formData.endereco}
                        onChange={(e) => setFormData({ ...formData, endereco: e.target.value })}
                        className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                        placeholder="Ex: Av. Paulista, 1000"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Telefone / Contato</label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                      <input
                        type="text"
                        required
                        value={formData.telefone}
                        onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                        className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                        placeholder="(11) 3000-1111"
                      />
                    </div>
                  </div>
                </div>

                {/* Configuracoes Financeiras */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <CreditCard className="h-4 w-4 text-emerald-500" />
                    Configurações Financeiras
                  </h3>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">ID Machine API</label>
                      <input
                        type="text"
                        readOnly
                        value={formData.machineEmpresaId}
                        className="w-full px-3 py-2 text-sm bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-400 cursor-not-allowed font-mono"
                      />
                    </div>
                    <div>
                       <label className="block text-xs font-semibold text-zinc-700 mb-1">Status do Painel</label>
                       <select
                         value={formData.status}
                         onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                         className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                       >
                         <option value="Ativo">Ativo</option>
                         <option value="Inativo">Inativo</option>
                       </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Modelo de Relatório</label>
                      <select
                        value={formData.reportType}
                        onChange={(e) => setFormData({ ...formData, reportType: e.target.value as any })}
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                      >
                        <option value="producao">Produção (Diária + Taxas)</option>
                        <option value="garantida">Garantida Mínima</option>
                        <option value="garantida_horas">Garantida por Horas</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Taxa por Entrega R$</label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        required
                        value={formData.taxaCorridaPerEntrega}
                        onChange={(e) => setFormData({ ...formData, taxaCorridaPerEntrega: parseFloat(e.target.value) || 0 })}
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all font-mono"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Taxa ADM (Piso semanal) R$</label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        required
                        value={formData.pisoFixo}
                        onChange={(e) => setFormData({ ...formData, pisoFixo: parseFloat(e.target.value) || 0 })}
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Piso Percentual %</label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.1"
                        required
                        value={formData.pisoPercentual}
                        onChange={(e) => setFormData({ ...formData, pisoPercentual: parseFloat(e.target.value) || 0 })}
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all font-mono"
                      />
                    </div>
                  </div>

                  {/* Diárias por dia da semana */}
                  <div className="p-3 bg-zinc-50 rounded-lg border border-zinc-100 space-y-3">
                    <label className="block text-[10px] font-black text-zinc-500 uppercase tracking-widest">
                      Diárias Base (por dia da semana)
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[10px] text-zinc-500 mb-1">SEG-SEX R$</label>
                        <input
                          type="number"
                          value={formData.diaria_weekday}
                          onChange={(e) => setFormData({ ...formData, diaria_weekday: parseFloat(e.target.value) || 0 })}
                          className="w-full px-2 py-1 text-xs border border-zinc-200 rounded bg-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-zinc-500 mb-1">SÁBADO R$</label>
                        <input
                          type="number"
                          value={formData.diaria_saturday}
                          onChange={(e) => setFormData({ ...formData, diaria_saturday: parseFloat(e.target.value) || 0 })}
                          className="w-full px-2 py-1 text-xs border border-zinc-200 rounded bg-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-zinc-500 mb-1">DOMINGO R$</label>
                        <input
                          type="number"
                          value={formData.diaria_sunday}
                          onChange={(e) => setFormData({ ...formData, diaria_sunday: parseFloat(e.target.value) || 0 })}
                          className="w-full px-2 py-1 text-xs border border-zinc-200 rounded bg-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-zinc-500 mb-1">FERIADO R$</label>
                        <input
                          type="number"
                          value={formData.diaria_holiday}
                          onChange={(e) => setFormData({ ...formData, diaria_holiday: parseFloat(e.target.value) || 0 })}
                          className="w-full px-2 py-1 text-xs border border-zinc-200 rounded bg-white font-mono"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Garantia Mínima (quando reportType === 'garantida') */}
                  {formData.reportType === 'garantida' && (
                    <div className="p-4 bg-amber-50/80 rounded-xl border border-amber-200/80 space-y-3">
                      <div>
                        <label className="block text-[11px] font-black text-amber-900 uppercase tracking-wider">
                          Garantia Mínima de Ganhos (por dia da semana)
                        </label>
                        <p className="text-[10px] text-amber-700 font-medium">
                          Define o piso mínimo garantido por dia trabalhado. Se a soma (Produção + Diária) ficar abaixo deste valor, o sistema pagará o complemento.
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[10px] text-amber-800 mb-1 font-bold">SEG-SEX R$</label>
                          <input
                            type="number"
                            value={garantidoDiario.weekday}
                            onChange={(e) => updateGarantidoDiario('weekday', parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 text-xs border border-amber-300 rounded bg-white font-mono text-amber-900 focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] text-amber-800 mb-1 font-bold">SÁBADO R$</label>
                          <input
                            type="number"
                            value={garantidoDiario.saturday}
                            onChange={(e) => updateGarantidoDiario('saturday', parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 text-xs border border-amber-300 rounded bg-white font-mono text-amber-900 focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] text-amber-800 mb-1 font-bold">DOMINGO R$</label>
                          <input
                            type="number"
                            value={garantidoDiario.sunday}
                            onChange={(e) => updateGarantidoDiario('sunday', parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 text-xs border border-amber-300 rounded bg-white font-mono text-amber-900 focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] text-amber-800 mb-1 font-bold">FERIADO R$</label>
                          <input
                            type="number"
                            value={garantidoDiario.holiday}
                            onChange={(e) => updateGarantidoDiario('holiday', parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 text-xs border border-amber-300 rounded bg-white font-mono text-amber-900 focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {formData.reportType === 'garantida_horas' && (
                    <div className="p-4 bg-zinc-50/80 rounded-xl border border-zinc-200/80 space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="block text-[11px] font-black text-zinc-700 uppercase tracking-wider">Garantia Mínima por Horas Trabalhadas</label>
                          <p className="text-[10px] text-zinc-500 font-medium">Define o garantido para cada turno independentemente com base em sua duração (ex: 0 a 4h = R$ 110, 0 a 6h = R$ 140).</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            const id = `faixa_${Date.now()}`;
                            setFormData(prev => ({
                              ...prev,
                              faixasHoras: [
                                ...(prev.faixasHoras || []),
                                { id, label: 'Faixa', horasMinimas: 0, horasMaximas: 4, valor: 0 },
                              ],
                            }));
                          }}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-black uppercase tracking-wider rounded-lg bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-100 shadow-2xs transition-all shrink-0 ml-2"
                        >
                          <Plus className="h-3.5 w-3.5 text-blue-600" /> Adicionar Faixa
                        </button>
                      </div>

                      <div className="grid grid-cols-12 gap-2 px-1 text-[9px] font-black text-zinc-400 uppercase tracking-widest pt-1">
                        <div className="col-span-4">Descrição da Faixa</div>
                        <div className="col-span-2 text-center">Horas Mínimas</div>
                        <div className="col-span-2 text-center">Horas Máximas</div>
                        <div className="col-span-3 text-right">Valor Garantido</div>
                        <div className="col-span-1"></div>
                      </div>

                      <div className="space-y-2.5">
                        {((formData.faixasHoras || []).filter(f => f.id !== 'garantido_diario')).length === 0 ? (
                          <div className="text-xs text-zinc-500 italic p-2 text-center bg-white rounded-lg border border-dashed border-zinc-200">
                            Nenhuma faixa horária cadastrada. Utilize o botão acima para adicionar.
                          </div>
                        ) : (
                          ((formData.faixasHoras || []).filter(f => f.id !== 'garantido_diario')).map((f) => (
                            <div key={f.id} className="grid grid-cols-12 gap-2 items-center bg-white p-2 rounded-lg border border-zinc-200 shadow-2xs transition-all">
                              <input
                                className="col-span-4 px-2 py-1 text-xs bg-zinc-50/50 border border-zinc-200 rounded-md font-medium text-zinc-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                value={f.label}
                                placeholder="ex: 0 a 4 horas"
                                onChange={(e) => setFormData(prev => ({
                                  ...prev,
                                  faixasHoras: prev.faixasHoras.map(item => item.id === f.id ? { ...item, label: e.target.value } : item)
                                }))}
                              />
                              <div className="col-span-2 relative">
                                <input
                                  type="number"
                                  min={0}
                                  step="0.5"
                                  className="w-full px-1 py-1 text-xs bg-zinc-50/50 border border-zinc-200 rounded-md font-mono text-center text-zinc-900 font-bold focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                  value={f.horasMinimas}
                                  onChange={(e) => setFormData(prev => ({
                                    ...prev,
                                    faixasHoras: prev.faixasHoras.map(item => item.id === f.id ? { ...item, horasMinimas: Number(e.target.value) || 0 } : item)
                                  }))}
                                />
                                <span className="absolute right-1 top-1/2 -translate-y-1/2 text-[9px] text-zinc-400 font-bold pointer-events-none hidden sm:inline">h</span>
                              </div>
                              <div className="col-span-2 relative">
                                <input
                                  type="number"
                                  min={0}
                                  step="0.5"
                                  className="w-full px-1 py-1 text-xs bg-zinc-50/50 border border-zinc-200 rounded-md font-mono text-center text-zinc-900 font-bold focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                  value={f.horasMaximas}
                                  onChange={(e) => setFormData(prev => ({
                                    ...prev,
                                    faixasHoras: prev.faixasHoras.map(item => item.id === f.id ? { ...item, horasMaximas: Number(e.target.value) || 0 } : item)
                                  }))}
                                />
                                <span className="absolute right-1 top-1/2 -translate-y-1/2 text-[9px] text-zinc-400 font-bold pointer-events-none hidden sm:inline">h</span>
                              </div>
                              <div className="col-span-3 relative">
                                <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-zinc-400 font-bold pointer-events-none">R$</span>
                                <input
                                  type="number"
                                  min={0}
                                  step="0.01"
                                  className="w-full pl-6 pr-2 py-1 text-xs bg-zinc-50/50 border border-zinc-200 rounded-md font-mono text-right text-zinc-900 font-bold focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                  value={f.valor}
                                  onChange={(e) => setFormData(prev => ({
                                    ...prev,
                                    faixasHoras: prev.faixasHoras.map(item => item.id === f.id ? { ...item, valor: Number(e.target.value) || 0 } : item)
                                  }))}
                                />
                              </div>
                              <button
                                type="button"
                                onClick={() => setFormData(prev => ({ ...prev, faixasHoras: prev.faixasHoras.filter(x => x.id !== f.id) }))}
                                className="col-span-1 p-1 rounded-md hover:bg-rose-50 text-rose-600 ml-auto transition-colors"
                                title="Remover faixa"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}

                  {/* Taxas Extras */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Taxa Supervisão R$</label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        required
                        value={formData.taxaSupervisao}
                        onChange={(e) => setFormData({ ...formData, taxaSupervisao: parseFloat(e.target.value) || 0 })}
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Débito Pendente R$</label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        required
                        value={formData.debitoPendente}
                        onChange={(e) => setFormData({ ...formData, debitoPendente: parseFloat(e.target.value) || 0 })}
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all font-mono text-rose-600"
                      />
                    </div>
                  </div>

                  {/* Configuração Extra KM */}
                  <div className="space-y-3 pt-2 border-t border-zinc-100">
                    <label className="block text-xs font-bold text-zinc-900">Configuração de Extra KM</label>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="col-span-2">
                        <label className="block text-[10px] text-zinc-500 mb-1">Modo de Cálculo</label>
                        <select
                          value={formData.extraKmMode}
                          onChange={(e) => setFormData({ ...formData, extraKmMode: e.target.value as any })}
                          className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                        >
                          <option value="disabled">Desativado</option>
                          <option value="fixed">Valor Fixo (Excedente)</option>
                          <option value="delivery_fee">Cobrar Taxa de Entrega</option>
                        </select>
                      </div>
                      {formData.extraKmMode !== 'disabled' && (
                        <>
                          <div>
                            <label className="block text-[10px] text-zinc-500 mb-1">KM Mínimo</label>
                            <input
                              type="number"
                              value={formData.extraKmMinDistance}
                              onChange={(e) => setFormData({ ...formData, extraKmMinDistance: parseFloat(e.target.value) || 0 })}
                              className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg font-mono"
                            />
                          </div>
                          {formData.extraKmMode === 'fixed' && (
                            <div>
                              <label className="block text-[10px] text-zinc-500 mb-1">Valor do Extra R$</label>
                              <input
                                type="number"
                                value={formData.extraKmFixedAmount}
                                onChange={(e) => setFormData({ ...formData, extraKmFixedAmount: parseFloat(e.target.value) || 0 })}
                                className="w-full px-3 py-2 text-sm border border-zinc-200 rounded-lg font-mono"
                              />
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>

              </form>
            </div>

            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-zinc-200 bg-white text-zinc-700 rounded-lg hover:bg-zinc-50 text-sm font-bold transition-all"
              >
                Cancelar
              </button>
              <button
                type="submit"
                form="empresa-form"
                className="flex-1 px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 text-sm font-bold shadow-sm transition-all"
              >
                Salvar Empresa
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

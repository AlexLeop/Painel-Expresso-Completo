import { logger } from '@/lib/logger';
import React, { useState, useEffect } from "react";
import { X, Check, Building2, User, Mail, Phone, Shield } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";
import { authFetch } from "../lib/api";

const roles = ["Gestor", "Supervisor", "Coordenador", "Operador", "Visualizador"];

export interface UserType {
  id?: string;
  nome: string;
  email: string;
  telefone: string;
  cargo: string;
  status: string;
  empresas: string[];
  password?: string;
}

interface UserModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: UserType | null;
  onSave: (user: UserType) => void;
}

export function UserModal({ isOpen, onClose, user, onSave }: UserModalProps) {
  const [availableCompanies, setAvailableCompanies] = useState<Array<{ id: string; name: string; machineEmpresaId?: string; active: boolean }>>([]);
  const [formData, setFormData] = useState<UserType>({
    nome: "",
    email: "",
    telefone: "",
    cargo: "Operador",
    status: "Ativo",
    empresas: [],
    password: "",
  });

  useEffect(() => {
    if (isOpen) {
      authFetch('/api/db/companies')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) {
            setAvailableCompanies(data);
          } else if (data && Array.isArray(data.companies)) {
            setAvailableCompanies(data.companies);
          }
        })
        .catch(err => logger.error('Erro ao buscar empresas no modal:', err));
    }
  }, [isOpen]);

  useEffect(() => {
    if (user) {
      setFormData({ ...user, password: "" });
    } else {
      setFormData({
        nome: "",
        email: "",
        telefone: "",
        cargo: "Operador",
        status: "Ativo",
        empresas: [],
        password: "",
      });
    }
  }, [user, isOpen]);

  if (!isOpen) return null;

  const toggleCompany = (companyId: string) => {
    setFormData((prev) => ({
      ...prev,
      empresas: prev.empresas.includes(companyId)
        ? prev.empresas.filter((id) => id !== companyId)
        : [...prev.empresas, companyId],
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
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
                {user ? "Editar Usuário" : "Novo Usuário"}
              </h2>
              <button
                onClick={onClose}
                className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <form id="user-form" onSubmit={handleSubmit} className="space-y-6">
                
                {/* Basic Info */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <User className="h-4 w-4 text-emerald-500" />
                    Informações Básicas
                  </h3>
                  
                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Nome Completo</label>
                    <input
                      type="text"
                      required
                      value={formData.nome}
                      onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                      className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all placeholder:text-zinc-400"
                      placeholder="Ex: João da Silva"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">E-mail</label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                      <input
                        type="email"
                        required
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all placeholder:text-zinc-400"
                        placeholder="joao@exemplo.com"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Telefone</label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                      <input
                        type="tel"
                        value={formData.telefone}
                        onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                        className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all placeholder:text-zinc-400"
                        placeholder="(11) 99999-9999"
                      />
                    </div>
                  </div>

                  {!user && (
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Senha de Acesso</label>
                      <input
                        type="password"
                        required
                        value={formData.password || ""}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all placeholder:text-zinc-400"
                        placeholder="Mínimo 6 caracteres"
                        minLength={6}
                      />
                    </div>
                  )}
                </div>

                {/* Role and Status */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <Shield className="h-4 w-4 text-emerald-500" />
                    Acessos e Permissões
                  </h3>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Cargo / Função</label>
                      <select
                        value={formData.cargo}
                        onChange={(e) => setFormData({ ...formData, cargo: e.target.value })}
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                      >
                        {roles.map((role) => (
                          <option key={role} value={role}>{role}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Status</label>
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
                </div>

                {/* Companies */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <Building2 className="h-4 w-4 text-emerald-500" />
                    Empresas Vinculadas
                  </h3>
                  <p className="text-xs text-zinc-500 -mt-2">Selecione uma ou mais empresas para as quais este usuário terá acesso.</p>
                  
                  <div className="space-y-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
                    {availableCompanies.length === 0 && (
                      <p className="text-xs text-zinc-400 py-2">Nenhuma empresa encontrada...</p>
                    )}
                    {availableCompanies.map((company) => {
                      const isSelected = formData.empresas.includes(company.id);
                      return (
                        <div
                          key={company.id}
                          onClick={() => toggleCompany(company.id)}
                          className={cn(
                            "flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all",
                            isSelected
                              ? "border-emerald-500 bg-emerald-50/50"
                              : "border-zinc-200 bg-white hover:border-emerald-200 hover:bg-zinc-50"
                          )}
                        >
                          <span className={cn(
                            "text-sm font-medium",
                            isSelected ? "text-emerald-900" : "text-zinc-700"
                          )}>
                            {company.name} {company.machineEmpresaId ? `(#${company.machineEmpresaId})` : ''}
                          </span>
                          <div className={cn(
                            "w-5 h-5 rounded flex items-center justify-center transition-colors border",
                            isSelected
                              ? "bg-emerald-500 border-emerald-500 text-white"
                              : "bg-white border-zinc-300"
                          )}>
                            {isSelected && <Check className="h-3.5 w-3.5" />}
                          </div>
                        </div>
                      );
                    })}
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
                form="user-form"
                className="flex-1 px-4 py-2 bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 text-sm font-bold shadow-sm transition-all"
              >
                Salvar Usuário
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}


import { logger } from "@/lib/logger";
import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Check, Building2, User, Mail, Phone, Shield } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";
import { authFetch } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const DEFAULT_ROLES = [
  "Gestor",
  "Operador",
  "Supervisor",
  "Coordenador",
  "Visualizador",
  "Lojista",
];

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
  const { session } = useAuth();
  const isPlatformAdmin = Boolean(session?.user?.is_platform_admin);
  const rolesList = isPlatformAdmin
    ? ["SuperAdmin Master", "Administrador", ...DEFAULT_ROLES]
    : DEFAULT_ROLES;

  const [availableCompanies, setAvailableCompanies] = useState<
    Array<{
      id: string;
      name: string;
      machineEmpresaId?: string;
      active: boolean;
    }>
  >([]);
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
      authFetch("/api/v1/db/companies")
        .then((res) => res.json())
        .then((data) => {
          if (Array.isArray(data)) {
            setAvailableCompanies(data);
          } else if (data && Array.isArray(data.companies)) {
            setAvailableCompanies(data.companies);
          }
        })
        .catch((err) => logger.error("Erro ao buscar empresas no modal:", err));
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
            className="fixed top-0 right-0 h-full w-full max-w-xl md:max-w-2xl bg-white shadow-2xl border-l border-zinc-200 z-10 flex flex-col pointer-events-auto overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 md:px-8 py-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/70 shrink-0">
              <div className="flex items-center gap-3.5">
                <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 shrink-0">
                  <User className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                      Controle de Acesso
                    </span>
                    {user && (
                      <span
                        className={cn(
                          "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border",
                          formData.status === "Ativo"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-rose-50 text-rose-700 border-rose-200",
                        )}
                      >
                        {formData.status}
                      </span>
                    )}
                  </div>
                  <h2 className="text-xl font-black text-zinc-900 tracking-tight mt-0.5">
                    {user ? "Editar Usuário" : "Novo Usuário"}
                  </h2>
                  <p className="text-xs text-zinc-500 font-medium">
                    {user
                      ? `Edite os privilégios e vínculos de ${user.nome}`
                      : "Cadastre um novo usuário com cargo e lojas atribuídas"}
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
                id="user-form"
                onSubmit={handleSubmit}
                className="space-y-6"
              >
                {/* Basic Info */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <User className="h-4 w-4 text-emerald-500" />
                    Informações Básicas
                  </h3>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Nome Completo
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.nome}
                      onChange={(e) =>
                        setFormData({ ...formData, nome: e.target.value })
                      }
                      className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all placeholder:text-zinc-400"
                      placeholder="Ex: João da Silva"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      E-mail
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                      <input
                        type="email"
                        required
                        value={formData.email}
                        onChange={(e) =>
                          setFormData({ ...formData, email: e.target.value })
                        }
                        className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all placeholder:text-zinc-400"
                        placeholder="joao@exemplo.com"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">
                      Telefone
                    </label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                      <input
                        type="tel"
                        value={formData.telefone}
                        onChange={(e) =>
                          setFormData({ ...formData, telefone: e.target.value })
                        }
                        className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all placeholder:text-zinc-400"
                        placeholder="(11) 99999-9999"
                      />
                    </div>
                  </div>

                  {!user && (
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        Senha de Acesso
                      </label>
                      <input
                        type="password"
                        required
                        value={formData.password || ""}
                        onChange={(e) =>
                          setFormData({ ...formData, password: e.target.value })
                        }
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all placeholder:text-zinc-400"
                        placeholder="Mínimo 10 caracteres"
                        minLength={10}
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
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        Cargo / Função
                      </label>
                      <select
                        value={formData.cargo}
                        onChange={(e) =>
                          setFormData({ ...formData, cargo: e.target.value })
                        }
                        className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
                      >
                        {rolesList.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">
                        Status
                      </label>
                      <select
                        value={formData.status}
                        onChange={(e) =>
                          setFormData({ ...formData, status: e.target.value })
                        }
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
                  <p className="text-xs text-zinc-500 -mt-2">
                    Selecione uma ou mais empresas para as quais este usuário
                    terá acesso.
                  </p>

                  <div className="space-y-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
                    {availableCompanies.length === 0 && (
                      <p className="text-xs text-zinc-400 py-2">
                        Nenhuma empresa encontrada...
                      </p>
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
                              : "border-zinc-200 bg-white hover:border-emerald-200 hover:bg-zinc-50",
                          )}
                        >
                          <span
                            className={cn(
                              "text-sm font-medium",
                              isSelected ? "text-emerald-900" : "text-zinc-700",
                            )}
                          >
                            {company.name}{" "}
                            {company.machineEmpresaId
                              ? `(#${company.machineEmpresaId})`
                              : ""}
                          </span>
                          <div
                            className={cn(
                              "w-5 h-5 rounded flex items-center justify-center transition-colors border",
                              isSelected
                                ? "bg-emerald-500 border-emerald-500 text-white"
                                : "bg-white border-zinc-300",
                            )}
                          >
                            {isSelected && <Check className="h-3.5 w-3.5" />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
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
                form="user-form"
                className="px-6 py-2.5 bg-zinc-900 text-white rounded-xl hover:bg-zinc-800 text-xs font-bold shadow-sm transition-all cursor-pointer"
              >
                Salvar Usuário
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

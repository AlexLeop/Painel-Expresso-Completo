import React, { useEffect, useState } from "react";
import {
  X,
  Phone,
  ShieldCheck,
  User,
  Wallet,
  Activity,
  MapPin,
  Bike,
  FileText,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";

export interface MotoboyType {
  id?: string;
  nome: string;
  telefone: string;
  email?: string;
  document?: string;
  rg?: string;
  birthDate?: string;
  // Endereço
  cep?: string;
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
  // Veículo
  vehicleType?: string;
  placa?: string;
  modelo?: string;
  marca?: string;
  ano?: string;
  cor?: string;
  // CNH
  cnhNumero?: string;
  cnhCategoria?: string;
  cnhValidade?: string;
  cnhPrimeiraHabilitacao?: string;
  // Financeiro & Operação
  pixKeyType?: string;
  pixKey?: string;
  maxActiveOrders?: number;
  password?: string;
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

type TabType = "geral" | "endereco" | "veiculo" | "documentos" | "financeiro";

export function MotoboyModal({
  isOpen,
  onClose,
  motoboy,
  onToggleActive,
  onSave,
}: MotoboyModalProps) {
  const [saving, setSaving] = useState(false);
  const [loadingCep, setLoadingCep] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>("geral");
  const [formData, setFormData] = useState({
    nome: "",
    telefone: "",
    email: "",
    document: "",
    rg: "",
    birthDate: "",
    cep: "",
    logradouro: "",
    numero: "",
    complemento: "",
    bairro: "",
    cidade: "",
    estado: "RJ",
    vehicleType: "MOTORCYCLE",
    placa: "",
    modelo: "",
    marca: "",
    ano: "",
    cor: "",
    cnhNumero: "",
    cnhCategoria: "A",
    cnhValidade: "",
    cnhPrimeiraHabilitacao: "",
    pixKeyType: "TELEFONE",
    pixKey: "",
    maxActiveOrders: 3,
    password: "",
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
        rg: "",
        birthDate: "",
        cep: "",
        logradouro: "",
        numero: "",
        complemento: "",
        bairro: "",
        cidade: "",
        estado: "RJ",
        vehicleType: "MOTORCYCLE",
        placa: "",
        modelo: "",
        marca: "",
        ano: "",
        cor: "",
        cnhNumero: "",
        cnhCategoria: "A",
        cnhValidade: "",
        cnhPrimeiraHabilitacao: "",
        pixKeyType: "TELEFONE",
        pixKey: "",
        maxActiveOrders: 3,
        password: "",
      });
    } else {
      setFormData({
        nome: motoboy.nome || "",
        telefone: motoboy.telefone || "",
        email: motoboy.email || "",
        document: motoboy.document || "",
        rg: motoboy.rg || "",
        birthDate: motoboy.birthDate || "",
        cep: motoboy.cep || "",
        logradouro: motoboy.logradouro || "",
        numero: motoboy.numero || "",
        complemento: motoboy.complemento || "",
        bairro: motoboy.bairro || "",
        cidade: motoboy.cidade || "",
        estado: motoboy.estado || "RJ",
        vehicleType: motoboy.vehicleType || "MOTORCYCLE",
        placa: motoboy.placa || "",
        modelo: motoboy.modelo || "",
        marca: motoboy.marca || "",
        ano: motoboy.ano || "",
        cor: motoboy.cor || "",
        cnhNumero: motoboy.cnhNumero || "",
        cnhCategoria: motoboy.cnhCategoria || "A",
        cnhValidade: motoboy.cnhValidade || "",
        cnhPrimeiraHabilitacao: motoboy.cnhPrimeiraHabilitacao || "",
        pixKeyType: motoboy.pixKeyType || "TELEFONE",
        pixKey: motoboy.pixKey || "",
        maxActiveOrders: motoboy.maxActiveOrders || 3,
        password: "",
      });
    }
  }, [isOpen, motoboy]);

  if (!isOpen) return null;

  const isCreating = !motoboy;

  const handleCepLookup = async (cepRaw: string) => {
    const clean = cepRaw.replace(/\D/g, "");
    setFormData((prev) => ({ ...prev, cep: cepRaw }));
    if (clean.length === 8) {
      setLoadingCep(true);
      try {
        const res = await fetch(`https://viacep.com.br/ws/${clean}/json/`);
        const data = await res.json();
        if (!data.erro) {
          setFormData((prev) => ({
            ...prev,
            logradouro: data.logradouro || prev.logradouro,
            bairro: data.bairro || prev.bairro,
            cidade: data.localidade || prev.cidade,
            estado: data.uf || prev.estado,
          }));
        }
      } catch (err) {
        // Silently fail or keep current inputs
      } finally {
        setLoadingCep(false);
      }
    }
  };

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

  const TabButton = ({
    id,
    icon: Icon,
    label,
  }: {
    id: TabType;
    icon: any;
    label: string;
  }) => (
    <button
      type="button"
      onClick={() => setActiveTab(id)}
      className={cn(
        "flex items-center gap-2 px-3 py-2 text-xs font-bold rounded-lg transition-all border shrink-0 whitespace-nowrap",
        activeTab === id
          ? "bg-emerald-50 text-emerald-700 border-emerald-300 shadow-sm"
          : "bg-white text-zinc-500 border-transparent hover:bg-zinc-100 hover:text-zinc-700",
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
            className="fixed top-0 right-0 h-full w-full max-w-xl bg-white shadow-2xl z-[51] flex flex-col border-l border-zinc-200"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/70 shrink-0">
              <div>
                <h2 className="text-lg font-bold text-zinc-900">
                  {isCreating ? "Novo Motoboy (Parceiro)" : "Perfil do Motoboy"}
                </h2>
                <p className="text-xs text-zinc-500 mt-0.5">
                  {isCreating
                    ? "Preencha os dados cadastrais, endereço, veículo e CNH."
                    : `Gestão cadastral e operacional de ${motoboy?.nome || "Entregador"}`}
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-full transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {isCreating && (
                <div className="px-6 py-2.5 border-b border-zinc-100 bg-white flex gap-2 overflow-x-auto hide-scrollbar shrink-0">
                  <TabButton id="geral" icon={User} label="Pessoais" />
                  <TabButton id="endereco" icon={MapPin} label="Endereço" />
                  <TabButton id="veiculo" icon={Bike} label="Veículo" />
                  <TabButton id="documentos" icon={FileText} label="Documentação" />
                  <TabButton id="financeiro" icon={Wallet} label="Financeiro & Operação" />
                </div>
              )}

              <div className="flex-1 overflow-y-auto p-6 bg-zinc-50/30">
                {isCreating ? (
                  <form
                    id="motoboy-form"
                    onSubmit={handleSubmit}
                    className="space-y-4"
                  >
                    {/* TAB 1: DADOS PESSOAIS */}
                    {activeTab === "geral" && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-4"
                      >
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">
                            Nome Completo *
                          </label>
                          <input
                            required
                            type="text"
                            value={formData.nome}
                            onChange={(e) =>
                              setFormData({ ...formData, nome: e.target.value })
                            }
                            className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                            placeholder="Ex: Carlos Eduardo de Oliveira"
                          />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              CPF ou CNPJ (MEI) *
                            </label>
                            <input
                              required
                              type="text"
                              value={formData.document}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  document: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="000.000.000-00"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              RG / Órgão Emissor
                            </label>
                            <input
                              type="text"
                              value={formData.rg}
                              onChange={(e) =>
                                setFormData({ ...formData, rg: e.target.value })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Ex: 12.345.678-9 SSP/RJ"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Telefone (WhatsApp) *
                            </label>
                            <input
                              required
                              type="text"
                              value={formData.telefone}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  telefone: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="(21) 98888-7777"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Data de Nascimento
                            </label>
                            <input
                              type="date"
                              value={formData.birthDate}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  birthDate: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">
                            E-mail de Acesso *
                          </label>
                          <input
                            required
                            type="email"
                            value={formData.email}
                            onChange={(e) =>
                              setFormData({ ...formData, email: e.target.value })
                            }
                            className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                            placeholder="motoboy@email.com"
                          />
                          <p className="text-[11px] text-zinc-500 mt-1">
                            Será criada uma conta de login no aplicativo com este e-mail.
                          </p>
                        </div>
                      </motion.div>
                    )}

                    {/* TAB 2: ENDEREÇO */}
                    {activeTab === "endereco" && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-4"
                      >
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1 flex items-center gap-1.5">
                              <span>CEP</span>
                              {loadingCep && (
                                <Loader2 className="h-3 w-3 animate-spin text-emerald-600" />
                              )}
                            </label>
                            <input
                              type="text"
                              value={formData.cep}
                              onChange={(e) => handleCepLookup(e.target.value)}
                              maxLength={9}
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="00000-000"
                            />
                            <span className="text-[10px] text-zinc-400">
                              Digite o CEP para preencher o endereço
                            </span>
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Bairro
                            </label>
                            <input
                              type="text"
                              value={formData.bairro}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  bairro: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Ex: Centro"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                          <div className="col-span-2">
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Logradouro (Rua / Av.)
                            </label>
                            <input
                              type="text"
                              value={formData.logradouro}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  logradouro: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Ex: Rua das Flores"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Número
                            </label>
                            <input
                              type="text"
                              value={formData.numero}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  numero: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="123"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Complemento
                            </label>
                            <input
                              type="text"
                              value={formData.complemento}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  complemento: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Apto 101"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Cidade
                            </label>
                            <input
                              type="text"
                              value={formData.cidade}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  cidade: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Rio de Janeiro"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              UF / Estado
                            </label>
                            <input
                              type="text"
                              value={formData.estado}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  estado: e.target.value.toUpperCase(),
                                })
                              }
                              maxLength={2}
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900 uppercase font-mono"
                              placeholder="RJ"
                            />
                          </div>
                        </div>
                      </motion.div>
                    )}

                    {/* TAB 3: VEÍCULO */}
                    {activeTab === "veiculo" && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-4"
                      >
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Tipo de Veículo
                            </label>
                            <select
                              value={formData.vehicleType}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  vehicleType: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                            >
                              <option value="MOTORCYCLE">Motocicleta</option>
                              <option value="CAR">Carro / Furgão</option>
                              <option value="BICYCLE">Bicicleta / Elétrica</option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Placa do Veículo
                            </label>
                            <input
                              type="text"
                              value={formData.placa}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  placa: e.target.value.toUpperCase(),
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900 font-mono uppercase"
                              placeholder="ABC1D23 ou ABC-1234"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Marca
                            </label>
                            <input
                              type="text"
                              value={formData.marca}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  marca: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Ex: Honda, Yamaha"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Modelo
                            </label>
                            <input
                              type="text"
                              value={formData.modelo}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  modelo: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Ex: CG 160 Fan"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Ano de Fabricação
                            </label>
                            <input
                              type="text"
                              value={formData.ano}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  ano: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Ex: 2023"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Cor
                            </label>
                            <input
                              type="text"
                              value={formData.cor}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  cor: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Ex: Vermelha, Preta"
                            />
                          </div>
                        </div>
                      </motion.div>
                    )}

                    {/* TAB 4: DOCUMENTAÇÃO / CNH */}
                    {activeTab === "documentos" && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-4"
                      >
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Número da CNH
                            </label>
                            <input
                              type="text"
                              value={formData.cnhNumero}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  cnhNumero: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900 font-mono"
                              placeholder="00000000000"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Categoria CNH
                            </label>
                            <select
                              value={formData.cnhCategoria}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  cnhCategoria: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                            >
                              <option value="A">Categoria A (Moto)</option>
                              <option value="AB">Categoria AB (Moto + Carro)</option>
                              <option value="B">Categoria B (Carro)</option>
                              <option value="C">Categoria C (Caminhão)</option>
                            </select>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Data de Validade CNH
                            </label>
                            <input
                              type="date"
                              value={formData.cnhValidade}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  cnhValidade: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                            />
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Primeira Habilitação
                            </label>
                            <input
                              type="date"
                              value={formData.cnhPrimeiraHabilitacao}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  cnhPrimeiraHabilitacao: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                            />
                          </div>
                        </div>
                      </motion.div>
                    )}

                    {/* TAB 5: FINANCEIRO & OPERAÇÃO */}
                    {activeTab === "financeiro" && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-4"
                      >
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Tipo de Chave PIX
                            </label>
                            <select
                              value={formData.pixKeyType}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  pixKeyType: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                            >
                              <option value="TELEFONE">Telefone</option>
                              <option value="CPF">CPF / CNPJ</option>
                              <option value="EMAIL">E-mail</option>
                              <option value="ALEATORIA">Chave Aleatória</option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Chave PIX para Repasses
                            </label>
                            <input
                              type="text"
                              value={formData.pixKey}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  pixKey: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Chave PIX do entregador"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Limite de Pedidos Simultâneos
                            </label>
                            <input
                              required
                              type="number"
                              min="1"
                              max="10"
                              value={formData.maxActiveOrders}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  maxActiveOrders: Number(e.target.value),
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                            />
                            <p className="text-[10px] text-zinc-500 mt-1">
                              Máximo de pedidos aceitos na bag ao mesmo tempo.
                            </p>
                          </div>

                          <div>
                            <label className="block text-xs font-semibold text-zinc-700 mb-1">
                              Senha Inicial do App
                            </label>
                            <input
                              type="password"
                              value={formData.password}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  password: e.target.value,
                                })
                              }
                              className="w-full px-3 py-2 text-sm bg-white border border-zinc-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none rounded-lg text-zinc-900"
                              placeholder="Padrão: 123456"
                            />
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </form>
                ) : (
                  /* VIEW MODE: PERFIL COMPLETO DO ENTREGADOR */
                  <div className="space-y-6">
                    <div className="flex items-center gap-4 bg-white p-4 rounded-xl border border-zinc-200">
                      <div className="h-14 w-14 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-800 font-bold text-xl">
                        {motoboy.nome ? motoboy.nome.charAt(0).toUpperCase() : "M"}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-bold text-zinc-900 truncate">
                            {motoboy.nome}
                          </h3>
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider",
                              motoboy.ativo
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-red-100 text-red-800",
                            )}
                          >
                            {motoboy.ativo ? "Ativo" : "Bloqueado"}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-500 flex items-center gap-2 mt-1">
                          <span>{motoboy.telefone || "Sem telefone"}</span>
                          {motoboy.placa && (
                            <>
                              <span>•</span>
                              <span className="font-mono uppercase font-bold text-zinc-700">
                                {motoboy.placa}
                              </span>
                            </>
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-white p-3 rounded-xl border border-zinc-200">
                        <span className="text-[11px] font-semibold text-zinc-500 block">
                          Avaliação
                        </span>
                        <span className="text-lg font-bold text-zinc-900">
                          {motoboy.avaliacao ? motoboy.avaliacao.toFixed(1) : "5.0"} ★
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-xl border border-zinc-200">
                        <span className="text-[11px] font-semibold text-zinc-500 block">
                          Status Operacional
                        </span>
                        <span className="text-sm font-bold text-zinc-900">
                          {motoboy.status || "Disponível"}
                        </span>
                      </div>
                    </div>

                    {/* Dados Cadastrais Adicionais se houver */}
                    <div className="bg-white p-4 rounded-xl border border-zinc-200 space-y-3">
                      <h4 className="text-xs font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-1.5 border-b border-zinc-100 pb-2">
                        <ShieldCheck className="h-4 w-4 text-emerald-600" />
                        Identificação e Documentos
                      </h4>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <span className="text-zinc-500 block">CPF / CNPJ:</span>
                          <span className="font-semibold text-zinc-900">
                            {motoboy.document || "—"}
                          </span>
                        </div>
                        <div>
                          <span className="text-zinc-500 block">Chave PIX:</span>
                          <span className="font-semibold text-zinc-900">
                            {motoboy.pixKey || motoboy.telefone || "—"}
                          </span>
                        </div>
                        <div>
                          <span className="text-zinc-500 block">Veículo / Placa:</span>
                          <span className="font-semibold text-zinc-900">
                            {motoboy.modelo || "Motocicleta"} ({motoboy.placa || "—"})
                          </span>
                        </div>
                        <div>
                          <span className="text-zinc-500 block">Limite de Corridas:</span>
                          <span className="font-semibold text-zinc-900">
                            {motoboy.maxActiveOrders || 3} na bag
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="pt-2">
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
                          "w-full px-4 py-2.5 rounded-lg text-sm font-bold shadow-sm transition-all border",
                          motoboy.ativo
                            ? "bg-white border-zinc-200 text-rose-700 hover:bg-rose-50"
                            : "bg-zinc-900 border-zinc-900 text-white hover:bg-zinc-800",
                        )}
                      >
                        {motoboy.ativo ? "Bloquear Acesso" : "Liberar Acesso"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-zinc-200 bg-white flex gap-3 shadow-[0_-4px_10px_rgba(0,0,0,0.02)] shrink-0">
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
                  disabled={
                    saving ||
                    !formData.nome ||
                    !formData.telefone ||
                    !formData.email ||
                    !formData.document
                  }
                  className="flex-1 px-4 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 border border-emerald-600 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Registrando...</span>
                    </>
                  ) : (
                    <span>Registrar Parceiro</span>
                  )}
                </button>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

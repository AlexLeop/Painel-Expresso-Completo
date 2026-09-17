import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
  X,
  Store,
  MapPin,
  Phone,
  CreditCard,
  Plus,
  Trash2,
  Clock,
  Car,
  Search,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Save,
  Building2,
  Navigation,
  FileText,
  BadgeCheck,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";

export interface EmpresaType {
  id?: number;
  nome: string;
  endereco: string;
  telefone: string;
  status: string;
  documento?: string;
  lat?: number;
  lng?: number;
  averagePrepTimeMinutes?: number;
  // Campos Estruturados de Endereço (opcionais para UI e retrocompatibilidade)
  cep?: string;
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro?: string;
  cidade?: string;
  estado?: string;
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
  reportType: "producao" | "garantida" | "garantida_horas";
  turnos: Array<{
    id: string;
    nome: string;
    startTime: string;
    endTime: string;
    diaria: {
      weekday: number;
      saturday: number;
      sunday: number;
      holiday: number;
    };
  }>;
  faixasHoras: Array<{
    id: string;
    label: string;
    horasMinimas: number;
    horasMaximas: number;
    valor: number;
  }>;
  extraKmMode: "disabled" | "fixed" | "delivery_fee";
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

type TabType = "geral" | "endereco" | "financeiro" | "turnos" | "km";

const TABS: Array<{ id: TabType; label: string; icon: React.ElementType }> = [
  { id: "geral", label: "Geral & Contato", icon: Store },
  { id: "endereco", label: "Endereço & GPS", icon: MapPin },
  { id: "financeiro", label: "Financeiro & Diárias", icon: CreditCard },
  { id: "turnos", label: "Horas & Turnos", icon: Clock },
  { id: "km", label: "KM Adicional", icon: Car },
];

function maskCEP(val: string): string {
  const digits = val.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

function maskCNPJ(val: string): string {
  const digits = val.replace(/\D/g, "").slice(0, 14);
  if (digits.length <= 2) return digits;
  if (digits.length <= 5) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  if (digits.length <= 8) return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5)}`;
  if (digits.length <= 12) return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8)}`;
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

function maskPhone(val: string): string {
  const digits = val.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 2) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  if (digits.length <= 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

function parseAddressString(addr: string) {
  if (!addr) return { cep: "", logradouro: "", numero: "", complemento: "", bairro: "", cidade: "", estado: "" };

  let cep = "";
  const cepMatch = addr.match(/\b\d{5}-?\d{3}\b/);
  if (cepMatch) {
    cep = maskCEP(cepMatch[0]);
  }

  // Remove CEP do texto para facilitar parsing
  const clean = addr.replace(/(?:CEP:?\s*)?\b\d{5}-?\d{3}\b/i, "").trim().replace(/,\s*$/, "");
  const parts = clean.split(",").map((p) => p.trim()).filter(Boolean);

  let logradouro = parts[0] || "";
  let numero = parts[1] || "";
  let complemento = "";
  let bairro = "";
  let cidade = "";
  let estado = "";

  if (parts.length === 2) {
    // Ex: "Av. Paulista, 1000"
    logradouro = parts[0];
    numero = parts[1];
  } else if (parts.length >= 3) {
    // Ex: "Rua das Flores, 123, Centro, Belo Horizonte - MG"
    const last = parts[parts.length - 1];
    const ufMatch = last.match(/^(.*?)\s*-\s*([A-Za-z]{2})$/);
    if (ufMatch) {
      cidade = ufMatch[1].trim();
      estado = ufMatch[2].toUpperCase();
    } else {
      cidade = last;
    }

    if (parts.length === 3) {
      bairro = parts[2].split("-")[0].trim();
    } else if (parts.length === 4) {
      bairro = parts[2];
    } else if (parts.length >= 5) {
      complemento = parts[2];
      bairro = parts[3];
    }
  }

  return { cep, logradouro, numero, complemento, bairro, cidade, estado };
}

export function EmpresaModal({
  isOpen,
  onClose,
  empresa,
  onSave,
}: EmpresaModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>("geral");
  const numeroInputRef = useRef<HTMLInputElement>(null);

  const [formData, setFormData] = useState<EmpresaType>({
    nome: "",
    endereco: "",
    telefone: "",
    status: "Ativo",
    documento: "",
    lat: undefined,
    lng: undefined,
    averagePrepTimeMinutes: 15,
    taxaCorridaPerEntrega: 1.6,
    pisoFixo: 350,
    pisoPercentual: 0,
    taxaSupervisao: 0,
    debitoPendente: 0,
    diaria_weekday: 60,
    diaria_saturday: 70,
    diaria_sunday: 80,
    diaria_holiday: 80,
    reportType: "producao",
    turnos: [],
    faixasHoras: [],
    extraKmMode: "disabled",
    extraKmMinDistance: 6,
    extraKmFixedAmount: 3,
    machineEmpresaId: "",
  });

  // Estado dos campos individuais de endereço
  const [addressFields, setAddressFields] = useState({
    cep: "",
    logradouro: "",
    numero: "",
    complemento: "",
    bairro: "",
    cidade: "",
    estado: "MG",
  });

  const [isSearchingCep, setIsSearchingCep] = useState(false);
  const [cepError, setCepError] = useState<string | null>(null);
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [geoStatus, setGeoStatus] = useState<"success" | "not_found" | "error" | null>(null);

  const [garantidoDiario, setGarantidoDiario] = useState({
    weekday: 80,
    saturday: 80,
    sunday: 80,
    holiday: 80,
  });

  // Monta o endereço formatado consolidado
  const formatConsolidatedAddress = (fields = addressFields): string => {
    const parts = [
      fields.logradouro ? `${fields.logradouro}${fields.numero ? `, ${fields.numero}` : ""}` : "",
      fields.complemento ? fields.complemento : "",
      fields.bairro ? fields.bairro : "",
      fields.cidade ? `${fields.cidade}${fields.estado ? ` - ${fields.estado}` : ""}` : fields.estado || "",
      fields.cep ? `CEP: ${fields.cep}` : "",
    ].filter(Boolean);
    return parts.join(", ");
  };

  useEffect(() => {
    if (empresa) {
      const faixas = Array.isArray((empresa as any).faixasHoras)
        ? (empresa as any).faixasHoras
        : Array.isArray((empresa as any).faixas_horas_config)
          ? (empresa as any).faixas_horas_config
          : [];
      const gd = faixas.find((f: any) => f.id === "garantido_diario");
      if (gd) {
        setGarantidoDiario({
          weekday: Number(gd.weekday) || 0,
          saturday: Number(gd.saturday) || 0,
          sunday: Number(gd.sunday) || 0,
          holiday: Number(gd.holiday) || 0,
        });
      } else {
        setGarantidoDiario({
          weekday: 80,
          saturday: 80,
          sunday: 80,
          holiday: 80,
        });
      }

      const parsedAddr = parseAddressString(empresa.endereco || "");
      setAddressFields({
        cep: empresa.cep || parsedAddr.cep || "",
        logradouro: empresa.logradouro || parsedAddr.logradouro || "",
        numero: empresa.numero || parsedAddr.numero || "",
        complemento: empresa.complemento || parsedAddr.complemento || "",
        bairro: empresa.bairro || parsedAddr.bairro || "",
        cidade: empresa.cidade || parsedAddr.cidade || "",
        estado: empresa.estado || parsedAddr.estado || "MG",
      });

      setFormData({
        ...empresa,
        documento: empresa.documento || "",
        lat: empresa.lat,
        lng: empresa.lng,
        averagePrepTimeMinutes: empresa.averagePrepTimeMinutes ?? 15,
        taxaCorridaPerEntrega: empresa.taxaCorridaPerEntrega ?? 1.6,
        pisoFixo: empresa.pisoFixo ?? 350,
        pisoPercentual: empresa.pisoPercentual ?? 0,
        taxaSupervisao: empresa.taxaSupervisao ?? 0,
        debitoPendente: empresa.debitoPendente ?? 0,
        diaria_weekday: empresa.diaria_weekday ?? 60,
        diaria_saturday: empresa.diaria_saturday ?? 70,
        diaria_sunday: empresa.diaria_sunday ?? 80,
        diaria_holiday: empresa.diaria_holiday ?? 80,
        reportType: empresa.reportType ?? "producao",
        turnos: Array.isArray((empresa as any).turnos)
          ? (empresa as any).turnos
          : Array.isArray((empresa as any).turnos_config)
            ? (empresa as any).turnos_config
            : [],
        faixasHoras: faixas,
        extraKmMode: empresa.extraKmMode ?? "disabled",
        extraKmMinDistance: empresa.extraKmMinDistance ?? 6,
        extraKmFixedAmount: empresa.extraKmFixedAmount ?? 3,
        machineEmpresaId: empresa.machineEmpresaId ?? "",
      });

      if (empresa.lat && empresa.lng) {
        setGeoStatus("success");
      }
    } else {
      // Novo cadastro - reset
      setFormData({
        nome: "",
        endereco: "",
        telefone: "",
        status: "Ativo",
        documento: "",
        lat: undefined,
        lng: undefined,
        averagePrepTimeMinutes: 15,
        taxaCorridaPerEntrega: 1.6,
        pisoFixo: 350,
        pisoPercentual: 0,
        taxaSupervisao: 0,
        debitoPendente: 0,
        diaria_weekday: 60,
        diaria_saturday: 70,
        diaria_sunday: 80,
        diaria_holiday: 80,
        reportType: "producao",
        turnos: [],
        faixasHoras: [],
        extraKmMode: "disabled",
        extraKmMinDistance: 6,
        extraKmFixedAmount: 3,
        machineEmpresaId: "",
      });
      setAddressFields({
        cep: "",
        logradouro: "",
        numero: "",
        complemento: "",
        bairro: "",
        cidade: "",
        estado: "MG",
      });
      setGeoStatus(null);
    }
    setActiveTab("geral");
    setCepError(null);
  }, [empresa, isOpen]);

  useEffect(() => {
    if (isOpen) {
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prevOverflow;
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Busca no ViaCEP
  const searchCep = async (cepToSearch: string) => {
    const cleanCep = cepToSearch.replace(/\D/g, "");
    if (cleanCep.length !== 8) {
      setCepError("Informe um CEP válido com 8 dígitos.");
      return;
    }

    setIsSearchingCep(true);
    setCepError(null);

    try {
      const res = await fetch(`https://viacep.com.br/ws/${cleanCep}/json/`);
      const data = await res.json();

      if (data.erro) {
        setCepError("CEP não localizado. Verifique e preencha os dados manualmente.");
        return;
      }

      const updated = {
        ...addressFields,
        cep: maskCEP(cleanCep),
        logradouro: data.logradouro || addressFields.logradouro,
        bairro: data.bairro || addressFields.bairro,
        cidade: data.localidade || addressFields.cidade,
        estado: data.uf || addressFields.estado,
      };

      setAddressFields(updated);
      setFormData((prev) => ({
        ...prev,
        endereco: formatConsolidatedAddress(updated),
      }));

      // Dispara geocodificação com os dados retornados
      fetchCoordinates({
        logradouro: data.logradouro,
        bairro: data.bairro,
        cidade: data.localidade,
        estado: data.uf,
      });

      // Foca automaticamente no campo número
      setTimeout(() => {
        numeroInputRef.current?.focus();
      }, 100);
    } catch {
      setCepError("Erro na consulta do CEP. Preencha os campos manualmente.");
    } finally {
      setIsSearchingCep(false);
    }
  };

  // Geocodificação OpenStreetMap / Nominatim
  const fetchCoordinates = async (override?: Partial<typeof addressFields>) => {
    const fields = { ...addressFields, ...(override || {}) };
    const street = fields.logradouro;
    const num = fields.numero;
    const city = fields.cidade;
    const state = fields.estado;
    const neighborhood = fields.bairro;

    if (!street && !city) {
      return;
    }

    setIsGeocoding(true);
    setGeoStatus(null);

    try {
      // 1ª tentativa: Logradouro + Número + Bairro + Cidade + Estado + Brasil
      const fullQuery = [street, num, neighborhood, city, state, "Brasil"].filter(Boolean).join(", ");
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(fullQuery)}&countrycodes=br&limit=1`,
        { headers: { "Accept-Language": "pt-BR" } }
      );
      const data = await res.json();

      if (data && data.length > 0) {
        const lat = parseFloat(data[0].lat);
        const lng = parseFloat(data[0].lon);
        setFormData((prev) => ({ ...prev, lat, lng }));
        setGeoStatus("success");
        return;
      }

      // 2ª tentativa (fallback): Logradouro + Cidade + Estado + Brasil (sem número restritivo)
      const fallbackQuery = [street, city, state, "Brasil"].filter(Boolean).join(", ");
      const resFallback = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(fallbackQuery)}&countrycodes=br&limit=1`,
        { headers: { "Accept-Language": "pt-BR" } }
      );
      const dataFallback = await resFallback.json();

      if (dataFallback && dataFallback.length > 0) {
        const lat = parseFloat(dataFallback[0].lat);
        const lng = parseFloat(dataFallback[0].lon);
        setFormData((prev) => ({ ...prev, lat, lng }));
        setGeoStatus("success");
      } else {
        setGeoStatus("not_found");
      }
    } catch (err) {
      console.error("Geocoding failed:", err);
      setGeoStatus("error");
    } finally {
      setIsGeocoding(false);
    }
  };

  const updateAddressField = (field: keyof typeof addressFields, val: string) => {
    const updated = { ...addressFields, [field]: val };
    setAddressFields(updated);
    setFormData((prev) => ({
      ...prev,
      endereco: formatConsolidatedAddress(updated),
    }));
  };

  const handleCepChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const masked = maskCEP(e.target.value);
    updateAddressField("cep", masked);
    const rawDigits = masked.replace(/\D/g, "");
    if (rawDigits.length === 8) {
      searchCep(rawDigits);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    let finalFaixas = (formData.faixasHoras || []).filter(
      (f) => f.id !== "garantido_diario",
    );
    if (formData.reportType === "garantida") {
      finalFaixas.push({
        id: "garantido_diario",
        label: "Garantido Diário Mínimo",
        weekday: garantidoDiario.weekday,
        saturday: garantidoDiario.saturday,
        sunday: garantidoDiario.sunday,
        holiday: garantidoDiario.holiday,
      } as any);
    }

    const consolidated = formatConsolidatedAddress(addressFields);

    onSave({
      ...formData,
      endereco: consolidated || formData.endereco,
      cep: addressFields.cep,
      logradouro: addressFields.logradouro,
      numero: addressFields.numero,
      complemento: addressFields.complemento,
      bairro: addressFields.bairro,
      cidade: addressFields.cidade,
      estado: addressFields.estado,
      faixasHoras: finalFaixas,
    });
  };

  const updateGarantidoDiario = (
    field: keyof typeof garantidoDiario,
    val: number,
  ) => {
    const updated = { ...garantidoDiario, [field]: val };
    setGarantidoDiario(updated);
    const currentFaixas = (formData.faixasHoras || []).filter(
      (f) => f.id !== "garantido_diario",
    );
    currentFaixas.push({
      id: "garantido_diario",
      label: "Garantido Diário Mínimo",
      ...updated,
    } as any);
    setFormData({ ...formData, faixasHoras: currentFaixas });
  };

  const currentTabIndex = TABS.findIndex((t) => t.id === activeTab);

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[9999] overflow-hidden pointer-events-none">
          {/* Backdrop Blur */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-zinc-950/50 backdrop-blur-xs pointer-events-auto"
            onClick={onClose}
          />

          {/* Modal Lateral Amplo (Slide-over Drawer sem scroll nas abas) */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 280 }}
            className="fixed top-0 right-0 h-full w-full max-w-3xl md:max-w-4xl lg:max-w-5xl bg-white shadow-2xl flex flex-col border-l border-zinc-200 pointer-events-auto"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/70 shrink-0">
              <div className="flex items-center gap-3.5">
                <div className="h-11 w-11 rounded-2xl bg-zinc-900 text-white flex items-center justify-center shadow-md shadow-zinc-900/10 shrink-0">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-lg font-extrabold text-zinc-900 tracking-tight flex items-center gap-2">
                    {empresa ? "Editar Loja Parceira" : "Nova Loja Parceira"}
                    <span
                      className={cn(
                        "text-[11px] font-bold px-2.5 py-0.5 rounded-full border",
                        formData.status === "Ativo"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-zinc-100 text-zinc-600 border-zinc-200"
                      )}
                    >
                      {formData.status}
                    </span>
                  </h2>
                  <p className="text-xs text-zinc-500 font-medium">
                    Configure os dados cadastrais, geolocalização exata e regras financeiras da loja.
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-full transition-colors"
                title="Fechar (Esc)"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Abas Superiores Segmentadas em Grid de 5 colunas - SEM NENHUM SCROLL */}
            <div className="px-6 py-2.5 border-b border-zinc-200/80 bg-zinc-50/70 shrink-0">
              <div className="grid grid-cols-5 gap-1.5 p-1 bg-zinc-200/70 rounded-2xl">
                {TABS.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setActiveTab(tab.id)}
                      className={cn(
                        "w-full flex items-center justify-center gap-1.5 py-2 px-1 rounded-xl text-xs font-bold transition-all select-none truncate",
                        isActive
                          ? "bg-white text-zinc-900 shadow-sm border border-zinc-200/80"
                          : "text-zinc-600 hover:text-zinc-900 hover:bg-white/50"
                      )}
                    >
                      <Icon className={cn("h-4 w-4 shrink-0", isActive ? "text-zinc-900" : "text-zinc-500")} />
                      <span className="truncate">{tab.label}</span>
                      {tab.id === "endereco" && formData.lat && formData.lng && (
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" title="Localizado" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Conteúdo das Abas */}
            <div className="flex-1 overflow-y-auto p-6 sm:p-7">
              <form id="empresa-form" onSubmit={handleSubmit} className="space-y-6">
                {/* ========================================================================= */}
                {/* ABA 1: DADOS GERAIS & CONTATO */}
                {/* ========================================================================= */}
                {activeTab === "geral" && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15 }}
                    className="space-y-5"
                  >
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="sm:col-span-2">
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Nome da Loja / Estabelecimento Parceiro <span className="text-rose-500">*</span>
                        </label>
                        <div className="relative">
                          <Store className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400 pointer-events-none" />
                          <input
                            type="text"
                            required
                            value={formData.nome}
                            onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                            className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-medium"
                            placeholder="Ex: Pizzaria Bella, Farmácia Central, Burger King Centro..."
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          CNPJ ou Documento
                        </label>
                        <div className="relative">
                          <FileText className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400 pointer-events-none" />
                          <input
                            type="text"
                            value={formData.documento || ""}
                            onChange={(e) =>
                              setFormData({ ...formData, documento: maskCNPJ(e.target.value) })
                            }
                            className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-mono"
                            placeholder="00.000.000/0000-00"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Telefone / WhatsApp de Contato <span className="text-rose-500">*</span>
                        </label>
                        <div className="relative">
                          <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400 pointer-events-none" />
                          <input
                            type="text"
                            required
                            value={formData.telefone}
                            onChange={(e) =>
                              setFormData({ ...formData, telefone: maskPhone(e.target.value) })
                            }
                            className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-medium"
                            placeholder="(31) 99999-9999"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Tempo Médio de Preparo (minutos)
                        </label>
                        <div className="relative">
                          <Clock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400 pointer-events-none" />
                          <input
                            type="number"
                            min="1"
                            value={formData.averagePrepTimeMinutes}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                averagePrepTimeMinutes: Number(e.target.value),
                              })
                            }
                            className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-mono"
                            placeholder="15"
                          />
                        </div>
                        <p className="text-[11px] text-zinc-400 mt-1">
                          Tempo padrão que a loja leva para embalar os pedidos antes do despacho.
                        </p>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Status Operacional
                        </label>
                        <select
                          value={formData.status}
                          onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                          className="w-full px-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-semibold"
                        >
                          <option value="Ativo">Ativo (Habilitada para entregas)</option>
                          <option value="Inativo">Inativo (Pausada no painel)</option>
                        </select>
                      </div>

                      {formData.machineEmpresaId && (
                        <div className="sm:col-span-2 p-3 bg-zinc-50 border border-zinc-200/80 rounded-xl flex items-center justify-between">
                          <div>
                            <span className="text-[11px] font-bold text-zinc-500 uppercase">
                              ID Machine API (Integração)
                            </span>
                            <div className="font-mono text-xs text-zinc-900 font-semibold">
                              {formData.machineEmpresaId}
                            </div>
                          </div>
                          <span className="text-[10px] text-zinc-400">
                            Sincronizado automaticamente com o sistema central
                          </span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}

                {/* ========================================================================= */}
                {/* ABA 2: ENDEREÇO & GEOLOCALIZAÇÃO (NOVO PADRÃO PROFISSIONAL) */}
                {/* ========================================================================= */}
                {activeTab === "endereco" && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15 }}
                    className="space-y-6"
                  >
                    {/* Box de Busca de CEP com Auto-preenchimento */}
                    <div className="p-4 bg-gradient-to-r from-blue-50/70 via-indigo-50/40 to-blue-50/70 rounded-2xl border border-blue-200/70 space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <label className="text-xs font-black text-blue-950 uppercase tracking-wider flex items-center gap-1.5">
                            <Search className="h-3.5 w-3.5 text-blue-600" />
                            Busca Rápida de Endereço via CEP
                          </label>
                          <p className="text-[11px] text-blue-800/80 font-medium">
                            Digite os 8 dígitos para preencher rua, bairro, cidade e obter coordenadas GPS.
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <div className="relative w-44">
                            <input
                              type="text"
                              value={addressFields.cep}
                              onChange={handleCepChange}
                              maxLength={9}
                              placeholder="00000-000"
                              className="w-full px-3 py-2 text-sm bg-white border border-blue-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all font-mono font-bold text-blue-950"
                            />
                            {isSearchingCep && (
                              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-blue-600 animate-spin" />
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={() => searchCep(addressFields.cep)}
                            disabled={isSearchingCep || addressFields.cep.replace(/\D/g, "").length !== 8}
                            className="px-3.5 py-2 text-xs font-bold rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white shadow-xs transition-all flex items-center gap-1.5 shrink-0"
                          >
                            {isSearchingCep ? "Buscando..." : "Consultar"}
                          </button>
                        </div>
                      </div>

                      {cepError && (
                        <p className="text-xs font-semibold text-rose-600 flex items-center gap-1.5">
                          <AlertCircle className="h-4 w-4 shrink-0" />
                          {cepError}
                        </p>
                      )}
                    </div>

                    {/* Inputs Estruturados */}
                    <div className="grid grid-cols-12 gap-3.5">
                      {/* Logradouro */}
                      <div className="col-span-12 sm:col-span-8">
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Logradouro (Rua, Avenida, Praça) <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={addressFields.logradouro}
                          onChange={(e) => updateAddressField("logradouro", e.target.value)}
                          onBlur={() => fetchCoordinates()}
                          placeholder="Ex: Av. Afonso Pena, Rua São Paulo..."
                          className="w-full px-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-medium"
                        />
                      </div>

                      {/* Número */}
                      <div className="col-span-6 sm:col-span-4">
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Número <span className="text-rose-500">*</span>
                        </label>
                        <input
                          ref={numeroInputRef}
                          type="text"
                          required
                          value={addressFields.numero}
                          onChange={(e) => updateAddressField("numero", e.target.value)}
                          onBlur={() => fetchCoordinates()}
                          placeholder="Ex: 1500, S/N"
                          className="w-full px-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-mono font-bold"
                        />
                      </div>

                      {/* Complemento */}
                      <div className="col-span-6 sm:col-span-4">
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Complemento (Opcional)
                        </label>
                        <input
                          type="text"
                          value={addressFields.complemento}
                          onChange={(e) => updateAddressField("complemento", e.target.value)}
                          placeholder="Ex: Loja 2, Bloco B, Sala 101"
                          className="w-full px-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-medium"
                        />
                      </div>

                      {/* Bairro */}
                      <div className="col-span-12 sm:col-span-4">
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Bairro <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={addressFields.bairro}
                          onChange={(e) => updateAddressField("bairro", e.target.value)}
                          placeholder="Ex: Centro, Savassi..."
                          className="w-full px-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-medium"
                        />
                      </div>

                      {/* Cidade */}
                      <div className="col-span-8 sm:col-span-3">
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          Cidade <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={addressFields.cidade}
                          onChange={(e) => updateAddressField("cidade", e.target.value)}
                          placeholder="Ex: Belo Horizonte"
                          className="w-full px-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-medium"
                        />
                      </div>

                      {/* Estado (UF) */}
                      <div className="col-span-4 sm:col-span-1">
                        <label className="block text-xs font-bold text-zinc-700 mb-1">
                          UF <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          maxLength={2}
                          value={addressFields.estado}
                          onChange={(e) => updateAddressField("estado", e.target.value.toUpperCase())}
                          placeholder="MG"
                          className="w-full px-2 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-bold text-center uppercase"
                        />
                      </div>
                    </div>

                    {/* Preview do Endereço Consolidado */}
                    <div className="p-3 bg-zinc-50 border border-zinc-200/80 rounded-xl flex items-center gap-2 text-xs text-zinc-600">
                      <MapPin className="h-4 w-4 text-zinc-400 shrink-0" />
                      <span className="font-semibold text-zinc-700 shrink-0">Endereço Salvo:</span>
                      <span className="font-medium text-zinc-900 truncate">
                        {formatConsolidatedAddress() || "Preencha os campos acima para gerar o endereço completo"}
                      </span>
                    </div>

                    {/* Bloco de Geolocalização (Lat / Lng) com PostGIS */}
                    <div className="p-4 sm:p-5 bg-zinc-50/80 rounded-2xl border border-zinc-200 space-y-4">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="flex items-center gap-2.5">
                          <div className="h-9 w-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
                            <Navigation className="h-4 w-4" />
                          </div>
                          <div>
                            <h4 className="text-xs font-bold text-zinc-900 uppercase tracking-wider">
                              Coordenadas GPS (Latitude / Longitude)
                            </h4>
                            <p className="text-[11px] text-zinc-500">
                              Crucial para cálculo de distância por raio PostGIS e despacho aos motoboys.
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => fetchCoordinates()}
                            disabled={isGeocoding || (!addressFields.logradouro && !addressFields.cidade)}
                            className="px-3 py-1.5 text-xs font-bold rounded-xl bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900 disabled:opacity-40 transition-all shadow-2xs flex items-center gap-1.5"
                          >
                            {isGeocoding ? (
                              <>
                                <Loader2 className="h-3.5 w-3.5 animate-spin text-zinc-600" />
                                Geocodificando...
                              </>
                            ) : (
                              <>
                                <Navigation className="h-3.5 w-3.5 text-indigo-600" />
                                Buscar GPS Automático
                              </>
                            )}
                          </button>

                          {formData.lat && formData.lng && (
                            <a
                              href={`https://www.google.com/maps?q=${formData.lat},${formData.lng}`}
                              target="_blank"
                              rel="noreferrer"
                              className="px-3 py-1.5 text-xs font-bold rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100 transition-all flex items-center gap-1.5"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                              Ver no Mapa
                            </a>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">
                            Latitude
                          </label>
                          <input
                            type="number"
                            step="0.000001"
                            value={formData.lat ?? ""}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                lat: e.target.value ? parseFloat(e.target.value) : undefined,
                              })
                            }
                            className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-mono font-semibold"
                            placeholder="-19.92083"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-zinc-700 mb-1">
                            Longitude
                          </label>
                          <input
                            type="number"
                            step="0.000001"
                            value={formData.lng ?? ""}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                lng: e.target.value ? parseFloat(e.target.value) : undefined,
                              })
                            }
                            className="w-full px-3 py-2 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-mono font-semibold"
                            placeholder="-43.93778"
                          />
                        </div>
                      </div>

                      {/* Status da Geolocalização */}
                      <div className="flex items-center justify-between pt-1">
                        {formData.lat && formData.lng ? (
                          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700">
                            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                            Loja devidamente geolocalizada no mapa.
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-700">
                            <AlertCircle className="h-4 w-4 text-amber-600" />
                            Coordenadas não informadas. Digite o CEP ou clique em "Buscar GPS Automático".
                          </div>
                        )}

                        {geoStatus === "not_found" && (
                          <span className="text-[11px] text-zinc-500">
                            Endereço não localizado automaticamente. Insira a lat/lng manualmente se souber.
                          </span>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ========================================================================= */}
                {/* ABA 3: FINANCEIRO & DIÁRIAS */}
                {/* ========================================================================= */}
                {activeTab === "financeiro" && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15 }}
                    className="space-y-6"
                  >
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Modelo de Fechamento / Relatório
                        </label>
                        <select
                          value={formData.reportType}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              reportType: e.target.value as any,
                            })
                          }
                          className="w-full px-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-semibold"
                        >
                          <option value="producao">Produção (Diária + Taxas por Entrega)</option>
                          <option value="garantida">Garantida Mínima (Complemento de Piso)</option>
                          <option value="garantida_horas">Garantida por Horas Trabalhadas</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Taxa Cobrada por Entrega (R$)
                        </label>
                        <div className="relative">
                          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-400">
                            R$
                          </span>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            required
                            value={formData.taxaCorridaPerEntrega}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                taxaCorridaPerEntrega: parseFloat(e.target.value) || 0,
                              })
                            }
                            className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-mono font-bold"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Taxa ADM Fixa (Piso Semanal R$)
                        </label>
                        <div className="relative">
                          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-400">
                            R$
                          </span>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            required
                            value={formData.pisoFixo}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                pisoFixo: parseFloat(e.target.value) || 0,
                              })
                            }
                            className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-mono font-bold"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Piso Percentual (%)
                        </label>
                        <div className="relative">
                          <input
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            required
                            value={formData.pisoPercentual}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                pisoPercentual: parseFloat(e.target.value) || 0,
                              })
                            }
                            className="w-full pl-3.5 pr-8 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-mono font-bold"
                          />
                          <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-400">
                            %
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Diárias Base */}
                    <div className="p-4 sm:p-5 bg-zinc-50/80 rounded-2xl border border-zinc-200 space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-zinc-900 uppercase tracking-wider">
                          Diárias Base dos Entregadores (por dia da semana)
                        </h4>
                        <span className="text-[11px] text-zinc-400 font-medium">
                          Repassado conforme a escala
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="bg-white p-3 rounded-xl border border-zinc-200 shadow-2xs">
                          <label className="block text-[11px] font-bold text-zinc-500 uppercase mb-1">
                            SEG-SEX
                          </label>
                          <div className="relative">
                            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[11px] text-zinc-400 font-bold">
                              R$
                            </span>
                            <input
                              type="number"
                              value={formData.diaria_weekday}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  diaria_weekday: parseFloat(e.target.value) || 0,
                                })
                              }
                              className="w-full pl-8 pr-2 py-1.5 text-xs border border-zinc-200 rounded-lg font-mono font-bold text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                            />
                          </div>
                        </div>

                        <div className="bg-white p-3 rounded-xl border border-zinc-200 shadow-2xs">
                          <label className="block text-[11px] font-bold text-zinc-500 uppercase mb-1">
                            SÁBADO
                          </label>
                          <div className="relative">
                            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[11px] text-zinc-400 font-bold">
                              R$
                            </span>
                            <input
                              type="number"
                              value={formData.diaria_saturday}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  diaria_saturday: parseFloat(e.target.value) || 0,
                                })
                              }
                              className="w-full pl-8 pr-2 py-1.5 text-xs border border-zinc-200 rounded-lg font-mono font-bold text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                            />
                          </div>
                        </div>

                        <div className="bg-white p-3 rounded-xl border border-zinc-200 shadow-2xs">
                          <label className="block text-[11px] font-bold text-zinc-500 uppercase mb-1">
                            DOMINGO
                          </label>
                          <div className="relative">
                            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[11px] text-zinc-400 font-bold">
                              R$
                            </span>
                            <input
                              type="number"
                              value={formData.diaria_sunday}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  diaria_sunday: parseFloat(e.target.value) || 0,
                                })
                              }
                              className="w-full pl-8 pr-2 py-1.5 text-xs border border-zinc-200 rounded-lg font-mono font-bold text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                            />
                          </div>
                        </div>

                        <div className="bg-white p-3 rounded-xl border border-zinc-200 shadow-2xs">
                          <label className="block text-[11px] font-bold text-zinc-500 uppercase mb-1">
                            FERIADO
                          </label>
                          <div className="relative">
                            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[11px] text-zinc-400 font-bold">
                              R$
                            </span>
                            <input
                              type="number"
                              value={formData.diaria_holiday}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  diaria_holiday: parseFloat(e.target.value) || 0,
                                })
                              }
                              className="w-full pl-8 pr-2 py-1.5 text-xs border border-zinc-200 rounded-lg font-mono font-bold text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Garantia Mínima Diária (Se selecionado modelo garantida) */}
                    {formData.reportType === "garantida" && (
                      <div className="p-4 sm:p-5 bg-amber-50/70 rounded-2xl border border-amber-200/80 space-y-3">
                        <div>
                          <label className="block text-xs font-bold text-amber-950 uppercase tracking-wider">
                            Garantia Mínima de Ganhos (Piso Diário por Dia da Semana)
                          </label>
                          <p className="text-[11px] text-amber-800 font-medium mt-0.5">
                            Se a soma (Produção + Diária) ficar abaixo deste valor, o sistema calcula o complemento automático.
                          </p>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          {["weekday", "saturday", "sunday", "holiday"].map((day) => (
                            <div key={day} className="bg-white p-2.5 rounded-xl border border-amber-300">
                              <label className="block text-[10px] font-extrabold text-amber-900 uppercase mb-1">
                                {day === "weekday"
                                  ? "SEG-SEX"
                                  : day === "saturday"
                                    ? "SÁBADO"
                                    : day === "sunday"
                                      ? "DOMINGO"
                                      : "FERIADO"}
                              </label>
                              <div className="relative">
                                <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-amber-500 font-bold">
                                  R$
                                </span>
                                <input
                                  type="number"
                                  value={garantidoDiario[day as keyof typeof garantidoDiario]}
                                  onChange={(e) =>
                                    updateGarantidoDiario(
                                      day as keyof typeof garantidoDiario,
                                      parseFloat(e.target.value) || 0
                                    )
                                  }
                                  className="w-full pl-7 pr-2 py-1.5 text-xs border border-amber-200 rounded-lg font-mono font-bold text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Taxas Administrativas & Débito */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Taxa de Supervisão (R$)
                        </label>
                        <div className="relative">
                          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-400">
                            R$
                          </span>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={formData.taxaSupervisao}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                taxaSupervisao: parseFloat(e.target.value) || 0,
                              })
                            }
                            className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-mono"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                          Débito Pendente Anterior (R$)
                        </label>
                        <div className="relative">
                          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-rose-400">
                            R$
                          </span>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={formData.debitoPendente}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                debitoPendente: parseFloat(e.target.value) || 0,
                              })
                            }
                            className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all font-mono font-bold text-rose-600"
                          />
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ========================================================================= */}
                {/* ABA 4: HORAS & TURNOS */}
                {/* ========================================================================= */}
                {activeTab === "turnos" && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15 }}
                    className="space-y-6"
                  >
                    {/* Faixas de Horas */}
                    <div className="p-4 sm:p-5 bg-zinc-50/80 rounded-2xl border border-zinc-200 space-y-4">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <h4 className="text-xs font-bold text-zinc-900 uppercase tracking-wider">
                            Garantia Mínima por Faixa de Horas Trabalhadas
                          </h4>
                          <p className="text-[11px] text-zinc-500">
                            Define o valor garantido de acordo com a jornada (ex: 0 a 4h = R$ 110, 0 a 6h = R$ 140).
                          </p>
                        </div>

                        <button
                          type="button"
                          onClick={() => {
                            const id = `faixa_${Date.now()}`;
                            setFormData((prev) => ({
                              ...prev,
                              faixasHoras: [
                                ...(prev.faixasHoras || []),
                                {
                                  id,
                                  label: "Nova Faixa",
                                  horasMinimas: 0,
                                  horasMaximas: 4,
                                  valor: 100,
                                },
                              ],
                            }));
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-100 shadow-2xs transition-all shrink-0"
                        >
                          <Plus className="h-4 w-4 text-blue-600" />
                          Adicionar Faixa
                        </button>
                      </div>

                      <div className="space-y-2.5">
                        {(formData.faixasHoras || []).filter((f) => f.id !== "garantido_diario").length === 0 ? (
                          <div className="text-xs text-zinc-400 italic p-6 text-center bg-white rounded-xl border border-dashed border-zinc-200">
                            Nenhuma faixa horária cadastrada. Clique no botão acima para adicionar.
                          </div>
                        ) : (
                          (formData.faixasHoras || [])
                            .filter((f) => f.id !== "garantido_diario")
                            .map((f) => (
                              <div
                                key={f.id}
                                className="grid grid-cols-12 gap-2.5 items-center bg-white p-3 rounded-xl border border-zinc-200 shadow-2xs"
                              >
                                <div className="col-span-4">
                                  <label className="block text-[10px] text-zinc-400 font-bold uppercase mb-0.5">
                                    Identificação
                                  </label>
                                  <input
                                    className="w-full px-2.5 py-1.5 text-xs bg-zinc-50 border border-zinc-200 rounded-lg font-medium text-zinc-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-zinc-900/10"
                                    value={f.label}
                                    placeholder="Ex: 0 a 4 horas"
                                    onChange={(e) =>
                                      setFormData((prev) => ({
                                        ...prev,
                                        faixasHoras: prev.faixasHoras.map((item) =>
                                          item.id === f.id ? { ...item, label: e.target.value } : item
                                        ),
                                      }))
                                    }
                                  />
                                </div>

                                <div className="col-span-2">
                                  <label className="block text-[10px] text-zinc-400 font-bold uppercase mb-0.5 text-center">
                                    Min (h)
                                  </label>
                                  <input
                                    type="number"
                                    min={0}
                                    step="0.5"
                                    className="w-full px-2 py-1.5 text-xs bg-zinc-50 border border-zinc-200 rounded-lg font-mono text-center font-bold text-zinc-900 focus:bg-white focus:outline-none"
                                    value={f.horasMinimas}
                                    onChange={(e) =>
                                      setFormData((prev) => ({
                                        ...prev,
                                        faixasHoras: prev.faixasHoras.map((item) =>
                                          item.id === f.id
                                            ? { ...item, horasMinimas: Number(e.target.value) || 0 }
                                            : item
                                        ),
                                      }))
                                    }
                                  />
                                </div>

                                <div className="col-span-2">
                                  <label className="block text-[10px] text-zinc-400 font-bold uppercase mb-0.5 text-center">
                                    Max (h)
                                  </label>
                                  <input
                                    type="number"
                                    min={0}
                                    step="0.5"
                                    className="w-full px-2 py-1.5 text-xs bg-zinc-50 border border-zinc-200 rounded-lg font-mono text-center font-bold text-zinc-900 focus:bg-white focus:outline-none"
                                    value={f.horasMaximas}
                                    onChange={(e) =>
                                      setFormData((prev) => ({
                                        ...prev,
                                        faixasHoras: prev.faixasHoras.map((item) =>
                                          item.id === f.id
                                            ? { ...item, horasMaximas: Number(e.target.value) || 0 }
                                            : item
                                        ),
                                      }))
                                    }
                                  />
                                </div>

                                <div className="col-span-3">
                                  <label className="block text-[10px] text-zinc-400 font-bold uppercase mb-0.5">
                                    Valor (R$)
                                  </label>
                                  <div className="relative">
                                    <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[11px] text-zinc-400 font-bold">
                                      R$
                                    </span>
                                    <input
                                      type="number"
                                      min={0}
                                      step="0.01"
                                      className="w-full pl-8 pr-2 py-1.5 text-xs bg-zinc-50 border border-zinc-200 rounded-lg font-mono text-right font-bold text-zinc-900 focus:bg-white focus:outline-none"
                                      value={f.valor}
                                      onChange={(e) =>
                                        setFormData((prev) => ({
                                          ...prev,
                                          faixasHoras: prev.faixasHoras.map((item) =>
                                            item.id === f.id ? { ...item, valor: Number(e.target.value) || 0 } : item
                                          ),
                                        }))
                                      }
                                    />
                                  </div>
                                </div>

                                <div className="col-span-1 flex items-center justify-end pt-4">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setFormData((prev) => ({
                                        ...prev,
                                        faixasHoras: prev.faixasHoras.filter((x) => x.id !== f.id),
                                      }))
                                    }
                                    className="p-1.5 rounded-lg hover:bg-rose-50 text-rose-500 hover:text-rose-700 transition-colors"
                                    title="Remover faixa"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                </div>
                              </div>
                            ))
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ========================================================================= */}
                {/* ABA 5: KM ADICIONAL */}
                {/* ========================================================================= */}
                {activeTab === "km" && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15 }}
                    className="space-y-6"
                  >
                    <div className="p-4 sm:p-5 bg-zinc-50/80 rounded-2xl border border-zinc-200 space-y-4">
                      <div>
                        <h4 className="text-xs font-bold text-zinc-900 uppercase tracking-wider">
                          Regras de Cobrança de KM Excedente
                        </h4>
                        <p className="text-[11px] text-zinc-500 mt-0.5">
                          Configure a cobrança automática quando o destino da entrega exceder a quilometragem padrão da praça.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="sm:col-span-2">
                          <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                            Modo de Cálculo
                          </label>
                          <select
                            value={formData.extraKmMode}
                            onChange={(e) =>
                              setFormData({
                                ...formData,
                                extraKmMode: e.target.value as any,
                              })
                            }
                            className="w-full px-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900 transition-all font-semibold"
                          >
                            <option value="disabled">Desativado (Sem cobrança extra por distância)</option>
                            <option value="fixed">Valor Fixo por KM Excedente</option>
                            <option value="delivery_fee">Cobrar Nova Taxa de Entrega Inteira</option>
                          </select>
                        </div>

                        {formData.extraKmMode !== "disabled" && (
                          <>
                            <div>
                              <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                                Distância Mínima de Isenção (KM)
                              </label>
                              <div className="relative">
                                <input
                                  type="number"
                                  min="0"
                                  step="0.5"
                                  value={formData.extraKmMinDistance}
                                  onChange={(e) =>
                                    setFormData({
                                      ...formData,
                                      extraKmMinDistance: parseFloat(e.target.value) || 0,
                                    })
                                  }
                                  className="w-full pl-3.5 pr-10 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl font-mono font-bold focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                                />
                                <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-400">
                                  km
                                </span>
                              </div>
                              <p className="text-[11px] text-zinc-400 mt-1">
                                Corridas até essa distância não têm acréscimo.
                              </p>
                            </div>

                            {formData.extraKmMode === "fixed" && (
                              <div>
                                <label className="block text-xs font-bold text-zinc-700 mb-1.5">
                                  Valor por KM Excedente (R$)
                                </label>
                                <div className="relative">
                                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-zinc-400">
                                    R$
                                  </span>
                                  <input
                                    type="number"
                                    min="0"
                                    step="0.10"
                                    value={formData.extraKmFixedAmount}
                                    onChange={(e) =>
                                      setFormData({
                                        ...formData,
                                        extraKmFixedAmount: parseFloat(e.target.value) || 0,
                                      })
                                    }
                                    className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white border border-zinc-200 rounded-xl font-mono font-bold focus:outline-none focus:ring-2 focus:ring-zinc-900/10 focus:border-zinc-900"
                                  />
                                </div>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </form>
            </div>
            {/* Rodapé Moderno com Navegação entre Abas e Salvar */}
            <div className="px-6 py-4 border-t border-zinc-200 bg-zinc-50/90 flex items-center justify-between gap-4 shrink-0">
              {/* Navegação entre Abas */}
              <div className="flex items-center gap-2">
                {currentTabIndex > 0 ? (
                  <button
                    type="button"
                    onClick={() => setActiveTab(TABS[currentTabIndex - 1].id)}
                    className="px-3.5 py-2 text-xs font-bold rounded-xl border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900 transition-all flex items-center gap-1.5 shadow-2xs"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Anterior
                  </button>
                ) : (
                  <div className="text-[11px] font-semibold text-zinc-400 pl-1">
                    Passo 1 de 5
                  </div>
                )}

                {currentTabIndex < TABS.length - 1 && (
                  <button
                    type="button"
                    onClick={() => setActiveTab(TABS[currentTabIndex + 1].id)}
                    className="px-3.5 py-2 text-xs font-bold rounded-xl border border-zinc-200 bg-white text-zinc-800 hover:bg-zinc-100 hover:text-zinc-900 transition-all flex items-center gap-1.5 shadow-2xs"
                  >
                    Próximo: {TABS[currentTabIndex + 1].label}
                    <ChevronRight className="h-4 w-4" />
                  </button>
                )}
              </div>

              {/* Ações Primárias */}
              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-bold rounded-xl border border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 transition-all"
                >
                  Cancelar
                </button>

                <button
                  type="submit"
                  form="empresa-form"
                  className="px-5 py-2 text-xs font-extrabold rounded-xl bg-zinc-900 hover:bg-zinc-800 text-white shadow-md shadow-zinc-900/10 transition-all flex items-center gap-2"
                >
                  <Save className="h-4 w-4" />
                  {empresa ? "Salvar Alterações" : "Cadastrar Loja"}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}
